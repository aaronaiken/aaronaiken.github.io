"""
Settings blueprint — Phase 3 of the time-tracking spec.

Routes:

  GET   /command-deck/settings/         -- settings page
  POST  /command-deck/settings/update   -- per-field patch

Editable fields (all in the singleton `settings` row, id = 1):

  - reimbursement_rate_cents     -- IRS-style $/mi (form shows as 0.67)
  - vehicle_a_label              -- "Honda Pilot", "Subaru", etc.
  - vehicle_b_label
  - default_vehicle              -- 'a' or 'b'
  - default_mileage_project_id   -- which project the mileage form pre-selects
  - idle_threshold_minutes       -- Phase 4 will read this; column ships in Phase 1

The settings row is auto-created if missing. Phase 1's migrate_to_sqlite.py
already inserts a row at id=1, but defensive code here means a fresh DB or
hand-edited DB still works.
"""
from flask import Blueprint, jsonify, render_template, request

from helpers.auth import cd_auth_required, is_authenticated
from helpers.db import et_now, get_db


settings_bp = Blueprint('settings', __name__)


def _ensure_settings_row(conn):
	"""Insert the singleton settings row if missing. Returns the row."""
	row = conn.execute('SELECT * FROM settings WHERE id = 1').fetchone()
	if row:
		return row
	now = et_now()
	conn.execute('''
		INSERT INTO settings (id, idle_threshold_minutes, reimbursement_rate_cents,
		                      vehicle_a_label, vehicle_b_label, default_vehicle,
		                      created, updated)
		VALUES (1, 15, 67, 'Vehicle A', 'Vehicle B', 'a', ?, ?)
	''', (now, now))
	conn.commit()
	return conn.execute('SELECT * FROM settings WHERE id = 1').fetchone()


@settings_bp.route('/command-deck/settings/', methods=['GET'])
@settings_bp.route('/command-deck/settings', methods=['GET'])
@cd_auth_required
def settings_page():
	conn = get_db()
	settings_row = _ensure_settings_row(conn)
	projects = conn.execute('''
		SELECT id, title, slug
		FROM projects
		WHERE project_type IN ('work_subproject', 'personal')
		  AND is_private = 0
		ORDER BY title ASC
	''').fetchall()
	conn.close()
	return render_template(
		'command_deck_settings.html',
		settings=dict(settings_row),
		projects=[dict(p) for p in projects],
	)


@settings_bp.route('/command-deck/settings/update', methods=['POST'])
def settings_update():
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 403

	data = request.get_json(silent=True) or request.form
	conn = get_db()
	_ensure_settings_row(conn)

	updates = {}

	if 'reimbursement_rate_cents' in data:
		try:
			val = int(data.get('reimbursement_rate_cents'))
		except (ValueError, TypeError):
			conn.close()
			return jsonify({'error': 'invalid_rate'}), 400
		if val < 0 or val > 1000:
			conn.close()
			return jsonify({'error': 'invalid_rate'}), 400
		updates['reimbursement_rate_cents'] = val

	if 'vehicle_a_label' in data:
		v = (data.get('vehicle_a_label') or '').strip()
		if not v:
			conn.close()
			return jsonify({'error': 'invalid_vehicle_a_label'}), 400
		updates['vehicle_a_label'] = v

	if 'vehicle_b_label' in data:
		v = (data.get('vehicle_b_label') or '').strip()
		if not v:
			conn.close()
			return jsonify({'error': 'invalid_vehicle_b_label'}), 400
		updates['vehicle_b_label'] = v

	if 'default_vehicle' in data:
		v = (data.get('default_vehicle') or '').strip().lower()
		if v not in ('a', 'b'):
			conn.close()
			return jsonify({'error': 'invalid_default_vehicle'}), 400
		updates['default_vehicle'] = v

	if 'default_mileage_project_id' in data:
		val = data.get('default_mileage_project_id')
		if val in (None, '', 'null'):
			updates['default_mileage_project_id'] = None
		else:
			try:
				updates['default_mileage_project_id'] = int(val)
			except (ValueError, TypeError):
				conn.close()
				return jsonify({'error': 'invalid_default_mileage_project'}), 400

	if 'idle_threshold_minutes' in data:
		try:
			val = int(data.get('idle_threshold_minutes'))
		except (ValueError, TypeError):
			conn.close()
			return jsonify({'error': 'invalid_idle_threshold'}), 400
		if val < 1 or val > 480:
			conn.close()
			return jsonify({'error': 'invalid_idle_threshold'}), 400
		updates['idle_threshold_minutes'] = val

	if not updates:
		conn.close()
		return jsonify({'error': 'no_fields'}), 400

	updates['updated'] = et_now()
	set_sql = ', '.join(f'{k} = ?' for k in updates)
	conn.execute(
		f'UPDATE settings SET {set_sql} WHERE id = 1',
		list(updates.values()),
	)
	conn.commit()
	row = conn.execute('SELECT * FROM settings WHERE id = 1').fetchone()
	conn.close()
	return jsonify({'success': True, 'settings': dict(row)})
