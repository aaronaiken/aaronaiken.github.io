"""
Meetings blueprint — Phase 5 of the Command Deck spec.

Routes (all under /command-deck/meetings/*, all PIN-gated when the linked
project is private — privacy inherits from the project per spec §1 #10):

  GET   /command-deck/meetings/                  -- index page (chronological)
  GET   /command-deck/meetings/<id>/             -- detail page
  POST  /command-deck/meetings/new               -- create
  POST  /command-deck/meetings/<id>/update       -- per-field patch
  POST  /command-deck/meetings/<id>/delete       -- hard delete (cascades NULL)
  POST  /command-deck/meetings/<id>/complete     -- mark complete + spawn next on recurrence
  POST  /command-deck/meetings/<id>/action-items/add  -- creates a tasks row

Cascade rules are baked into the schema (migrate_add_meetings.py):
  - project delete  → meetings.project_id          = NULL
  - meeting delete  → tasks.meeting_id             = NULL
  - meeting delete  → time_entries.meeting_id      = NULL
  - meeting delete  → meetings.recurrence_anchor_id = NULL (chain unlinks)

Notes are markdown source; rendering happens client-side via marked.js
(same pipeline as note blocks).
"""
import calendar
import datetime as _dt

from flask import (
	Blueprint, jsonify, redirect, render_template, request, url_for,
)

from helpers.auth import cd_auth_required, is_authenticated
from helpers.db import et_now, get_db


meetings_bp = Blueprint('meetings', __name__)


VALID_STATUSES = ('scheduled', 'complete', 'canceled', 'no_show')
VALID_RECURRENCES = ('weekly', 'biweekly', 'monthly')


# ---- Helpers ----


def _serialize_meeting(row, action_count=None):
	d = dict(row)
	if action_count is not None:
		d['action_count'] = action_count
	return d


def _parse_meeting_date(val):
	"""Validate an ET-local datetime string. Accepts:
	- ISO 8601 with offset (what et_now() emits) — used as-is
	- 'YYYY-MM-DDTHH:MM' from a <input type="datetime-local"> — localized to ET via et_now's tz
	- empty / None → falls back to et_now()
	"""
	if not val:
		return et_now()
	val = val.strip()
	if not val:
		return et_now()
	try:
		_dt.datetime.fromisoformat(val)
		return val
	except (ValueError, TypeError):
		return None


def _shift_iso_for_recurrence(iso_str, recurrence):
	"""Advance an ISO 8601 datetime forward by one recurrence interval.

	Preserves the original offset/format by parsing → adding → isoformat-ing.
	For monthly, clamps to the last valid day of the target month (Jan 31 →
	Feb 28/29, not March 3).
	"""
	dt = _dt.datetime.fromisoformat(iso_str)
	if recurrence == 'weekly':
		return (dt + _dt.timedelta(days=7)).isoformat()
	if recurrence == 'biweekly':
		return (dt + _dt.timedelta(days=14)).isoformat()
	if recurrence == 'monthly':
		year = dt.year + (dt.month // 12)
		month = (dt.month % 12) + 1
		last_day = calendar.monthrange(year, month)[1]
		return dt.replace(year=year, month=month, day=min(dt.day, last_day)).isoformat()
	return iso_str


def _spawn_next_in_series(conn, meeting):
	"""Given a recurring meeting row that was just completed, create the next
	instance in the series. Caller is responsible for the commit.

	Returns the new meeting id, or None if the next instance already exists
	(idempotent — repeat complete calls don't double-spawn).
	"""
	if not meeting['recurrence']:
		return None
	anchor_id = meeting['recurrence_anchor_id'] or meeting['id']
	next_date = _shift_iso_for_recurrence(meeting['meeting_date'], meeting['recurrence'])
	# Idempotency: if a later meeting in this anchor chain already exists at
	# or beyond next_date, don't spawn another one. Compare on exact ISO match
	# first (the common "already spawned" case), then on any future date in
	# the chain (covers manual edits to dates).
	existing = conn.execute('''
		SELECT id FROM meetings
		WHERE (recurrence_anchor_id = ? OR id = ?)
		  AND id != ?
		  AND meeting_date >= ?
		ORDER BY meeting_date ASC
		LIMIT 1
	''', (anchor_id, anchor_id, meeting['id'], next_date)).fetchone()
	if existing:
		return None
	now = et_now()
	cur = conn.execute('''
		INSERT INTO meetings
			(project_id, title, meeting_date, notes, status, recurrence,
			 recurrence_anchor_id, time_category_id, created, updated)
		VALUES (?, ?, ?, ?, 'scheduled', ?, ?, ?, ?, ?)
	''', (
		meeting['project_id'],
		meeting['title'],
		next_date,
		None,  # fresh notes for the new instance — old notes stay on the completed one
		meeting['recurrence'],
		anchor_id,
		meeting['time_category_id'],
		now,
		now,
	))
	return cur.lastrowid


# ---- Index page ----


@meetings_bp.route('/command-deck/meetings/', methods=['GET'])
@meetings_bp.route('/command-deck/meetings', methods=['GET'])
@cd_auth_required
def meetings_index():
	conn = get_db()
	project_filter = request.args.get('project')
	args = []
	where = ''
	if project_filter:
		project_row = conn.execute(
			'SELECT id, title, slug FROM projects WHERE slug = ?', (project_filter,)
		).fetchone()
		if project_row:
			where = 'WHERE m.project_id = ?'
			args.append(project_row['id'])
			project_filter_obj = dict(project_row)
		else:
			project_filter_obj = None
	else:
		project_filter_obj = None

	rows = conn.execute(f'''
		SELECT m.*,
		       p.title AS project_title,
		       p.slug  AS project_slug,
		       p.is_private AS project_is_private,
		       tc.name  AS time_category_name,
		       tc.color AS time_category_color,
		       (SELECT COUNT(*) FROM tasks WHERE meeting_id = m.id) AS action_count
		FROM meetings m
		LEFT JOIN projects p          ON m.project_id      = p.id
		LEFT JOIN time_categories tc  ON m.time_category_id = tc.id
		{where}
		ORDER BY m.meeting_date DESC, m.id DESC
	''', args).fetchall()

	# Drop private-project meetings unless the user has unlocked. The lock is
	# advisory (over-the-shoulder); auth guarantees it's Aaron, the lock just
	# hides them from passers-by. Mirror the dashboard convention: if the
	# unlock cookie/localStorage is set, the client passes ?include_private=1.
	include_private = request.args.get('include_private') == '1'
	if not include_private:
		rows = [r for r in rows if not (r['project_is_private'] or 0)]

	conn.close()
	return render_template(
		'command_deck_meetings.html',
		meetings=[dict(r) for r in rows],
		project_filter=project_filter_obj,
		include_private=include_private,
	)


# ---- Detail page ----


@meetings_bp.route('/command-deck/meetings/<int:meeting_id>/', methods=['GET'])
@meetings_bp.route('/command-deck/meetings/<int:meeting_id>', methods=['GET'])
@cd_auth_required
def meeting_detail(meeting_id):
	conn = get_db()
	meeting = conn.execute('''
		SELECT m.*,
		       p.title AS project_title,
		       p.slug  AS project_slug,
		       p.tracking_enabled AS project_tracking_enabled,
		       p.is_private AS project_is_private,
		       tc.name  AS time_category_name,
		       tc.color AS time_category_color
		FROM meetings m
		LEFT JOIN projects p          ON m.project_id      = p.id
		LEFT JOIN time_categories tc  ON m.time_category_id = tc.id
		WHERE m.id = ?
	''', (meeting_id,)).fetchone()
	if not meeting:
		conn.close()
		return "Meeting not found", 404

	# Active time categories for the dropdown — same source the timer surfaces
	# use. Archived categories aren't selectable for a new default.
	time_categories = conn.execute('''
		SELECT id, name, color FROM time_categories
		WHERE is_active = 1
		ORDER BY sort_order ASC, name ASC
	''').fetchall()

	action_items = conn.execute('''
		SELECT * FROM tasks
		WHERE meeting_id = ? AND status = 'open'
		ORDER BY "order" ASC, id ASC
	''', (meeting_id,)).fetchall()

	# Lifetime time tracked on this meeting — sum of all duration_seconds where
	# meeting_id = ?. Mirrors the per-task lifetime tag pattern from cd_project.
	lifetime_row = conn.execute('''
		SELECT COALESCE(SUM(duration_seconds), 0) AS secs
		FROM time_entries
		WHERE meeting_id = ? AND duration_seconds IS NOT NULL
	''', (meeting_id,)).fetchone()
	lifetime_seconds = int(lifetime_row['secs'] or 0)

	# Project picker for the reassign dropdown (work sub-projects + personals)
	projects = conn.execute('''
		SELECT id, title, slug, project_type, parent_project_id, is_private
		FROM projects
		WHERE project_type IN ('work_subproject', 'personal')
		  AND is_private = 0
		  AND archived_at IS NULL
		ORDER BY title ASC
	''').fetchall()

	conn.close()
	return render_template(
		'command_deck_meeting.html',
		meeting=dict(meeting),
		action_items=[dict(t) for t in action_items],
		projects=[dict(p) for p in projects],
		lifetime_seconds=lifetime_seconds,
		time_categories=[dict(c) for c in time_categories],
	)


# ---- Create ----


@meetings_bp.route('/command-deck/meetings/new', methods=['POST'])
@cd_auth_required
def meeting_new():
	title = (request.form.get('title') or '').strip()
	if not title:
		# Inline modal sends application/x-www-form-urlencoded; either redirect
		# back to the referrer or land the user on the index.
		return redirect(request.referrer or url_for('meetings.meetings_index'))

	meeting_date = _parse_meeting_date(request.form.get('meeting_date'))
	if meeting_date is None:
		return redirect(request.referrer or url_for('meetings.meetings_index'))

	project_id = request.form.get('project_id')
	try:
		project_id = int(project_id) if project_id else None
	except (ValueError, TypeError):
		project_id = None

	notes = request.form.get('notes')

	recurrence = (request.form.get('recurrence') or '').strip() or None
	if recurrence and recurrence not in VALID_RECURRENCES:
		recurrence = None

	time_category_id = request.form.get('time_category_id')
	try:
		time_category_id = int(time_category_id) if time_category_id else None
	except (ValueError, TypeError):
		time_category_id = None

	now = et_now()

	conn = get_db()
	cur = conn.execute('''
		INSERT INTO meetings
			(project_id, title, meeting_date, notes, status, recurrence,
			 time_category_id, created, updated)
		VALUES (?, ?, ?, ?, 'scheduled', ?, ?, ?, ?)
	''', (project_id, title, meeting_date, notes, recurrence,
	      time_category_id, now, now))
	new_id = cur.lastrowid
	conn.commit()
	conn.close()
	return redirect(url_for('meetings.meeting_detail', meeting_id=new_id))


# ---- Per-field update ----


@meetings_bp.route('/command-deck/meetings/<int:meeting_id>/update', methods=['POST'])
@cd_auth_required
def meeting_update(meeting_id):
	data = request.get_json(silent=True) or request.form
	conn = get_db()
	row = conn.execute('SELECT * FROM meetings WHERE id = ?', (meeting_id,)).fetchone()
	if not row:
		conn.close()
		return jsonify({'error': 'not_found'}), 404

	updates = {}
	if 'title' in data:
		title = (data.get('title') or '').strip()
		if not title:
			conn.close()
			return jsonify({'error': 'title_required'}), 400
		updates['title'] = title

	if 'meeting_date' in data:
		val = _parse_meeting_date(data.get('meeting_date'))
		if val is None:
			conn.close()
			return jsonify({'error': 'invalid_meeting_date'}), 400
		updates['meeting_date'] = val

	if 'project_id' in data:
		val = data.get('project_id')
		if val in (None, '', 'null', 'standalone'):
			updates['project_id'] = None
		else:
			try:
				updates['project_id'] = int(val)
			except (ValueError, TypeError):
				conn.close()
				return jsonify({'error': 'invalid_project_id'}), 400

	if 'notes' in data:
		updates['notes'] = data.get('notes') or ''

	if 'status' in data:
		val = (data.get('status') or '').strip() or 'scheduled'
		if val not in VALID_STATUSES:
			conn.close()
			return jsonify({'error': 'invalid_status'}), 400
		updates['status'] = val

	if 'recurrence' in data:
		val = data.get('recurrence')
		if val in (None, '', 'null', 'none'):
			updates['recurrence'] = None
		elif val in VALID_RECURRENCES:
			updates['recurrence'] = val
		else:
			conn.close()
			return jsonify({'error': 'invalid_recurrence'}), 400

	if 'time_category_id' in data:
		val = data.get('time_category_id')
		if val in (None, '', 'null'):
			updates['time_category_id'] = None
		else:
			try:
				cat_id = int(val)
			except (ValueError, TypeError):
				conn.close()
				return jsonify({'error': 'invalid_time_category_id'}), 400
			cat = conn.execute(
				'SELECT id FROM time_categories WHERE id = ? AND is_active = 1',
				(cat_id,)
			).fetchone()
			if not cat:
				conn.close()
				return jsonify({'error': 'time_category_not_found'}), 404
			updates['time_category_id'] = cat_id

	if not updates:
		conn.close()
		return jsonify({'error': 'no_fields'}), 400

	updates['updated'] = et_now()
	set_sql = ', '.join(f'{k} = ?' for k in updates)
	vals = list(updates.values()) + [meeting_id]
	conn.execute(f'UPDATE meetings SET {set_sql} WHERE id = ?', vals)
	conn.commit()
	row = conn.execute('SELECT * FROM meetings WHERE id = ?', (meeting_id,)).fetchone()
	conn.close()
	return jsonify({'success': True, 'meeting': dict(row)})


# ---- Delete ----


@meetings_bp.route('/command-deck/meetings/<int:meeting_id>/delete', methods=['POST'])
@cd_auth_required
def meeting_delete(meeting_id):
	conn = get_db()
	row = conn.execute('SELECT id FROM meetings WHERE id = ?', (meeting_id,)).fetchone()
	if not row:
		conn.close()
		return jsonify({'error': 'not_found'}), 404
	# Cascade is SET NULL on tasks.meeting_id and time_entries.meeting_id —
	# tasks survive as orphan action items, time entries keep their project
	# attribution. The DB does this automatically given the FK declaration,
	# but SQLite doesn't enforce FKs by default; do it explicitly so we don't
	# rely on PRAGMA foreign_keys=ON being set somewhere upstream.
	conn.execute('UPDATE tasks SET meeting_id = NULL WHERE meeting_id = ?', (meeting_id,))
	conn.execute('UPDATE time_entries SET meeting_id = NULL WHERE meeting_id = ?', (meeting_id,))
	conn.execute('DELETE FROM meetings WHERE id = ?', (meeting_id,))
	conn.commit()
	conn.close()
	return jsonify({'success': True, 'deleted_id': meeting_id})


# ---- Mark complete (spawns next on recurrence) ----


@meetings_bp.route('/command-deck/meetings/<int:meeting_id>/complete', methods=['POST'])
def meeting_complete(meeting_id):
	"""Set status='complete' and, if recurrence is set, spawn the next
	instance in the series. Response payload includes spawned.id when a new
	meeting was created so the caller can show "next: <date>" inline."""
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 403
	conn = get_db()
	row = conn.execute('SELECT * FROM meetings WHERE id = ?', (meeting_id,)).fetchone()
	if not row:
		conn.close()
		return jsonify({'error': 'not_found'}), 404
	now = et_now()
	conn.execute(
		'UPDATE meetings SET status = ?, updated = ? WHERE id = ?',
		('complete', now, meeting_id)
	)
	spawned_id = _spawn_next_in_series(conn, row)
	conn.commit()
	spawned = None
	if spawned_id:
		new_row = conn.execute(
			'SELECT id, title, meeting_date FROM meetings WHERE id = ?',
			(spawned_id,)
		).fetchone()
		if new_row:
			spawned = dict(new_row)
	conn.close()
	return jsonify({'success': True, 'status': 'complete', 'spawned': spawned})


# ---- Action items ----


@meetings_bp.route('/command-deck/meetings/<int:meeting_id>/action-items/add', methods=['POST'])
def meeting_action_item_add(meeting_id):
	# This route is also POSTed to from inline JS on the meeting detail page,
	# which uses XHR; cd_auth_required redirects to /login on auth failure
	# (HTML), which would break JSON consumers. Match the pattern from
	# tasks_bp routes and return JSON 403.
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 403

	title = (request.form.get('title') or '').strip()
	if not title:
		return jsonify({'error': 'title_required'}), 400

	conn = get_db()
	meeting = conn.execute(
		'SELECT id, project_id FROM meetings WHERE id = ?', (meeting_id,)
	).fetchone()
	if not meeting:
		conn.close()
		return jsonify({'error': 'not_found'}), 404

	# Pull the next "order" within this meeting's project bucket so the action
	# item lands at the bottom of the project task list (not jammed in random)
	# — mirroring the cd_project_task_add convention.
	if meeting['project_id'] is not None:
		row = conn.execute(
			'SELECT COALESCE(MAX("order"), -1) + 1 AS next_order '
			'FROM tasks WHERE project_id = ?',
			(meeting['project_id'],)
		).fetchone()
	else:
		row = conn.execute(
			'SELECT COALESCE(MAX("order"), -1) + 1 AS next_order '
			'FROM tasks WHERE project_id IS NULL'
		).fetchone()
	next_order = row['next_order'] if row else 0

	now = et_now()
	cur = conn.execute('''
		INSERT INTO tasks
			(title, status, created, project_id, "order", today, meeting_id)
		VALUES (?, 'open', ?, ?, ?, 0, ?)
	''', (title, now, meeting['project_id'], next_order, meeting_id))
	new_id = cur.lastrowid
	conn.commit()
	task = conn.execute('SELECT * FROM tasks WHERE id = ?', (new_id,)).fetchone()
	conn.close()
	return jsonify({'success': True, 'task': dict(task)})
