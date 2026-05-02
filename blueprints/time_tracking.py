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
	"""Re-fetch a time_entries row with task + checklist_item context joined."""
	return conn.execute('''
		SELECT te.*, t.title AS task_title, ci.text AS checklist_item_text
		FROM time_entries te
		LEFT JOIN tasks t ON te.task_id = t.id
		LEFT JOIN checklist_items ci ON te.checklist_item_id = ci.id
		WHERE te.id = ?
	''', (entry_id,)).fetchone()


def _serialize_active_entry(row):
	"""Active-entry shape — Phase 1 §3.1 + Phase 1.5 task/item context."""
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
		       te.task_id, te.checklist_item_id,
		       p.title             AS project_title,
		       p.parent_project_id,
		       parent.id           AS area_id,
		       parent.title        AS area_title,
		       parent.area_color   AS area_color,
		       t.title             AS task_title,
		       ci.text             AS checklist_item_text
		FROM time_entries te
		JOIN projects p ON te.project_id = p.id
		LEFT JOIN projects parent ON p.parent_project_id = parent.id
		LEFT JOIN tasks t ON te.task_id = t.id
		LEFT JOIN checklist_items ci ON te.checklist_item_id = ci.id
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

	if not project_id:
		return jsonify({'error': 'project_id required'}), 400

	# Phase 1.5 — mutual exclusion of task vs checklist item
	if task_id and checklist_item_id:
		return jsonify({'error': 'task_or_item_not_both'}), 400

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
			WHERE ci.id = ?
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
			(project_id, task_id, checklist_item_id, description,
			 started_at, created, updated)
		VALUES (?, ?, ?, ?, ?, ?, ?)
	''', (
		project_id,
		int(task_id) if task_id else None,
		int(checklist_item_id) if checklist_item_id else None,
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
	Update description, started_at, and/or ended_at on an entry (running or stopped).
	Per §0a.2 #2 — recomputes duration_seconds when ended_at is set.
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
		    duration_seconds = ?, updated = ?
		WHERE id = ?
	''', (new_description, new_started, new_ended, new_duration, now_iso, entry_id))
	conn.commit()
	row = _fetch_entry_with_context(conn, entry_id)
	conn.close()
	return jsonify({'success': True, 'entry': _serialize_entry(row)})


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
		SELECT te.*, t.title AS task_title, ci.text AS checklist_item_text
		FROM time_entries te
		LEFT JOIN tasks t ON te.task_id = t.id
		LEFT JOIN checklist_items ci ON te.checklist_item_id = ci.id
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
