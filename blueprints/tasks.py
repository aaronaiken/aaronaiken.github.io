"""Tasks blueprint — public-tasks JSON CRUD + per-id Below Deck task ops.

Routes: /tasks/add, /tasks/complete, /tasks/delete (legacy public, JSON-backed)
        /tasks/<id>/edit, /tasks/<id>/assign (per-id, SQLite-backed)
"""
import os
import time
from datetime import datetime
import pytz
from flask import Blueprint, request, jsonify

from helpers.auth import is_authenticated
from helpers.db import get_db, et_now
from helpers.git import perform_git_ops
from helpers.tasks_json import load_tasks, save_tasks, TASKS_FILE
from helpers.omg_lol import post_to_omg_lol


tasks_bp = Blueprint('tasks', __name__)


def post_task_status(title):
	now = datetime.now(pytz.timezone('America/New_York'))
	fn = now.strftime("_status_updates/%Y-%m-%d-%H%M%S.markdown")
	text = f"📋 New task logged: {title} → [aaronaiken.me/tools/tasks/](https://aaronaiken.me/tools/tasks/)"
	fm = (
		f"---\ntitle: Status\ndate: {now.strftime('%Y-%m-%d %H:%M:%S %z')}\n"
		f"layout: status_update\nauthor: aaron\nsource: web\n---\n"
	)
	os.makedirs("_status_updates", exist_ok=True)
	with open(fn, "w") as f:
		f.write(fm + text + "\n")
	return fn, text


@tasks_bp.route("/tasks/add", methods=['POST'])
def tasks_add():
	if not is_authenticated():
		return jsonify({"error": "unauthorized"}), 401

	title = request.form.get('title', '').strip()
	if not title:
		return jsonify({"error": "title required"}), 400

	data = load_tasks()
	task = {
		"id": str(int(time.time())),
		"title": title,
		"status": "open",
		"created": datetime.now(pytz.timezone('America/New_York')).isoformat(),
		"completed": None
	}
	data['tasks'].insert(0, task)
	save_tasks(data)

	fn, status_text = post_task_status(title)
	perform_git_ops(fn)
	post_to_omg_lol(status_text)

	return jsonify({"ok": True, "task": task})


@tasks_bp.route("/tasks/complete", methods=['POST'])
def tasks_complete():
	if not is_authenticated():
		return jsonify({"error": "unauthorized"}), 401

	task_id = request.form.get('id', '').strip()
	if not task_id:
		return jsonify({"error": "id required"}), 400

	data = load_tasks()
	target = next((t for t in data['tasks'] if t['id'] == task_id), None)
	if not target:
		return jsonify({"error": "task not found"}), 404

	target['status'] = 'complete'
	target['completed'] = datetime.now(pytz.timezone('America/New_York')).isoformat()
	save_tasks(data)
	perform_git_ops(TASKS_FILE)

	return jsonify({"ok": True, "task": target})


@tasks_bp.route("/tasks/delete", methods=['POST'])
def tasks_delete():
	if not is_authenticated():
		return jsonify({"error": "unauthorized"}), 401

	task_id = request.form.get('id', '').strip()
	if not task_id:
		return jsonify({"error": "id required"}), 400

	data = load_tasks()
	before = len(data['tasks'])
	data['tasks'] = [t for t in data['tasks'] if t['id'] != task_id]
	if len(data['tasks']) == before:
		return jsonify({"error": "task not found"}), 404

	save_tasks(data)
	perform_git_ops(TASKS_FILE)

	return jsonify({"ok": True})


@tasks_bp.route('/tasks/<int:task_id>/edit', methods=['POST'])
def task_edit(task_id):
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 403
	title = request.form.get('title', '').strip()
	if not title:
		return jsonify({'error': 'title required'}), 400
	conn = get_db()
	conn.execute('UPDATE tasks SET title = ? WHERE id = ?', (title, task_id))
	conn.commit()
	task = conn.execute('SELECT * FROM tasks WHERE id = ?', (task_id,)).fetchone()
	conn.close()
	if not task:
		return jsonify({'error': 'not found'}), 404
	return jsonify({'success': True, 'task': dict(task)})


@tasks_bp.route('/tasks/<int:task_id>/assign', methods=['POST'])
def task_assign(task_id):
	"""Assign a Below Deck task to a project."""
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 403
	project_id = request.form.get('project_id')
	if not project_id:
		return jsonify({'error': 'project_id required'}), 400
	conn = get_db()
	# Verify task is a Below Deck task
	task = conn.execute(
		'SELECT * FROM tasks WHERE id = ? AND project_id IS NULL', (task_id,)
	).fetchone()
	if not task:
		conn.close()
		return jsonify({'error': 'task not found'}), 404
	# Verify project exists
	project = conn.execute('SELECT * FROM projects WHERE id = ?', (project_id,)).fetchone()
	if not project:
		conn.close()
		return jsonify({'error': 'project not found'}), 404
	# Move the task — clear tag since project provides context
	conn.execute(
		'UPDATE tasks SET project_id = ?, tag = NULL WHERE id = ?',
		(project_id, task_id)
	)
	conn.execute('UPDATE projects SET updated = ? WHERE id = ?', (et_now(), project_id))
	conn.commit()
	conn.close()
	return jsonify({'success': True})
