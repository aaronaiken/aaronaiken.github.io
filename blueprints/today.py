"""Today blueprint — daily focus master view + per-task/item star/complete + 4am ET auto-clear.

Phase 2.1 (.kt/spec-time-tracking-phase-2-1.md): checklist items are first-
class Today citizens alongside tasks. /today/star, /today/complete, and
/today/data all accept task_id OR item_id (mutually exclusive); the
auto-clear pass clears today=0 on checked items past 4am ET.
"""
from datetime import datetime, timedelta
import pytz
from flask import Blueprint, request, redirect, url_for, jsonify, render_template

from helpers.auth import is_authenticated
from helpers.db import get_db, et_now


today_bp = Blueprint('today', __name__)


def _today_autoclear(conn):
	"""Clear today flags on completed-and-old rows.

	Tasks: cleared when status='completed' AND completed_date < today's
	       4am ET cutoff.
	Items: cleared when checked=1, simply rolled off at every autoclear
	       pass past 4am. checklist_items has no checked_at column yet
	       (Phase 2.2 adds it for stricter timing) — for v1, accept the
	       sloppiness: an item checked at 11pm + starred at 11:55pm
	       would lose the star at 4am. Documented in spec §5.5.
	"""
	eastern = pytz.timezone('US/Eastern')
	now_et = datetime.now(eastern)
	if now_et.hour < 4:
		cutoff_date = (now_et - timedelta(days=1)).strftime('%Y-%m-%d')
	else:
		cutoff_date = now_et.strftime('%Y-%m-%d')
	cutoff = f"{cutoff_date}T04:00:00"

	conn.execute('''
		UPDATE tasks SET today = 0
		WHERE today = 1
		  AND status = 'completed'
		  AND completed_date IS NOT NULL
		  AND completed_date < ?
	''', (cutoff,))
	conn.execute('''
		UPDATE checklist_items SET today = 0
		WHERE today = 1 AND checked = 1
	''')
	conn.commit()


@today_bp.route('/today/')
@today_bp.route('/today')
def today_page():
	if not is_authenticated():
		return redirect(url_for('cockpit.login'))
	return render_template('today.html')


@today_bp.route('/today/count')
def today_count():
	"""Open today count — tasks + items combined for the global pill."""
	if not is_authenticated():
		return jsonify({'count': 0})
	conn = get_db()
	task_count = conn.execute(
		"SELECT COUNT(*) as cnt FROM tasks WHERE today = 1 AND status = 'open'"
	).fetchone()['cnt']
	item_count = conn.execute(
		"SELECT COUNT(*) as cnt FROM checklist_items WHERE today = 1 AND checked = 0"
	).fetchone()['cnt']
	conn.close()
	return jsonify({'count': task_count + item_count})


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

	# Master browse — Below Deck (project_id NULL) + per-project task lists
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
		if tasks:
			project_groups.append({
				'title': proj['title'],
				'slug': proj['slug'],
				'tasks': [dict(t) for t in tasks],
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

	return jsonify({
		# Mixed lists — kind='task' or kind='item' on each entry. Renderers
		# branch on kind to draw the right row shape.
		'today_open': (
			[_serialize_task(r) for r in today_tasks_open] +
			[_serialize_item(r) for r in today_items_open]
		),
		'today_done': (
			[_serialize_task(r) for r in today_tasks_done] +
			[_serialize_item(r) for r in today_items_done]
		),
		'below_deck': [dict(t) for t in below_deck_tasks],
		'projects': project_groups,
	})


@today_bp.route('/today/star', methods=['POST'])
def today_star():
	"""Toggle the today flag on a task OR a checklist item.

	Phase 2.1: accepts either task_id or item_id (mutually exclusive).
	Form-encoded for parity with the existing star UI; either field is
	picked up via request.form. 400 if neither field present, OR if both."""
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 403

	task_id = request.form.get('task_id') or request.form.get('id')  # legacy fallback
	item_id = request.form.get('item_id')

	if task_id and item_id:
		return jsonify({'error': 'task_or_item_not_both'}), 400
	if not task_id and not item_id:
		return jsonify({'error': 'task_id_or_item_id_required'}), 400

	conn = get_db()
	if task_id:
		row = conn.execute('SELECT id, today FROM tasks WHERE id = ?', (task_id,)).fetchone()
		if not row:
			conn.close()
			return jsonify({'error': 'not_found'}), 404
		new_today = 0 if row['today'] else 1
		conn.execute('UPDATE tasks SET today = ? WHERE id = ?', (new_today, task_id))
	else:
		row = conn.execute('SELECT id, today FROM checklist_items WHERE id = ?', (item_id,)).fetchone()
		if not row:
			conn.close()
			return jsonify({'error': 'not_found'}), 404
		new_today = 0 if row['today'] else 1
		conn.execute('UPDATE checklist_items SET today = ? WHERE id = ?', (new_today, item_id))

	conn.commit()
	# Combined open count for the badge
	count = conn.execute(
		"SELECT (SELECT COUNT(*) FROM tasks WHERE today = 1 AND status = 'open') + "
		"       (SELECT COUNT(*) FROM checklist_items WHERE today = 1 AND checked = 0) "
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
		conn.execute('UPDATE checklist_items SET checked = 1 WHERE id = ?', (item_id,))
		conn.execute(
			'UPDATE projects SET updated = ? WHERE id = ?',
			(now, item['project_id'])
		)

	conn.commit()
	conn.close()
	return jsonify({'success': True})
