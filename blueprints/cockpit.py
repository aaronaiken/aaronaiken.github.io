"""Cockpit blueprint — publishing flow + auth + scratch + mode + focus timer + after-dark media."""
import os
import io
import glob
import json
import logging
from datetime import datetime
import pytz
from PIL import Image
import requests as req_lib
from flask import (
	Blueprint, request, redirect, url_for, jsonify, render_template, make_response,
)

from helpers.auth import is_authenticated
from helpers.git import get_git_status, perform_git_ops
from helpers.comms import get_valid_comms, get_after_dark_comms
from helpers.tasks_json import load_tasks
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


cockpit_bp = Blueprint('cockpit', __name__)


# ---- PUBLISHING + AUTH ----

@cockpit_bp.route("/publish", methods=['GET', 'POST'])
def publish_status():
	if not is_authenticated():
		return redirect(url_for('cockpit.login'))

	if request.method == 'POST':
		txt = request.form['status']
		image_file = request.files.get('image')
		now = datetime.now(pytz.timezone('America/New_York'))
		fn = now.strftime("_status_updates/%Y-%m-%d-%H%M%S.markdown")
		image_markdown = ""
		has_image = False

		if image_file and image_file.filename != '':
			has_image = True
			img_filename = f"{now.strftime('%Y%m%d%H%M%S')}.jpg"
			with Image.open(image_file) as img:
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
			image_markdown = f"\n\n![Status Image]({cdn_url})"

		tags = [t for t in ["movie", "book", "music", "idea", "coffee"] if f"#{t}" in txt.lower()]
		fm = f"---\ntitle: Status\ndate: {now.strftime('%Y-%m-%d %H:%M:%S %z')}\nlayout: status_update\n"
		fm += "author: aaron\n"
		fm += "source: web\n"
		if tags: fm += f"tags: {tags}\n"

		full_markdown = f"{fm}---\n{txt}{image_markdown}\n"

		os.makedirs("_status_updates", exist_ok=True)
		with open(fn, "w") as f:
			f.write(full_markdown)

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
	)


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

@cockpit_bp.route('/cockpit/after-dark/library')
def after_dark_library():
	"""List video files from Bunny AD zone /videos/ subfolder."""
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 401
	items = list_bunny_ad_folder('videos')
	return jsonify({'items': items})


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
