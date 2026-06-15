"""Today blueprint — daily focus master view + per-task/item/block star/complete + 4am ET auto-clear.

Phase 2.1 (.kt/spec-time-tracking-phase-2-1.md): checklist items as Today
citizens. Phase 2.2 (.kt/spec-time-tracking-phase-2-2.md): blocks join the
party as their own peer rows; checklist_items.checked_at stamped on every
toggle drives a precise (vs sloppy) 4am autoclear cutoff.
Phase 2.4 (.kt/spec-time-tracking-phase-2-4.md): block recurrence + per-cycle
item instances + due dates. Autoclear gains a cycle-fire pass that archives
old items and spawns fresh instances on cycle boundary.
"""
from datetime import datetime, timedelta
import pytz
from flask import Blueprint, request, redirect, url_for, jsonify, render_template

from helpers.auth import is_authenticated
from helpers.db import get_db, et_now


_UTC_FORMAT = '%Y-%m-%dT%H:%M:%S.%fZ'
_ET_FORMAT = '%Y-%m-%dT%H:%M:%S.%f%z'

_WEEKDAY_SHORT = {0: 'Mon', 1: 'Tue', 2: 'Wed', 3: 'Thu', 4: 'Fri', 5: 'Sat', 6: 'Sun'}
_WEEKDAY_FROM_SHORT = {v: k for k, v in _WEEKDAY_SHORT.items()}


def _utc_now_iso():
	return datetime.now(pytz.UTC).strftime(_UTC_FORMAT)


def _et_now_iso():
	"""ET-local ISO with offset — same shape as helpers.db.et_now() but full microseconds."""
	eastern = pytz.timezone('US/Eastern')
	return datetime.now(eastern).strftime(_ET_FORMAT)


# ---- Phase 2.4 — recurrence helpers ----

def _et_today_4am_iso(now_et):
	"""Return today's 4am ET (or yesterday's 4am if it's before 4am right now) as an
	ET-local ISO string suitable for lex compare against last_reset_at."""
	if now_et.hour < 4:
		base_date = (now_et - timedelta(days=1)).date()
	else:
		base_date = now_et.date()
	eastern = pytz.timezone('US/Eastern')
	cutoff = eastern.localize(datetime.combine(base_date, datetime.min.time()).replace(hour=4))
	return cutoff.strftime(_ET_FORMAT)


def _et_this_monday_4am_iso(now_et):
	"""Most recent Monday 4am ET (inclusive of today if today is Mon and time>=4am)."""
	# Walk back to the most recent Monday.
	days_back = now_et.weekday()  # Mon=0
	target_date = (now_et - timedelta(days=days_back)).date()
	eastern = pytz.timezone('US/Eastern')
	cutoff = eastern.localize(datetime.combine(target_date, datetime.min.time()).replace(hour=4))
	# If we're on Monday but before 4am, the boundary just passed is the PRIOR Monday.
	if cutoff > now_et:
		cutoff = cutoff - timedelta(days=7)
	return cutoff.strftime(_ET_FORMAT)


def _et_first_of_month_4am_iso(now_et):
	"""Most recent 1st-of-month 4am ET (inclusive of today if today=1st and time>=4am)."""
	first_this_month = now_et.replace(day=1, hour=4, minute=0, second=0, microsecond=0)
	if first_this_month > now_et:
		# We're on the 1st before 4am — the boundary just passed is the prior month's 1st.
		prior = (first_this_month - timedelta(days=1)).replace(day=1)
		return prior.strftime(_ET_FORMAT)
	return first_this_month.strftime(_ET_FORMAT)


def _next_weekday_iso(now_et, target_day_short):
	"""Next occurrence of target_day_short ('Mon'..'Sun') from now (inclusive of today),
	within 7 days. Returns ISO YYYY-MM-DD."""
	target = _WEEKDAY_FROM_SHORT.get(target_day_short, 4)  # default Friday
	days_ahead = (target - now_et.weekday()) % 7
	return (now_et + timedelta(days=days_ahead)).strftime('%Y-%m-%d')


def _this_month_target_iso(now_et, target):
	"""Target day-of-month in the current month. Accepts '1'..'31' or 'last'.
	Clamps over-large values to last day of month (e.g. 31 in Feb → 28/29)."""
	# Last day of current month
	next_month_first = (now_et.replace(day=28) + timedelta(days=4)).replace(day=1)
	last_day = (next_month_first - timedelta(days=1)).day
	if target == 'last':
		actual = last_day
	else:
		try:
			actual = min(max(1, int(target)), last_day)
		except (ValueError, TypeError):
			actual = now_et.day
	return now_et.replace(day=actual).strftime('%Y-%m-%d')


def _all_items_checked(conn, block_id):
	"""True iff the block has at least one active item AND every active item is checked."""
	row = conn.execute('''
		SELECT
		  COUNT(*) AS total,
		  SUM(CASE WHEN checked = 1 THEN 1 ELSE 0 END) AS checked
		FROM checklist_items
		WHERE block_id = ? AND archived_at IS NULL
	''', (block_id,)).fetchone()
	if not row or not row['total']:
		return False
	return row['checked'] == row['total']


def _spawn_cycle(conn, block_id, cycle_due_date, et_now, expected_boundary=None):
	"""Archive current active items + spawn fresh instances with the new due_date.

	Idempotent at the cycle boundary because last_reset_at is bumped after spawn —
	subsequent autoclear passes the same day skip.

	Concurrency (autoclear path, expected_boundary supplied): the bump of
	last_reset_at runs FIRST as a conditional UPDATE — only the first concurrent
	caller's WHERE clause matches against committed state; subsequent callers
	see the bumped value and bail (rowcount=0). Fix for 2026-05-11 where two
	near-simultaneous /today/data requests each spawned a fresh daily cycle,
	leaving the first batch as never-checked orphans in history.

	Manual reset path (expected_boundary=None): always proceeds.

	Returns the count of spawned items (0 if claim lost or block had no structure)."""
	now_iso = et_now.strftime(_ET_FORMAT)
	if expected_boundary is not None:
		cur = conn.execute(
			'UPDATE blocks SET last_reset_at = ? '
			'WHERE id = ? AND (last_reset_at IS NULL OR last_reset_at < ?)',
			(now_iso, block_id, expected_boundary)
		)
		if cur.rowcount == 0:
			return 0
	structure = conn.execute('''
		SELECT text, "order", time_category_id FROM checklist_items
		WHERE block_id = ? AND archived_at IS NULL
		ORDER BY "order" ASC, id ASC
	''', (block_id,)).fetchall()
	if not structure:
		# Empty block — bump last_reset_at so we don't loop, return 0.
		# (Claim path already bumped it; redundant but harmless.)
		conn.execute('UPDATE blocks SET last_reset_at = ? WHERE id = ?', (now_iso, block_id))
		return 0
	conn.execute('''
		UPDATE checklist_items SET archived_at = ?
		WHERE block_id = ? AND archived_at IS NULL
	''', (now_iso, block_id))
	for row in structure:
		conn.execute('''
			INSERT INTO checklist_items (block_id, text, due_date, checked, today, "order", time_category_id)
			VALUES (?, ?, ?, 0, 0, ?, ?)
		''', (block_id, row['text'], cycle_due_date, row['order'], row['time_category_id']))
	if expected_boundary is None:
		conn.execute(
			'UPDATE blocks SET today = 0, last_reset_at = ? WHERE id = ?',
			(now_iso, block_id)
		)
	else:
		conn.execute('UPDATE blocks SET today = 0 WHERE id = ?', (block_id,))
	return len(structure)


today_bp = Blueprint('today', __name__)


def _today_autoclear(conn):
	"""Clear today flags on completed-and-old rows.

	Tasks: cleared when status='completed' AND completed_date < today's
	       4am ET cutoff.
	Items (Phase 2.2): cleared when checked=1 AND checked_at IS NOT NULL
	       AND checked_at < UTC(4am ET cutoff). Items with NULL
	       checked_at survive — we don't know when they were checked,
	       so we don't presume.
	Blocks (Phase 2.2): cleared when (a) the block has at least one
	       item, (b) every item is checked, AND (c) every item's
	       checked_at is non-null AND before the 4am cutoff. Empty
	       starred blocks persist (no surprise removal).
	"""
	eastern = pytz.timezone('US/Eastern')
	now_et = datetime.now(eastern)
	if now_et.hour < 4:
		cutoff_date = (now_et - timedelta(days=1)).strftime('%Y-%m-%d')
	else:
		cutoff_date = now_et.strftime('%Y-%m-%d')
	# Tasks compare against an ET-local string (their completed_date is also
	# stored as an ET-local ISO from et_now()). Items compare against UTC
	# (their checked_at is stored in UTC by the toggle handler).
	cutoff_et = f"{cutoff_date}T04:00:00"
	cutoff_utc_dt = eastern.localize(
		datetime.strptime(cutoff_et, '%Y-%m-%dT%H:%M:%S')
	).astimezone(pytz.UTC)
	cutoff_utc = cutoff_utc_dt.strftime(_UTC_FORMAT)

	conn.execute('''
		UPDATE tasks SET today = 0, today_segment_id = NULL
		WHERE today = 1
		  AND status = 'completed'
		  AND completed_date IS NOT NULL
		  AND completed_date < ?
	''', (cutoff_et,))
	conn.execute('''
		UPDATE checklist_items SET today = 0, today_segment_id = NULL
		WHERE today = 1
		  AND checked = 1
		  AND checked_at IS NOT NULL
		  AND checked_at < ?
	''', (cutoff_utc,))
	conn.execute('''
		UPDATE blocks SET today = 0, today_segment_id = NULL
		WHERE today = 1
		  AND id IN (
		    SELECT b.id FROM blocks b
		    WHERE b.today = 1
		      AND EXISTS (
		        SELECT 1 FROM checklist_items ci WHERE ci.block_id = b.id AND ci.archived_at IS NULL
		      )
		      AND NOT EXISTS (
		        SELECT 1 FROM checklist_items ci
		        WHERE ci.block_id = b.id AND ci.archived_at IS NULL AND ci.checked = 0
		      )
		      AND NOT EXISTS (
		        SELECT 1 FROM checklist_items ci
		        WHERE ci.block_id = b.id AND ci.archived_at IS NULL
		          AND ci.checked = 1
		          AND (ci.checked_at IS NULL OR ci.checked_at >= ?)
		      )
		  )
	''', (cutoff_utc,))
	# Tickets — clear today when status='closed' AND closed_date < cutoff.
	# Mirrors the task pattern (completed + completed_date). Closed tickets
	# from earlier today survive until 4am the next morning so Aaron can
	# review what landed today before they roll off the list.
	conn.execute('''
		UPDATE tickets SET today = 0, today_segment_id = NULL
		WHERE today = 1
		  AND status = 'closed'
		  AND closed_date IS NOT NULL
		  AND closed_date < ?
	''', (cutoff_et,))

	# Phase 2.4 — recurrence-spawn pass. For each recurring block whose cycle
	# boundary has passed since last_reset_at, archive the current cycle and
	# spawn fresh instances. last_reset_at is in ET-local format; cycle
	# boundaries are computed as ET-local strings that lex-compare cleanly.
	today_short = _WEEKDAY_SHORT[now_et.weekday()]

	# DAILY — fires every day in recurrence_days (or every day if NULL).
	daily_boundary = _et_today_4am_iso(now_et)
	daily_blocks = conn.execute(
		"SELECT id, recurrence_days, last_reset_at FROM blocks "
		"WHERE recurrence = 'daily'"
	).fetchall()
	for b in daily_blocks:
		days = b['recurrence_days']
		if days:
			allowed = {d.strip() for d in days.split(',') if d.strip()}
			if today_short not in allowed:
				continue
		if b['last_reset_at'] and b['last_reset_at'] >= daily_boundary:
			continue
		_spawn_cycle(conn, b['id'], cycle_due_date=now_et.strftime('%Y-%m-%d'),
		             et_now=now_et, expected_boundary=daily_boundary)

	# WEEKLY — fires Monday 4am ET, ONLY IF all current items are checked.
	if today_short == 'Mon' or now_et.hour >= 4:
		# Eligible to evaluate weekly fires (we're past this Monday's 4am OR
		# any later day in the week — the boundary check below filters).
		weekly_boundary = _et_this_monday_4am_iso(now_et)
		weekly_blocks = conn.execute(
			"SELECT id, recurrence_days, last_reset_at FROM blocks "
			"WHERE recurrence = 'weekly'"
		).fetchall()
		for b in weekly_blocks:
			if b['last_reset_at'] and b['last_reset_at'] >= weekly_boundary:
				continue
			if not _all_items_checked(conn, b['id']):
				continue
			target_day = (b['recurrence_days'] or 'Fri').split(',')[0].strip() or 'Fri'
			due = _next_weekday_iso(now_et, target_day)
			_spawn_cycle(conn, b['id'], cycle_due_date=due, et_now=now_et,
			             expected_boundary=weekly_boundary)

	# MONTHLY — fires 1st of month 4am ET, ONLY IF all current items are checked.
	monthly_boundary = _et_first_of_month_4am_iso(now_et)
	monthly_blocks = conn.execute(
		"SELECT id, recurrence_days, last_reset_at FROM blocks "
		"WHERE recurrence = 'monthly'"
	).fetchall()
	for b in monthly_blocks:
		if b['last_reset_at'] and b['last_reset_at'] >= monthly_boundary:
			continue
		if not _all_items_checked(conn, b['id']):
			continue
		target = (b['recurrence_days'] or '1').strip() or '1'
		due = _this_month_target_iso(now_et, target)
		_spawn_cycle(conn, b['id'], cycle_due_date=due, et_now=now_et,
		             expected_boundary=monthly_boundary)

	conn.commit()


_AUTOCLEAR_LAST_RUN_TS = 0.0
_AUTOCLEAR_THROTTLE_SEC = 60


def maybe_run_autoclear():
	"""Run _today_autoclear at most once per minute per worker process.

	Used by app.before_request so the daily/weekly/monthly recurrence cycle
	fires regardless of which page Aaron lands on after 4am ET. Originally
	the cycle only ran on /today/data hits, which meant skipping Today
	(e.g. going straight to a Command Deck project) left yesterday's
	checked items stuck at the top.

	Race-safe across PA workers because _spawn_cycle's claim-then-spawn
	makes duplicate fires a no-op (cur.rowcount==0 → bail)."""
	global _AUTOCLEAR_LAST_RUN_TS
	import time
	now = time.time()
	if now - _AUTOCLEAR_LAST_RUN_TS < _AUTOCLEAR_THROTTLE_SEC:
		return
	_AUTOCLEAR_LAST_RUN_TS = now
	conn = get_db()
	try:
		_today_autoclear(conn)
	finally:
		conn.close()


@today_bp.route('/today/')
@today_bp.route('/today')
def today_page():
	if not is_authenticated():
		return redirect(url_for('cockpit.login'))
	return render_template('today.html')


@today_bp.route('/today/count')
def today_count():
	"""Open today count — tasks + items + blocks combined for the global pill.
	Phase 2.2: blocks count too. A starred block contributes 1 regardless of
	how many items it has."""
	if not is_authenticated():
		return jsonify({'count': 0})
	conn = get_db()
	task_count = conn.execute(
		"SELECT COUNT(*) as cnt FROM tasks WHERE today = 1 AND status = 'open'"
	).fetchone()['cnt']
	item_count = conn.execute(
		"SELECT COUNT(*) as cnt FROM checklist_items WHERE today = 1 AND checked = 0 AND archived_at IS NULL"
	).fetchone()['cnt']
	block_count = conn.execute(
		"SELECT COUNT(*) as cnt FROM blocks WHERE today = 1"
	).fetchone()['cnt']
	ticket_count = conn.execute(
		"SELECT COUNT(*) as cnt FROM tickets WHERE today = 1 AND status != 'closed'"
	).fetchone()['cnt']
	conn.close()
	return jsonify({'count': task_count + item_count + block_count + ticket_count})


@today_bp.route('/today/data')
def today_data():
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 403
	conn = get_db()
	_today_autoclear(conn)

	# Today section — open: tasks (status='open') + items (checked=0).
	# All today queries JOIN through to the parent area (when the project
	# is a work_subproject) so the rendering surfaces can show area context
	# alongside project context.
	# Sort: due-dated rows first chronologically (earliest first), then undated
	# rows in their original order beneath. NULL-handling: `due_date IS NULL`
	# sorts FALSE (0) before TRUE (1), putting dated rows on top.
	today_tasks_open = conn.execute('''
		SELECT t.id, t.title, t.status, t.today, t.today_segment_id, t.today_order, t.project_id, t.due_date,
		       p.title AS project_title, p.slug AS project_slug,
		       parent.id AS area_id, parent.title AS area_title,
		       parent.area_color AS area_color
		FROM tasks t
		LEFT JOIN projects p      ON t.project_id = p.id
		LEFT JOIN projects parent ON p.parent_project_id = parent.id
		WHERE t.today = 1 AND t.status = 'open'
		ORDER BY t.today_order ASC, t.due_date IS NULL ASC, t.due_date ASC, t.id ASC
	''').fetchall()
	today_items_open = conn.execute('''
		SELECT ci.id, ci.text, ci.checked, ci.today, ci.today_segment_id, ci.today_order, ci.block_id, ci.due_date,
		       b.title AS block_title, b.project_id,
		       p.title AS project_title, p.slug AS project_slug,
		       parent.id AS area_id, parent.title AS area_title,
		       parent.area_color AS area_color
		FROM checklist_items ci
		JOIN blocks b             ON ci.block_id = b.id
		JOIN projects p           ON b.project_id = p.id
		LEFT JOIN projects parent ON p.parent_project_id = parent.id
		WHERE ci.today = 1 AND ci.checked = 0 AND ci.archived_at IS NULL
		ORDER BY ci.today_order ASC, ci.due_date IS NULL ASC, ci.due_date ASC, ci.id ASC
	''').fetchall()

	# Today section — done: completed tasks + checked items still flagged
	today_tasks_done = conn.execute('''
		SELECT t.id, t.title, t.status, t.today, t.today_segment_id, t.project_id,
		       p.title AS project_title, p.slug AS project_slug,
		       parent.id AS area_id, parent.title AS area_title,
		       parent.area_color AS area_color
		FROM tasks t
		LEFT JOIN projects p      ON t.project_id = p.id
		LEFT JOIN projects parent ON p.parent_project_id = parent.id
		WHERE t.today = 1 AND t.status = 'completed'
		ORDER BY t.completed_date DESC
	''').fetchall()
	today_items_done = conn.execute('''
		SELECT ci.id, ci.text, ci.checked, ci.today, ci.today_segment_id, ci.block_id,
		       b.title AS block_title, b.project_id,
		       p.title AS project_title, p.slug AS project_slug,
		       parent.id AS area_id, parent.title AS area_title,
		       parent.area_color AS area_color
		FROM checklist_items ci
		JOIN blocks b             ON ci.block_id = b.id
		JOIN projects p           ON b.project_id = p.id
		LEFT JOIN projects parent ON p.parent_project_id = parent.id
		WHERE ci.today = 1 AND ci.checked = 1 AND ci.archived_at IS NULL
		ORDER BY ci.id DESC
	''').fetchall()

	# Phase 2.2 — block rows. A block row carries title + project context +
	# a progress triple (total / checked / open). "Open" placement: blocks
	# with any unchecked items OR no items go in today_open; blocks with
	# every item checked go in today_done (post-completion limbo until
	# the autoclear pass on the next 4am rollover).
	today_blocks = conn.execute('''
		SELECT b.id, b.title, b.today, b.today_segment_id, b.today_order, b.project_id,
		       p.title AS project_title, p.slug AS project_slug,
		       parent.id AS area_id, parent.title AS area_title,
		       parent.area_color AS area_color,
		       (SELECT COUNT(*) FROM checklist_items ci WHERE ci.block_id = b.id AND ci.archived_at IS NULL) AS total_count,
		       (SELECT COUNT(*) FROM checklist_items ci WHERE ci.block_id = b.id AND ci.archived_at IS NULL AND ci.checked = 1) AS checked_count
		FROM blocks b
		JOIN projects p           ON b.project_id = p.id
		LEFT JOIN projects parent ON p.parent_project_id = parent.id
		WHERE b.today = 1 AND b.type = 'checklist'
		ORDER BY b.today_order ASC, b.id ASC
	''').fetchall()
	today_blocks_open = []
	today_blocks_done = []
	for row in today_blocks:
		d = dict(row)
		d['open_count'] = d['total_count'] - d['checked_count']
		# Empty starred blocks count as "open" (something to do — even if just
		# adding items). Done = at least one item exists AND all are checked.
		if d['total_count'] > 0 and d['open_count'] == 0:
			today_blocks_done.append(d)
		else:
			today_blocks_open.append(d)

	# Tickets — starred non-closed go in today_open; starred closed go in
	# today_done (post-resolution limbo until 4am autoclear). The slim panel
	# treats ticket rows as navigation-only (no inline complete button —
	# closing requires a resolution prompt).
	today_tickets_open = conn.execute('''
		SELECT t.id, t.ticket_number, t.title, t.status, t.priority, t.today, t.today_segment_id, t.today_order,
		       t.project_id, t.due_date, t.requested_date,
		       p.title AS project_title, p.slug AS project_slug,
		       parent.id AS area_id, parent.title AS area_title,
		       parent.area_color AS area_color,
		       cg.name AS customer_group_name,
		       c.name AS customer_name,
		       tt.name AS type_name, tt.color AS type_color
		FROM tickets t
		LEFT JOIN projects p             ON t.project_id = p.id
		LEFT JOIN projects parent        ON p.parent_project_id = parent.id
		LEFT JOIN customer_groups cg     ON t.customer_group_id = cg.id
		LEFT JOIN customers c            ON t.customer_id = c.id
		LEFT JOIN ticket_types tt        ON t.type_id = tt.id
		WHERE t.today = 1 AND t.status != 'closed'
		ORDER BY t.today_order ASC, t.due_date IS NULL ASC, t.due_date ASC,
		         (t.priority = 'urgent') DESC, t.updated DESC
	''').fetchall()
	today_tickets_done = conn.execute('''
		SELECT t.id, t.ticket_number, t.title, t.status, t.priority, t.today, t.today_segment_id, t.today_order,
		       t.project_id, t.closed_date,
		       p.title AS project_title, p.slug AS project_slug,
		       parent.id AS area_id, parent.title AS area_title,
		       parent.area_color AS area_color,
		       cg.name AS customer_group_name,
		       c.name AS customer_name,
		       tt.name AS type_name, tt.color AS type_color
		FROM tickets t
		LEFT JOIN projects p             ON t.project_id = p.id
		LEFT JOIN projects parent        ON p.parent_project_id = parent.id
		LEFT JOIN customer_groups cg     ON t.customer_group_id = cg.id
		LEFT JOIN customers c            ON t.customer_id = c.id
		LEFT JOIN ticket_types tt        ON t.type_id = tt.id
		WHERE t.today = 1 AND t.status = 'closed'
		ORDER BY t.closed_date DESC
	''').fetchall()

	# All non-closed tickets (browseable list for the master picker on /today/)
	# — top-level group like Below Deck, sorted urgent-first then recency.
	tickets_browse = conn.execute('''
		SELECT t.id, t.ticket_number, t.title, t.status, t.priority, t.today, t.today_segment_id, t.today_order,
		       t.project_id, t.due_date, t.requested_date,
		       p.title AS project_title, p.slug AS project_slug,
		       parent.title AS area_title,
		       parent.area_color AS area_color,
		       cg.name AS customer_group_name,
		       c.name AS customer_name,
		       tt.name AS type_name, tt.color AS type_color
		FROM tickets t
		LEFT JOIN projects p             ON t.project_id = p.id
		LEFT JOIN projects parent        ON p.parent_project_id = parent.id
		LEFT JOIN customer_groups cg     ON t.customer_group_id = cg.id
		LEFT JOIN customers c            ON t.customer_id = c.id
		LEFT JOIN ticket_types tt        ON t.type_id = tt.id
		WHERE t.status != 'closed'
		ORDER BY t.due_date IS NULL ASC, t.due_date ASC,
		         (t.priority = 'urgent') DESC, t.updated DESC
	''').fetchall()

	# Master browse — Below Deck (project_id NULL) +
	# per-area groups for work sub-projects + Personal group.
	# Each project carries tasks + checklist blocks (with open items).
	below_deck_tasks = conn.execute('''
		SELECT id, title, status, today, project_id, due_date
		FROM tasks
		WHERE project_id IS NULL AND status = 'open'
		ORDER BY due_date IS NULL ASC, due_date ASC, "order" ASC, id ASC
	''').fetchall()
	all_projects = conn.execute('''
		SELECT p.id, p.title, p.slug, p.project_type, p.parent_project_id,
		       parent.title AS area_title, parent.slug AS area_slug,
		       parent.area_color AS area_color
		FROM projects p
		LEFT JOIN projects parent ON p.parent_project_id = parent.id
		WHERE p.project_type IN ('personal', 'work_subproject')
		ORDER BY parent.title ASC, p.title ASC
	''').fetchall()

	def _project_payload(proj):
		tasks = conn.execute('''
			SELECT id, title, status, today, project_id, due_date
			FROM tasks
			WHERE project_id = ? AND status = 'open'
			ORDER BY due_date IS NULL ASC, due_date ASC, "order" ASC, id ASC
		''', (proj['id'],)).fetchall()
		blocks_raw = conn.execute('''
			SELECT b.id, b.title, b.today,
			       (SELECT COUNT(*) FROM checklist_items ci WHERE ci.block_id = b.id AND ci.archived_at IS NULL) AS total_count,
			       (SELECT COUNT(*) FROM checklist_items ci WHERE ci.block_id = b.id AND ci.archived_at IS NULL AND ci.checked = 1) AS checked_count
			FROM blocks b
			WHERE b.project_id = ? AND b.type = 'checklist'
			ORDER BY b.id ASC
		''', (proj['id'],)).fetchall()
		blocks_with_items = []
		for b in blocks_raw:
			b_dict = dict(b)
			b_dict['open_count'] = b_dict['total_count'] - b_dict['checked_count']
			open_items = conn.execute('''
				SELECT id, text, checked, today, block_id, due_date
				FROM checklist_items
				WHERE block_id = ? AND checked = 0 AND archived_at IS NULL
				ORDER BY due_date IS NULL ASC, due_date ASC, "order" ASC, id ASC
			''', (b_dict['id'],)).fetchall()
			b_dict['open_items'] = [dict(i) for i in open_items]
			# Empty unstarred blocks excluded; starred blocks always shown
			# (consistent with autoclear rule that empty starred blocks
			# persist).
			if b_dict['open_items'] or b_dict['today']:
				blocks_with_items.append(b_dict)
		return tasks, blocks_with_items

	# Group sub-projects by their parent area; personal projects in their own bucket.
	area_groups_by_id = {}      # area_id → {area_title, area_color, area_slug, projects: []}
	personal_projects = []
	for proj in all_projects:
		tasks, blocks = _project_payload(proj)
		if not tasks and not blocks:
			continue
		entry = {
			'title': proj['title'],
			'slug': proj['slug'],
			'tasks': [dict(t) for t in tasks],
			'blocks': blocks,
		}
		if proj['project_type'] == 'work_subproject':
			aid = proj['parent_project_id']
			if aid not in area_groups_by_id:
				area_groups_by_id[aid] = {
					'area_id': aid,
					'area_title': proj['area_title'] or 'Work',
					'area_slug': proj['area_slug'],
					'area_color': proj['area_color'] or '',
					'projects': [],
				}
			area_groups_by_id[aid]['projects'].append(entry)
		else:
			personal_projects.append(entry)

	# Stable area order — alpha by title (mirrors the dashboard's area list).
	area_groups = sorted(
		area_groups_by_id.values(), key=lambda g: g['area_title']
	)

	# Day segments — persistent, user-defined parts of the day. Today-flagged
	# entities carry an optional today_segment_id; NULL = the Unassigned bucket.
	segments = conn.execute(
		'SELECT id, title, "order" FROM today_segments ORDER BY "order" ASC, id ASC'
	).fetchall()

	conn.close()

	def _serialize_task(row):
		d = dict(row)
		d['kind'] = 'task'
		return d

	def _serialize_item(row):
		d = dict(row)
		d['kind'] = 'item'
		return d

	def _serialize_block(d):
		# Already a dict (built above with computed fields)
		d = dict(d)
		d['kind'] = 'block'
		return d

	def _serialize_ticket(row):
		d = dict(row)
		d['kind'] = 'ticket'
		return d

	return jsonify({
		# Day segments — ordered list for the My Day view.
		'segments': [dict(s) for s in segments],
		# Mixed lists — kind='task' / 'item' / 'block' / 'ticket' on each entry.
		# Each carries area_title + area_color when under a sub-project.
		'today_open': (
			[_serialize_task(r) for r in today_tasks_open] +
			[_serialize_item(r) for r in today_items_open] +
			[_serialize_block(r) for r in today_blocks_open] +
			[_serialize_ticket(r) for r in today_tickets_open]
		),
		'today_done': (
			[_serialize_task(r) for r in today_tasks_done] +
			[_serialize_item(r) for r in today_items_done] +
			[_serialize_block(r) for r in today_blocks_done] +
			[_serialize_ticket(r) for r in today_tickets_done]
		),
		'below_deck': [dict(t) for t in below_deck_tasks],
		# Phase 2.2 — master browse grouped by parent area for sub-projects;
		# personal projects in their own bucket. Below Deck stays its own
		# top-level group above all of this.
		'area_groups': area_groups,
		'personal_projects': personal_projects,
		# Tickets — top-level browseable list of non-closed tickets, parallel
		# to below_deck. Surfaces in /today/ as its own panel with star buttons
		# so Aaron can pick which tickets he intends to work on today.
		'tickets_browse': [dict(t) for t in tickets_browse],
		# Backward-compat: legacy 'projects' field kept for any consumer
		# still expecting flat per-project shape. Equals area_groups
		# flattened + personal_projects appended.
		'projects': [
			p for ag in area_groups for p in ag['projects']
		] + personal_projects,
	})


@today_bp.route('/today/star', methods=['POST'])
def today_star():
	"""Toggle the today flag on a task / checklist item / checklist block / ticket.

	Phase 2.1: accepts task_id or item_id.
	Phase 2.2: also accepts block_id.
	Tickets: also accepts ticket_id. All four mutually exclusive.
	Form-encoded for parity with existing star UIs; fields picked up via
	request.form. 400 if zero or 2+ fields, 404 if not found."""
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 403

	task_id = request.form.get('task_id') or request.form.get('id')  # legacy fallback = task
	item_id = request.form.get('item_id')
	block_id = request.form.get('block_id')
	ticket_id = request.form.get('ticket_id')

	provided = [x for x in (task_id, item_id, block_id, ticket_id) if x]
	if len(provided) > 1:
		return jsonify({'error': 'one_of_task_item_block_or_ticket_only'}), 400
	if not provided:
		return jsonify({'error': 'task_id_or_item_id_or_block_id_or_ticket_id_required'}), 400

	conn = get_db()
	if task_id:
		row = conn.execute('SELECT id, today FROM tasks WHERE id = ?', (task_id,)).fetchone()
		if not row:
			conn.close()
			return jsonify({'error': 'not_found'}), 404
		new_today = 0 if row['today'] else 1
		conn.execute(
			'UPDATE tasks SET today = ?, '
			'today_segment_id = CASE WHEN ? = 0 THEN NULL ELSE today_segment_id END '
			'WHERE id = ?',
			(new_today, new_today, task_id)
		)
	elif item_id:
		row = conn.execute('SELECT id, today FROM checklist_items WHERE id = ?', (item_id,)).fetchone()
		if not row:
			conn.close()
			return jsonify({'error': 'not_found'}), 404
		new_today = 0 if row['today'] else 1
		conn.execute(
			'UPDATE checklist_items SET today = ?, '
			'today_segment_id = CASE WHEN ? = 0 THEN NULL ELSE today_segment_id END '
			'WHERE id = ?',
			(new_today, new_today, item_id)
		)
	elif block_id:
		row = conn.execute(
			"SELECT id, today, type FROM blocks WHERE id = ?", (block_id,)
		).fetchone()
		if not row:
			conn.close()
			return jsonify({'error': 'not_found'}), 404
		if row['type'] != 'checklist':
			conn.close()
			return jsonify({'error': 'block_not_checklist'}), 400
		new_today = 0 if row['today'] else 1
		conn.execute(
			'UPDATE blocks SET today = ?, '
			'today_segment_id = CASE WHEN ? = 0 THEN NULL ELSE today_segment_id END '
			'WHERE id = ?',
			(new_today, new_today, block_id)
		)
	else:
		# ticket_id
		row = conn.execute(
			'SELECT id, today FROM tickets WHERE id = ?', (ticket_id,)
		).fetchone()
		if not row:
			conn.close()
			return jsonify({'error': 'not_found'}), 404
		new_today = 0 if row['today'] else 1
		conn.execute(
			'UPDATE tickets SET today = ?, '
			'today_segment_id = CASE WHEN ? = 0 THEN NULL ELSE today_segment_id END '
			'WHERE id = ?',
			(new_today, new_today, ticket_id)
		)

	conn.commit()
	# Combined open count for the badge — tasks + items + blocks + tickets
	count = conn.execute(
		"SELECT (SELECT COUNT(*) FROM tasks WHERE today = 1 AND status = 'open') + "
		"       (SELECT COUNT(*) FROM checklist_items WHERE today = 1 AND checked = 0 AND archived_at IS NULL) + "
		"       (SELECT COUNT(*) FROM blocks WHERE today = 1) + "
		"       (SELECT COUNT(*) FROM tickets WHERE today = 1 AND status != 'closed') "
		"AS cnt"
	).fetchone()['cnt']
	conn.close()
	return jsonify({'success': True, 'today': new_today, 'count': count})


@today_bp.route('/today/complete', methods=['POST'])
def today_complete():
	"""Complete a task (sets status='completed'), or check a checklist item
	(sets checked=1). For items, the existing Phase 1.5 auto-stop hook will
	stop any timer scoped to the item — but that runs client-side via the
	'change' event on the checkbox. From this server-side path, we just
	set the state; the auto-stop is a separate code path on the project
	page when the user un/checks via the checkbox itself."""
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 403

	task_id = request.form.get('task_id') or request.form.get('id')  # legacy fallback
	item_id = request.form.get('item_id')

	if task_id and item_id:
		return jsonify({'error': 'task_or_item_not_both'}), 400
	if not task_id and not item_id:
		return jsonify({'error': 'task_id_or_item_id_required'}), 400

	conn = get_db()
	now = et_now()

	if task_id:
		task = conn.execute('SELECT * FROM tasks WHERE id = ?', (task_id,)).fetchone()
		if not task:
			conn.close()
			return jsonify({'error': 'not_found'}), 404
		conn.execute(
			"UPDATE tasks SET status = 'completed', completed_date = ? WHERE id = ?",
			(now, task_id)
		)
		if task['project_id']:
			conn.execute(
				'UPDATE projects SET updated = ? WHERE id = ?',
				(now, task['project_id'])
			)
	else:
		item = conn.execute('''
			SELECT ci.id, b.project_id
			FROM checklist_items ci
			JOIN blocks b ON ci.block_id = b.id
			WHERE ci.id = ?
		''', (item_id,)).fetchone()
		if not item:
			conn.close()
			return jsonify({'error': 'not_found'}), 404
		# Phase 2.2 — stamp checked_at parallel to the project-page toggle
		# handler so the autoclear precision works regardless of which
		# surface the item gets checked from.
		conn.execute(
			'UPDATE checklist_items SET checked = 1, checked_at = ? WHERE id = ?',
			(_utc_now_iso(), item_id)
		)
		conn.execute(
			'UPDATE projects SET updated = ? WHERE id = ?',
			(now, item['project_id'])
		)

	conn.commit()
	conn.close()
	return jsonify({'success': True})


# ---- Day segments — persistent "parts of my day" + task assignment ----

# kind → table whitelist for /today/assign. Table names are interpolated into
# SQL, so this dict is the trust boundary — never pass request input straight in.
_ASSIGN_TABLES = {
	'task': 'tasks',
	'item': 'checklist_items',
	'block': 'blocks',
	'ticket': 'tickets',
}


@today_bp.route('/today/segments', methods=['POST'])
def today_segment_create():
	"""Create a persistent day-segment. Appended to the end of the order."""
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 403
	title = (request.form.get('title') or '').strip()
	if not title:
		return jsonify({'error': 'title_required'}), 400
	conn = get_db()
	max_order = conn.execute(
		'SELECT COALESCE(MAX("order"), -1) FROM today_segments'
	).fetchone()[0]
	cur = conn.execute(
		'INSERT INTO today_segments (title, "order", created_at) VALUES (?, ?, ?)',
		(title, max_order + 1, et_now())
	)
	seg_id = cur.lastrowid
	conn.commit()
	conn.close()
	return jsonify({'success': True, 'id': seg_id, 'title': title})


@today_bp.route('/today/segments/<int:seg_id>/rename', methods=['POST'])
def today_segment_rename(seg_id):
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 403
	title = (request.form.get('title') or '').strip()
	if not title:
		return jsonify({'error': 'title_required'}), 400
	conn = get_db()
	row = conn.execute('SELECT id FROM today_segments WHERE id = ?', (seg_id,)).fetchone()
	if not row:
		conn.close()
		return jsonify({'error': 'not_found'}), 404
	conn.execute('UPDATE today_segments SET title = ? WHERE id = ?', (title, seg_id))
	conn.commit()
	conn.close()
	return jsonify({'success': True, 'id': seg_id, 'title': title})


@today_bp.route('/today/segments/<int:seg_id>/delete', methods=['POST'])
def today_segment_delete(seg_id):
	"""Delete a segment. Any entities assigned to it revert to Unassigned
	(today_segment_id = NULL) — they stay in Today, just lose their slot."""
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 403
	conn = get_db()
	row = conn.execute('SELECT id FROM today_segments WHERE id = ?', (seg_id,)).fetchone()
	if not row:
		conn.close()
		return jsonify({'error': 'not_found'}), 404
	for table in _ASSIGN_TABLES.values():
		conn.execute(
			f'UPDATE {table} SET today_segment_id = NULL WHERE today_segment_id = ?',
			(seg_id,)
		)
	conn.execute('DELETE FROM today_segments WHERE id = ?', (seg_id,))
	conn.commit()
	conn.close()
	return jsonify({'success': True})


@today_bp.route('/today/segments/reorder', methods=['POST'])
def today_segment_reorder():
	"""Persist a new segment order. Body: {order: [seg_id, ...]}."""
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 403
	data = request.get_json(silent=True) or {}
	order = data.get('order', [])
	conn = get_db()
	for i, sid in enumerate(order):
		conn.execute('UPDATE today_segments SET "order" = ? WHERE id = ?', (i, sid))
	conn.commit()
	conn.close()
	return jsonify({'success': True})


@today_bp.route('/today/assign', methods=['POST'])
def today_assign():
	"""Move a Today entity into a segment (or to Unassigned).

	Form fields: kind ('task'|'item'|'block'|'ticket'), id, segment_id.
	An empty/absent segment_id means Unassigned. Assigning into the day also
	sets today = 1 — dragging something from the picker straight into a segment
	both stars it for Today and slots it."""
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 403
	kind = request.form.get('kind')
	entity_id = request.form.get('id')
	segment_id = request.form.get('segment_id')  # '' / None => Unassigned
	table = _ASSIGN_TABLES.get(kind)
	if not table or not entity_id:
		return jsonify({'error': 'kind_and_id_required'}), 400
	conn = get_db()
	row = conn.execute(f'SELECT id FROM {table} WHERE id = ?', (entity_id,)).fetchone()
	if not row:
		conn.close()
		return jsonify({'error': 'not_found'}), 404
	seg_val = None
	if segment_id:
		seg = conn.execute(
			'SELECT id FROM today_segments WHERE id = ?', (segment_id,)
		).fetchone()
		if not seg:
			conn.close()
			return jsonify({'error': 'segment_not_found'}), 404
		seg_val = seg['id']
	# Append to the end of the destination segment (drag handles precise ordering).
	order_val = _next_today_order(conn, seg_val)
	conn.execute(
		f'UPDATE {table} SET today = 1, today_segment_id = ?, today_order = ? WHERE id = ?',
		(seg_val, order_val, entity_id)
	)
	conn.commit()
	conn.close()
	return jsonify({'success': True, 'today_segment_id': seg_val})


def _next_today_order(conn, seg_val):
	"""Max today_order across all four Today-citizen tables for a segment
	(seg_val=None → the Unassigned bucket), plus one. Used to append."""
	m = -1
	for t in _ASSIGN_TABLES.values():
		if seg_val is None:
			r = conn.execute(
				f'SELECT MAX(today_order) AS m FROM {t} WHERE today = 1 AND today_segment_id IS NULL'
			).fetchone()
		else:
			r = conn.execute(
				f'SELECT MAX(today_order) AS m FROM {t} WHERE today = 1 AND today_segment_id = ?',
				(seg_val,)
			).fetchone()
		if r and r['m'] is not None and r['m'] > m:
			m = r['m']
	return m + 1


@today_bp.route('/today/reorder', methods=['POST'])
def today_reorder():
	"""Persist the manual order of entities within a My Day segment.

	Body: {segment_id: <id|''|null>, order: [{kind, id}, ...]}. Sets each
	listed entity's today_segment_id to the target segment and today_order to
	its index — so a drag both re-slots (if it crossed segments) and reorders."""
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 403
	data = request.get_json(silent=True) or {}
	order = data.get('order', [])
	seg_raw = data.get('segment_id')
	conn = get_db()
	seg_val = None
	if seg_raw not in (None, '', 'null'):
		seg = conn.execute('SELECT id FROM today_segments WHERE id = ?', (seg_raw,)).fetchone()
		if not seg:
			conn.close()
			return jsonify({'error': 'segment_not_found'}), 404
		seg_val = seg['id']
	for i, item in enumerate(order):
		table = _ASSIGN_TABLES.get(item.get('kind'))
		eid = item.get('id')
		if not table or not eid:
			continue
		conn.execute(
			f'UPDATE {table} SET today = 1, today_segment_id = ?, today_order = ? WHERE id = ?',
			(seg_val, i, eid)
		)
	conn.commit()
	conn.close()
	return jsonify({'success': True})
