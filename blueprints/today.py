"""Today blueprint — daily focus master view + per-task/item/block star/complete + 4am ET auto-clear.

Phase 2.1 (.kt/spec-time-tracking-phase-2-1.md): checklist items as Today
citizens. Phase 2.2 (.kt/spec-time-tracking-phase-2-2.md): blocks join the
party as their own peer rows; checklist_items.checked_at stamped on every
toggle drives a precise (vs sloppy) 4am autoclear cutoff.
"""
from datetime import datetime, timedelta
import pytz
from flask import Blueprint, request, redirect, url_for, jsonify, render_template

from helpers.auth import is_authenticated
from helpers.db import get_db, et_now


_UTC_FORMAT = '%Y-%m-%dT%H:%M:%S.%fZ'


def _utc_now_iso():
	return datetime.now(pytz.UTC).strftime(_UTC_FORMAT)


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
		UPDATE tasks SET today = 0
		WHERE today = 1
		  AND status = 'completed'
		  AND completed_date IS NOT NULL
		  AND completed_date < ?
	''', (cutoff_et,))
	conn.execute('''
		UPDATE checklist_items SET today = 0
		WHERE today = 1
		  AND checked = 1
		  AND checked_at IS NOT NULL
		  AND checked_at < ?
	''', (cutoff_utc,))
	conn.execute('''
		UPDATE blocks SET today = 0
		WHERE today = 1
		  AND id IN (
		    SELECT b.id FROM blocks b
		    WHERE b.today = 1
		      AND EXISTS (
		        SELECT 1 FROM checklist_items ci WHERE ci.block_id = b.id
		      )
		      AND NOT EXISTS (
		        SELECT 1 FROM checklist_items ci
		        WHERE ci.block_id = b.id AND ci.checked = 0
		      )
		      AND NOT EXISTS (
		        SELECT 1 FROM checklist_items ci
		        WHERE ci.block_id = b.id
		          AND ci.checked = 1
		          AND (ci.checked_at IS NULL OR ci.checked_at >= ?)
		      )
		  )
	''', (cutoff_utc,))
	conn.commit()


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
		"SELECT COUNT(*) as cnt FROM checklist_items WHERE today = 1 AND checked = 0"
	).fetchone()['cnt']
	block_count = conn.execute(
		"SELECT COUNT(*) as cnt FROM blocks WHERE today = 1"
	).fetchone()['cnt']
	conn.close()
	return jsonify({'count': task_count + item_count + block_count})


@today_bp.route('/today/data')
def today_data():
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 403
	conn = get_db()
	_today_autoclear(conn)

	# Today section — open: tasks (status='open') + items (checked=0)
	today_tasks_open = conn.execute('''
		SELECT t.id, t.title, t.status, t.today, t.project_id,
		       p.title AS project_title, p.slug AS project_slug
		FROM tasks t
		LEFT JOIN projects p ON t.project_id = p.id
		WHERE t.today = 1 AND t.status = 'open'
		ORDER BY t.id ASC
	''').fetchall()
	today_items_open = conn.execute('''
		SELECT ci.id, ci.text, ci.checked, ci.today, ci.block_id,
		       b.title AS block_title, b.project_id,
		       p.title AS project_title, p.slug AS project_slug
		FROM checklist_items ci
		JOIN blocks b ON ci.block_id = b.id
		JOIN projects p ON b.project_id = p.id
		WHERE ci.today = 1 AND ci.checked = 0
		ORDER BY ci.id ASC
	''').fetchall()

	# Today section — done: completed tasks + checked items still flagged
	today_tasks_done = conn.execute('''
		SELECT t.id, t.title, t.status, t.today, t.project_id,
		       p.title AS project_title, p.slug AS project_slug
		FROM tasks t
		LEFT JOIN projects p ON t.project_id = p.id
		WHERE t.today = 1 AND t.status = 'completed'
		ORDER BY t.completed_date DESC
	''').fetchall()
	today_items_done = conn.execute('''
		SELECT ci.id, ci.text, ci.checked, ci.today, ci.block_id,
		       b.title AS block_title, b.project_id,
		       p.title AS project_title, p.slug AS project_slug
		FROM checklist_items ci
		JOIN blocks b ON ci.block_id = b.id
		JOIN projects p ON b.project_id = p.id
		WHERE ci.today = 1 AND ci.checked = 1
		ORDER BY ci.id DESC
	''').fetchall()

	# Phase 2.2 — block rows. A block row carries title + project context +
	# a progress triple (total / checked / open). "Open" placement: blocks
	# with any unchecked items OR no items go in today_open; blocks with
	# every item checked go in today_done (post-completion limbo until
	# the autoclear pass on the next 4am rollover).
	today_blocks = conn.execute('''
		SELECT b.id, b.title, b.today, b.project_id,
		       p.title AS project_title, p.slug AS project_slug,
		       (SELECT COUNT(*) FROM checklist_items ci WHERE ci.block_id = b.id) AS total_count,
		       (SELECT COUNT(*) FROM checklist_items ci WHERE ci.block_id = b.id AND ci.checked = 1) AS checked_count
		FROM blocks b
		JOIN projects p ON b.project_id = p.id
		WHERE b.today = 1 AND b.type = 'checklist'
		ORDER BY b.id ASC
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

	# Master browse — Below Deck (project_id NULL) + per-project task lists
	# Phase 2.2 fix: each project group now also surfaces its checklist
	# blocks + open items so they can be starred from /today/ alongside
	# tasks. Items already-checked are excluded (no action to take).
	below_deck_tasks = conn.execute('''
		SELECT id, title, status, today, project_id
		FROM tasks
		WHERE project_id IS NULL AND status = 'open'
		ORDER BY "order" ASC, id ASC
	''').fetchall()
	projects = conn.execute(
		'SELECT id, title, slug FROM projects ORDER BY title ASC'
	).fetchall()
	project_groups = []
	for proj in projects:
		tasks = conn.execute('''
			SELECT id, title, status, today, project_id
			FROM tasks
			WHERE project_id = ? AND status = 'open'
			ORDER BY "order" ASC, id ASC
		''', (proj['id'],)).fetchall()
		# Phase 2.2 — per-project checklist blocks (open items only)
		blocks_raw = conn.execute('''
			SELECT b.id, b.title, b.today,
			       (SELECT COUNT(*) FROM checklist_items ci WHERE ci.block_id = b.id) AS total_count,
			       (SELECT COUNT(*) FROM checklist_items ci WHERE ci.block_id = b.id AND ci.checked = 1) AS checked_count
			FROM blocks b
			WHERE b.project_id = ? AND b.type = 'checklist'
			ORDER BY b.id ASC
		''', (proj['id'],)).fetchall()
		blocks_with_items = []
		for b in blocks_raw:
			b_dict = dict(b)
			b_dict['open_count'] = b_dict['total_count'] - b_dict['checked_count']
			open_items = conn.execute('''
				SELECT id, text, checked, today, block_id
				FROM checklist_items
				WHERE block_id = ? AND checked = 0
				ORDER BY id ASC
			''', (b_dict['id'],)).fetchall()
			b_dict['open_items'] = [dict(i) for i in open_items]
			# Surface only blocks with at least one open item OR an empty
			# starred block (the latter for symmetry with the autoclear
			# rule — empty starred blocks persist).
			if b_dict['open_items'] or b_dict['today']:
				blocks_with_items.append(b_dict)
		if tasks or blocks_with_items:
			project_groups.append({
				'title': proj['title'],
				'slug': proj['slug'],
				'tasks': [dict(t) for t in tasks],
				'blocks': blocks_with_items,
			})

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

	return jsonify({
		# Mixed lists — kind='task' / 'item' / 'block' on each entry.
		# Renderers branch on kind to draw the right row shape.
		'today_open': (
			[_serialize_task(r) for r in today_tasks_open] +
			[_serialize_item(r) for r in today_items_open] +
			[_serialize_block(r) for r in today_blocks_open]
		),
		'today_done': (
			[_serialize_task(r) for r in today_tasks_done] +
			[_serialize_item(r) for r in today_items_done] +
			[_serialize_block(r) for r in today_blocks_done]
		),
		'below_deck': [dict(t) for t in below_deck_tasks],
		'projects': project_groups,
	})


@today_bp.route('/today/star', methods=['POST'])
def today_star():
	"""Toggle the today flag on a task OR a checklist item OR a checklist block.

	Phase 2.1: accepts task_id or item_id.
	Phase 2.2: also accepts block_id. All three mutually exclusive.
	Form-encoded for parity with existing star UIs; fields picked up via
	request.form. 400 if zero or 2+ fields, 404 if not found."""
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 403

	task_id = request.form.get('task_id') or request.form.get('id')  # legacy fallback = task
	item_id = request.form.get('item_id')
	block_id = request.form.get('block_id')

	provided = [x for x in (task_id, item_id, block_id) if x]
	if len(provided) > 1:
		return jsonify({'error': 'one_of_task_item_or_block_only'}), 400
	if not provided:
		return jsonify({'error': 'task_id_or_item_id_or_block_id_required'}), 400

	conn = get_db()
	if task_id:
		row = conn.execute('SELECT id, today FROM tasks WHERE id = ?', (task_id,)).fetchone()
		if not row:
			conn.close()
			return jsonify({'error': 'not_found'}), 404
		new_today = 0 if row['today'] else 1
		conn.execute('UPDATE tasks SET today = ? WHERE id = ?', (new_today, task_id))
	elif item_id:
		row = conn.execute('SELECT id, today FROM checklist_items WHERE id = ?', (item_id,)).fetchone()
		if not row:
			conn.close()
			return jsonify({'error': 'not_found'}), 404
		new_today = 0 if row['today'] else 1
		conn.execute('UPDATE checklist_items SET today = ? WHERE id = ?', (new_today, item_id))
	else:
		# block_id
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
		conn.execute('UPDATE blocks SET today = ? WHERE id = ?', (new_today, block_id))

	conn.commit()
	# Combined open count for the badge — tasks + items + blocks
	count = conn.execute(
		"SELECT (SELECT COUNT(*) FROM tasks WHERE today = 1 AND status = 'open') + "
		"       (SELECT COUNT(*) FROM checklist_items WHERE today = 1 AND checked = 0) + "
		"       (SELECT COUNT(*) FROM blocks WHERE today = 1) "
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
