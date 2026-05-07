"""
Time tracking blueprint — multi-timer back end.

Phase 1 of .kt/spec-time-tracking-phase-1.md.

Storage convention:
  started_at, ended_at, created, updated are stored as ISO 8601 UTC strings
  in the canonical format '%Y-%m-%dT%H:%M:%S.%fZ' (microseconds, Z suffix).
  Clients may send Z or +00:00; server normalizes before storing.

Day-boundary timezone for the /time/today route is America/New_York
(per spec §0a.2 #4). Storage stays UTC; only the day-window math is ET.
"""
from datetime import datetime, timedelta
import pytz
from flask import Blueprint, request, jsonify

from helpers.auth import is_authenticated
from helpers.db import get_db


time_tracking_bp = Blueprint('time_tracking', __name__)


_UTC_FORMAT = '%Y-%m-%dT%H:%M:%S.%fZ'
_TRACKABLE_TYPES = ('work_subproject', 'personal')


# ---- Time helpers (module-private) ----


def _utc_now_iso():
	return datetime.now(pytz.UTC).strftime(_UTC_FORMAT)


def _parse_iso_utc(s):
	"""Parse an ISO 8601 string (Z or +00:00 or naive) to a UTC-aware datetime."""
	if not s:
		return None
	s = s.strip()
	if s.endswith('Z'):
		s = s[:-1] + '+00:00'
	dt = datetime.fromisoformat(s)
	if dt.tzinfo is None:
		dt = pytz.UTC.localize(dt)
	return dt.astimezone(pytz.UTC)


def _normalize_iso_utc(s):
	"""Round-trip an ISO string to canonical Z-suffix microsecond UTC for storage."""
	dt = _parse_iso_utc(s)
	return dt.strftime(_UTC_FORMAT) if dt else None


def _et_today_bounds_utc():
	"""Return (start_utc_iso, end_utc_iso) for the current ET day (00:00–24:00 ET)."""
	eastern = pytz.timezone('US/Eastern')
	today_et = datetime.now(eastern).date()
	start_et = eastern.localize(datetime.combine(today_et, datetime.min.time()))
	end_et = start_et + timedelta(days=1)
	return (
		start_et.astimezone(pytz.UTC).strftime(_UTC_FORMAT),
		end_et.astimezone(pytz.UTC).strftime(_UTC_FORMAT),
	)


# ---- Serializers ----


def _row_get(row, key, default=None):
	"""sqlite3.Row doesn't support .get() — this fills the gap for optional join cols."""
	try:
		return row[key]
	except (IndexError, KeyError):
		return default


def _fetch_entry_with_context(conn, entry_id):
	"""Re-fetch a time_entries row with task + checklist_item + parent-block
	+ meeting + ticket + time-category context joined. The tickets JOIN
	supports the [TKT-NNNN — title] context badge across all timer surfaces;
	the time_categories JOIN supplies the work-bucket label rendered as a
	color dot/pill alongside the scope ctx."""
	return conn.execute('''
		SELECT te.*,
		       t.title          AS task_title,
		       ci.text           AS checklist_item_text,
		       b.id              AS block_id,
		       b.title           AS block_title,
		       m.title           AS meeting_title,
		       tk.ticket_number  AS ticket_number,
		       tk.title          AS ticket_title,
		       tc.name           AS time_category_name,
		       tc.color          AS time_category_color
		FROM time_entries te
		LEFT JOIN tasks t            ON te.task_id = t.id
		LEFT JOIN checklist_items ci ON te.checklist_item_id = ci.id
		LEFT JOIN blocks b           ON ci.block_id = b.id
		LEFT JOIN meetings m         ON te.meeting_id = m.id
		LEFT JOIN tickets tk         ON te.ticket_id = tk.id
		LEFT JOIN time_categories tc ON te.time_category_id = tc.id
		WHERE te.id = ?
	''', (entry_id,)).fetchone()


def _serialize_active_entry(row):
	"""Active-entry shape — scope ctx (task / item / meeting / ticket — mutex)
	plus the orthogonal time_category label."""
	started = _parse_iso_utc(row['started_at'])
	elapsed = int((datetime.now(pytz.UTC) - started).total_seconds()) if started else 0
	return {
		'id': row['id'],
		'project_id': row['project_id'],
		'project_title': row['project_title'],
		'area_id': row['area_id'],
		'area_title': row['area_title'],
		'area_color': row['area_color'],
		'description': row['description'],
		'started_at': row['started_at'],
		'elapsed_seconds': max(0, elapsed),
		'task_id': _row_get(row, 'task_id'),
		'task_title': _row_get(row, 'task_title'),
		'checklist_item_id': _row_get(row, 'checklist_item_id'),
		'checklist_item_text': _row_get(row, 'checklist_item_text'),
		'block_id': _row_get(row, 'block_id'),
		'block_title': _row_get(row, 'block_title'),
		'meeting_id': _row_get(row, 'meeting_id'),
		'meeting_title': _row_get(row, 'meeting_title'),
		'ticket_id': _row_get(row, 'ticket_id'),
		'ticket_number': _row_get(row, 'ticket_number'),
		'ticket_title': _row_get(row, 'ticket_title'),
		'time_category_id': _row_get(row, 'time_category_id'),
		'time_category_name': _row_get(row, 'time_category_name'),
		'time_category_color': _row_get(row, 'time_category_color'),
	}


def _serialize_entry(row):
	"""Full entry shape — for start/stop/update/today responses."""
	return {
		'id': row['id'],
		'project_id': row['project_id'],
		'task_id': row['task_id'],
		'checklist_item_id': _row_get(row, 'checklist_item_id'),
		'task_title': _row_get(row, 'task_title'),
		'checklist_item_text': _row_get(row, 'checklist_item_text'),
		'block_id': _row_get(row, 'block_id'),
		'block_title': _row_get(row, 'block_title'),
		'meeting_id': _row_get(row, 'meeting_id'),
		'meeting_title': _row_get(row, 'meeting_title'),
		'ticket_id': _row_get(row, 'ticket_id'),
		'ticket_number': _row_get(row, 'ticket_number'),
		'ticket_title': _row_get(row, 'ticket_title'),
		'time_category_id': _row_get(row, 'time_category_id'),
		'time_category_name': _row_get(row, 'time_category_name'),
		'time_category_color': _row_get(row, 'time_category_color'),
		'description': row['description'],
		'started_at': row['started_at'],
		'ended_at': row['ended_at'],
		'duration_seconds': row['duration_seconds'],
		'created': row['created'],
		'updated': row['updated'],
	}


# ---- Routes ----


@time_tracking_bp.route('/time/active', methods=['GET'])
def time_active():
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 403
	conn = get_db()
	rows = conn.execute('''
		SELECT te.id, te.project_id, te.description, te.started_at,
		       te.task_id, te.checklist_item_id, te.meeting_id,
		       te.ticket_id, te.time_category_id,
		       p.title             AS project_title,
		       p.parent_project_id,
		       parent.id           AS area_id,
		       parent.title        AS area_title,
		       parent.area_color   AS area_color,
		       t.title             AS task_title,
		       ci.text             AS checklist_item_text,
		       b.id                AS block_id,
		       b.title             AS block_title,
		       m.title             AS meeting_title,
		       tk.ticket_number    AS ticket_number,
		       tk.title            AS ticket_title,
		       tc.name             AS time_category_name,
		       tc.color            AS time_category_color
		FROM time_entries te
		JOIN projects p ON te.project_id = p.id
		LEFT JOIN projects parent    ON p.parent_project_id = parent.id
		LEFT JOIN tasks t            ON te.task_id = t.id
		LEFT JOIN checklist_items ci ON te.checklist_item_id = ci.id
		LEFT JOIN blocks b           ON ci.block_id = b.id
		LEFT JOIN meetings m         ON te.meeting_id = m.id
		LEFT JOIN tickets tk         ON te.ticket_id = tk.id
		LEFT JOIN time_categories tc ON te.time_category_id = tc.id
		WHERE te.ended_at IS NULL
		ORDER BY te.started_at ASC
	''').fetchall()
	conn.close()
	return jsonify({'active': [_serialize_active_entry(r) for r in rows]})


@time_tracking_bp.route('/time/start', methods=['POST'])
def time_start():
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 403
	data = request.get_json(silent=True) or request.form
	project_id = data.get('project_id')
	description = (data.get('description') or '').strip()
	task_id = data.get('task_id')
	checklist_item_id = data.get('checklist_item_id')
	meeting_id = data.get('meeting_id')
	ticket_id = data.get('ticket_id')
	time_category_id = data.get('time_category_id')

	if not project_id:
		return jsonify({'error': 'project_id required'}), 400

	# 4-way mutex — at most one of task / item / meeting / ticket may scope an entry
	scopes_set = sum(1 for x in (task_id, checklist_item_id, meeting_id, ticket_id) if x)
	if scopes_set > 1:
		return jsonify({'error': 'task_item_meeting_or_ticket_not_multiple'}), 400

	conn = get_db()
	project = conn.execute(
		'SELECT id, project_type FROM projects WHERE id = ?', (project_id,)
	).fetchone()
	if not project:
		conn.close()
		return jsonify({'error': 'project_not_found'}), 404
	if project['project_type'] not in _TRACKABLE_TYPES:
		conn.close()
		return jsonify({
			'error': 'project_not_trackable',
			'project_type': project['project_type'],
		}), 400

	# Phase 1.5 — task_id must point to a task on this project
	if task_id:
		task = conn.execute(
			'SELECT id, project_id FROM tasks WHERE id = ?', (task_id,)
		).fetchone()
		if not task:
			conn.close()
			return jsonify({'error': 'task_not_found'}), 404
		if task['project_id'] != int(project_id):
			conn.close()
			return jsonify({
				'error': 'task_project_mismatch',
				'task_project_id': task['project_id'],
			}), 400

	# Phase 1.5 — checklist_item_id must reach this project via blocks
	if checklist_item_id:
		item = conn.execute('''
			SELECT ci.id, b.project_id
			FROM checklist_items ci
			JOIN blocks b ON ci.block_id = b.id
			WHERE ci.id = ? AND ci.archived_at IS NULL
		''', (checklist_item_id,)).fetchone()
		if not item:
			conn.close()
			return jsonify({'error': 'checklist_item_not_found'}), 404
		if item['project_id'] != int(project_id):
			conn.close()
			return jsonify({
				'error': 'item_project_mismatch',
				'item_project_id': item['project_id'],
			}), 400

	# Phase 5 — meeting_id must point to a meeting on this project
	if meeting_id:
		meeting = conn.execute(
			'SELECT id, project_id FROM meetings WHERE id = ?', (meeting_id,)
		).fetchone()
		if not meeting:
			conn.close()
			return jsonify({'error': 'meeting_not_found'}), 404
		if meeting['project_id'] != int(project_id):
			conn.close()
			return jsonify({
				'error': 'meeting_project_mismatch',
				'meeting_project_id': meeting['project_id'],
			}), 400

	# Tickets — ticket must exist; if it has a project_id, must match the
	# entry's project_id. A ticket with NULL project_id can be timed against
	# any trackable project Aaron picks (e.g., a Corp ticket that doesn't
	# tie to a specific sub-project but he's clocking time against Onboarding).
	if ticket_id:
		ticket = conn.execute(
			'SELECT id, project_id FROM tickets WHERE id = ?', (ticket_id,)
		).fetchone()
		if not ticket:
			conn.close()
			return jsonify({'error': 'ticket_not_found'}), 404
		if ticket['project_id'] is not None and ticket['project_id'] != int(project_id):
			conn.close()
			return jsonify({
				'error': 'ticket_project_mismatch',
				'ticket_project_id': ticket['project_id'],
			}), 400

	# Time category is just a label — validate existence + active state. Doesn't
	# need to relate to project / ticket; user picks freely.
	if time_category_id:
		cat = conn.execute(
			'SELECT id, is_active FROM time_categories WHERE id = ?',
			(time_category_id,)
		).fetchone()
		if not cat:
			conn.close()
			return jsonify({'error': 'time_category_not_found'}), 404
		# Allow archived categories on existing references but not on new starts
		if not cat['is_active']:
			conn.close()
			return jsonify({'error': 'time_category_archived'}), 400

	# §0a.2 #3 — 409 on concurrent same-project timer
	existing = conn.execute(
		'SELECT id FROM time_entries WHERE project_id = ? AND ended_at IS NULL',
		(project_id,)
	).fetchone()
	if existing:
		conn.close()
		return jsonify({
			'error': 'already_running',
			'existing_id': existing['id'],
		}), 409

	now = _utc_now_iso()
	cur = conn.execute('''
		INSERT INTO time_entries
			(project_id, task_id, checklist_item_id, meeting_id, ticket_id,
			 time_category_id, description, started_at, created, updated)
		VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
	''', (
		project_id,
		int(task_id) if task_id else None,
		int(checklist_item_id) if checklist_item_id else None,
		int(meeting_id) if meeting_id else None,
		int(ticket_id) if ticket_id else None,
		int(time_category_id) if time_category_id else None,
		description, now, now, now,
	))
	new_id = cur.lastrowid
	conn.commit()
	row = _fetch_entry_with_context(conn, new_id)
	conn.close()
	return jsonify({'success': True, 'entry': _serialize_entry(row)})


@time_tracking_bp.route('/time/<int:entry_id>/stop', methods=['POST'])
def time_stop(entry_id):
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 403
	conn = get_db()
	row = conn.execute('SELECT * FROM time_entries WHERE id = ?', (entry_id,)).fetchone()
	if not row:
		conn.close()
		return jsonify({'error': 'not_found'}), 404
	if row['ended_at']:
		conn.close()
		return jsonify({
			'error': 'already_stopped',
			'entry': _serialize_entry(row),
		}), 409

	now_dt = datetime.now(pytz.UTC)
	now_iso = now_dt.strftime(_UTC_FORMAT)
	started = _parse_iso_utc(row['started_at'])
	duration = int((now_dt - started).total_seconds()) if started else 0
	conn.execute('''
		UPDATE time_entries
		SET ended_at = ?, duration_seconds = ?, updated = ?
		WHERE id = ?
	''', (now_iso, max(0, duration), now_iso, entry_id))
	conn.commit()
	row = _fetch_entry_with_context(conn, entry_id)
	conn.close()
	return jsonify({'success': True, 'entry': _serialize_entry(row)})


@time_tracking_bp.route('/time/<int:entry_id>/update', methods=['POST'])
def time_update(entry_id):
	"""
	Update description, started_at, ended_at, task_id, and/or
	checklist_item_id on an entry (running or stopped).

	Per §0a.2 #2 — recomputes duration_seconds when ended_at is set.
	Per Phase 2 spec §3.2 — re-assigning task_id or checklist_item_id
	is allowed but validated against the entry's existing project_id.
	Cross-project re-assignment is forbidden (delete + recreate
	instead). The entry's project_id is never changed by this route.
	"""
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 403
	data = request.get_json(silent=True) or request.form
	conn = get_db()
	row = conn.execute('SELECT * FROM time_entries WHERE id = ?', (entry_id,)).fetchone()
	if not row:
		conn.close()
		return jsonify({'error': 'not_found'}), 404

	new_description = row['description']
	new_started = row['started_at']
	new_ended = row['ended_at']
	new_task_id = row['task_id']
	new_item_id = row['checklist_item_id']
	new_meeting_id = _row_get(row, 'meeting_id')
	new_ticket_id = _row_get(row, 'ticket_id')
	new_category_id = _row_get(row, 'time_category_id')

	if 'description' in data:
		new_description = (data.get('description') or '').strip()

	if 'started_at' in data:
		val = data.get('started_at')
		if not val:
			conn.close()
			return jsonify({'error': 'started_at_required'}), 400
		try:
			new_started = _normalize_iso_utc(val)
		except (ValueError, TypeError):
			conn.close()
			return jsonify({'error': 'invalid_started_at'}), 400

	if 'ended_at' in data:
		val = data.get('ended_at')
		if val in (None, '', 'null'):
			new_ended = None
		else:
			try:
				new_ended = _normalize_iso_utc(val)
			except (ValueError, TypeError):
				conn.close()
				return jsonify({'error': 'invalid_ended_at'}), 400

	if 'task_id' in data:
		val = data.get('task_id')
		if val in (None, '', 'null'):
			new_task_id = None
		else:
			try:
				new_task_id = int(val)
			except (ValueError, TypeError):
				conn.close()
				return jsonify({'error': 'invalid_task_id'}), 400

	if 'checklist_item_id' in data:
		val = data.get('checklist_item_id')
		if val in (None, '', 'null'):
			new_item_id = None
		else:
			try:
				new_item_id = int(val)
			except (ValueError, TypeError):
				conn.close()
				return jsonify({'error': 'invalid_checklist_item_id'}), 400

	if 'meeting_id' in data:
		val = data.get('meeting_id')
		if val in (None, '', 'null'):
			new_meeting_id = None
		else:
			try:
				new_meeting_id = int(val)
			except (ValueError, TypeError):
				conn.close()
				return jsonify({'error': 'invalid_meeting_id'}), 400

	if 'ticket_id' in data:
		val = data.get('ticket_id')
		if val in (None, '', 'null'):
			new_ticket_id = None
		else:
			try:
				new_ticket_id = int(val)
			except (ValueError, TypeError):
				conn.close()
				return jsonify({'error': 'invalid_ticket_id'}), 400

	if 'time_category_id' in data:
		val = data.get('time_category_id')
		if val in (None, '', 'null'):
			new_category_id = None
		else:
			try:
				new_category_id = int(val)
			except (ValueError, TypeError):
				conn.close()
				return jsonify({'error': 'invalid_time_category_id'}), 400

	scopes_set = sum(1 for x in (new_task_id, new_item_id, new_meeting_id, new_ticket_id) if x is not None)
	if scopes_set > 1:
		conn.close()
		return jsonify({'error': 'task_item_meeting_or_ticket_not_multiple'}), 400

	entry_project_id = row['project_id']

	if 'task_id' in data and new_task_id is not None:
		task = conn.execute(
			'SELECT id, project_id FROM tasks WHERE id = ?', (new_task_id,)
		).fetchone()
		if not task:
			conn.close()
			return jsonify({'error': 'task_not_found'}), 404
		if task['project_id'] != entry_project_id:
			conn.close()
			return jsonify({
				'error': 'task_project_mismatch',
				'task_project_id': task['project_id'],
			}), 400

	if 'checklist_item_id' in data and new_item_id is not None:
		item = conn.execute('''
			SELECT ci.id, b.project_id
			FROM checklist_items ci
			JOIN blocks b ON ci.block_id = b.id
			WHERE ci.id = ? AND ci.archived_at IS NULL
		''', (new_item_id,)).fetchone()
		if not item:
			conn.close()
			return jsonify({'error': 'checklist_item_not_found'}), 404
		if item['project_id'] != entry_project_id:
			conn.close()
			return jsonify({
				'error': 'item_project_mismatch',
				'item_project_id': item['project_id'],
			}), 400

	if 'meeting_id' in data and new_meeting_id is not None:
		meeting = conn.execute(
			'SELECT id, project_id FROM meetings WHERE id = ?', (new_meeting_id,)
		).fetchone()
		if not meeting:
			conn.close()
			return jsonify({'error': 'meeting_not_found'}), 404
		if meeting['project_id'] != entry_project_id:
			conn.close()
			return jsonify({
				'error': 'meeting_project_mismatch',
				'meeting_project_id': meeting['project_id'],
			}), 400

	if 'ticket_id' in data and new_ticket_id is not None:
		ticket = conn.execute(
			'SELECT id, project_id FROM tickets WHERE id = ?', (new_ticket_id,)
		).fetchone()
		if not ticket:
			conn.close()
			return jsonify({'error': 'ticket_not_found'}), 404
		if ticket['project_id'] is not None and ticket['project_id'] != entry_project_id:
			conn.close()
			return jsonify({
				'error': 'ticket_project_mismatch',
				'ticket_project_id': ticket['project_id'],
			}), 400

	if 'time_category_id' in data and new_category_id is not None:
		cat = conn.execute(
			'SELECT id FROM time_categories WHERE id = ?', (new_category_id,)
		).fetchone()
		if not cat:
			conn.close()
			return jsonify({'error': 'time_category_not_found'}), 404

	if new_ended:
		try:
			s = _parse_iso_utc(new_started)
			e = _parse_iso_utc(new_ended)
			new_duration = max(0, int((e - s).total_seconds()))
		except (ValueError, TypeError):
			conn.close()
			return jsonify({'error': 'invalid_timestamps'}), 400
	else:
		new_duration = None

	now_iso = _utc_now_iso()
	conn.execute('''
		UPDATE time_entries
		SET description = ?, started_at = ?, ended_at = ?,
		    duration_seconds = ?, task_id = ?, checklist_item_id = ?,
		    meeting_id = ?, ticket_id = ?, time_category_id = ?,
		    updated = ?
		WHERE id = ?
	''', (
		new_description, new_started, new_ended, new_duration,
		new_task_id, new_item_id, new_meeting_id,
		new_ticket_id, new_category_id, now_iso, entry_id,
	))
	conn.commit()
	row = _fetch_entry_with_context(conn, entry_id)
	conn.close()
	return jsonify({'success': True, 'entry': _serialize_entry(row)})


@time_tracking_bp.route('/time/today/total', methods=['GET'])
def time_today_total():
	"""Phase 2 §3.4 — today's tracked time across all projects (ET day).

	Returns both:
	  stopped_today_seconds — sum of duration_seconds for entries with
	    ended_at set today. The client adds local elapsed-so-far for
	    any running entries (from /time/active) to get a live total
	    that ticks up every second without polling this route every
	    second.
	  today_total_seconds — convenience snapshot at fetch time. Equal
	    to stopped + sum of running elapsed AT fetch time. Useful for
	    consumers that don't subscribe to /time/active.

	Drives the today total in the Cockpit floating-panel titlebar."""
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 403
	start_utc, end_utc = _et_today_bounds_utc()
	conn = get_db()
	rows = conn.execute('''
		SELECT started_at, ended_at, duration_seconds
		FROM time_entries
		WHERE started_at >= ? AND started_at < ?
	''', (start_utc, end_utc)).fetchall()
	conn.close()

	stopped = 0
	running_elapsed = 0
	now = datetime.now(pytz.UTC)
	for r in rows:
		if r['ended_at'] and r['duration_seconds'] is not None:
			stopped += max(0, int(r['duration_seconds']))
		elif not r['ended_at']:
			started = _parse_iso_utc(r['started_at'])
			if started:
				running_elapsed += max(0, int((now - started).total_seconds()))

	today_et = datetime.now(pytz.timezone('US/Eastern')).date().isoformat()
	return jsonify({
		'stopped_today_seconds': stopped,
		'today_total_seconds': stopped + running_elapsed,
		'today_date': today_et,
	})


@time_tracking_bp.route('/time/<int:entry_id>/delete', methods=['POST'])
def time_delete(entry_id):
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 403
	conn = get_db()
	row = conn.execute('SELECT id FROM time_entries WHERE id = ?', (entry_id,)).fetchone()
	if not row:
		conn.close()
		return jsonify({'error': 'not_found'}), 404
	conn.execute('DELETE FROM time_entries WHERE id = ?', (entry_id,))
	conn.commit()
	conn.close()
	return jsonify({'success': True, 'deleted_id': entry_id})


@time_tracking_bp.route('/time/projects', methods=['GET'])
def time_projects():
	"""
	Project list for the timer panel's picker. Returns work areas with their
	sub-projects, plus tracking-enabled personal projects. Excludes private.
	Not in spec §3.1, added to support the floating-panel picker (§5.5).
	"""
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 403
	conn = get_db()
	areas = conn.execute('''
		SELECT id, title, slug, area_color
		FROM projects
		WHERE project_type = 'work_area'
		  AND is_private = 0
		ORDER BY title ASC
	''').fetchall()
	out = {'areas': [], 'personal': []}
	for a in areas:
		subs = conn.execute('''
			SELECT id, title, slug, tracking_enabled
			FROM projects
			WHERE project_type = 'work_subproject'
			  AND parent_project_id = ?
			  AND is_private = 0
			ORDER BY updated DESC, title ASC
		''', (a['id'],)).fetchall()
		out['areas'].append({
			'id': a['id'],
			'title': a['title'],
			'slug': a['slug'],
			'area_color': a['area_color'],
			'subprojects': [dict(s) for s in subs],
		})
	personals = conn.execute('''
		SELECT id, title, slug, tracking_enabled
		FROM projects
		WHERE project_type = 'personal'
		  AND is_private = 0
		  AND tracking_enabled = 1
		ORDER BY updated DESC, title ASC
	''').fetchall()
	out['personal'] = [dict(p) for p in personals]
	conn.close()
	return jsonify(out)


@time_tracking_bp.route('/time/today/<int:project_id>', methods=['GET'])
def time_today(project_id):
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 403
	start_utc, end_utc = _et_today_bounds_utc()
	conn = get_db()
	rows = conn.execute('''
		SELECT te.*,
		       t.title           AS task_title,
		       ci.text            AS checklist_item_text,
		       b.id               AS block_id,
		       b.title            AS block_title,
		       m.title            AS meeting_title,
		       tk.ticket_number   AS ticket_number,
		       tk.title           AS ticket_title,
		       tc.name            AS time_category_name,
		       tc.color           AS time_category_color
		FROM time_entries te
		LEFT JOIN tasks t            ON te.task_id = t.id
		LEFT JOIN checklist_items ci ON te.checklist_item_id = ci.id
		LEFT JOIN blocks b           ON ci.block_id = b.id
		LEFT JOIN meetings m         ON te.meeting_id = m.id
		LEFT JOIN tickets tk         ON te.ticket_id = tk.id
		LEFT JOIN time_categories tc ON te.time_category_id = tc.id
		WHERE te.project_id = ?
		  AND te.started_at >= ?
		  AND te.started_at <  ?
		ORDER BY te.started_at ASC
	''', (project_id, start_utc, end_utc)).fetchall()
	conn.close()
	return jsonify({
		'project_id': project_id,
		'day_start_utc': start_utc,
		'day_end_utc': end_utc,
		'entries': [_serialize_entry(r) for r in rows],
	})
