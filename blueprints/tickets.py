"""
Tickets blueprint — support-ticket queue.

Routes:

  GET   /command-deck/tickets/                   -- index page
  GET   /command-deck/tickets/data               -- JSON for index (filterable)
  GET   /command-deck/tickets/new                -- new form page
  POST  /command-deck/tickets/new                -- create + redirect
  GET   /command-deck/tickets/<id>/              -- detail page
  POST  /command-deck/tickets/<id>/update        -- per-field PATCH
  POST  /command-deck/tickets/<id>/status        -- transition status
  POST  /command-deck/tickets/<id>/close         -- close (resolution required)
  POST  /command-deck/tickets/<id>/reopen        -- reopen (clears resolution + closed_date)
  POST  /command-deck/tickets/<id>/delete        -- hard delete

Status flow: open → pending → in_progress → closed. Reopening allowed.
Closing requires resolution text (server-enforced). Reopening clears
resolution + closed_date.

Ticket numbers: TKT-NNNN, zero-padded to 4 digits, derived from the row's
own id post-insert. A temporary unique placeholder is used during INSERT
(the ticket_number column is NOT NULL UNIQUE; we can't insert NULL). We
then UPDATE to the canonical TKT-NNNN value.
"""
import uuid

from flask import (
	Blueprint, jsonify, redirect, render_template, request, url_for,
)

from helpers.auth import cd_auth_required, is_authenticated
from helpers.db import et_now, get_db


tickets_bp = Blueprint('tickets', __name__)


VALID_STATUSES = ('open', 'pending', 'in_progress', 'closed')
VALID_PRIORITIES = ('normal', 'urgent')


# ---- Helpers ----


def _to_int(v, default=None):
	if v in (None, '', 'null'):
		return default
	try:
		return int(v)
	except (ValueError, TypeError):
		return default


def _serialize_ticket(row):
	return dict(row)


def _ticket_with_joins(conn, ticket_id):
	"""Fetch a ticket row with all FK display fields joined."""
	return conn.execute('''
		SELECT t.*,
		       p.title           AS project_title,
		       p.slug            AS project_slug,
		       p.is_private      AS project_is_private,
		       cg.name           AS customer_group_name,
		       cg.color          AS customer_group_color,
		       c.name            AS customer_name,
		       c.email           AS customer_email,
		       c.archived_at     AS customer_archived_at,
		       tt.name           AS type_name,
		       tt.color          AS type_color,
		       tt.is_active      AS type_is_active,
		       tc.name           AS time_category_name,
		       tc.color          AS time_category_color
		FROM tickets t
		LEFT JOIN projects p             ON t.project_id = p.id
		LEFT JOIN customer_groups cg     ON t.customer_group_id = cg.id
		LEFT JOIN customers c            ON t.customer_id = c.id
		LEFT JOIN ticket_types tt        ON t.type_id = tt.id
		LEFT JOIN time_categories tc     ON t.time_category_id = tc.id
		WHERE t.id = ?
	''', (ticket_id,)).fetchone()


# ---- Index ----


@tickets_bp.route('/command-deck/tickets/', methods=['GET'])
@tickets_bp.route('/command-deck/tickets', methods=['GET'])
@cd_auth_required
def tickets_index():
	conn = get_db()
	# Lookups for filter pills + ticket form
	customer_groups = conn.execute(
		'SELECT id, name, color, default_project_id FROM customer_groups WHERE is_active = 1 '
		'ORDER BY sort_order ASC, name ASC'
	).fetchall()
	ticket_types = conn.execute(
		'SELECT id, name, color FROM ticket_types WHERE is_active = 1 '
		'ORDER BY sort_order ASC, name ASC'
	).fetchall()
	time_categories = conn.execute(
		'SELECT id, name, color FROM time_categories WHERE is_active = 1 '
		'ORDER BY sort_order ASC, name ASC'
	).fetchall()
	customers = conn.execute(
		'SELECT id, name, customer_group_id FROM customers '
		'WHERE archived_at IS NULL ORDER BY name ASC'
	).fetchall()
	projects = conn.execute('''
		SELECT id, title, slug
		FROM projects
		WHERE project_type IN ('work_subproject', 'personal')
		  AND is_private = 0
		  AND archived_at IS NULL
		ORDER BY title ASC
	''').fetchall()
	conn.close()
	return render_template(
		'command_deck_tickets.html',
		customer_groups=[dict(r) for r in customer_groups],
		ticket_types=[dict(r) for r in ticket_types],
		time_categories=[dict(r) for r in time_categories],
		customers=[dict(r) for r in customers],
		projects=[dict(r) for r in projects],
	)


@tickets_bp.route('/command-deck/tickets/data', methods=['GET'])
def tickets_data():
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 403

	args = request.args
	clauses = []
	params = []

	status = args.get('status')
	if status == 'open':
		clauses.append("t.status != 'closed'")  # convenience: "open" filter = anything not closed
	elif status in ('pending', 'in_progress', 'closed'):
		clauses.append('t.status = ?')
		params.append(status)
	elif status == 'open_only':
		clauses.append("t.status = 'open'")

	type_id = _to_int(args.get('type'))
	if type_id:
		clauses.append('t.type_id = ?')
		params.append(type_id)

	group_id = _to_int(args.get('customer_group'))
	if group_id:
		clauses.append('t.customer_group_id = ?')
		params.append(group_id)

	customer_id = _to_int(args.get('customer'))
	if customer_id:
		clauses.append('t.customer_id = ?')
		params.append(customer_id)

	project_id = _to_int(args.get('project'))
	if project_id:
		clauses.append('t.project_id = ?')
		params.append(project_id)

	include_private = args.get('include_private') == '1'
	if not include_private:
		clauses.append('(p.is_private IS NULL OR p.is_private = 0)')

	where_sql = ('WHERE ' + ' AND '.join(clauses)) if clauses else ''

	conn = get_db()
	rows = conn.execute(f'''
		SELECT t.*,
		       p.title           AS project_title,
		       p.slug            AS project_slug,
		       p.is_private      AS project_is_private,
		       cg.name           AS customer_group_name,
		       cg.color          AS customer_group_color,
		       c.name            AS customer_name,
		       c.archived_at     AS customer_archived_at,
		       tt.name           AS type_name,
		       tt.color          AS type_color
		FROM tickets t
		LEFT JOIN projects p             ON t.project_id = p.id
		LEFT JOIN customer_groups cg     ON t.customer_group_id = cg.id
		LEFT JOIN customers c            ON t.customer_id = c.id
		LEFT JOIN ticket_types tt        ON t.type_id = tt.id
		{where_sql}
		ORDER BY (t.status = 'closed') ASC, t.priority = 'urgent' DESC,
		         t.updated DESC, t.id DESC
	''', params).fetchall()

	# Summary counts (always over the filtered set)
	open_count = sum(1 for r in rows if r['status'] == 'open')
	pending_count = sum(1 for r in rows if r['status'] == 'pending')
	in_progress_count = sum(1 for r in rows if r['status'] == 'in_progress')
	closed_count = sum(1 for r in rows if r['status'] == 'closed')
	urgent_count = sum(1 for r in rows
	                   if r['priority'] == 'urgent' and r['status'] != 'closed')

	conn.close()
	return jsonify({
		'tickets': [_serialize_ticket(r) for r in rows],
		'summary': {
			'total': len(rows),
			'open': open_count,
			'pending': pending_count,
			'in_progress': in_progress_count,
			'closed': closed_count,
			'urgent': urgent_count,
		},
	})


# ---- Detail ----


@tickets_bp.route('/command-deck/tickets/<int:ticket_id>/', methods=['GET'])
@tickets_bp.route('/command-deck/tickets/<int:ticket_id>', methods=['GET'])
@cd_auth_required
def ticket_detail(ticket_id):
	conn = get_db()
	ticket = _ticket_with_joins(conn, ticket_id)
	if not ticket:
		conn.close()
		return "Ticket not found", 404

	# Recent time entries on this ticket — used by the detail page's // Time spent strip
	time_entries = conn.execute('''
		SELECT te.*,
		       tc.name AS time_category_name,
		       tc.color AS time_category_color
		FROM time_entries te
		LEFT JOIN time_categories tc ON te.time_category_id = tc.id
		WHERE te.ticket_id = ?
		ORDER BY te.started_at DESC
		LIMIT 25
	''', (ticket_id,)).fetchall()

	# Lifetime + today on this ticket
	lifetime_seconds = conn.execute(
		'SELECT COALESCE(SUM(duration_seconds), 0) AS s '
		'FROM time_entries WHERE ticket_id = ? AND duration_seconds IS NOT NULL',
		(ticket_id,)
	).fetchone()['s']

	# Lookups for inline edits
	customer_groups = conn.execute(
		'SELECT id, name, color FROM customer_groups WHERE is_active = 1 '
		'ORDER BY sort_order ASC, name ASC'
	).fetchall()
	ticket_types = conn.execute(
		'SELECT id, name, color FROM ticket_types WHERE is_active = 1 '
		'ORDER BY sort_order ASC, name ASC'
	).fetchall()
	customers = conn.execute(
		'SELECT id, name, customer_group_id FROM customers '
		'WHERE archived_at IS NULL ORDER BY name ASC'
	).fetchall()
	projects = conn.execute('''
		SELECT id, title, slug
		FROM projects
		WHERE project_type IN ('work_subproject', 'personal')
		  AND is_private = 0
		  AND archived_at IS NULL
		ORDER BY title ASC
	''').fetchall()
	time_categories = conn.execute(
		'SELECT id, name, color FROM time_categories WHERE is_active = 1 '
		'ORDER BY sort_order ASC, name ASC'
	).fetchall()

	conn.close()
	return render_template(
		'command_deck_ticket.html',
		ticket=dict(ticket),
		time_entries=[dict(r) for r in time_entries],
		lifetime_seconds=int(lifetime_seconds or 0),
		customer_groups=[dict(r) for r in customer_groups],
		ticket_types=[dict(r) for r in ticket_types],
		customers=[dict(r) for r in customers],
		projects=[dict(r) for r in projects],
		time_categories=[dict(r) for r in time_categories],
	)


# ---- New form (GET + POST) ----


@tickets_bp.route('/command-deck/tickets/new', methods=['GET'])
@cd_auth_required
def ticket_new_form():
	"""The dedicated new-ticket page is gone — modal lives on the index now.
	Old bookmarks + cross-page links land here and get redirected to the index
	with ?new=1 (plus any ?project_id passthrough), which auto-opens the modal."""
	qs = {'new': '1'}
	pid = request.args.get('project_id')
	if pid:
		qs['project_id'] = pid
	from urllib.parse import urlencode
	return redirect(url_for('tickets.tickets_index') + '?' + urlencode(qs))


@tickets_bp.route('/command-deck/tickets/new', methods=['POST'])
def ticket_new():
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 403

	data = request.form
	title = (data.get('title') or '').strip()
	if not title:
		return jsonify({'error': 'title_required'}), 400

	priority = (data.get('priority') or 'normal').strip().lower()
	if priority not in VALID_PRIORITIES:
		priority = 'normal'

	status = (data.get('status') or 'open').strip().lower()
	if status not in VALID_STATUSES:
		status = 'open'
	if status == 'closed':
		# Don't let a brand-new ticket land closed without resolution; force open
		status = 'open'

	project_id = _to_int(data.get('project_id'))
	customer_group_id = _to_int(data.get('customer_group_id'))
	customer_id = _to_int(data.get('customer_id'))
	type_id = _to_int(data.get('type_id'))
	time_category_id = _to_int(data.get('time_category_id'))
	description = (data.get('description') or '').strip() or None

	conn = get_db()

	# If customer is set but customer_group isn't, infer from the customer
	if customer_id and not customer_group_id:
		row = conn.execute(
			'SELECT customer_group_id FROM customers WHERE id = ?',
			(customer_id,)
		).fetchone()
		if row and row['customer_group_id']:
			customer_group_id = row['customer_group_id']

	now = et_now()

	# Two-step ticket_number: insert with a unique placeholder, then UPDATE
	# with the canonical TKT-NNNN derived from the row's id. SQLite serializes
	# writes so this is race-free at our scale.
	placeholder = f'TMP-{uuid.uuid4().hex[:8]}'
	cur = conn.execute('''
		INSERT INTO tickets
			(ticket_number, project_id, customer_group_id, customer_id, type_id,
			 time_category_id, title, description, priority, status, created, updated)
		VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
	''', (placeholder, project_id, customer_group_id, customer_id, type_id,
	      time_category_id, title, description, priority, status, now, now))
	new_id = cur.lastrowid
	ticket_number = f'TKT-{new_id:04d}'
	conn.execute(
		'UPDATE tickets SET ticket_number = ? WHERE id = ?',
		(ticket_number, new_id),
	)
	conn.commit()
	conn.close()

	# Browser POSTs redirect to the detail page; XHR consumers can pass
	# `return=json` to get the JSON shape instead.
	if data.get('return') == 'json':
		conn2 = get_db()
		row = _ticket_with_joins(conn2, new_id)
		conn2.close()
		return jsonify({'success': True, 'ticket': _serialize_ticket(row)})
	return redirect(url_for('tickets.ticket_detail', ticket_id=new_id))


# ---- Update (per-field PATCH) ----


@tickets_bp.route('/command-deck/tickets/<int:ticket_id>/update', methods=['POST'])
def ticket_update(ticket_id):
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 403
	data = request.get_json(silent=True) or request.form

	conn = get_db()
	row = conn.execute('SELECT * FROM tickets WHERE id = ?', (ticket_id,)).fetchone()
	if not row:
		conn.close()
		return jsonify({'error': 'not_found'}), 404

	updates = {}

	if 'title' in data:
		v = (data.get('title') or '').strip()
		if not v:
			conn.close()
			return jsonify({'error': 'title_required'}), 400
		updates['title'] = v

	if 'description' in data:
		v = (data.get('description') or '').strip()
		updates['description'] = v or None

	if 'priority' in data:
		v = (data.get('priority') or '').strip().lower()
		if v not in VALID_PRIORITIES:
			conn.close()
			return jsonify({'error': 'invalid_priority'}), 400
		updates['priority'] = v

	if 'project_id' in data:
		updates['project_id'] = _to_int(data.get('project_id'))

	if 'customer_group_id' in data:
		updates['customer_group_id'] = _to_int(data.get('customer_group_id'))

	if 'customer_id' in data:
		updates['customer_id'] = _to_int(data.get('customer_id'))
		# When customer changes, re-infer customer_group only if it wasn't
		# also passed in this same update (explicit takes precedence).
		if 'customer_group_id' not in data and updates['customer_id']:
			cg = conn.execute(
				'SELECT customer_group_id FROM customers WHERE id = ?',
				(updates['customer_id'],)
			).fetchone()
			if cg and cg['customer_group_id']:
				updates['customer_group_id'] = cg['customer_group_id']

	if 'type_id' in data:
		updates['type_id'] = _to_int(data.get('type_id'))

	if 'time_category_id' in data:
		updates['time_category_id'] = _to_int(data.get('time_category_id'))

	if not updates:
		conn.close()
		return jsonify({'error': 'no_fields'}), 400

	updates['updated'] = et_now()
	set_sql = ', '.join(f'{k} = ?' for k in updates)
	conn.execute(
		f'UPDATE tickets SET {set_sql} WHERE id = ?',
		list(updates.values()) + [ticket_id],
	)
	conn.commit()
	row = _ticket_with_joins(conn, ticket_id)
	conn.close()
	return jsonify({'success': True, 'ticket': _serialize_ticket(row)})


# ---- Status transition ----


@tickets_bp.route('/command-deck/tickets/<int:ticket_id>/status', methods=['POST'])
def ticket_status(ticket_id):
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 403
	data = request.get_json(silent=True) or request.form
	target = (data.get('status') or '').strip().lower()
	if target not in VALID_STATUSES:
		return jsonify({'error': 'invalid_status'}), 400

	# Closing requires resolution — must use /close. Block here so the UI
	# can't accidentally bypass.
	if target == 'closed':
		return jsonify({
			'error': 'use_close_endpoint',
			'detail': 'POST /close with a resolution to close a ticket.',
		}), 400

	conn = get_db()
	row = conn.execute('SELECT * FROM tickets WHERE id = ?', (ticket_id,)).fetchone()
	if not row:
		conn.close()
		return jsonify({'error': 'not_found'}), 404

	now = et_now()
	# If transitioning AWAY from closed (i.e. reopening), clear closed_date
	# + resolution implicitly. Mirrors what /reopen does, but lets UI flip
	# the status in one click without requiring confirm.
	if row['status'] == 'closed' and target != 'closed':
		conn.execute(
			'UPDATE tickets SET status = ?, closed_date = NULL, resolution = NULL, '
			'updated = ? WHERE id = ?',
			(target, now, ticket_id),
		)
	else:
		conn.execute(
			'UPDATE tickets SET status = ?, updated = ? WHERE id = ?',
			(target, now, ticket_id),
		)
	conn.commit()
	row = _ticket_with_joins(conn, ticket_id)
	conn.close()
	return jsonify({'success': True, 'ticket': _serialize_ticket(row)})


# ---- Close (with resolution) ----


@tickets_bp.route('/command-deck/tickets/<int:ticket_id>/close', methods=['POST'])
def ticket_close(ticket_id):
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 403
	data = request.get_json(silent=True) or request.form
	resolution = (data.get('resolution') or '').strip()
	if not resolution:
		return jsonify({'error': 'resolution_required'}), 400

	conn = get_db()
	row = conn.execute('SELECT * FROM tickets WHERE id = ?', (ticket_id,)).fetchone()
	if not row:
		conn.close()
		return jsonify({'error': 'not_found'}), 404

	now = et_now()
	conn.execute(
		"UPDATE tickets SET status = 'closed', resolution = ?, "
		"closed_date = ?, updated = ? WHERE id = ?",
		(resolution, now, now, ticket_id),
	)
	conn.commit()
	row = _ticket_with_joins(conn, ticket_id)
	conn.close()
	return jsonify({'success': True, 'ticket': _serialize_ticket(row)})


# ---- Reopen ----


@tickets_bp.route('/command-deck/tickets/<int:ticket_id>/reopen', methods=['POST'])
def ticket_reopen(ticket_id):
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 403
	conn = get_db()
	row = conn.execute('SELECT id FROM tickets WHERE id = ?', (ticket_id,)).fetchone()
	if not row:
		conn.close()
		return jsonify({'error': 'not_found'}), 404
	now = et_now()
	conn.execute(
		"UPDATE tickets SET status = 'open', closed_date = NULL, "
		"resolution = NULL, updated = ? WHERE id = ?",
		(now, ticket_id),
	)
	conn.commit()
	row = _ticket_with_joins(conn, ticket_id)
	conn.close()
	return jsonify({'success': True, 'ticket': _serialize_ticket(row)})


# ---- Delete ----


@tickets_bp.route('/command-deck/tickets/<int:ticket_id>/delete', methods=['POST'])
def ticket_delete(ticket_id):
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 403
	conn = get_db()
	row = conn.execute('SELECT id FROM tickets WHERE id = ?', (ticket_id,)).fetchone()
	if not row:
		conn.close()
		return jsonify({'error': 'not_found'}), 404
	# Cascade SET NULL on time_entries.ticket_id is declared on the FK; do it
	# explicitly here so we don't depend on PRAGMA foreign_keys=ON being set
	# upstream (matches the meetings + mileage convention).
	conn.execute('UPDATE time_entries SET ticket_id = NULL WHERE ticket_id = ?', (ticket_id,))
	conn.execute('DELETE FROM tickets WHERE id = ?', (ticket_id,))
	conn.commit()
	conn.close()
	return jsonify({'success': True, 'deleted_id': ticket_id})
