"""Today blueprint — daily focus master view + per-task star/complete + 4am ET auto-clear."""
from datetime import datetime, timedelta
import pytz
from flask import Blueprint, request, redirect, url_for, jsonify, render_template

from helpers.auth import is_authenticated
from helpers.db import get_db, et_now


today_bp = Blueprint('today', __name__)


def _today_autoclear(conn):
	"""Clear today flags on completed tasks before the 4am ET boundary."""
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
	conn.commit()


@today_bp.route('/today/')
@today_bp.route('/today')
def today_page():
	if not is_authenticated():
		return redirect(url_for('cockpit.login'))
	return render_template('today.html')


@today_bp.route('/today/count')
def today_count():
	if not is_authenticated():
		return jsonify({'count': 0})
	conn = get_db()
	row = conn.execute(
		"SELECT COUNT(*) as cnt FROM tasks WHERE today = 1 AND status = 'open'"
	).fetchone()
	conn.close()
	return jsonify({'count': row['cnt']})


@today_bp.route('/today/data')
def today_data():
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 403
	conn = get_db()
	_today_autoclear(conn)
	today_open = conn.execute('''
		SELECT t.id, t.title, t.status, t.today, t.project_id,
		       p.title as project_title, p.slug as project_slug
		FROM tasks t
		LEFT JOIN projects p ON t.project_id = p.id
		WHERE t.today = 1 AND t.status = 'open'
		ORDER BY t.id ASC
	''').fetchall()
	today_done = conn.execute('''
		SELECT t.id, t.title, t.status, t.today, t.project_id,
		       p.title as project_title, p.slug as project_slug
		FROM tasks t
		LEFT JOIN projects p ON t.project_id = p.id
		WHERE t.today = 1 AND t.status = 'completed'
		ORDER BY t.completed_date DESC
	''').fetchall()
	below_deck_tasks = conn.execute('''
		SELECT id, title, status, today, project_id
		FROM tasks
		WHERE project_id IS NULL AND status = 'open'
		ORDER BY "order" ASC, id ASC
	''').fetchall()
	projects = conn.execute(
		'SELECT id, title, slug FROM projects ORDER BY title ASC'
	).fetchall()
	project_tasks = {}
	for proj in projects:
		tasks = conn.execute('''
			SELECT id, title, status, today, project_id
			FROM tasks
			WHERE project_id = ? AND status = 'open'
			ORDER BY "order" ASC, id ASC
		''', (proj['id'],)).fetchall()
		if tasks:
			project_tasks[proj['id']] = {
				'title': proj['title'],
				'slug': proj['slug'],
				'tasks': [dict(t) for t in tasks]
			}
	conn.close()
	return jsonify({
		'today_open': [dict(t) for t in today_open],
		'today_done': [dict(t) for t in today_done],
		'below_deck': [dict(t) for t in below_deck_tasks],
		'projects': list(project_tasks.values())
	})


@today_bp.route('/today/star', methods=['POST'])
def today_star():
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 403
	task_id = request.form.get('id')
	if not task_id:
		return jsonify({'error': 'id required'}), 400
	conn = get_db()
	task = conn.execute('SELECT * FROM tasks WHERE id = ?', (task_id,)).fetchone()
	if not task:
		conn.close()
		return jsonify({'error': 'not found'}), 404
	new_today = 0 if task['today'] else 1
	conn.execute('UPDATE tasks SET today = ? WHERE id = ?', (new_today, task_id))
	conn.commit()
	count = conn.execute(
		"SELECT COUNT(*) as cnt FROM tasks WHERE today = 1 AND status = 'open'"
	).fetchone()['cnt']
	conn.close()
	return jsonify({'success': True, 'today': new_today, 'count': count})


@today_bp.route('/today/complete', methods=['POST'])
def today_complete():
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 403
	task_id = request.form.get('id')
	if not task_id:
		return jsonify({'error': 'id required'}), 400
	conn = get_db()
	task = conn.execute('SELECT * FROM tasks WHERE id = ?', (task_id,)).fetchone()
	if not task:
		conn.close()
		return jsonify({'error': 'not found'}), 404
	now = et_now()
	conn.execute(
		"UPDATE tasks SET status = 'completed', completed_date = ? WHERE id = ?",
		(now, task_id)
	)
	if task['project_id']:
		conn.execute(
			'UPDATE projects SET updated = ? WHERE id = ?',
			(now, task['project_id'])
		)
	conn.commit()
	conn.close()
	return jsonify({'success': True})
