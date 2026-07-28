"""Notebook blueprint — the cockpit's 48pages "side-door" client.

Owns the page store endpoints (mirroring the 48pages `/v1/*` contract) and the
`/notebook` fullscreen. This phase ships the page store + home-slip capture + a
minimal working fullscreen editor; the full INKWELL UI (iA-style inline render,
scraps, ROLL/FILE/TEAR, cabinet, live Below Deck on the right page) lands next phase.

Keep this module self-contained (its own template + static/notebook.{css,js}) so the
notebook can be lifted out later as the standalone 48pages product — the local
`helpers/notebook.py` store is a swappable placeholder, not a fork to maintain.
"""
import os
from flask import Blueprint, request, jsonify, render_template

from helpers.auth import is_authenticated
from helpers import notebook as nb

notebook_bp = Blueprint('notebook', __name__)

# Cache-bust the notebook bundle off the max mtime of its own static files, so a
# normal reload always fetches the latest (mirrors the cockpit's asset_v approach).
_NB_ASSETS = ('notebook.css', 'notebook.js', 'notebook-editor.js')


def _asset_v():
	static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static')
	mtimes = []
	for name in _NB_ASSETS:
		try:
			mtimes.append(int(os.path.getmtime(os.path.join(static_dir, name))))
		except OSError:
			pass
	return max(mtimes) if mtimes else 0


@notebook_bp.route('/notebook')
def notebook_home():
	"""The notebook fullscreen. Esc / ← COCKPIT returns to /publish."""
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 401
	data = nb.load_notebook()
	return render_template(
		'notebook.html',
		page=data['page'],
		last_modified=data['last_modified'],
		budget=nb.budget(data['page']),
		asset_v=_asset_v(),
	)


@notebook_bp.route('/notebook/page')
def notebook_page():
	"""GET the whole page buffer + budget. Mirrors 48pages GET /v1/page."""
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 401
	data = nb.load_notebook()
	return jsonify({
		'page': data['page'],
		'last_modified': data['last_modified'],
		'budget': nb.budget(data['page']),
	})


@notebook_bp.route('/notebook/page', methods=['POST'])
def notebook_page_save():
	"""Persist the whole page buffer (autosave from the fullscreen editor). If the editor
	sends its measured line_units (contentHeight/30), persist that as the authoritative
	budget too, so the app + every surface read one PG n/48 number."""
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 401
	d = request.get_json(silent=True) or {}
	lm = nb.save_page(d.get('content', ''), force=bool(d.get('force')), line_units=d.get('line_units'))
	return jsonify({'ok': True, 'last_modified': lm, 'budget': nb.budget(d.get('content', ''))})


@notebook_bp.route('/notebook/usage')
def notebook_usage():
	"""GET the authoritative PG n/48 (last measured + written by an editor). Mirrors GET
	/v1/usage. None until first measured."""
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 401
	return jsonify({'usage': nb.usage()})


@notebook_bp.route('/notebook/usage', methods=['POST'])
def notebook_usage_save():
	"""Persist a measured line-unit count (editor contentHeight/30). Mirrors PUT /v1/usage."""
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 401
	d = request.get_json(silent=True) or {}
	nb.save_usage(d.get('line_units'))
	return jsonify({'ok': True, 'usage': nb.usage()})


@notebook_bp.route('/notebook/tasks')
def notebook_tasks():
	"""GET the rolled task list: [{id, text, done, rolledAt}]. Mirrors GET /v1/tasks."""
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 401
	return jsonify({'tasks': nb.tasks_all()})


@notebook_bp.route('/notebook/tasks', methods=['POST'])
def notebook_task_create():
	"""Add a task directly (no page stub — that's the ROLL verb). Mirrors POST /v1/tasks."""
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 401
	d = request.get_json(silent=True) or {}
	task = nb.task_create(d.get('text', ''), bool(d.get('done')))
	return jsonify({'ok': task is not None, 'task': task})


@notebook_bp.route('/notebook/tasks/<task_id>/update', methods=['POST'])
def notebook_task_update(task_id):
	"""Edit a task — check done (send done=true) or rename. Mirrors PUT /v1/tasks/<id>.
	Pass the current text back (from the list)."""
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 401
	d = request.get_json(silent=True) or {}
	task = nb.task_update(task_id, d.get('text', ''), bool(d.get('done')))
	return jsonify({'ok': task is not None, 'task': task})


@notebook_bp.route('/notebook/tasks/<task_id>/delete', methods=['POST'])
def notebook_task_delete(task_id):
	"""Remove a task. Mirrors DELETE /v1/tasks/<id>."""
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 401
	return jsonify({'ok': nb.task_delete(task_id)})


def _verb_args():
	"""Shared: the current page + the exact scrap text from the editor, for a verb call."""
	d = request.get_json(silent=True) or {}
	return d, (d.get('page') or ''), (d.get('scrap') or '')


@notebook_bp.route('/notebook/roll', methods=['POST'])
def notebook_roll():
	"""ROLL a scrap → task list + `↑ rolled ·` stub. Returns {tasks, page} (feed page back)."""
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 401
	_d, page, scrap = _verb_args()
	res = nb.roll_scrap(page, scrap)
	return jsonify({'ok': res is not None, **(res or {})})


@notebook_bp.route('/notebook/file', methods=['POST'])
def notebook_file_verb():
	"""FILE a scrap → cabinet + `→ filed ·` stub. Returns {entry, page}. (FILE+KEEP with no
	stub is the separate /notebook/cabinet POST.)"""
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 401
	d, page, scrap = _verb_args()
	res = nb.file_scrap(page, scrap, d.get('tags', []), d.get('title'))
	return jsonify({'ok': res is not None, **(res or {})})


@notebook_bp.route('/notebook/tear', methods=['POST'])
def notebook_tear():
	"""TEAR a scrap → `✂ torn ·` stub (no copy). Returns {page} (feed it back to the editor)."""
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 401
	_d, page, scrap = _verb_args()
	res = nb.tear_scrap(page, scrap)
	return jsonify({'ok': res is not None, **(res or {})})


@notebook_bp.route('/notebook/slip', methods=['POST'])
def notebook_slip():
	"""Append a captured slip to the bottom of the page. Mirrors 48pages POST /v1/slip."""
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 401
	d = request.get_json(silent=True) or {}
	res = nb.append_slip(d.get('text', ''))
	return jsonify({'ok': True, **res})


@notebook_bp.route('/notebook/cabinet')
def notebook_cabinet():
	"""List filed scraps (+ tag counts). Mirrors 48pages GET /v1/cabinet?search=&tag=."""
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 401
	search = request.args.get('search', '').strip()
	tag = request.args.get('tag', '').strip().lower()
	return jsonify({
		'items': nb.cabinet_list(search, tag),
		'tags': nb.cabinet_tag_counts(),
	})


@notebook_bp.route('/notebook/cabinet', methods=['POST'])
def notebook_cabinet_file():
	"""File a scrap into the cabinet (copy). The page-side tear is done client-side."""
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 401
	d = request.get_json(silent=True) or {}
	item = nb.cabinet_file(d.get('title', ''), d.get('body_md', ''), d.get('tags', []))
	return jsonify({'ok': True, 'item': item})


@notebook_bp.route('/notebook/cabinet/<item_id>/delete', methods=['POST'])
def notebook_cabinet_delete(item_id):
	"""Shred a filed scrap. (The cockpit's local placeholder allows delete; the 48pages
	/v1 contract deliberately has no DELETE — tearing needs the notebook in hand.)"""
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 401
	return jsonify({'ok': nb.cabinet_delete(item_id)})


@notebook_bp.route('/notebook/cabinet/<item_id>/retag', methods=['POST'])
def notebook_cabinet_retag(item_id):
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 401
	d = request.get_json(silent=True) or {}
	item = nb.cabinet_retag(item_id, d.get('tags', []))
	return jsonify({'ok': item is not None, 'item': item})
