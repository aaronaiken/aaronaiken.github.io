"""Command Deck blueprint — private project knowledge base + Huyang AI companion.

Routes: ~25 routes under /command-deck/* (dashboard, projects CRUD, blocks, checklists,
tasks, file uploads, Huyang chat).
Internal helpers: _huyang_build_context, _huyang_build_system_with_content.
PIN-gated for private projects via cd_auth_required decorator (in helpers/auth.py).
"""
import os
import io
import json
import re
import uuid
import logging
from datetime import datetime
import pytz
import anthropic
import requests as req_lib
from flask import (
	Blueprint, request, redirect, url_for, jsonify, render_template, make_response,
)
from werkzeug.utils import secure_filename

from helpers.auth import is_authenticated, cd_auth_required
from helpers.db import get_db, slugify, unique_slug, et_now, fetch_assign_picker_groups
from helpers.bunny import (
	_allowed_file, _upload_to_bunny,
	BUNNY_STORAGE_ZONE, BUNNY_API_KEY, BUNNY_CDN_URL,
)


logger = logging.getLogger(__name__)


# Module constants — read from env at import time.
PRIVATE_PROJECTS_PIN = os.environ.get('PRIVATE_PROJECTS_PIN', '')
ANTHROPIC_API_KEY    = os.environ.get('ANTHROPIC_API_KEY')

# File-upload size cap (MB) — used by /command-deck/projects/<slug>/upload.
MAX_FILE_SIZE_MB = 25


command_deck_bp = Blueprint('command_deck', __name__)


# ---- Project-query helpers (Phase 1 time-tracking) ----

def _fetch_work_areas(conn):
	"""Work areas with sub-project, open-task, and active-timer counts."""
	return conn.execute('''
		SELECT a.id, a.title, a.slug, a.description, a.area_color,
		       a.is_private, a.created, a.updated, a.is_favorite,
		       (SELECT COUNT(*) FROM projects sp
		        WHERE sp.parent_project_id = a.id
		          AND sp.project_type = 'work_subproject') AS subproject_count,
		       (SELECT COUNT(*) FROM tasks t
		        JOIN projects sp ON t.project_id = sp.id
		        WHERE sp.parent_project_id = a.id
		          AND t.status = 'open') AS open_task_count,
		       (SELECT COUNT(*) FROM time_entries te
		        JOIN projects sp ON te.project_id = sp.id
		        WHERE sp.parent_project_id = a.id
		          AND te.ended_at IS NULL) AS active_timer_count
		FROM projects a
		WHERE a.project_type = 'work_area'
		ORDER BY a.title ASC
	''').fetchall()


def _fetch_subprojects(conn, area_id=None, favorites_only=False):
	"""Sub-projects with parent area joined. Optional filters by area or favorite."""
	sql = '''
		SELECT sp.*,
		       parent.id         AS area_id,
		       parent.title      AS area_title,
		       parent.slug       AS area_slug,
		       parent.area_color AS area_color,
		       (SELECT COUNT(*) FROM tasks t WHERE t.project_id = sp.id AND t.status = 'open') AS open_task_count,
		       (SELECT COUNT(*) FROM blocks b WHERE b.project_id = sp.id) AS block_count,
		       (SELECT id FROM time_entries WHERE project_id = sp.id AND ended_at IS NULL LIMIT 1) AS active_timer_id
		FROM projects sp
		LEFT JOIN projects parent ON sp.parent_project_id = parent.id
		WHERE sp.project_type = 'work_subproject'
	'''
	args = []
	if area_id is not None:
		sql += ' AND sp.parent_project_id = ?'
		args.append(area_id)
	if favorites_only:
		sql += ' AND sp.is_favorite = 1'
	sql += ' ORDER BY sp.updated DESC'
	return conn.execute(sql, args).fetchall()


# ---- COMMAND DECK ROUTES ----

@command_deck_bp.route('/command-deck/verify-pin', methods=['POST'])
@cd_auth_required
def cd_verify_pin():
	pin = (request.get_json() or {}).get('pin', '')
	if pin == PRIVATE_PROJECTS_PIN and PRIVATE_PROJECTS_PIN:
		return jsonify({'success': True})
	return jsonify({'success': False}), 403

# --- Dashboard ---

@command_deck_bp.route('/command-deck/')
@command_deck_bp.route('/command-deck')
@cd_auth_required
def cd_dashboard():
	conn = get_db()

	# Today's Below Deck tasks (open, no project)
	bd_tasks = conn.execute('''
		SELECT * FROM tasks
		WHERE project_id IS NULL AND status = 'open'
		ORDER BY "order" ASC, id ASC
	''').fetchall()

	# Personal projects only — work areas + sub-projects flow through
	# work_areas / favorited_subprojects below. (§3.2 partitioning)
	projects = conn.execute('''
		SELECT p.*,
		       (SELECT COUNT(*) FROM tasks t WHERE t.project_id = p.id AND t.status = 'open') AS open_task_count,
		       (SELECT COUNT(*) FROM blocks b WHERE b.project_id = p.id) AS block_count,
		       (SELECT id FROM time_entries WHERE project_id = p.id AND ended_at IS NULL LIMIT 1) AS active_timer_id
		FROM projects p
		WHERE p.project_type = 'personal'
		ORDER BY p.updated DESC
	''').fetchall()

	work_areas = _fetch_work_areas(conn)
	favorited_subprojects = _fetch_subprojects(conn, favorites_only=True)
	# BD assign picker — same shape as standalone /below-deck so sub-projects
	# show up grouped under their area, not buried in a flat personal list.
	picker_groups = fetch_assign_picker_groups(conn)

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
		work_areas=[dict(a) for a in work_areas],
		favorited_subprojects=[dict(s) for s in favorited_subprojects],
		picker_groups=picker_groups,
		recent_chat=[dict(m) for m in reversed(recent_chat)],
		private_projects_enabled=bool(PRIVATE_PROJECTS_PIN),
		today_count=today_count
	)


# --- Projects list ---

@command_deck_bp.route('/command-deck/projects/')
@command_deck_bp.route('/command-deck/projects')
@cd_auth_required
def cd_projects():
	conn = get_db()
	projects = conn.execute('''
		SELECT p.*,
		       (SELECT COUNT(*) FROM tasks t WHERE t.project_id = p.id AND t.status = 'open') AS open_task_count,
		       (SELECT COUNT(*) FROM blocks b WHERE b.project_id = p.id) AS block_count,
		       (SELECT COUNT(*) FROM files f WHERE f.project_id = p.id) AS file_count,
		       (SELECT id FROM time_entries WHERE project_id = p.id AND ended_at IS NULL LIMIT 1) AS active_timer_id
		FROM projects p
		WHERE p.project_type = 'personal'
		ORDER BY p.updated DESC
	''').fetchall()
	work_areas = _fetch_work_areas(conn)
	subprojects = _fetch_subprojects(conn)
	conn.close()
	return render_template(
		'command_deck_projects.html',
		projects=[dict(p) for p in projects],
		work_areas=[dict(a) for a in work_areas],
		subprojects=[dict(s) for s in subprojects],
		private_projects_enabled=bool(PRIVATE_PROJECTS_PIN),
	)


@command_deck_bp.route('/command-deck/projects/new', methods=['POST'])
@cd_auth_required
def cd_project_new():
	title = request.form.get('title', '').strip()
	description = request.form.get('description', '').strip() or None
	is_private = 1 if request.form.get('is_private') == '1' else 0
	tracking_enabled = 1 if request.form.get('tracking_enabled') in ('1', 'true', 'on') else 0

	if not title:
		return redirect(url_for('command_deck.cd_projects'))

	conn = get_db()
	slug = unique_slug(title, conn)
	now = et_now()
	conn.execute('''
		INSERT INTO projects (title, slug, description, is_private,
		                      project_type, tracking_enabled, created, updated)
		VALUES (?, ?, ?, ?, 'personal', ?, ?, ?)
	''', (title, slug, description, is_private, tracking_enabled, now, now))
	conn.commit()
	conn.close()
	return redirect(url_for('command_deck.cd_project', slug=slug))


# --- Individual project ---

@command_deck_bp.route('/command-deck/projects/<slug>/')
@command_deck_bp.route('/command-deck/projects/<slug>')
@cd_auth_required
def cd_project(slug):
	conn = get_db()

	project = conn.execute('SELECT * FROM projects WHERE slug = ?', (slug,)).fetchone()
	if not project:
		conn.close()
		return "Project not found", 404

	project = dict(project)

	# Parent area (for breadcrumb + per-area styling on sub-projects)
	parent_area = None
	if project.get('project_type') == 'work_subproject' and project.get('parent_project_id'):
		parent_row = conn.execute(
			"SELECT id, title, slug, area_color FROM projects WHERE id = ?",
			(project['parent_project_id'],)
		).fetchone()
		if parent_row:
			parent_area = dict(parent_row)

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
		parent_area=parent_area,
		blocks=blocks,
		project_tasks=[dict(t) for t in project_tasks],
		files=[dict(f) for f in files],
		chat_history=[dict(m) for m in chat_history]
	)


@command_deck_bp.route('/command-deck/projects/<slug>/update', methods=['POST'])
@cd_auth_required
def cd_project_update(slug):
	title = request.form.get('title', '').strip()
	description = request.form.get('description', '').strip() or None
	is_private = 1 if request.form.get('is_private') == '1' else 0

	if not title:
		return redirect(url_for('command_deck.cd_project', slug=slug))

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
	return redirect(url_for('command_deck.cd_project', slug=new_slug))


@command_deck_bp.route('/command-deck/projects/<slug>/delete', methods=['POST'])
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
	return redirect(url_for('command_deck.cd_projects'))


@command_deck_bp.route('/command-deck/areas/<slug>/')
@command_deck_bp.route('/command-deck/areas/<slug>')
@cd_auth_required
def cd_area(slug):
	conn = get_db()
	area = conn.execute(
		"SELECT * FROM projects WHERE slug = ? AND project_type = 'work_area'",
		(slug,)
	).fetchone()
	if not area:
		conn.close()
		return "Area not found", 404
	area = dict(area)

	subprojects = [dict(s) for s in _fetch_subprojects(conn, area_id=area['id'])]

	chat_history = conn.execute('''
		SELECT * FROM chat_messages
		WHERE project_id = ?
		ORDER BY id ASC
		LIMIT 50
	''', (area['id'],)).fetchall()

	active_timer_count = conn.execute('''
		SELECT COUNT(*) AS cnt
		FROM time_entries te
		JOIN projects sp ON te.project_id = sp.id
		WHERE sp.parent_project_id = ? AND te.ended_at IS NULL
	''', (area['id'],)).fetchone()['cnt']

	# Lifetime time-entry count for the PennDOT mile-marker easter egg
	# (computed for all areas, harmless to over-fetch)
	lifetime_entry_count = conn.execute('''
		SELECT COUNT(*) AS cnt
		FROM time_entries te
		JOIN projects sp ON te.project_id = sp.id
		WHERE sp.parent_project_id = ?
	''', (area['id'],)).fetchone()['cnt']

	conn.close()
	return render_template(
		'command_deck_area.html',
		area=area,
		subprojects=subprojects,
		chat_history=[dict(m) for m in chat_history],
		active_timer_count=active_timer_count,
		lifetime_entry_count=lifetime_entry_count,
		private_projects_enabled=bool(PRIVATE_PROJECTS_PIN),
	)


@command_deck_bp.route('/command-deck/projects/<slug>/favorite', methods=['POST'])
@cd_auth_required
def cd_project_favorite(slug):
	conn = get_db()
	project = conn.execute('SELECT * FROM projects WHERE slug = ?', (slug,)).fetchone()
	if not project:
		conn.close()
		return jsonify({'error': 'not_found'}), 404
	new_state = 0 if project['is_favorite'] else 1
	conn.execute(
		'UPDATE projects SET is_favorite = ?, updated = ? WHERE id = ?',
		(new_state, et_now(), project['id'])
	)
	conn.commit()
	conn.close()
	return jsonify({'success': True, 'is_favorite': bool(new_state)})


@command_deck_bp.route('/command-deck/projects/<slug>/tracking', methods=['POST'])
@cd_auth_required
def cd_project_tracking(slug):
	conn = get_db()
	project = conn.execute('SELECT * FROM projects WHERE slug = ?', (slug,)).fetchone()
	if not project:
		conn.close()
		return jsonify({'error': 'not_found'}), 404
	# tracking_enabled only meaningful on work_subproject + personal (§2.1)
	if project['project_type'] not in ('work_subproject', 'personal'):
		conn.close()
		return jsonify({
			'error': 'project_not_trackable',
			'project_type': project['project_type'],
		}), 400
	new_state = 0 if project['tracking_enabled'] else 1
	conn.execute(
		'UPDATE projects SET tracking_enabled = ?, updated = ? WHERE id = ?',
		(new_state, et_now(), project['id'])
	)
	conn.commit()
	conn.close()
	return jsonify({'success': True, 'tracking_enabled': bool(new_state)})


@command_deck_bp.route('/command-deck/areas/<slug>/subprojects/new', methods=['POST'])
@cd_auth_required
def cd_area_subproject_new(slug):
	data = request.get_json(silent=True) or request.form
	title = (data.get('title') or '').strip()
	description = (data.get('description') or '').strip() or None
	tracking_enabled = 1 if data.get('tracking_enabled') in (True, '1', 1, 'true', 'True') else 0
	if not title:
		return jsonify({'error': 'title required'}), 400

	conn = get_db()
	area = conn.execute(
		"SELECT * FROM projects WHERE slug = ? AND project_type = 'work_area'",
		(slug,)
	).fetchone()
	if not area:
		conn.close()
		return jsonify({'error': 'area_not_found'}), 404

	new_slug = unique_slug(title, conn)
	now = et_now()
	cur = conn.execute('''
		INSERT INTO projects
			(title, slug, description, is_private,
			 project_type, parent_project_id, tracking_enabled,
			 is_favorite, area_color, created, updated)
		VALUES (?, ?, ?, 0, 'work_subproject', ?, ?, 0, NULL, ?, ?)
	''', (title, new_slug, description, area['id'], tracking_enabled, now, now))
	new_id = cur.lastrowid
	conn.commit()
	sp = conn.execute('SELECT * FROM projects WHERE id = ?', (new_id,)).fetchone()
	conn.close()
	return jsonify({
		'success': True,
		'subproject': {
			'id': sp['id'],
			'title': sp['title'],
			'slug': sp['slug'],
			'description': sp['description'],
			'parent_project_id': sp['parent_project_id'],
			'area_id': area['id'],
			'area_title': area['title'],
			'area_slug': area['slug'],
			'area_color': area['area_color'],
			'tracking_enabled': bool(sp['tracking_enabled']),
			'is_favorite': bool(sp['is_favorite']),
		}
	})


# --- Blocks ---

@command_deck_bp.route('/command-deck/projects/<slug>/blocks/add', methods=['POST'])
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


@command_deck_bp.route('/command-deck/projects/<slug>/blocks/<int:block_id>/update', methods=['POST'])
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

@command_deck_bp.route('/command-deck/projects/<slug>/blocks/<int:block_id>/update-title', methods=['POST'])
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

@command_deck_bp.route('/command-deck/projects/<slug>/blocks/<int:block_id>/delete', methods=['POST'])
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


@command_deck_bp.route('/command-deck/projects/<slug>/blocks/reorder', methods=['POST'])
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

@command_deck_bp.route('/command-deck/projects/<slug>/checklist/<int:item_id>/toggle', methods=['POST'])
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


@command_deck_bp.route('/command-deck/projects/<slug>/checklist/add', methods=['POST'])
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


@command_deck_bp.route('/command-deck/projects/<slug>/checklist/<int:item_id>/delete', methods=['POST'])
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

@command_deck_bp.route('/command-deck/projects/<slug>/tasks/add', methods=['POST'])
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


@command_deck_bp.route('/command-deck/projects/<slug>/tasks/<int:task_id>/complete', methods=['POST'])
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


@command_deck_bp.route('/command-deck/projects/<slug>/tasks/<int:task_id>/delete', methods=['POST'])
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

@command_deck_bp.route('/command-deck/promote-task', methods=['POST'])
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

@command_deck_bp.route('/command-deck/projects/<slug>/upload', methods=['POST'])
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
			img.thumbnail((1200, 1200), Image.Resampling.LANCZOS)
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
		logger.error(f"Bunny upload error: {e}")
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


@command_deck_bp.route('/command-deck/projects/<slug>/files/<int:file_id>/delete', methods=['POST'])
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
			logger.error(f"Bunny delete error: {e}")
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


def _huyang_load_project_content(conn, project_id):
	"""Blocks (with checklist items), open tasks, files for a single project."""
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
	project_tasks = [dict(t) for t in conn.execute(
		'SELECT * FROM tasks WHERE project_id = ? AND status = "open"', (project_id,)
	).fetchall()]
	files = [dict(f) for f in conn.execute(
		'SELECT * FROM files WHERE project_id = ?', (project_id,)
	).fetchall()]
	return blocks, project_tasks, files


def _huyang_load_area_content(conn, area_id):
	"""
	Aggregate blocks, open tasks, files across all (non-private) sub-projects
	under a work area. Used for area-scoped Huyang chat.
	"""
	sub_ids = [r['id'] for r in conn.execute(
		'SELECT id FROM projects WHERE parent_project_id = ? AND is_private = 0',
		(area_id,)
	).fetchall()]
	if not sub_ids:
		return [], [], []
	placeholders = ','.join('?' * len(sub_ids))
	blocks_raw = conn.execute(
		f'SELECT b.*, p.title AS project_title FROM blocks b '
		f'JOIN projects p ON b.project_id = p.id '
		f'WHERE b.project_id IN ({placeholders}) ORDER BY p.title, b."order"',
		sub_ids
	).fetchall()
	blocks = []
	for b in blocks_raw:
		bd = dict(b)
		if bd['type'] == 'checklist':
			items = conn.execute(
				'SELECT * FROM checklist_items WHERE block_id = ? ORDER BY id ASC',
				(bd['id'],)
			).fetchall()
			bd['items'] = [dict(i) for i in items]
		blocks.append(bd)
	project_tasks = [dict(t) for t in conn.execute(
		f'SELECT t.*, p.title AS project_title FROM tasks t '
		f'JOIN projects p ON t.project_id = p.id '
		f'WHERE t.project_id IN ({placeholders}) AND t.status = "open" ORDER BY p.title',
		sub_ids
	).fetchall()]
	files = [dict(f) for f in conn.execute(
		f'SELECT * FROM files WHERE project_id IN ({placeholders})',
		sub_ids
	).fetchall()]
	return blocks, project_tasks, files


def _huyang_search_work_content(query, k=5):
	"""
	Search work areas + sub-projects for keyword matches in titles, descriptions,
	note blocks, open task titles, and checklist items. Excludes private projects
	(per spec §9.4). Token-AND-ish ranking — more matched tokens = higher score;
	title hits weighted 2x.

	Returns up to k items with shape:
	  {breadcrumb, source_type, content_snippet, project_slug}
	"""
	tokens = [t.lower() for t in re.split(r'\s+', (query or '').strip()) if t and len(t) >= 2]
	if not tokens:
		return []

	def score(text):
		if not text:
			return 0
		tl = text.lower()
		return sum(1 for t in tokens if t in tl)

	def snippet(text, n=160):
		if not text:
			return ''
		tl = text.lower()
		hits = [tl.find(t) for t in tokens if t in tl]
		pos = min(hits) if hits else -1
		if pos == -1:
			return text[:n] + ('...' if len(text) > n else '')
		start = max(0, pos - n // 2)
		end = min(len(text), pos + n // 2)
		s = text[start:end].strip()
		if start > 0:
			s = '...' + s
		if end < len(text):
			s = s + '...'
		return s

	def crumb(area_title, project_title, ptype, source_type=None):
		"""area_title is the parent for sub-projects; the project's own title for areas."""
		if ptype == 'work_area':
			parts = [project_title]
		else:
			parts = [area_title, project_title]
		if source_type:
			parts.append(source_type)
		return ' > '.join(p for p in parts if p)

	conn = get_db()
	matches = []

	# 1. Work project titles + descriptions
	for row in conn.execute('''
		SELECT p.id, p.title, p.slug, p.description, p.project_type AS ptype,
		       parent.title AS area_title
		FROM projects p
		LEFT JOIN projects parent ON p.parent_project_id = parent.id
		WHERE p.project_type IN ('work_area', 'work_subproject')
		  AND p.is_private = 0
	''').fetchall():
		ts = score(row['title'])
		if ts > 0:
			matches.append({
				'breadcrumb': crumb(row['area_title'], row['title'], row['ptype']),
				'source_type': 'title',
				'content_snippet': row['title'],
				'project_slug': row['slug'],
				'score': ts * 2,
			})
		ds = score(row['description'])
		if ds > 0:
			matches.append({
				'breadcrumb': crumb(row['area_title'], row['title'], row['ptype'], 'description'),
				'source_type': 'description',
				'content_snippet': snippet(row['description']),
				'project_slug': row['slug'],
				'score': ds,
			})

	# 2. Note blocks
	for row in conn.execute('''
		SELECT b.content,
		       p.title AS project_title, p.slug AS project_slug,
		       p.project_type AS ptype,
		       parent.title AS area_title
		FROM blocks b
		JOIN projects p ON b.project_id = p.id
		LEFT JOIN projects parent ON p.parent_project_id = parent.id
		WHERE b.type = 'note'
		  AND p.project_type IN ('work_area', 'work_subproject')
		  AND p.is_private = 0
	''').fetchall():
		s = score(row['content'])
		if s > 0:
			matches.append({
				'breadcrumb': crumb(row['area_title'], row['project_title'], row['ptype'], 'note'),
				'source_type': 'note',
				'content_snippet': snippet(row['content']),
				'project_slug': row['project_slug'],
				'score': s,
			})

	# 3. Open task titles
	for row in conn.execute('''
		SELECT t.title AS task_title,
		       p.title AS project_title, p.slug AS project_slug,
		       p.project_type AS ptype,
		       parent.title AS area_title
		FROM tasks t
		JOIN projects p ON t.project_id = p.id
		LEFT JOIN projects parent ON p.parent_project_id = parent.id
		WHERE t.status = 'open'
		  AND p.project_type IN ('work_area', 'work_subproject')
		  AND p.is_private = 0
	''').fetchall():
		s = score(row['task_title'])
		if s > 0:
			matches.append({
				'breadcrumb': crumb(row['area_title'], row['project_title'], row['ptype'], 'task'),
				'source_type': 'task',
				'content_snippet': row['task_title'],
				'project_slug': row['project_slug'],
				'score': s,
			})

	# 4. Checklist items
	for row in conn.execute('''
		SELECT ci.text AS item_text,
		       p.title AS project_title, p.slug AS project_slug,
		       p.project_type AS ptype,
		       parent.title AS area_title
		FROM checklist_items ci
		JOIN blocks b ON ci.block_id = b.id
		JOIN projects p ON b.project_id = p.id
		LEFT JOIN projects parent ON p.parent_project_id = parent.id
		WHERE p.project_type IN ('work_area', 'work_subproject')
		  AND p.is_private = 0
	''').fetchall():
		s = score(row['item_text'])
		if s > 0:
			matches.append({
				'breadcrumb': crumb(row['area_title'], row['project_title'], row['ptype'], 'checklist'),
				'source_type': 'checklist',
				'content_snippet': row['item_text'],
				'project_slug': row['project_slug'],
				'score': s,
			})

	conn.close()
	matches.sort(key=lambda m: m['score'], reverse=True)
	return matches[:k]


def _huyang_build_search_work_system(matches):
	"""System prompt for search_work mode, with matched excerpts injected (§9.3)."""
	base = _huyang_build_context()
	preamble = (
		"\n\nThe user is searching across their work archive. Below are the "
		"relevant excerpts found. Cite the project breadcrumb when you reference "
		"content. If no excerpts match the question, say so plainly."
	)
	if not matches:
		return base + preamble + "\n\nSEARCH RESULTS: (none)"

	lines = [base + preamble, '', f"SEARCH RESULTS (top {len(matches)} matches across work projects):", '']
	for i, m in enumerate(matches, 1):
		lines.append(f"{i}. [{m['breadcrumb']}]")
		lines.append(f'   "{m["content_snippet"]}"')
		lines.append('')
	return '\n'.join(lines)


@command_deck_bp.route('/command-deck/chat', methods=['POST'])
@cd_auth_required
def cd_chat():
	data = request.get_json()
	message = (data.get('message') or '').strip()
	project_id = data.get('project_id')  # int or None
	mode = data.get('mode')  # 'search_work' (Phase 1), or absent/'general'/'project'

	if not message:
		return jsonify({'error': 'message required'}), 400

	if not ANTHROPIC_API_KEY:
		return jsonify({'error': 'Anthropic API key not configured'}), 500

	conn = get_db()
	persist_mode = None

	# Build system prompt — mode wins over project_id
	if mode == 'search_work':
		matches = _huyang_search_work_content(message, k=5)
		system = _huyang_build_search_work_system(matches)
		persist_mode = 'search_work'
		project_id = None  # search_work history is dashboard-bound
	elif project_id:
		project = conn.execute('SELECT * FROM projects WHERE id = ?', (project_id,)).fetchone()
		if project:
			project = dict(project)
			if project.get('project_type') == 'work_area':
				blocks, project_tasks, files = _huyang_load_area_content(conn, project['id'])
			else:
				blocks, project_tasks, files = _huyang_load_project_content(conn, project['id'])
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
		logger.error(f"Huyang API error: {e}")
		conn.close()
		return jsonify({'error': 'Huyang is unavailable right now.'}), 500

	# Save both messages — mode tags search_work turns (§0a.2 #5)
	now = et_now()
	conn.execute(
		'INSERT INTO chat_messages (role, content, project_id, created, mode) VALUES (?, ?, ?, ?, ?)',
		('user', message, project_id, now, persist_mode)
	)
	conn.execute(
		'INSERT INTO chat_messages (role, content, project_id, created, mode) VALUES (?, ?, ?, ?, ?)',
		('assistant', reply, project_id, now, persist_mode)
	)
	conn.commit()
	conn.close()

	return jsonify({'success': True, 'reply': reply})


@command_deck_bp.route('/command-deck/chat/history')
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


@command_deck_bp.route('/command-deck/chat/clear', methods=['POST'])
@cd_auth_required
def cd_chat_clear():
	data = request.get_json() or {}
	project_id = data.get('project_id')  # None clears general chat

	conn = get_db()
	conn.execute('DELETE FROM chat_messages WHERE project_id IS ?', (project_id,))
	conn.commit()
	conn.close()

	return jsonify({'success': True})

