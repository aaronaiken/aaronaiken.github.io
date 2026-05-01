"""Below Deck blueprint — private task kneeboard. SQLite-backed, 4am ET auto-clear."""
from datetime import datetime, timedelta
import pytz
from flask import Blueprint, request, redirect, url_for, jsonify, render_template

from helpers.auth import is_authenticated
from helpers.db import get_db, et_now


below_deck_bp = Blueprint('below_deck', __name__)


@below_deck_bp.route('/below-deck')
def below_deck():
	if not is_authenticated():
		return redirect(url_for('login'))

	conn = get_db()

	# 4am ET auto-clear
	eastern = pytz.timezone('US/Eastern')
	now_et = datetime.now(eastern)
	if now_et.hour < 4:
		cutoff_date = (now_et - timedelta(days=1)).strftime('%Y-%m-%d')
	else:
		cutoff_date = now_et.strftime('%Y-%m-%d')
	cutoff = f"{cutoff_date}T04:00:00"

	conn.execute('''
		DELETE FROM tasks
		WHERE project_id IS NULL
		  AND status = 'completed'
		  AND completed_date IS NOT NULL
		  AND completed_date < ?
	''', (cutoff,))
	conn.commit()

	open_tasks = conn.execute('''
		SELECT * FROM tasks
		WHERE project_id IS NULL AND status = 'open'
		ORDER BY "order" ASC, id ASC
	''').fetchall()

	completed_tasks = conn.execute('''
		SELECT * FROM tasks
		WHERE project_id IS NULL AND status = 'completed'
		ORDER BY completed_date DESC
	''').fetchall()

	# Projects for the assign-to-project picker
	# Only show non-private projects (or all if PIN not configured)
	projects = conn.execute(
		"SELECT id, title FROM projects WHERE is_private = 0 OR is_private IS NULL ORDER BY title ASC"
	).fetchall()

	conn.close()

	return render_template(
		'below_deck.html',
		tasks=[dict(t) for t in open_tasks],
		completed_tasks=[dict(t) for t in completed_tasks],
		projects=[dict(p) for p in projects]
	)


@below_deck_bp.route('/below-deck/count')
def below_deck_count():
	if not is_authenticated():
		return jsonify({'count': 0})
	conn = get_db()
	row = conn.execute(
		'SELECT COUNT(*) as cnt FROM tasks WHERE project_id IS NULL AND status = "open"'
	).fetchone()
	conn.close()
	return jsonify({'count': row['cnt']})


@below_deck_bp.route('/below-deck/add', methods=['POST'])
def below_deck_add():
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 403

	title = request.form.get('title', '').strip()
	tag   = request.form.get('tag', '').strip() or None

	if not title:
		return jsonify({'error': 'title required'}), 400

	conn = get_db()
	max_order = conn.execute(
		'SELECT COALESCE(MAX("order"), -1) FROM tasks WHERE project_id IS NULL'
	).fetchone()[0]

	cursor = conn.execute('''
		INSERT INTO tasks (title, tag, status, created, "order", project_id)
		VALUES (?, ?, 'open', ?, ?, NULL)
	''', (title, tag, et_now(), max_order + 1))
	conn.commit()

	task_id = cursor.lastrowid
	task = dict(conn.execute('SELECT * FROM tasks WHERE id = ?', (task_id,)).fetchone())
	conn.close()

	return jsonify({'success': True, 'task': task})


@below_deck_bp.route('/below-deck/complete', methods=['POST'])
def below_deck_complete():
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 403

	task_id = request.form.get('id')
	if not task_id:
		return jsonify({'error': 'id required'}), 400

	conn = get_db()
	conn.execute('''
		UPDATE tasks SET status = 'completed', completed_date = ?
		WHERE id = ? AND project_id IS NULL
	''', (et_now(), task_id))
	conn.commit()
	conn.close()

	return jsonify({'success': True})


@below_deck_bp.route('/below-deck/delete', methods=['POST'])
def below_deck_delete():
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 403

	task_id = request.form.get('id')
	if not task_id:
		return jsonify({'error': 'id required'}), 400

	conn = get_db()
	conn.execute('DELETE FROM tasks WHERE id = ? AND project_id IS NULL', (task_id,))
	conn.commit()
	conn.close()

	return jsonify({'success': True})


@below_deck_bp.route('/below-deck/clear-completed', methods=['POST'])
def below_deck_clear_completed():
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 403

	conn = get_db()
	conn.execute("DELETE FROM tasks WHERE project_id IS NULL AND status = 'completed'")
	conn.commit()
	conn.close()

	return jsonify({'success': True})


@below_deck_bp.route('/below-deck/reorder', methods=['POST'])
def below_deck_reorder():
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 403

	data = request.get_json()
	order = data.get('order', [])

	conn = get_db()
	for i, task_id in enumerate(order):
		conn.execute(
			'UPDATE tasks SET "order" = ? WHERE id = ? AND project_id IS NULL',
			(i, task_id)
		)
	conn.commit()
	conn.close()

	return jsonify({'success': True})
