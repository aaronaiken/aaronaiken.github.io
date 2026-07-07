"""Cockpit blueprint — publishing flow + auth + scratch + mode + focus timer + after-dark media."""
import os
import io
import re
import base64
import glob
import json
import random
import logging
from datetime import datetime
import pytz
from PIL import Image, ImageOps
import requests as req_lib
from flask import (
	Blueprint, request, redirect, url_for, jsonify, render_template, make_response, flash,
)

from helpers.auth import is_authenticated
from helpers.git import get_git_status, perform_git_ops
from helpers.comms import get_valid_comms, get_after_dark_comms
from helpers.tasks_json import load_tasks, save_tasks
from helpers.scratch import load_scratch_work, save_scratch_work
from helpers.bunny import list_bunny_ad_folder, upload_status_image_to_bunny
from helpers.omg_lol import post_to_omg_lol
from blueprints.ani import ani_notify_publish


logger = logging.getLogger(__name__)


# Module constants — read from env at import time, mirror what app.py does.
PASSWORD          = os.environ.get('FLASK_PASSWORD')
WORK_MODE_PIN     = os.environ.get('WORK_MODE_PIN', '')
AFTER_DARK_PIN    = os.environ.get('AFTER_DARK_PIN', '')
BRRR_WEBHOOK_URL  = os.environ.get('BRRR_WEBHOOK_URL', '')

SCRATCH_FILE = 'assets/data/scratch.json'


# Cache-busting token for the cockpit static bundle — max mtime of the files,
# appended as ?v=<n> so a NORMAL reload always fetches the latest CSS/JS (ends the
# recurring "did you hard-refresh?"). Cheap: a few stat() calls per page render.
_COCKPIT_ASSETS = (
	'cockpit.css', 'cockpit_modes.css', 'cockpit_after_dark.css', 'cockpit_ani.css',
	'cockpit.js', 'cockpit_modes.js', 'cockpit_ani.js',
)

def _asset_version():
	try:
		return int(max(os.path.getmtime(os.path.join('static', f)) for f in _COCKPIT_ASSETS))
	except Exception:
		return 0


cockpit_bp = Blueprint('cockpit', __name__)


# ---- PUBLISHING + AUTH ----

@cockpit_bp.route("/publish", methods=['GET', 'POST'])
def publish_status():
	if not is_authenticated():
		return redirect(url_for('cockpit.login'))

	if request.method == 'POST':
		txt = request.form['status']
		image_file = request.files.get('image')
		has_image = bool(image_file and image_file.filename != '')

		# Guard: a status needs *something* to transmit — text or an image.
		# An empty submission (accidental double-submit, a stray Enter, a JS
		# hiccup) would otherwise write a blank entry whose empty <content>
		# breaks the Atom feed for downstream consumers — micro.blog throws
		# `FrozenError: can't modify frozen String: ""` and stops ingesting
		# the whole feed until the bad post is removed (June 2026 incident).
		if not txt.strip() and not has_image:
			flash("Nothing to transmit — add text or an image before publishing.", "error")
			return redirect(url_for('cockpit.publish_status'))

		now = datetime.now(pytz.timezone('America/New_York'))
		fn = now.strftime("_status_updates/%Y-%m-%d-%H%M%S.markdown")
		image_markdown = ""

		if has_image:
			img_filename = f"{now.strftime('%Y%m%d%H%M%S')}.jpg"
			with Image.open(image_file) as img:
				# Apply EXIF rotation first — iPhone landscape shots arrive
				# with the pixels physically portrait + an Orientation tag.
				# JPEG save strips EXIF, so without this the landscape
				# photo would render as portrait after upload.
				img = ImageOps.exif_transpose(img)
				if img.mode in ("RGBA", "P"):
					img = img.convert("RGB")
				if img.size[0] > 1200:
					w_percent = 1200 / float(img.size[0])
					h_size = int(float(img.size[1]) * w_percent)
					img = img.resize((1200, h_size), Image.Resampling.LANCZOS)
				buf = io.BytesIO()
				img.save(buf, format="JPEG", optimize=True, quality=85)
				buf.seek(0)
			cdn_url = upload_status_image_to_bunny(buf.read(), img_filename)
			# Alt text from the form (optionally AI-suggested, always user-reviewed).
			# Strip chars that would break the markdown image syntax.
			alt = request.form.get('image_alt', '').strip().replace('\n', ' ').replace(']', '')
			image_markdown = f"\n\n![{alt or 'Status image'}]({cdn_url})"

		tags = [t for t in ["movie", "book", "music", "idea", "coffee"] if f"#{t}" in txt.lower()]
		fm = f"---\ntitle: Status\ndate: {now.strftime('%Y-%m-%d %H:%M:%S %z')}\nlayout: status_update\n"
		fm += "author: aaron\n"
		fm += "source: web\n"
		if tags: fm += f"tags: {tags}\n"

		full_markdown = f"{fm}---\n{txt}{image_markdown}\n"

		os.makedirs("_status_updates", exist_ok=True)
		with open(fn, "w") as f:
			f.write(full_markdown)

		# Auto-link: if this status update was posted from completing a Mission
		# Log task (the "STATUS UPDATE" log-prompt action sets link_task_id), set
		# that task's blog_url to this update's permalink so it shows publicly on
		# /tools/tasks/. Default collection permalink → /status_updates/<name>.html.
		# perform_git_ops does `git add .`, so tasks.json is committed alongside.
		link_task_id = request.form.get('link_task_id', '').strip()
		if link_task_id:
			try:
				status_url = '/status_updates/' + os.path.basename(fn).replace('.markdown', '.html')
				tdata = load_tasks()
				target = next((t for t in tdata.get('tasks', []) if t.get('id') == link_task_id), None)
				if target:
					target['blog_url'] = status_url
					save_tasks(tdata)
			except Exception as e:
				print(f"auto-link status->task error: {e}")

		perform_git_ops(fn)

		if not has_image:
			post_to_omg_lol(txt)

		try:
			ani_notify_publish(txt[:100])
		except Exception as e:
			print(f"Ani notify error: {e}")

		return render_template('success.html')

	files = sorted(glob.glob("_status_updates/*.markdown"), reverse=True)[:3]
	history = []
	for f in files:
		try:
			with open(f) as fh:
				history.append(fh.read().split("---")[-1].strip())
		except Exception:
			continue
	comms_list = get_valid_comms()
	after_dark_comms_list = get_after_dark_comms()
	tasks_data = load_tasks()
	cockpit_mode_cookie = request.cookies.get('cockpit_mode', '')
	return render_template(
		'publish_form.html',
		history=history,
		git_status=get_git_status(),
		comms_list=comms_list,
		after_dark_comms_list=after_dark_comms_list,
		tasks=tasks_data.get('tasks', []),
		cockpit_mode=cockpit_mode_cookie,
		asset_v=_asset_version(),
	)


@cockpit_bp.route("/publish/alt-suggest", methods=['POST'])
def alt_suggest():
	"""Generate suggested alt text for an uploaded image via Claude vision.
	Backs the publish form's "✨ suggest" button. Returns {ok, alt}. The user
	always reviews/edits the result before it's published — nothing auto-applies.
	Uses Haiku (cheap + fast) on a downscaled JPEG; the image is never stored."""
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 401
	image_file = request.files.get('image')
	if not image_file or image_file.filename == '':
		return jsonify({'error': 'no image'}), 400
	api_key = os.environ.get('ANTHROPIC_API_KEY')
	if not api_key:
		return jsonify({'error': 'alt-text AI is not configured'}), 503

	try:
		# Downscale to a modest JPEG — vision doesn't need full res, and this
		# keeps the request cheap/fast. Mirrors the publish-flow normalization.
		with Image.open(image_file) as img:
			img = ImageOps.exif_transpose(img)
			if img.mode in ("RGBA", "P"):
				img = img.convert("RGB")
			if img.size[0] > 1024:
				ratio = 1024 / float(img.size[0])
				img = img.resize((1024, int(img.size[1] * ratio)), Image.Resampling.LANCZOS)
			buf = io.BytesIO()
			img.save(buf, format="JPEG", quality=80)
			b64 = base64.standard_b64encode(buf.getvalue()).decode("utf-8")

		import anthropic
		client = anthropic.Anthropic(api_key=api_key)
		resp = client.messages.create(
			model="claude-haiku-4-5",
			max_tokens=120,
			system=(
				"You write concise, factual alt text for images on a personal blog. "
				"Reply with ONE plain sentence (max ~140 characters) describing what is "
				"visibly in the image. No 'image of'/'photo of' preamble, no markdown, "
				"no surrounding quotes."
			),
			messages=[{
				"role": "user",
				"content": [
					{"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": b64}},
					{"type": "text", "text": "Write alt text for this image."},
				],
			}],
		)
		alt = "".join(b.text for b in resp.content if b.type == "text").strip()
		return jsonify({'ok': True, 'alt': alt})
	except Exception as e:
		logger.error(f"alt-suggest error: {e}")
		return jsonify({'error': 'generation failed'}), 500


@cockpit_bp.route("/login", methods=['GET', 'POST'])
def login():
	if request.method == 'POST' and request.form.get('password') == PASSWORD:
		r = make_response(redirect(url_for('cockpit.publish_status')))
		r.set_cookie('auth_token', 'authenticated_user', max_age=2592000, httponly=True, samesite='Lax')
		return r
	return render_template('login.html')


@cockpit_bp.route("/logout")
def logout():
	r = make_response(redirect(url_for('cockpit.login')))
	r.set_cookie('auth_token', '', expires=0)
	return r


# ---- SCRATCH (HOME tab — JSON-backed in repo) ----

@cockpit_bp.route('/scratch', methods=['GET'])
def scratch_get():
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 401
	try:
		with open(SCRATCH_FILE, 'r') as f:
			data = json.load(f)
		return jsonify({'content': data.get('content', ''), 'last_modified': data.get('last_modified', None)})
	except FileNotFoundError:
		return jsonify({'content': '', 'last_modified': None})


@cockpit_bp.route('/scratch', methods=['POST'])
def scratch_post():
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 401
	data = request.json or {}
	content = data.get('content', '')
	force = data.get('force', False)
	# Guard: refuse to overwrite non-empty content with empty unless force=True
	if not content and not force:
		try:
			with open(SCRATCH_FILE, 'r') as f:
				existing = json.load(f)
			if existing.get('content', ''):
				return jsonify({'ok': False, 'reason': 'empty_rejected'}), 200
		except FileNotFoundError:
			pass
	pa_tz = pytz.timezone('America/New_York')
	last_modified = datetime.now(pa_tz).isoformat()
	os.makedirs(os.path.dirname(SCRATCH_FILE), exist_ok=True)
	tmp = SCRATCH_FILE + '.tmp'
	with open(tmp, 'w') as f:
		json.dump({'content': content, 'last_modified': last_modified}, f)
	os.replace(tmp, SCRATCH_FILE)
	return jsonify({'ok': True, 'last_modified': last_modified})


# ---- WORK SCRATCHPAD (DESK tab) ----

@cockpit_bp.route('/scratch/work', methods=['GET'])
def scratch_work_get():
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 401
	content, last_modified = load_scratch_work()
	return jsonify({'content': content, 'last_modified': last_modified})


@cockpit_bp.route('/scratch/work', methods=['POST'])
def scratch_work_post():
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 401
	data = request.json or {}
	content = data.get('content', '')
	force = data.get('force', False)
	last_modified = save_scratch_work(content, force=force)
	return jsonify({'ok': True, 'last_modified': last_modified})


# ---- COCKPIT MODE (PIN-gated work / after-dark mode toggle) ----

@cockpit_bp.route('/cockpit/mode', methods=['POST'])
def cockpit_mode():
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 401

	data = request.get_json() or {}
	pin = str(data.get('pin', '')).strip()

	if WORK_MODE_PIN and pin == WORK_MODE_PIN:
		mode = 'mode-work'
	elif AFTER_DARK_PIN and pin == AFTER_DARK_PIN:
		mode = 'mode-after-dark'
	else:
		# Silent fail — return 200 with no_match so JS does nothing
		return jsonify({'ok': False, 'match': False})

	resp = make_response(jsonify({'ok': True, 'match': True, 'mode': mode}))
	# Session cookie — no max_age means it expires when browser closes
	resp.set_cookie(
		'cockpit_mode',
		mode,
		httponly=True,
		samesite='Lax'
	)
	return resp


@cockpit_bp.route('/cockpit/mode/clear', methods=['POST'])
def cockpit_mode_clear():
	"""Purge & Hide — resets to default (no mode)."""
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 401
	resp = make_response(jsonify({'ok': True}))
	resp.set_cookie('cockpit_mode', '', expires=0, httponly=True, samesite='Lax')
	return resp


# ---- FOCUS TIMER / BRRR ----

@cockpit_bp.route('/cockpit/focus/break', methods=['POST'])
def cockpit_focus_break():
	"""
	Called by the focus timer when a break starts or ends.
	Fires a brrr push notification if webhook is configured.
	POST body: { "phase": "break_start" | "break_end" }
	"""
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 401

	if not BRRR_WEBHOOK_URL:
		return jsonify({'ok': False, 'reason': 'brrr not configured'})

	data = request.get_json() or {}
	phase = data.get('phase', 'break_start')

	if phase == 'break_end':
		payload = {
			'title': 'Back to it',
			'message': 'Break\'s over. Focus session resuming.',
			'sound': 'bell_ringing'
		}
	else:
		payload = {
			'title': 'Break time',
			'message': 'Step away from the screen. You earned it.',
			'sound': 'calm1'
		}

	try:
		resp = req_lib.post(
			BRRR_WEBHOOK_URL,
			json=payload,
			headers={'Content-Type': 'application/json'},
			timeout=8
		)
		return jsonify({'ok': resp.status_code == 200, 'status': resp.status_code})
	except Exception as e:
		logger.error(f"brrr webhook error: {e}")
		return jsonify({'ok': False, 'reason': str(e)})


# ---- AFTER DARK MEDIA LIBRARY ----

AD_VIDEOS_FILE   = 'static/after_dark_videos.txt'
AD_YOUTUBE_FILE  = 'static/after_dark_youtube.txt'
_VIEWKEY_RE = re.compile(r'viewkey=([A-Za-z0-9]+)')
# Matches the 11-char video id in youtu.be/<id>, watch?v=<id>, embed/<id>,
# or shorts/<id>. Trailing query string (?si=…&t=…) is ignored.
_YT_ID_RE = re.compile(r'(?:youtu\.be/|youtube\.com/(?:watch\?v=|embed/|shorts/))([A-Za-z0-9_-]{11})')


@cockpit_bp.route('/cockpit/after-dark/library')
def after_dark_library():
	"""Return a shuffled list of Pornhub embed entries parsed from
	static/after_dark_videos.txt. One URL per line; '#' / blank lines skipped;
	optional '|<label>' suffix sets the display name. Page URLs
	(`view_video.php?viewkey=…`) and share links are accepted — the viewkey is
	extracted and an `/embed/<viewkey>` URL is built. Returns the same
	`{items: [{name, url}, ...]}` shape the old Bunny route returned."""
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 401
	items = []
	try:
		with open(AD_VIDEOS_FILE, 'r') as f:
			for raw in f:
				line = raw.strip()
				if not line or line.startswith('#'):
					continue
				url_part, _, label = line.partition('|')
				url_part = url_part.strip()
				label = label.strip()
				m = _VIEWKEY_RE.search(url_part)
				if not m:
					continue
				viewkey = m.group(1)
				items.append({
					'id': viewkey,
					'name': label or viewkey,
					'url': f'https://www.pornhub.com/embed/{viewkey}',
				})
	except FileNotFoundError:
		pass
	random.shuffle(items)
	return jsonify({'items': items})


@cockpit_bp.route('/cockpit/after-dark/youtube')
def after_dark_youtube():
	"""Same shape as after_dark_library, but for YouTube share URLs in
	static/after_dark_youtube.txt. Accepts youtu.be/<id>, watch?v=<id>,
	embed/<id>, or shorts/<id> — any trailing query string is ignored."""
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 401
	items = []
	try:
		with open(AD_YOUTUBE_FILE, 'r') as f:
			for raw in f:
				line = raw.strip()
				if not line or line.startswith('#'):
					continue
				url_part, _, label = line.partition('|')
				url_part = url_part.strip()
				label = label.strip()
				m = _YT_ID_RE.search(url_part)
				if not m:
					continue
				vid = m.group(1)
				items.append({
					'id': vid,
					'name': label or vid,
					'url': f'https://www.youtube.com/embed/{vid}',
				})
	except FileNotFoundError:
		pass
	random.shuffle(items)
	return jsonify({'items': items})


# ---- UNIVERSAL SEARCH — one endpoint the Ctrl+K palette searches across everything the Cockpit owns.
# Extensible: add a source here (or, later, a federated adapter for an external app). Each query is
# wrapped so one bad source can't sink the search. ----

@cockpit_bp.route('/cockpit/search')
def cockpit_search():
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 401
	q = (request.args.get('q') or '').strip()
	if len(q) < 2:
		return jsonify({'results': []})
	like = '%' + q + '%'
	ql = q.lower()
	results = []

	try:
		from helpers.db import get_db
		conn = get_db()
	except Exception:
		conn = None
	if conn is not None:
		try:
			for r in conn.execute("SELECT title, status FROM tasks WHERE title LIKE ? "
			                      "ORDER BY (status='open') DESC, created DESC LIMIT 8", (like,)):
				results.append({'type': 'task', 'title': r[0], 'sub': 'Below Deck · ' + (r[1] or ''), 'url': '/below-deck'})
		except Exception:
			pass
		try:
			for r in conn.execute("SELECT ticket_number, title, status FROM tickets "
			                      "WHERE title LIKE ? OR description LIKE ? ORDER BY created DESC LIMIT 6", (like, like)):
				num = (str(r[0]) + ' · ') if r[0] else ''
				results.append({'type': 'ticket', 'title': num + (r[1] or ''), 'sub': 'Ticket · ' + (r[2] or ''),
				                'url': '/command-deck/tickets/'})
		except Exception:
			pass
		try:
			for r in conn.execute("SELECT title, slug FROM projects WHERE (title LIKE ? OR description LIKE ?) "
			                      "AND archived_at IS NULL LIMIT 6", (like, like)):
				results.append({'type': 'project', 'title': r[0], 'sub': 'Project',
				                'url': '/command-deck/projects/' + (r[1] or '')})
		except Exception:
			pass
		try:
			for r in conn.execute("SELECT title, meeting_date FROM meetings WHERE title LIKE ? OR notes LIKE ? "
			                      "ORDER BY meeting_date DESC LIMIT 6", (like, like)):
				results.append({'type': 'meeting', 'title': r[0], 'sub': 'Meeting · ' + (r[1] or '')[:10],
				                'url': '/command-deck/'})
		except Exception:
			pass
		try:
			conn.close()
		except Exception:
			pass

	try:
		n = 0
		for path in sorted(glob.glob('_posts/*.md') + glob.glob('_posts/*.markdown'), reverse=True):
			with open(path) as f:
				raw = f.read()
			if ql in raw.lower():
				mt = re.search(r'^title:\s*["\']?(.+?)["\']?\s*$', raw, re.M)
				results.append({'type': 'post', 'title': (mt.group(1).strip() if mt else os.path.basename(path)),
				                'sub': 'Blog post', 'url': '/blog/'})
				n += 1
				if n >= 6:
					break
	except Exception:
		pass

	try:
		n = 0
		for path in sorted(glob.glob('_status_updates/*.markdown'), reverse=True)[:250]:
			with open(path) as f:
				raw = f.read()
			if ql in raw.lower():
				parts = raw.split('---')
				body = (parts[2].strip() if len(parts) >= 3 else raw).replace('\n', ' ').strip()
				results.append({'type': 'status', 'title': body[:90] or 'status update', 'sub': 'Status update', 'url': '/'})
				n += 1
				if n >= 6:
					break
	except Exception:
		pass

	return jsonify({'results': results[:40], 'q': q})


# ---- library editing (add current / delete) — the .txt files are server-state ----

def _ad_read_raw(path):
	try:
		with open(path, 'r') as f:
			return [ln.rstrip('\n') for ln in f]
	except FileNotFoundError:
		return []


def _ad_write_lines(path, lines):
	with open(path, 'w') as f:
		f.write('\n'.join(lines) + ('\n' if lines else ''))


def _ad_clean_label(label):
	"""Normalize a label for the `<url> | <label>` line format: no pipes (they're
	the delimiter), no newlines, capped length."""
	return (label or '').strip().replace('|', '/').replace('\n', ' ')[:80]


def _ad_lib_add(path, id_re, vid, label, canonical):
	"""Append a canonical library line for `vid` (+ optional label) unless its id is already present.
	Returns True if present/added, False on a bad id."""
	if not vid:
		return False
	lines = _ad_read_raw(path)
	for ln in lines:
		m = id_re.search(ln)
		if m and m.group(1) == vid:
			return True  # already in the library — idempotent
	label = _ad_clean_label(label)
	lines.append(canonical + (' | ' + label if label else ''))
	_ad_write_lines(path, lines)
	return True


def _ad_backfill_titles(path, id_re, kind, limit=40):
	"""Walk an existing library file and fetch a real title for every entry that has
	none (bare id, or label echoing the id). Preserves the original URL text and any
	comment/blank lines. Bounded per call (fetches are network-bound) — returns how
	many were filled and how many still lack a title so the UI can re-run for more."""
	lines = _ad_read_raw(path)
	out, updated, remaining = [], 0, 0
	for ln in lines:
		stripped = ln.strip()
		if not stripped or stripped.startswith('#'):
			out.append(ln)
			continue
		m = id_re.search(ln)
		if not m:
			out.append(ln)
			continue
		vid = m.group(1)
		url_part, _, existing = ln.partition('|')
		existing = existing.strip()
		if existing and existing != vid:
			out.append(ln)  # already has a real title
			continue
		if updated >= limit:
			remaining += 1
			out.append(ln)
			continue
		title = _ad_clean_label(_fetch_media_title(kind, vid))
		if title:
			out.append(url_part.rstrip() + ' | ' + title)
			updated += 1
		else:
			remaining += 1
			out.append(ln)
	if updated:
		_ad_write_lines(path, out)
	return {'updated': updated, 'remaining': remaining}


def _ad_lib_delete(path, id_re, vid):
	"""Drop every line whose extracted id matches `vid`. Returns the count removed."""
	if not vid:
		return 0
	lines = _ad_read_raw(path)
	kept, removed = [], 0
	for ln in lines:
		m = id_re.search(ln)
		if m and m.group(1) == vid:
			removed += 1
			continue
		kept.append(ln)
	if removed:
		_ad_write_lines(path, kept)
	return removed


def _fetch_media_title(kind, vid):
	"""Best-effort fetch of a human title for a library item so saved entries read
	as the real video name instead of a bare id. YouTube via oEmbed (reliable, no
	key needed). PH via oEmbed (best-effort — age-gate / CDN may refuse). Returns a
	trimmed title, or '' on any failure. Never raises; a short timeout keeps the
	save snappy."""
	try:
		if kind == 'youtube':
			r = req_lib.get('https://www.youtube.com/oembed',
			                params={'format': 'json', 'url': f'https://youtu.be/{vid}'}, timeout=4)
			if r.ok:
				return (r.json().get('title') or '').strip()
		elif kind == 'ph':
			r = req_lib.get('https://www.pornhub.com/oembed',
			                params={'format': 'json',
			                        'url': f'https://www.pornhub.com/view_video.php?viewkey={vid}'}, timeout=4)
			if r.ok:
				return (r.json().get('title') or '').strip()
	except Exception:
		pass
	return ''


@cockpit_bp.route('/cockpit/after-dark/youtube/add', methods=['POST'])
def after_dark_youtube_add():
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 401
	body = request.json or {}
	vid = (body.get('id') or '').strip()
	if not re.fullmatch(r'[A-Za-z0-9_-]{11}', vid):
		return jsonify({'ok': False, 'error': 'bad id'}), 400
	# Prefer the live title the player already captured; enrich server-side only
	# when the client had nothing useful (empty, or the bare id echoed back).
	label = (body.get('label') or '').strip()
	if not label or label == vid:
		label = _fetch_media_title('youtube', vid) or label
	ok = _ad_lib_add(AD_YOUTUBE_FILE, _YT_ID_RE, vid, label, f'https://youtu.be/{vid}')
	return jsonify({'ok': ok, 'id': vid, 'label': label})


@cockpit_bp.route('/cockpit/after-dark/youtube/delete', methods=['POST'])
def after_dark_youtube_delete():
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 401
	vid = ((request.json or {}).get('id') or '').strip()
	removed = _ad_lib_delete(AD_YOUTUBE_FILE, _YT_ID_RE, vid)
	return jsonify({'ok': removed > 0, 'removed': removed})


@cockpit_bp.route('/cockpit/after-dark/library/add', methods=['POST'])
def after_dark_library_add():
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 401
	body = request.json or {}
	vk = (body.get('id') or '').strip()
	if not re.fullmatch(r'[A-Za-z0-9]{6,30}', vk):
		return jsonify({'ok': False, 'error': 'bad id'}), 400
	label = (body.get('label') or '').strip()
	if not label or label == vk:
		label = _fetch_media_title('ph', vk) or label
	ok = _ad_lib_add(AD_VIDEOS_FILE, _VIEWKEY_RE, vk, label,
	                 f'https://www.pornhub.com/view_video.php?viewkey={vk}')
	return jsonify({'ok': ok, 'id': vk, 'label': label})


@cockpit_bp.route('/cockpit/after-dark/library/delete', methods=['POST'])
def after_dark_library_delete():
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 401
	vk = ((request.json or {}).get('id') or '').strip()
	removed = _ad_lib_delete(AD_VIDEOS_FILE, _VIEWKEY_RE, vk)
	return jsonify({'ok': removed > 0, 'removed': removed})


@cockpit_bp.route('/cockpit/after-dark/youtube/refresh-titles', methods=['POST'])
def after_dark_youtube_refresh_titles():
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 401
	res = _ad_backfill_titles(AD_YOUTUBE_FILE, _YT_ID_RE, 'youtube')
	return jsonify({'ok': True, **res})


@cockpit_bp.route('/cockpit/after-dark/library/refresh-titles', methods=['POST'])
def after_dark_library_refresh_titles():
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 401
	res = _ad_backfill_titles(AD_VIDEOS_FILE, _VIEWKEY_RE, 'ph')
	return jsonify({'ok': True, **res})


@cockpit_bp.route('/cockpit/after-dark/resolve-titles', methods=['POST'])
def after_dark_resolve_titles():
	"""Resolve real titles for TRANSIENT items that aren't in a library file — the paste-queue.
	Takes {items: [{id, kind}]} and returns {titles: {id: title}} via the same oEmbed lookup the
	library uses. Bounded per call (fetches are network-bound); unresolved ids are just omitted."""
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 401
	items = (request.json or {}).get('items') or []
	if not isinstance(items, list):
		return jsonify({'ok': False, 'error': 'bad items'}), 400
	titles, seen = {}, set()
	for it in items[:40]:
		if not isinstance(it, dict):
			continue
		vid = str(it.get('id') or '').strip()
		kind = (it.get('kind') or 'ph').strip()
		if not vid or vid in seen or not re.fullmatch(r'[A-Za-z0-9_-]{6,30}', vid):
			continue
		seen.add(vid)
		title = _ad_clean_label(_fetch_media_title(kind, vid))
		if title:
			titles[vid] = title
	return jsonify({'ok': True, 'titles': titles})


@cockpit_bp.route('/cockpit/after-dark/music')
def after_dark_music():
	"""List audio files from Bunny AD zone /music/ subfolder."""
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 401
	items = list_bunny_ad_folder('music')
	return jsonify({'items': items})


@cockpit_bp.route('/cockpit/after-dark/ani-loops')
def after_dark_ani_loops():
	"""List Ani loop video files from Bunny AD zone /ani/ subfolder."""
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 401
	items = list_bunny_ad_folder('ani')
	return jsonify({'items': items})
