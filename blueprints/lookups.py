"""
Lookups blueprint — settings-managed lookup tables.

Generic CRUD for four tables that the user manages from the Settings page:
  - customer_groups
  - customers          (also has email + customer_group_id + notes; archived_at instead of is_active)
  - ticket_types
  - time_categories

The non-customer tables share a uniform shape (id, name, color, sort_order,
is_active, created, updated). Customers has the same shape plus email, FK to
customer_groups, notes, and uses archived_at (datetime) as the soft-delete
mechanism instead of is_active (boolean).

Routes:

  GET   /command-deck/lookups/<kind>             -- list (active first, archived last)
  POST  /command-deck/lookups/<kind>/new         -- create; returns full row
  POST  /command-deck/lookups/<kind>/<id>        -- update fields (per-blur autosave shape)
  POST  /command-deck/lookups/<kind>/<id>/archive   -- soft-archive
  POST  /command-deck/lookups/<kind>/<id>/restore   -- un-archive
"""
from flask import Blueprint, jsonify, request

from helpers.auth import is_authenticated
from helpers.db import et_now, get_db


lookups_bp = Blueprint('lookups', __name__)


# kind → (table, archive_field, archive_value_active, archive_value_archived,
#         active_filter_sql_active, active_filter_sql_archived)
KINDS = {
	'customer_groups': {
		'table': 'customer_groups',
		'archive_field': 'is_active',
		'fields': {'name', 'color', 'sort_order', 'default_project_id'},
		'archive_active': '1',
		'archive_archived': '0',
		'active_predicate': 'is_active = 1',
		'archived_predicate': 'is_active = 0',
	},
	'ticket_types': {
		'table': 'ticket_types',
		'archive_field': 'is_active',
		'fields': {'name', 'color', 'sort_order'},
		'archive_active': '1',
		'archive_archived': '0',
		'active_predicate': 'is_active = 1',
		'archived_predicate': 'is_active = 0',
	},
	'time_categories': {
		'table': 'time_categories',
		'archive_field': 'is_active',
		'fields': {'name', 'color', 'sort_order'},
		'archive_active': '1',
		'archive_archived': '0',
		'active_predicate': 'is_active = 1',
		'archived_predicate': 'is_active = 0',
	},
	'customers': {
		'table': 'customers',
		'archive_field': 'archived_at',
		'fields': {'name', 'email', 'customer_group_id', 'notes'},
		# Note: archive_active / _archived are used for the SET clause in
		# archive/restore. For customers, "active" means archived_at = NULL.
		'archive_active': None,    # NULL when active
		'archive_archived': 'NOW', # sentinel — archive sets archived_at to et_now()
		'active_predicate': 'archived_at IS NULL',
		'archived_predicate': 'archived_at IS NOT NULL',
	},
}


def _kind_or_404(kind):
	cfg = KINDS.get(kind)
	if not cfg:
		return None
	return cfg


@lookups_bp.route('/command-deck/lookups/<kind>', methods=['GET'])
def lookups_list(kind):
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 403
	cfg = _kind_or_404(kind)
	if not cfg:
		return jsonify({'error': 'unknown_kind'}), 404

	include_archived = request.args.get('include_archived') == '1'
	conn = get_db()
	if include_archived:
		# Active first, then archived, both alphabetically (or by sort_order
		# when applicable)
		if cfg['archive_field'] == 'is_active':
			rows = conn.execute(
				f'SELECT * FROM {cfg["table"]} '
				f'ORDER BY is_active DESC, sort_order ASC, name ASC'
			).fetchall()
		else:
			rows = conn.execute(
				f'SELECT * FROM {cfg["table"]} '
				f'ORDER BY (archived_at IS NULL) DESC, name ASC'
			).fetchall()
	else:
		if cfg['archive_field'] == 'is_active':
			rows = conn.execute(
				f'SELECT * FROM {cfg["table"]} '
				f'WHERE {cfg["active_predicate"]} '
				f'ORDER BY sort_order ASC, name ASC'
			).fetchall()
		else:
			rows = conn.execute(
				f'SELECT * FROM {cfg["table"]} '
				f'WHERE {cfg["active_predicate"]} '
				f'ORDER BY name ASC'
			).fetchall()
	conn.close()
	return jsonify({'rows': [dict(r) for r in rows]})


@lookups_bp.route('/command-deck/lookups/<kind>/new', methods=['POST'])
def lookups_new(kind):
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 403
	cfg = _kind_or_404(kind)
	if not cfg:
		return jsonify({'error': 'unknown_kind'}), 404

	data = request.get_json(silent=True) or request.form
	name = (data.get('name') or '').strip()
	if not name:
		return jsonify({'error': 'name_required'}), 400

	now = et_now()
	conn = get_db()

	if kind == 'customers':
		email = (data.get('email') or '').strip() or None
		notes = (data.get('notes') or '').strip() or None
		group_id = data.get('customer_group_id')
		try:
			group_id = int(group_id) if group_id not in (None, '', 'null') else None
		except (ValueError, TypeError):
			group_id = None
		cur = conn.execute(
			'INSERT INTO customers (name, email, customer_group_id, notes, created, updated) '
			'VALUES (?, ?, ?, ?, ?, ?)',
			(name, email, group_id, notes, now, now),
		)
	else:
		color = data.get('color') or None
		# sort_order: append to the end by default
		max_sort = conn.execute(
			f'SELECT COALESCE(MAX(sort_order), -1) + 1 AS n FROM {cfg["table"]}'
		).fetchone()['n']
		cur = conn.execute(
			f'INSERT INTO {cfg["table"]} (name, color, sort_order, is_active, created, updated) '
			f'VALUES (?, ?, ?, 1, ?, ?)',
			(name, color, max_sort, now, now),
		)

	new_id = cur.lastrowid
	conn.commit()
	row = conn.execute(f'SELECT * FROM {cfg["table"]} WHERE id = ?', (new_id,)).fetchone()
	conn.close()
	return jsonify({'success': True, 'row': dict(row)})


@lookups_bp.route('/command-deck/lookups/<kind>/<int:row_id>', methods=['POST'])
def lookups_update(kind, row_id):
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 403
	cfg = _kind_or_404(kind)
	if not cfg:
		return jsonify({'error': 'unknown_kind'}), 404

	data = request.get_json(silent=True) or request.form
	updates = {}

	for field in cfg['fields']:
		if field not in data:
			continue
		val = data.get(field)
		if field == 'name':
			s = (val or '').strip()
			if not s:
				return jsonify({'error': 'name_required'}), 400
			updates[field] = s
		elif field in ('color', 'email', 'notes'):
			s = (val or '').strip()
			updates[field] = s or None
		elif field == 'sort_order':
			try:
				updates[field] = int(val)
			except (ValueError, TypeError):
				return jsonify({'error': f'invalid_{field}'}), 400
		elif field == 'customer_group_id':
			if val in (None, '', 'null'):
				updates[field] = None
			else:
				try:
					updates[field] = int(val)
				except (ValueError, TypeError):
					return jsonify({'error': 'invalid_customer_group_id'}), 400
		elif field == 'default_project_id':
			if val in (None, '', 'null'):
				updates[field] = None
			else:
				try:
					updates[field] = int(val)
				except (ValueError, TypeError):
					return jsonify({'error': 'invalid_default_project_id'}), 400

	if not updates:
		return jsonify({'error': 'no_fields'}), 400

	updates['updated'] = et_now()
	set_sql = ', '.join(f'{k} = ?' for k in updates)
	conn = get_db()
	row = conn.execute(f'SELECT id FROM {cfg["table"]} WHERE id = ?', (row_id,)).fetchone()
	if not row:
		conn.close()
		return jsonify({'error': 'not_found'}), 404
	conn.execute(
		f'UPDATE {cfg["table"]} SET {set_sql} WHERE id = ?',
		list(updates.values()) + [row_id],
	)
	conn.commit()
	row = conn.execute(f'SELECT * FROM {cfg["table"]} WHERE id = ?', (row_id,)).fetchone()
	conn.close()
	return jsonify({'success': True, 'row': dict(row)})


def _set_archive_state(kind, row_id, archive):
	cfg = _kind_or_404(kind)
	if not cfg:
		return None, jsonify({'error': 'unknown_kind'}), 404

	now = et_now()
	conn = get_db()
	row = conn.execute(f'SELECT id FROM {cfg["table"]} WHERE id = ?', (row_id,)).fetchone()
	if not row:
		conn.close()
		return None, jsonify({'error': 'not_found'}), 404

	if cfg['archive_field'] == 'is_active':
		new_val = 0 if archive else 1
		conn.execute(
			f'UPDATE {cfg["table"]} SET is_active = ?, updated = ? WHERE id = ?',
			(new_val, now, row_id),
		)
	else:  # archived_at on customers
		new_val = now if archive else None
		conn.execute(
			f'UPDATE {cfg["table"]} SET archived_at = ?, updated = ? WHERE id = ?',
			(new_val, now, row_id),
		)
	conn.commit()
	row = conn.execute(f'SELECT * FROM {cfg["table"]} WHERE id = ?', (row_id,)).fetchone()
	conn.close()
	return row, None, None


@lookups_bp.route('/command-deck/lookups/<kind>/<int:row_id>/archive', methods=['POST'])
def lookups_archive(kind, row_id):
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 403
	row, err, code = _set_archive_state(kind, row_id, archive=True)
	if err:
		return err, code
	return jsonify({'success': True, 'row': dict(row)})


@lookups_bp.route('/command-deck/lookups/<kind>/<int:row_id>/restore', methods=['POST'])
def lookups_restore(kind, row_id):
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 403
	row, err, code = _set_archive_state(kind, row_id, archive=False)
	if err:
		return err, code
	return jsonify({'success': True, 'row': dict(row)})
