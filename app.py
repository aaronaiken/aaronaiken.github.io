from flask import Flask, request, render_template, make_response, redirect, url_for, jsonify
from werkzeug.utils import secure_filename
from PIL import Image
import os, subprocess, pytz, requests, emoji, glob, json, time, re
from datetime import datetime, timedelta
import sqlite3
import anthropic
import requests as req_lib
import uuid
from functools import wraps

# Load .env if python-dotenv is available. load_dotenv() never overrides
# already-set env vars, so it's safe alongside whatever PA uses to populate them.
try:
	from dotenv import load_dotenv
	load_dotenv()
except ImportError:
	pass

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY')
PASSWORD = os.environ.get('FLASK_PASSWORD')

UPLOAD_FOLDER = os.environ.get('COCKPIT_UPLOAD_FOLDER', '/home/aaronaiken/status_update/assets/img/status/')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

TASKS_FILE = 'assets/data/tasks.json'
SCRATCH_FILE = 'assets/data/scratch.json'
BELOW_DECK_FILE = 'assets/data/below_deck.json'
ANI_CONVERSATION_FILE = 'ani_conversation.json'
ANI_MEMORY_FILE = 'static/ani_memory.txt'
REPO_ROOT = os.environ.get('COCKPIT_REPO_ROOT', '/home/aaronaiken/status_update')

DB_FILE           = os.path.join(REPO_ROOT, 'assets/data/command_deck.db')
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
BUNNY_STORAGE_ZONE = os.environ.get('BUNNY_STORAGE_ZONE')
BUNNY_API_KEY      = os.environ.get('BUNNY_API_KEY')
BUNNY_CDN_URL      = os.environ.get('BUNNY_CDN_URL', '').rstrip('/')

BUNNY_STATUS_STORAGE_ZONE = os.environ.get('BUNNY_STATUS_STORAGE_ZONE')
BUNNY_STATUS_API_KEY      = os.environ.get('BUNNY_STATUS_API_KEY')
BUNNY_STATUS_CDN_URL      = os.environ.get('BUNNY_STATUS_CDN_URL', '').rstrip('/')

SCRATCH_WORK_FILE        = 'assets/data/scratch_work.json'
AFTER_DARK_COMMS_FILE    = 'static/after_dark_comms.txt'

WORK_MODE_PIN            = os.environ.get('WORK_MODE_PIN', '')
AFTER_DARK_PIN           = os.environ.get('AFTER_DARK_PIN', '')
BRRR_WEBHOOK_URL         = os.environ.get('BRRR_WEBHOOK_URL', '')

BUNNY_AD_STORAGE_ZONE    = os.environ.get('BUNNY_AFTER_DARK_STORAGE_ZONE', '')
BUNNY_AD_API_KEY         = os.environ.get('BUNNY_AFTER_DARK_API_KEY', '')
BUNNY_AD_CDN_URL         = os.environ.get('BUNNY_AFTER_DARK_CDN_URL', '').rstrip('/')


PRIVATE_PROJECTS_PIN = os.environ.get('PRIVATE_PROJECTS_PIN', '')

ALLOWED_FILE_EXTENSIONS = {
	'jpg', 'jpeg', 'png', 'gif', 'webp',
	'pdf', 'txt', 'md',
	'doc', 'docx', 'xls', 'xlsx',
	'zip', 'mp4', 'mov'
}
MAX_FILE_SIZE_MB = 25

# ---- COMMS CACHE ----
_comms_cache = {'data': None, 'timestamp': 0}
COMMS_CACHE_TTL = 300  # 5 minutes


# ---- AUTH ---- (moved to helpers/auth.py)

from helpers.auth import is_authenticated, cd_auth_required
from helpers.git import get_git_status, perform_git_ops


# ---- COMMS HELPERS ---- (moved to helpers/comms.py)

from helpers.comms import get_active_tags, get_valid_comms, get_after_dark_comms


from helpers.scratch import load_scratch_work, save_scratch_work


from helpers.omg_lol import post_to_omg_lol


from helpers.bunny import (
	list_bunny_ad_folder,
	optimize_image,
	upload_status_image_to_bunny,
	_allowed_file,
	_upload_to_bunny,
)


# ---- TASKS HELPERS ---- (load/save to helpers/tasks_json.py; post_task_status stays for cockpit blueprint)

from helpers.tasks_json import load_tasks, save_tasks


# ---- ANI HELPERS ---- (moved to blueprints/ani.py)
from blueprints.ani import ani_notify_publish  # used by publish_status

# ---- TODAY ROUTES ---- (moved to blueprints/today.py)

# ---- COMMAND DECK HELPERS ---- (moved to helpers/db.py)

from helpers.db import get_db, slugify, unique_slug, et_now

# ---- EXISTING ROUTES ----

# ---- COCKPIT ROUTES ---- (moved to blueprints/cockpit.py)

# ---- TASKS ROUTES ----

# ---- TASKS ROUTES ---- (moved to blueprints/tasks.py, registered at app.py bottom)

# ---- SCRATCH ROUTES ----

# ---- BELOW DECK ROUTES ----

# ---- BELOW DECK ROUTES ---- (moved to blueprints/below_deck.py)

# ---- COMMAND DECK ROUTES ----

@app.route('/command-deck/verify-pin', methods=['POST'])
@cd_auth_required
def cd_verify_pin():
	pin = (request.get_json() or {}).get('pin', '')
	if pin == PRIVATE_PROJECTS_PIN and PRIVATE_PROJECTS_PIN:
		return jsonify({'success': True})
	return jsonify({'success': False}), 403

# --- Dashboard ---

@app.route('/command-deck/')
@app.route('/command-deck')
@cd_auth_required
def cd_dashboard():
	conn = get_db()

	# Today's Below Deck tasks (open, no project)
	bd_tasks = conn.execute('''
		SELECT * FROM tasks
		WHERE project_id IS NULL AND status = 'open'
		ORDER BY "order" ASC, id ASC
	''').fetchall()

	# All projects, most recently updated first
	projects = conn.execute('''
        SELECT p.*,
               (SELECT COUNT(*) FROM tasks t WHERE t.project_id = p.id AND t.status = 'open') AS open_task_count,
               (SELECT COUNT(*) FROM blocks b WHERE b.project_id = p.id) AS block_count
        FROM projects p
        ORDER BY p.updated DESC
    ''').fetchall()

	# Recent chat messages (last 3 — dashboard preview)
	recent_chat = conn.execute('''
		SELECT * FROM chat_messages
		WHERE project_id IS NULL
		ORDER BY id DESC LIMIT 3
	''').fetchall()

	today_count = conn.execute(
		"SELECT COUNT(*) as cnt FROM tasks WHERE today = 1 AND status = 'open'"
	).fetchone()['cnt']

	conn.close()

	return render_template(
		'command_deck_dashboard.html',
		bd_tasks=[dict(t) for t in bd_tasks],
		projects=[dict(p) for p in projects],
		recent_chat=[dict(m) for m in reversed(recent_chat)],
		private_projects_enabled=bool(PRIVATE_PROJECTS_PIN),
		today_count=today_count
	)


# --- Projects list ---

@app.route('/command-deck/projects/')
@app.route('/command-deck/projects')
@cd_auth_required
def cd_projects():
	conn = get_db()
	projects = conn.execute('''
		SELECT p.*,
			   (SELECT COUNT(*) FROM tasks t WHERE t.project_id = p.id AND t.status = 'open') AS open_task_count,
			   (SELECT COUNT(*) FROM blocks b WHERE b.project_id = p.id) AS block_count,
			   (SELECT COUNT(*) FROM files f WHERE f.project_id = p.id) AS file_count
		FROM projects p
		ORDER BY p.updated DESC
	''').fetchall()
	conn.close()
	return render_template('command_deck_projects.html', projects=[dict(p) for p in projects], private_projects_enabled=bool(PRIVATE_PROJECTS_PIN))


@app.route('/command-deck/projects/new', methods=['POST'])
@cd_auth_required
def cd_project_new():
	title = request.form.get('title', '').strip()
	description = request.form.get('description', '').strip() or None
	is_private = 1 if request.form.get('is_private') == '1' else 0

	if not title:
		return redirect(url_for('cd_projects'))

	conn = get_db()
	slug = unique_slug(title, conn)
	now = et_now()
	conn.execute('''
		INSERT INTO projects (title, slug, description, is_private, created, updated)
		VALUES (?, ?, ?, ?, ?, ?)
	''', (title, slug, description, is_private, now, now))
	conn.commit()
	conn.close()
	return redirect(url_for('cd_project', slug=slug))


# --- Individual project ---

@app.route('/command-deck/projects/<slug>/')
@app.route('/command-deck/projects/<slug>')
@cd_auth_required
def cd_project(slug):
	conn = get_db()

	project = conn.execute('SELECT * FROM projects WHERE slug = ?', (slug,)).fetchone()
	if not project:
		conn.close()
		return "Project not found", 404

	project = dict(project)

	blocks_raw = conn.execute('''
		SELECT * FROM blocks WHERE project_id = ? ORDER BY "order" ASC, id ASC
	''', (project['id'],)).fetchall()

	blocks = []
	for b in blocks_raw:
		block = dict(b)
		if block['type'] == 'checklist':
			items = conn.execute(
				'SELECT * FROM checklist_items WHERE block_id = ? ORDER BY id ASC',
				(block['id'],)
			).fetchall()
			block['items'] = [dict(i) for i in items]
		blocks.append(block)

	project_tasks = conn.execute('''
		SELECT * FROM tasks
		WHERE project_id = ? AND status = 'open'
		ORDER BY "order" ASC, id ASC
	''', (project['id'],)).fetchall()

	files = conn.execute(
		'SELECT * FROM files WHERE project_id = ? ORDER BY uploaded DESC',
		(project['id'],)
	).fetchall()

	# Huyang chat — last 50 messages for this project
	chat_history = conn.execute('''
		SELECT * FROM chat_messages
		WHERE project_id = ?
		ORDER BY id ASC
		LIMIT 50
	''', (project['id'],)).fetchall()

	conn.close()

	return render_template(
		'command_deck_project.html',
		project=project,
		blocks=blocks,
		project_tasks=[dict(t) for t in project_tasks],
		files=[dict(f) for f in files],
		chat_history=[dict(m) for m in chat_history]
	)


@app.route('/command-deck/projects/<slug>/update', methods=['POST'])
@cd_auth_required
def cd_project_update(slug):
	title = request.form.get('title', '').strip()
	description = request.form.get('description', '').strip() or None
	is_private = 1 if request.form.get('is_private') == '1' else 0

	if not title:
		return redirect(url_for('cd_project', slug=slug))

	conn = get_db()
	project = conn.execute('SELECT * FROM projects WHERE slug = ?', (slug,)).fetchone()
	if not project:
		conn.close()
		return "Not found", 404

	new_slug = unique_slug(title, conn, exclude_id=project['id'])
	conn.execute('''
		UPDATE projects SET title = ?, slug = ?, description = ?, is_private = ?, updated = ?
		WHERE id = ?
	''', (title, new_slug, description, is_private, et_now(), project['id']))
	conn.commit()
	conn.close()
	return redirect(url_for('cd_project', slug=new_slug))


@app.route('/command-deck/projects/<slug>/delete', methods=['POST'])
@cd_auth_required
def cd_project_delete(slug):
	conn = get_db()
	project = conn.execute('SELECT * FROM projects WHERE slug = ?', (slug,)).fetchone()
	if project:
		# Cascade deletes tasks, blocks, checklist_items, files, chat_messages
		# (enforced by ON DELETE CASCADE in schema)
		conn.execute('DELETE FROM projects WHERE id = ?', (project['id'],))
		conn.commit()
	conn.close()
	return redirect(url_for('cd_projects'))


# --- Blocks ---

@app.route('/command-deck/projects/<slug>/blocks/add', methods=['POST'])
@cd_auth_required
def cd_block_add(slug):
	block_type = request.form.get('type', 'note')
	if block_type not in ('note', 'checklist'):
		return jsonify({'error': 'invalid type'}), 400

	conn = get_db()
	project = conn.execute('SELECT * FROM projects WHERE slug = ?', (slug,)).fetchone()
	if not project:
		conn.close()
		return jsonify({'error': 'not found'}), 404

	max_order = conn.execute(
		'SELECT COALESCE(MAX("order"), -1) FROM blocks WHERE project_id = ?',
		(project['id'],)
	).fetchone()[0]

	cursor = conn.execute('''
		INSERT INTO blocks (project_id, type, content, "order", created)
		VALUES (?, ?, '', ?, ?)
	''', (project['id'], block_type, max_order + 1, et_now()))

	block_id = cursor.lastrowid
	block = dict(conn.execute('SELECT * FROM blocks WHERE id = ?', (block_id,)).fetchone())
	block['items'] = []

	conn.execute('UPDATE projects SET updated = ? WHERE id = ?', (et_now(), project['id']))
	conn.commit()
	conn.close()

	return jsonify({'success': True, 'block': block})


@app.route('/command-deck/projects/<slug>/blocks/<int:block_id>/update', methods=['POST'])
@cd_auth_required
def cd_block_update(slug, block_id):
	content = request.form.get('content', '')

	conn = get_db()
	project = conn.execute('SELECT * FROM projects WHERE slug = ?', (slug,)).fetchone()
	if not project:
		conn.close()
		return jsonify({'error': 'not found'}), 404

	conn.execute(
		'UPDATE blocks SET content = ? WHERE id = ? AND project_id = ?',
		(content, block_id, project['id'])
	)
	conn.execute('UPDATE projects SET updated = ? WHERE id = ?', (et_now(), project['id']))
	conn.commit()
	conn.close()

	return jsonify({'success': True})

@app.route('/command-deck/projects/<slug>/blocks/<int:block_id>/update-title', methods=['POST'])
@cd_auth_required
def cd_block_update_title(slug, block_id):
    title = request.form.get('title', '').strip() or None

    conn = get_db()
    project = conn.execute('SELECT * FROM projects WHERE slug = ?', (slug,)).fetchone()
    if not project:
        conn.close()
        return jsonify({'error': 'not found'}), 404

    conn.execute(
        'UPDATE blocks SET title = ? WHERE id = ? AND project_id = ?',
        (title, block_id, project['id'])
    )
    conn.execute('UPDATE projects SET updated = ? WHERE id = ?', (et_now(), project['id']))
    conn.commit()
    conn.close()

    return jsonify({'success': True, 'title': title})

@app.route('/command-deck/projects/<slug>/blocks/<int:block_id>/delete', methods=['POST'])
@cd_auth_required
def cd_block_delete(slug, block_id):
	conn = get_db()
	project = conn.execute('SELECT * FROM projects WHERE slug = ?', (slug,)).fetchone()
	if project:
		conn.execute(
			'DELETE FROM blocks WHERE id = ? AND project_id = ?',
			(block_id, project['id'])
		)
		conn.execute('UPDATE projects SET updated = ? WHERE id = ?', (et_now(), project['id']))
		conn.commit()
	conn.close()
	return jsonify({'success': True})


@app.route('/command-deck/projects/<slug>/blocks/reorder', methods=['POST'])
@cd_auth_required
def cd_blocks_reorder(slug):
	data = request.get_json()
	order = data.get('order', [])

	conn = get_db()
	project = conn.execute('SELECT * FROM projects WHERE slug = ?', (slug,)).fetchone()
	if not project:
		conn.close()
		return jsonify({'error': 'not found'}), 404

	for i, block_id in enumerate(order):
		conn.execute(
			'UPDATE blocks SET "order" = ? WHERE id = ? AND project_id = ?',
			(i, block_id, project['id'])
		)
	conn.execute('UPDATE projects SET updated = ? WHERE id = ?', (et_now(), project['id']))
	conn.commit()
	conn.close()

	return jsonify({'success': True})


# --- Checklist items ---

@app.route('/command-deck/projects/<slug>/checklist/<int:item_id>/toggle', methods=['POST'])
@cd_auth_required
def cd_checklist_toggle(slug, item_id):
	conn = get_db()
	item = conn.execute('SELECT * FROM checklist_items WHERE id = ?', (item_id,)).fetchone()
	if item:
		new_state = 0 if item['checked'] else 1
		conn.execute('UPDATE checklist_items SET checked = ? WHERE id = ?', (new_state, item_id))

		project = conn.execute('SELECT * FROM projects WHERE slug = ?', (slug,)).fetchone()
		if project:
			conn.execute('UPDATE projects SET updated = ? WHERE id = ?', (et_now(), project['id']))

		conn.commit()
		conn.close()
		return jsonify({'success': True, 'checked': bool(new_state)})

	conn.close()
	return jsonify({'error': 'not found'}), 404


@app.route('/command-deck/projects/<slug>/checklist/add', methods=['POST'])
@cd_auth_required
def cd_checklist_add(slug):
	block_id = request.form.get('block_id')
	text = request.form.get('text', '').strip()

	if not block_id or not text:
		return jsonify({'error': 'block_id and text required'}), 400

	conn = get_db()
	cursor = conn.execute(
		'INSERT INTO checklist_items (block_id, text, checked) VALUES (?, ?, 0)',
		(block_id, text)
	)
	item_id = cursor.lastrowid

	project = conn.execute('SELECT * FROM projects WHERE slug = ?', (slug,)).fetchone()
	if project:
		conn.execute('UPDATE projects SET updated = ? WHERE id = ?', (et_now(), project['id']))

	conn.commit()
	item = dict(conn.execute('SELECT * FROM checklist_items WHERE id = ?', (item_id,)).fetchone())
	conn.close()

	return jsonify({'success': True, 'item': item})


@app.route('/command-deck/projects/<slug>/checklist/<int:item_id>/delete', methods=['POST'])
@cd_auth_required
def cd_checklist_delete(slug, item_id):
	conn = get_db()
	conn.execute('DELETE FROM checklist_items WHERE id = ?', (item_id,))

	project = conn.execute('SELECT * FROM projects WHERE slug = ?', (slug,)).fetchone()
	if project:
		conn.execute('UPDATE projects SET updated = ? WHERE id = ?', (et_now(), project['id']))

	conn.commit()
	conn.close()
	return jsonify({'success': True})


# --- Project tasks ---

@app.route('/command-deck/projects/<slug>/tasks/add', methods=['POST'])
@cd_auth_required
def cd_project_task_add(slug):
	title = request.form.get('title', '').strip()
	if not title:
		return jsonify({'error': 'title required'}), 400

	conn = get_db()
	project = conn.execute('SELECT * FROM projects WHERE slug = ?', (slug,)).fetchone()
	if not project:
		conn.close()
		return jsonify({'error': 'not found'}), 404

	max_order = conn.execute(
		'SELECT COALESCE(MAX("order"), -1) FROM tasks WHERE project_id = ?',
		(project['id'],)
	).fetchone()[0]

	cursor = conn.execute('''
		INSERT INTO tasks (title, status, created, "order", project_id)
		VALUES (?, 'open', ?, ?, ?)
	''', (title, et_now(), max_order + 1, project['id']))

	task_id = cursor.lastrowid
	conn.execute('UPDATE projects SET updated = ? WHERE id = ?', (et_now(), project['id']))
	conn.commit()

	task = dict(conn.execute('SELECT * FROM tasks WHERE id = ?', (task_id,)).fetchone())
	conn.close()

	return jsonify({'success': True, 'task': task})


@app.route('/command-deck/projects/<slug>/tasks/<int:task_id>/complete', methods=['POST'])
@cd_auth_required
def cd_project_task_complete(slug, task_id):
	conn = get_db()
	project = conn.execute('SELECT * FROM projects WHERE slug = ?', (slug,)).fetchone()
	if not project:
		conn.close()
		return jsonify({'error': 'not found'}), 404

	conn.execute('''
		UPDATE tasks SET status = 'completed', completed_date = ?
		WHERE id = ? AND project_id = ?
	''', (et_now(), task_id, project['id']))
	conn.execute('UPDATE projects SET updated = ? WHERE id = ?', (et_now(), project['id']))
	conn.commit()
	conn.close()

	return jsonify({'success': True})


@app.route('/command-deck/projects/<slug>/tasks/<int:task_id>/delete', methods=['POST'])
@cd_auth_required
def cd_project_task_delete(slug, task_id):
	conn = get_db()
	project = conn.execute('SELECT * FROM projects WHERE slug = ?', (slug,)).fetchone()
	if project:
		conn.execute('DELETE FROM tasks WHERE id = ? AND project_id = ?', (task_id, project['id']))
		conn.execute('UPDATE projects SET updated = ? WHERE id = ?', (et_now(), project['id']))
		conn.commit()
	conn.close()
	return jsonify({'success': True})


# --- Promote Below Deck task to Project ---

@app.route('/command-deck/promote-task', methods=['POST'])
@cd_auth_required
def cd_promote_task():
	task_id     = request.form.get('task_id')
	project_title = request.form.get('project_title', '').strip()

	if not task_id or not project_title:
		return jsonify({'error': 'task_id and project_title required'}), 400

	conn = get_db()

	# Verify task exists and is a Below Deck task
	task = conn.execute(
		'SELECT * FROM tasks WHERE id = ? AND project_id IS NULL', (task_id,)
	).fetchone()
	if not task:
		conn.close()
		return jsonify({'error': 'task not found'}), 404

	# Create the project
	slug = unique_slug(project_title, conn)
	now = et_now()
	cursor = conn.execute('''
		INSERT INTO projects (title, slug, description, created, updated)
		VALUES (?, ?, NULL, ?, ?)
	''', (project_title, slug, now, now))
	project_id = cursor.lastrowid

	# Move the task into the project
	conn.execute(
		'UPDATE tasks SET project_id = ?, tag = NULL WHERE id = ?',
		(project_id, task_id)
	)
	conn.commit()
	conn.close()

	return jsonify({'success': True, 'slug': slug})


# --- File uploads (Bunny.net) --- (moved to helpers/bunny.py, imported above)

@app.route('/command-deck/projects/<slug>/upload', methods=['POST'])
@cd_auth_required
def cd_file_upload(slug):
	if 'file' not in request.files:
		return jsonify({'error': 'no file provided'}), 400

	file = request.files['file']
	if not file or file.filename == '':
		return jsonify({'error': 'empty filename'}), 400

	if not _allowed_file(file.filename):
		return jsonify({'error': 'file type not allowed'}), 400

	# Check file size
	file.seek(0, 2)
	size_mb = file.tell() / (1024 * 1024)
	file.seek(0)
	if size_mb > MAX_FILE_SIZE_MB:
		return jsonify({'error': f'file too large (max {MAX_FILE_SIZE_MB}MB)'}), 400

	conn = get_db()
	project = conn.execute('SELECT * FROM projects WHERE slug = ?', (slug,)).fetchone()
	if not project:
		conn.close()
		return jsonify({'error': 'project not found'}), 404

	ext = file.filename.rsplit('.', 1)[1].lower()
	original_name = file.filename
	unique_name = f"{project['slug']}/{uuid.uuid4().hex}.{ext}"

	# Resize images before upload
	is_image = ext in ('jpg', 'jpeg', 'png', 'gif', 'webp')
	content_type = file.content_type or 'application/octet-stream'

	try:
		if is_image:
			from PIL import Image
			import io
			img = Image.open(file)
			img.thumbnail((1200, 1200), Image.LANCZOS)
			buf = io.BytesIO()
			save_format = 'JPEG' if ext in ('jpg', 'jpeg') else ext.upper()
			if save_format == 'JPG':
				save_format = 'JPEG'
			img.save(buf, format=save_format, quality=85)
			buf.seek(0)
			cdn_url = _upload_to_bunny(buf, unique_name, content_type)
		else:
			cdn_url = _upload_to_bunny(file, unique_name, content_type)
	except Exception as e:
		conn.close()
		app.logger.error(f"Bunny upload error: {e}")
		return jsonify({'error': 'upload failed'}), 500

	cursor = conn.execute('''
		INSERT INTO files (project_id, filename, bunny_url, uploaded)
		VALUES (?, ?, ?, ?)
	''', (project['id'], original_name, cdn_url, et_now()))

	file_id = cursor.lastrowid
	conn.execute('UPDATE projects SET updated = ? WHERE id = ?', (et_now(), project['id']))
	conn.commit()

	file_record = dict(conn.execute('SELECT * FROM files WHERE id = ?', (file_id,)).fetchone())
	conn.close()

	return jsonify({'success': True, 'file': file_record})


@app.route('/command-deck/projects/<slug>/files/<int:file_id>/delete', methods=['POST'])
@cd_auth_required
def cd_file_delete(slug, file_id):
	conn = get_db()
	project = conn.execute('SELECT * FROM projects WHERE slug = ?', (slug,)).fetchone()
	if not project:
		conn.close()
		return jsonify({'error': 'not found'}), 404

	file_record = conn.execute(
		'SELECT * FROM files WHERE id = ? AND project_id = ?', (file_id, project['id'])
	).fetchone()

	if file_record:
		# Delete from Bunny
		filename = file_record['bunny_url'].replace(BUNNY_CDN_URL + '/', '')
		try:
			req_lib.delete(
                f"https://ny.storage.bunnycdn.com/{BUNNY_STORAGE_ZONE}/{filename}",
				headers={'AccessKey': BUNNY_API_KEY},
				timeout=15
			)
		except Exception as e:
			app.logger.error(f"Bunny delete error: {e}")
			# Continue — remove from DB regardless

		conn.execute('DELETE FROM files WHERE id = ?', (file_id,))
		conn.execute('UPDATE projects SET updated = ? WHERE id = ?', (et_now(), project['id']))
		conn.commit()

	conn.close()
	return jsonify({'success': True})


# --- Huyang chat ---

def _huyang_build_context(project=None):
	"""Build the system prompt for Huyang, optionally with project context."""
	base = (
		"You are Huyang, a precise and knowledgeable archivist embedded in a private personal "
		"operating system called the Command Deck. You assist one person — Aaron — with his "
		"projects, notes, and thinking. You are focused, accurate, and concise. You do not "
		"editorialize. You do not have a personality agenda. You read what is in front of you "
		"and answer questions about it carefully. If something is not in the provided context, "
		"say so plainly. You are not a general chatbot — you are the ship's archivist."
	)

	if not project:
		return base

	lines = [base, f"\n\nCURRENT PROJECT: {project['title']}"]
	if project.get('description'):
		lines.append(f"DESCRIPTION: {project['description']}")

	return '\n'.join(lines)


def _huyang_build_system_with_content(project, blocks, project_tasks, files):
	"""Full system prompt with all project content injected."""
	system = _huyang_build_context(project)

	note_sections = []
	checklist_sections = []

	for block in blocks:
		if block['type'] == 'note' and block.get('content'):
			note_sections.append(block['content'])
		elif block['type'] == 'checklist' and block.get('items'):
			items_text = '\n'.join(
				f"  [{'x' if i['checked'] else ' '}] {i['text']}"
				for i in block['items']
			)
			checklist_sections.append(items_text)

	if note_sections:
		system += '\n\nNOTES:\n' + '\n\n---\n\n'.join(note_sections)

	if checklist_sections:
		system += '\n\nCHECKLISTS:\n' + '\n\n'.join(checklist_sections)

	if project_tasks:
		task_lines = '\n'.join(f"  - {t['title']}" for t in project_tasks)
		system += f'\n\nOPEN TASKS:\n{task_lines}'

	if files:
		file_lines = '\n'.join(f"  - {f['filename']}" for f in files)
		system += f'\n\nATTACHED FILES:\n{file_lines}'

	return system


@app.route('/command-deck/chat', methods=['POST'])
@cd_auth_required
def cd_chat():
	data = request.get_json()
	message = (data.get('message') or '').strip()
	project_id = data.get('project_id')  # int or None

	if not message:
		return jsonify({'error': 'message required'}), 400

	if not ANTHROPIC_API_KEY:
		return jsonify({'error': 'Anthropic API key not configured'}), 500

	conn = get_db()

	# Build system prompt
	if project_id:
		project = conn.execute('SELECT * FROM projects WHERE id = ?', (project_id,)).fetchone()
		if project:
			project = dict(project)
			blocks_raw = conn.execute(
				'SELECT * FROM blocks WHERE project_id = ? ORDER BY "order" ASC', (project_id,)
			).fetchall()
			blocks = []
			for b in blocks_raw:
				block = dict(b)
				if block['type'] == 'checklist':
					items = conn.execute(
						'SELECT * FROM checklist_items WHERE block_id = ? ORDER BY id ASC',
						(block['id'],)
					).fetchall()
					block['items'] = [dict(i) for i in items]
				blocks.append(block)
			project_tasks = [
				dict(t) for t in conn.execute(
					'SELECT * FROM tasks WHERE project_id = ? AND status = "open"', (project_id,)
				).fetchall()
			]
			files = [
				dict(f) for f in conn.execute(
					'SELECT * FROM files WHERE project_id = ?', (project_id,)
				).fetchall()
			]
			system = _huyang_build_system_with_content(project, blocks, project_tasks, files)
		else:
			system = _huyang_build_context()
	else:
		system = _huyang_build_context()

	# Load last 50 messages for context
	history_rows = conn.execute('''
		SELECT role, content FROM chat_messages
		WHERE project_id IS ?
		ORDER BY id ASC
		LIMIT 50
	''', (project_id,)).fetchall()

	messages = [{'role': r['role'], 'content': r['content']} for r in history_rows]
	messages.append({'role': 'user', 'content': message})

	# Call Anthropic
	try:
		client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
		response = client.messages.create(
			model='claude-sonnet-4-5',
			max_tokens=1000,
			system=system,
			messages=messages
		)
		reply = response.content[0].text
	except Exception as e:
		app.logger.error(f"Huyang API error: {e}")
		conn.close()
		return jsonify({'error': 'Huyang is unavailable right now.'}), 500

	# Save both messages
	now = et_now()
	conn.execute(
		'INSERT INTO chat_messages (role, content, project_id, created) VALUES (?, ?, ?, ?)',
		('user', message, project_id, now)
	)
	conn.execute(
		'INSERT INTO chat_messages (role, content, project_id, created) VALUES (?, ?, ?, ?)',
		('assistant', reply, project_id, now)
	)
	conn.commit()
	conn.close()

	return jsonify({'success': True, 'reply': reply})


@app.route('/command-deck/chat/history')
@cd_auth_required
def cd_chat_history():
	project_id = request.args.get('project_id', type=int)  # None if not provided

	conn = get_db()
	rows = conn.execute('''
		SELECT * FROM chat_messages
		WHERE project_id IS ?
		ORDER BY id ASC
		LIMIT 50
	''', (project_id,)).fetchall()
	conn.close()

	return jsonify({'messages': [dict(r) for r in rows]})


@app.route('/command-deck/chat/clear', methods=['POST'])
@cd_auth_required
def cd_chat_clear():
	data = request.get_json() or {}
	project_id = data.get('project_id')  # None clears general chat

	conn = get_db()
	conn.execute('DELETE FROM chat_messages WHERE project_id IS ?', (project_id,))
	conn.commit()
	conn.close()

	return jsonify({'success': True})

# ---- BLUEPRINT REGISTRATION ----

from blueprints.tasks import tasks_bp
from blueprints.today import today_bp
from blueprints.below_deck import below_deck_bp
from blueprints.ani import ani_bp
from blueprints.cockpit import cockpit_bp
app.register_blueprint(tasks_bp)
app.register_blueprint(today_bp)
app.register_blueprint(below_deck_bp)
app.register_blueprint(ani_bp)
app.register_blueprint(cockpit_bp)


if __name__ == "__main__": app.run(debug=True)