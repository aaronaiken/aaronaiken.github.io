"""
Reports blueprint — Phase 2 of the time-tracking spec.

GET /command-deck/reports/data
  Aggregations for the reports page (template lands in commit 4).
  Returns entries within an ET-anchored date window plus four
  precomputed totals shapes — by_area, by_project, by_day, by_timesheet
  — so the client can switch between toggle views without re-fetching.

Storage convention matches helpers/db.py + blueprints/time_tracking.py:
  - time_entries.started_at / ended_at are ISO 8601 UTC strings
  - day-window math is anchored to America/New_York
  - running entries (ended_at IS NULL) get an effective end of "now"
    and elapsed-so-far is counted toward totals; they're flagged
    `running: true` in the entries list so the UI can pulse them.

Privacy:
  Default excludes is_private projects (locked semantics, matches
  Huyang search-work). Client opts in via ?include_private=1 once
  the user has unlocked via /command-deck/verify-pin. The unlock
  state is purely client-side (localStorage in the dashboard) — this
  endpoint trusts the client to pass the flag responsibly. The auth
  gate is the Cockpit session cookie; the lock is for over-the-
  shoulder peeks, not for security.
"""
from datetime import datetime, timedelta, date

import pytz
import os

from flask import Blueprint, jsonify, render_template, request

from helpers.auth import cd_auth_required, is_authenticated
from helpers.db import get_db


PRIVATE_PROJECTS_PIN = os.environ.get('PRIVATE_PROJECTS_PIN', '')


reports_bp = Blueprint('reports', __name__)


_UTC_FORMAT = '%Y-%m-%dT%H:%M:%S.%fZ'
_EASTERN = pytz.timezone('US/Eastern')


# ---- Period resolution ----


def _et_today():
	return datetime.now(_EASTERN).date()


def _resolve_period(period, start_arg, end_arg):
	"""
	Returns (start_date, end_date) — both Python dates, ET-anchored.
	end is exclusive (one day past the last included day).

	period precedence: explicit start/end if both present, otherwise
	the period preset, otherwise the current week (Sun–Sat).
	"""
	if start_arg and end_arg:
		try:
			return (
				date.fromisoformat(start_arg),
				date.fromisoformat(end_arg),
			)
		except ValueError:
			pass  # fall through to preset

	today = _et_today()

	if period == 'today':
		return (today, today + timedelta(days=1))

	if period == 'this-month':
		first = today.replace(day=1)
		next_month = (first.replace(day=28) + timedelta(days=4)).replace(day=1)
		return (first, next_month)

	# Default: this week, Sun–Sat. Python's weekday() makes Monday=0 / Sunday=6;
	# we want Sunday as start, so we shift by (weekday + 1) % 7 days back.
	days_since_sunday = (today.weekday() + 1) % 7
	sunday = today - timedelta(days=days_since_sunday)
	return (sunday, sunday + timedelta(days=7))


def _et_date_to_utc_iso(d):
	"""Take an ET date (00:00 ET on that calendar day) → UTC ISO storage string."""
	dt_et = _EASTERN.localize(datetime.combine(d, datetime.min.time()))
	return dt_et.astimezone(pytz.UTC).strftime(_UTC_FORMAT)


def _utc_now_iso():
	return datetime.now(pytz.UTC).strftime(_UTC_FORMAT)


def _started_at_to_et_day(started_at_iso):
	"""ISO UTC → 'YYYY-MM-DD' in ET (for day buckets)."""
	dt = datetime.strptime(started_at_iso, _UTC_FORMAT)
	dt = pytz.UTC.localize(dt)
	return dt.astimezone(_EASTERN).date().isoformat()


# ---- Aggregation builders ----


def _build_totals(entries, start_date, end_date):
	"""Walk the entries list once, build all four totals shapes."""
	by_area, by_project, by_day, by_timesheet = {}, {}, {}, {}

	# Pre-seed by_day + by_timesheet day keys so missing days render as 0
	day_keys = []
	d = start_date
	while d < end_date:
		key = d.isoformat()
		day_keys.append(key)
		by_day[key] = 0
		d += timedelta(days=1)

	total_seconds = 0
	for e in entries:
		secs = e['duration_seconds'] or 0
		total_seconds += secs

		area_id = e.get('area_id') or 0  # 0 = personal (no area)
		area_key = str(area_id)
		if area_key not in by_area:
			by_area[area_key] = {
				'title': e.get('area_title') or 'Personal',
				'color': e.get('area_color') or '',
				'seconds': 0,
			}
		by_area[area_key]['seconds'] += secs

		proj_key = str(e['project_id'])
		if proj_key not in by_project:
			by_project[proj_key] = {
				'title': e.get('project_title') or '',
				'area_color': e.get('area_color') or '',
				'area_title': e.get('area_title') or 'Personal',
				'seconds': 0,
			}
		by_project[proj_key]['seconds'] += secs

		day_key = _started_at_to_et_day(e['started_at'])
		if day_key in by_day:
			by_day[day_key] += secs

		if proj_key not in by_timesheet:
			by_timesheet[proj_key] = {
				'title': e.get('project_title') or '',
				'area_color': e.get('area_color') or '',
				'area_title': e.get('area_title') or 'Personal',
				'days': {k: 0 for k in day_keys},
				'total': 0,
			}
		if day_key in by_timesheet[proj_key]['days']:
			by_timesheet[proj_key]['days'][day_key] += secs
		by_timesheet[proj_key]['total'] += secs

	return {
		'by_area': by_area,
		'by_project': by_project,
		'by_day': by_day,
		'by_timesheet': by_timesheet,
		'total_seconds': total_seconds,
	}


# ---- Routes ----


@reports_bp.route('/command-deck/reports/', methods=['GET'])
@reports_bp.route('/command-deck/reports', methods=['GET'])
@cd_auth_required
def reports_page():
	"""Renders the reports page shell. The data comes from /reports/data
	via JS so the toggle + period nav can swap views without full reloads."""
	return render_template(
		'command_deck_reports.html',
		private_projects_enabled=bool(PRIVATE_PROJECTS_PIN),
	)


@reports_bp.route('/command-deck/reports/data', methods=['GET'])
def reports_data():
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 403

	period = request.args.get('period')
	start_arg = request.args.get('start')
	end_arg = request.args.get('end')
	group = request.args.get('group', 'area')
	if group not in ('area', 'project', 'day', 'timesheet'):
		group = 'area'

	area_filter = request.args.get('area')
	project_filter = request.args.get('project')
	include_private = request.args.get('include_private') == '1'

	start_date, end_date = _resolve_period(period, start_arg, end_arg)
	start_utc = _et_date_to_utc_iso(start_date)
	end_utc = _et_date_to_utc_iso(end_date)
	now_utc = _utc_now_iso()

	# Window is keyed by started_at, consistent with the Phase 1 midnight rule:
	# an entry that crosses midnight (or spans days) is attributed to the day
	# of its started_at. Same principle extended to weeks/months — keeps the
	# day buckets and the totals self-consistent. A running timer that started
	# yesterday would not appear in today's report; a timer started today that
	# crosses into tomorrow would appear in today's report with full elapsed.
	clauses = ['te.started_at >= ?', 'te.started_at < ?']
	args = [start_utc, end_utc]

	if not include_private:
		clauses.append('p.is_private = 0')
		clauses.append('(parent.is_private IS NULL OR parent.is_private = 0)')

	if area_filter:
		try:
			area_id = int(area_filter)
			clauses.append('(parent.id = ? OR p.id = ?)')
			args.extend([area_id, area_id])
		except (ValueError, TypeError):
			pass

	if project_filter:
		try:
			project_id = int(project_filter)
			clauses.append('p.id = ?')
			args.append(project_id)
		except (ValueError, TypeError):
			pass

	where_sql = ' AND '.join(clauses)

	conn = get_db()
	rows = conn.execute(f'''
		SELECT te.id, te.project_id, te.task_id, te.checklist_item_id,
		       te.description, te.started_at, te.ended_at,
		       te.duration_seconds,
		       p.title           AS project_title,
		       p.is_private      AS project_is_private,
		       parent.id         AS area_id,
		       parent.title      AS area_title,
		       parent.area_color AS area_color,
		       t.title           AS task_title,
		       ci.text           AS checklist_item_text,
		       b.id              AS block_id,
		       b.title           AS block_title
		FROM time_entries te
		JOIN projects p              ON te.project_id = p.id
		LEFT JOIN projects parent    ON p.parent_project_id = parent.id
		LEFT JOIN tasks t            ON te.task_id = t.id
		LEFT JOIN checklist_items ci ON te.checklist_item_id = ci.id
		LEFT JOIN blocks b           ON ci.block_id = b.id
		WHERE {where_sql}
		ORDER BY te.started_at ASC
	''', args).fetchall()

	# Count private entries we excluded so the UI can render the
	# "// N private projects hidden — unlock to include" note.
	hidden_private_count = 0
	if not include_private:
		hidden_count_row = conn.execute(f'''
			SELECT COUNT(DISTINCT p.id) AS n
			FROM time_entries te
			JOIN projects p           ON te.project_id = p.id
			LEFT JOIN projects parent ON p.parent_project_id = parent.id
			WHERE te.started_at >= ? AND te.started_at < ?
			  AND (p.is_private = 1 OR parent.is_private = 1)
		''', [start_utc, end_utc]).fetchone()
		hidden_private_count = hidden_count_row['n'] if hidden_count_row else 0

	conn.close()

	entries = []
	for r in rows:
		# For running entries, substitute now() so duration math reflects
		# elapsed-so-far. Annotate with running:true so the UI can pulse.
		ended = r['ended_at']
		duration = r['duration_seconds']
		running = ended is None
		if running:
			started_dt = datetime.strptime(r['started_at'], _UTC_FORMAT)
			started_dt = pytz.UTC.localize(started_dt)
			elapsed = int((datetime.now(pytz.UTC) - started_dt).total_seconds())
			duration = max(0, elapsed)
			ended = now_utc

		entries.append({
			'id': r['id'],
			'project_id': r['project_id'],
			'project_title': r['project_title'],
			'area_id': r['area_id'],
			'area_title': r['area_title'],
			'area_color': r['area_color'],
			'task_id': r['task_id'],
			'task_title': r['task_title'],
			'checklist_item_id': r['checklist_item_id'],
			'checklist_item_text': r['checklist_item_text'],
			'block_id': r['block_id'],
			'block_title': r['block_title'],
			'description': r['description'],
			'started_at': r['started_at'],
			'ended_at': ended,
			'duration_seconds': duration,
			'running': running,
		})

	totals = _build_totals(entries, start_date, end_date)

	return jsonify({
		'meta': {
			'start': start_date.isoformat(),
			'end': end_date.isoformat(),
			'group': group,
			'totals_seconds': totals['total_seconds'],
			'entry_count': len(entries),
			'hidden_private_count': hidden_private_count,
			'include_private': include_private,
		},
		'entries': entries,
		'totals': {
			'by_area': totals['by_area'],
			'by_project': totals['by_project'],
			'by_day': totals['by_day'],
			'by_timesheet': totals['by_timesheet'],
		},
	})
