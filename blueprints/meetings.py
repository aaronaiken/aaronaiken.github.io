"""
Meetings blueprint — Phase 5 of the Command Deck spec.

Routes (all under /command-deck/meetings/*, all PIN-gated when the linked
project is private — privacy inherits from the project per spec §1 #10):

  GET   /command-deck/meetings/                  -- index page (chronological)
  GET   /command-deck/meetings/<id>/             -- detail page
  POST  /command-deck/meetings/new               -- create
  POST  /command-deck/meetings/<id>/update       -- per-field patch
  POST  /command-deck/meetings/<id>/delete       -- hard delete (cascades NULL)
  POST  /command-deck/meetings/<id>/action-items/add  -- creates a tasks row

Cascade rules are baked into the schema (migrate_add_meetings.py):
  - project delete  → meetings.project_id          = NULL
  - meeting delete  → tasks.meeting_id             = NULL
  - meeting delete  → time_entries.meeting_id      = NULL

Notes are markdown source; rendering happens client-side via marked.js
(same pipeline as note blocks).
"""
import datetime as _dt

from flask import (
	Blueprint, jsonify, redirect, render_template, request, url_for,
)

from helpers.auth import cd_auth_required, is_authenticated
from helpers.db import et_now, get_db


meetings_bp = Blueprint('meetings', __name__)


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
		       (SELECT COUNT(*) FROM tasks WHERE meeting_id = m.id) AS action_count
		FROM meetings m
		LEFT JOIN projects p ON m.project_id = p.id
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
		       p.is_private AS project_is_private
		FROM meetings m
		LEFT JOIN projects p ON m.project_id = p.id
		WHERE m.id = ?
	''', (meeting_id,)).fetchone()
	if not meeting:
		conn.close()
		return "Meeting not found", 404

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
		ORDER BY title ASC
	''').fetchall()

	conn.close()
	return render_template(
		'command_deck_meeting.html',
		meeting=dict(meeting),
		action_items=[dict(t) for t in action_items],
		projects=[dict(p) for p in projects],
		lifetime_seconds=lifetime_seconds,
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
	now = et_now()

	conn = get_db()
	cur = conn.execute('''
		INSERT INTO meetings (project_id, title, meeting_date, notes, created, updated)
		VALUES (?, ?, ?, ?, ?, ?)
	''', (project_id, title, meeting_date, notes, now, now))
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
