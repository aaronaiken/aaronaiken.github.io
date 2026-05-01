"""Mozzie blueprint — flag football season tracker for Mozzie's Steelers.

Routes:
- GET  /mozzie                                  — main tracker page
- GET  /mozzie/api/games                        — list all games
- POST /mozzie/api/games                        — add new game
- PUT  /mozzie/api/games/<id>                   — apply play / undo / field updates
- DELETE /mozzie/api/games/<id>                 — remove game
- POST /mozzie/api/games/<id>/photo             — gallery photo upload (Bunny Mozzie zone)
- POST /mozzie/api/games/<id>/final             — mark final + auto-generate draft recap (no publish)
- GET  /mozzie/api/games/<id>/draft             — fetch saved draft + auto-regenerated draft
- PUT  /mozzie/api/games/<id>/draft             — save edited draft text (no publish)
- POST /mozzie/api/games/<id>/publish-recap     — publish recap via standard status update flow

Mark Final and Publish Recap are deliberately separate — Mark Final stages a draft, the user
edits as needed, then Publish Recap fires `perform_git_ops()` and writes the markdown file.
"""
import os
import io
import json
import time
import logging
from datetime import datetime
import pytz
from PIL import Image
import requests as req_lib
from flask import Blueprint, request, redirect, url_for, jsonify, render_template

from helpers.auth import is_authenticated
from helpers.git import perform_git_ops
from helpers.omg_lol import post_to_omg_lol
from helpers.bunny import upload_status_image_to_bunny


logger = logging.getLogger(__name__)


# Module constants — read from env at import time.
MOZZIE_FILE               = os.environ.get('MOZZIE_FILE', 'mozzie_games.json')
BUNNY_MOZZIE_STORAGE_ZONE = os.environ.get('BUNNY_MOZZIE_STORAGE_ZONE')
BUNNY_MOZZIE_API_KEY      = os.environ.get('BUNNY_MOZZIE_API_KEY')
BUNNY_MOZZIE_CDN_URL      = os.environ.get('BUNNY_MOZZIE_CDN_URL', '').rstrip('/')


MOZZIE_PLAYS = [
	{"id": "td",      "label": "Touchdown",        "pts": 6, "group": "main"},
	{"id": "safety",  "label": "Safety",            "pts": 2, "group": "main"},
	{"id": "pat_5",   "label": "Extra Pt (5 yd)",  "pts": 1, "group": "pat"},
	{"id": "pat_10",  "label": "Extra Pt (10 yd)", "pts": 2, "group": "pat"},
	{"id": "int_pat", "label": "INT Return (PAT)", "pts": 2, "group": "pat"},
]

_MOZZIE_PLAY_PTS = {p["id"]: p["pts"] for p in MOZZIE_PLAYS}


mozzie_bp = Blueprint('mozzie', __name__)


# ---- HELPERS (blueprint-internal) ----

def load_games():
	try:
		with open(MOZZIE_FILE, 'r') as f:
			return json.load(f)
	except FileNotFoundError:
		return []


def save_games(games):
	with open(MOZZIE_FILE, 'w') as f:
		json.dump(games, f, indent=2)


def upload_mozzie_photo_to_bunny(image_bytes, filename, game_id):
	"""Upload a Mozzie game photo to the dedicated Mozzie Bunny storage zone (gallery)."""
	path = f"mozzie/game-{game_id}/{filename}"
	upload_url = f"https://ny.storage.bunnycdn.com/{BUNNY_MOZZIE_STORAGE_ZONE}/{path}"
	response = req_lib.put(
		upload_url,
		data=image_bytes,
		headers={
			'AccessKey': BUNNY_MOZZIE_API_KEY,
			'Content-Type': 'image/jpeg',
		},
		timeout=60
	)
	if response.status_code != 201:
		raise Exception(f"Bunny Mozzie upload failed: {response.status_code} {response.text}")
	return f"{BUNNY_MOZZIE_CDN_URL}/{path}"


def build_mozzie_status_text(game):
	"""Auto-generate the recap status text from current game state. User can edit before publishing."""
	mozzie = game.get('mozzieScore', 0)
	opp    = game.get('oppScore', 0)
	opponent = game.get('opponent', 'Opponent')
	loc    = 'Home' if game.get('location') == 'home' else 'Away'
	if mozzie > opp:
		result = 'W'
	elif mozzie < opp:
		result = 'L'
	else:
		result = 'T'
	return f"🏈 Mozzie's Steelers — {result} {mozzie}–{opp} vs. {opponent} ({loc}) #flagfootball"


def process_status_image(image_file):
	"""Resize + JPEG-encode an uploaded image at 1200px max / 85% quality. Returns bytes."""
	with Image.open(image_file) as img:
		if img.mode in ("RGBA", "P"):
			img = img.convert("RGB")
		if img.size[0] > 1200:
			w_pct  = 1200 / float(img.size[0])
			h_size = int(float(img.size[1]) * w_pct)
			img = img.resize((1200, h_size), Image.Resampling.LANCZOS)
		buf = io.BytesIO()
		img.save(buf, format="JPEG", optimize=True, quality=85)
		buf.seek(0)
		return buf.read()


def publish_mozzie_recap(game, text, photo_file=None):
	"""
	Publish a recap status update. Photo flow:
	  - photo_file provided → process + upload to status zone (BUNNY_STATUS_*)
	  - else if game has gallery photos → use the first one (already on Bunny Mozzie zone)
	  - else → text-only (also fires omg.lol mirror)
	Mirrors the standard publish_status pipeline. Returns the markdown filename written.
	"""
	now = datetime.now(pytz.timezone('America/New_York'))
	fn  = now.strftime("_status_updates/%Y-%m-%d-%H%M%S.markdown")

	image_markdown = ""
	has_image = False

	if photo_file and photo_file.filename:
		image_bytes = process_status_image(photo_file)
		img_filename = f"{now.strftime('%Y%m%d%H%M%S')}.jpg"
		cdn_url = upload_status_image_to_bunny(image_bytes, img_filename)
		image_markdown = f"\n\n![Game photo]({cdn_url})"
		has_image = True
	elif game.get('photos'):
		# Reuse first gallery photo verbatim — it's already on Bunny Mozzie's CDN
		cdn_url = game['photos'][0]
		image_markdown = f"\n\n![Game photo]({cdn_url})"
		has_image = True

	fm  = f"---\ntitle: Status\ndate: {now.strftime('%Y-%m-%d %H:%M:%S %z')}\nlayout: status_update\n"
	fm += "author: aaron\nsource: web\ntags: [flagfootball]\n---\n"
	full_markdown = f"{fm}{text.strip()}{image_markdown}\n"

	os.makedirs("_status_updates", exist_ok=True)
	with open(fn, "w") as f:
		f.write(full_markdown)

	perform_git_ops(fn)

	if not has_image:
		post_to_omg_lol(text.strip())

	return fn


# ---- ROUTES ----

@mozzie_bp.route('/mozzie')
def mozzie_page():
	if not is_authenticated():
		return redirect(url_for('cockpit.login'))
	games = load_games()
	active   = [g for g in games if g.get('status') != 'final']
	finished = [g for g in games if g.get('status') == 'final']
	finished.sort(key=lambda g: g.get('date', ''), reverse=True)
	wins   = sum(1 for g in finished if g.get('mozzieScore', 0) > g.get('oppScore', 0))
	losses = sum(1 for g in finished if g.get('mozzieScore', 0) < g.get('oppScore', 0))
	ties   = sum(1 for g in finished if g.get('mozzieScore', 0) == g.get('oppScore', 0))
	return render_template(
		'mozzie.html',
		active=active,
		finished=finished,
		wins=wins,
		losses=losses,
		ties=ties,
		plays=MOZZIE_PLAYS,
	)


@mozzie_bp.route('/mozzie/api/games', methods=['GET'])
def mozzie_api_games_get():
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 401
	return jsonify(load_games())


@mozzie_bp.route('/mozzie/api/games', methods=['POST'])
def mozzie_api_games_post():
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 401
	data = request.get_json() or {}
	opponent = (data.get('opponent') or '').strip()
	if not opponent:
		return jsonify({'error': 'opponent required'}), 400
	game = {
		'id':              int(time.time() * 1000),
		'opponent':        opponent,
		'date':            data.get('date', datetime.now(pytz.timezone('America/New_York')).strftime('%Y-%m-%d')),
		'location':        data.get('location', 'home'),
		'status':          data.get('status', 'upcoming'),
		'mozzieScore':     0,
		'oppScore':        0,
		'plays':           [],
		'photos':          [],
		'notes':           '',
		'draft_status':    '',
		'recap_drafted':   False,
		'recap_published': False,
	}
	games = load_games()
	games.append(game)
	save_games(games)
	return jsonify(game), 201


@mozzie_bp.route('/mozzie/api/games/<int:game_id>', methods=['PUT'])
def mozzie_api_games_put(game_id):
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 401
	data  = request.get_json() or {}
	games = load_games()
	game  = next((g for g in games if g['id'] == game_id), None)
	if not game:
		return jsonify({'error': 'game not found'}), 404

	if 'play' in data:
		play_id = data['play'].get('playId')
		team    = data['play'].get('team')
		pts     = _MOZZIE_PLAY_PTS.get(play_id, 0)
		if team not in ('mozzie', 'opp') or play_id not in _MOZZIE_PLAY_PTS:
			return jsonify({'error': 'invalid play'}), 400
		game['plays'].append({'team': team, 'playId': play_id, 'pts': pts})
		if team == 'mozzie':
			game['mozzieScore'] = game.get('mozzieScore', 0) + pts
		else:
			game['oppScore'] = game.get('oppScore', 0) + pts

	if data.get('undo') and game.get('plays'):
		last = game['plays'].pop()
		if last['team'] == 'mozzie':
			game['mozzieScore'] = max(0, game.get('mozzieScore', 0) - last['pts'])
		else:
			game['oppScore'] = max(0, game.get('oppScore', 0) - last['pts'])

	for field in ('status', 'notes', 'location', 'date', 'opponent'):
		if field in data:
			game[field] = data[field]

	save_games(games)
	return jsonify(game)


@mozzie_bp.route('/mozzie/api/games/<int:game_id>', methods=['DELETE'])
def mozzie_api_games_delete(game_id):
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 401
	games = load_games()
	before = len(games)
	games  = [g for g in games if g['id'] != game_id]
	if len(games) == before:
		return jsonify({'error': 'game not found'}), 404
	save_games(games)
	return jsonify({'ok': True})


@mozzie_bp.route('/mozzie/api/games/<int:game_id>/photo', methods=['POST'])
def mozzie_upload_photo(game_id):
	"""Upload a photo to the game's gallery (Bunny Mozzie zone)."""
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 401
	file = request.files.get('photo')
	if not file or file.filename == '':
		return jsonify({'error': 'no file'}), 400

	with Image.open(file) as img:
		if img.mode in ("RGBA", "P"):
			img = img.convert("RGB")
		img.thumbnail((1200, 1200), Image.Resampling.LANCZOS)
		buf = io.BytesIO()
		img.save(buf, format='JPEG', quality=85)
		buf.seek(0)

	filename = f"{int(time.time())}.jpg"
	try:
		cdn_url = upload_mozzie_photo_to_bunny(buf.read(), filename, game_id)
	except Exception as e:
		logger.error(f"Mozzie photo upload error: {e}")
		return jsonify({'error': 'upload failed'}), 500

	games = load_games()
	game  = next((g for g in games if g['id'] == game_id), None)
	if not game:
		return jsonify({'error': 'game not found'}), 404
	game.setdefault('photos', []).append(cdn_url)
	save_games(games)
	return jsonify({'url': cdn_url})


@mozzie_bp.route('/mozzie/api/games/<int:game_id>/final', methods=['POST'])
def mozzie_mark_final(game_id):
	"""Mark a game final and auto-generate a draft recap. Does NOT publish."""
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 401

	games = load_games()
	game  = next((g for g in games if g['id'] == game_id), None)
	if not game:
		return jsonify({'error': 'game not found'}), 404

	game['status']         = 'final'
	game['draft_status']   = build_mozzie_status_text(game)
	game['recap_drafted']  = True
	save_games(games)

	return jsonify({'ok': True, 'game': game, 'draft': game['draft_status']})


@mozzie_bp.route('/mozzie/api/games/<int:game_id>/draft', methods=['GET'])
def mozzie_get_draft(game_id):
	"""Return the saved draft + the auto-generated draft (so the UI can offer 'reset to auto')."""
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 401
	games = load_games()
	game  = next((g for g in games if g['id'] == game_id), None)
	if not game:
		return jsonify({'error': 'game not found'}), 404
	return jsonify({
		'draft':           game.get('draft_status', '') or build_mozzie_status_text(game),
		'auto':            build_mozzie_status_text(game),
		'recap_published': bool(game.get('recap_published')),
		'has_gallery_photo': bool(game.get('photos')),
	})


@mozzie_bp.route('/mozzie/api/games/<int:game_id>/draft', methods=['PUT'])
def mozzie_save_draft(game_id):
	"""Save edited draft text (no publish)."""
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 401
	data = request.get_json() or {}
	text = (data.get('text') or '').strip()
	games = load_games()
	game  = next((g for g in games if g['id'] == game_id), None)
	if not game:
		return jsonify({'error': 'game not found'}), 404
	game['draft_status']  = text
	game['recap_drafted'] = True
	save_games(games)
	return jsonify({'ok': True})


@mozzie_bp.route('/mozzie/api/games/<int:game_id>/publish-recap', methods=['POST'])
def mozzie_publish_recap(game_id):
	"""Publish the recap to the standard status update flow (file write + git push + omg.lol if no image)."""
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 401

	games = load_games()
	game  = next((g for g in games if g['id'] == game_id), None)
	if not game:
		return jsonify({'error': 'game not found'}), 404
	if game.get('status') != 'final':
		return jsonify({'error': 'game not finalized'}), 400

	# Text comes from form (user-edited). Fallback to saved draft, then auto-draft.
	text = (request.form.get('text') or game.get('draft_status') or build_mozzie_status_text(game)).strip()
	if not text:
		return jsonify({'error': 'empty recap'}), 400

	photo_file = request.files.get('photo')

	try:
		publish_mozzie_recap(game, text, photo_file=photo_file)
	except Exception as e:
		logger.error(f"Mozzie recap publish error: {e}")
		return jsonify({'error': 'publish failed', 'detail': str(e)}), 500

	game['draft_status']    = text  # persist the version we actually shipped
	game['recap_published'] = True
	save_games(games)

	return jsonify({'ok': True, 'game': game})
