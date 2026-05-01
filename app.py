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


# ---- COMMS HELPERS ----

def get_active_tags():
	pa_tz = pytz.timezone('America/New_York')
	now = datetime.now(pa_tz)
	hour = now.hour
	tags = ["ALL"]

	tags.append(now.strftime("%A").upper())

	if 5 <= hour < 12:
		tags.append("AM")
	if 12 <= hour < 24:
		tags.append("PM")
	if hour >= 17 or hour < 5:
		tags.append("EVE")

	day_type = "WEEKEND" if now.weekday() >= 5 else "WEEKDAY"
	tags.append(day_type)

	date_str = now.strftime("%m/%d")
	if date_str == "12/25": tags.append("CHRISTMAS")
	if date_str == "03/11": tags.append("BIRTHDAY")
	if date_str == "04/05": tags.append("EASTER")

	return tags


def get_valid_comms():
	active_tags = get_active_tags()
	valid_comms = []

	try:
		with open('static/comms.txt', 'r') as f:
			for line in f:
				clean_line = line.strip()
				if not clean_line:
					continue

				if "|" not in clean_line:
					valid_comms.append(clean_line)
					continue

				parts = clean_line.split("|")
				message = parts[-1].strip()
				required_tags = [p.strip().upper() for p in parts[:-1] if p.strip()]

				if all(tag in active_tags for tag in required_tags):
					weight = 10 ** len(required_tags)
					for _ in range(weight):
						valid_comms.append(message)

	except FileNotFoundError:
		return ["Secure line cut."]

	return valid_comms if valid_comms else ["Scanning..."]

def get_after_dark_comms():
    """
    Load after_dark_comms.txt — same tag/pipe format as comms.txt.
    Returns a deduplicated list of currently valid lines.
    Silently returns [] if the file doesn't exist yet.
    """
    active_tags = get_active_tags()
    valid = []
    try:
        with open(AFTER_DARK_COMMS_FILE, 'r') as f:
            for line in f:
                clean = line.strip()
                if not clean:
                    continue
                if '|' not in clean:
                    valid.append(clean)
                    continue
                parts = clean.split('|')
                message = parts[-1].strip()
                required_tags = [p.strip().upper() for p in parts[:-1] if p.strip()]
                if all(tag in active_tags for tag in required_tags):
                    weight = 10 ** len(required_tags)
                    for _ in range(weight):
                        valid.append(message)
    except FileNotFoundError:
        return []
    # Deduplicate preserving order
    seen = set()
    unique = []
    for m in valid:
        if m not in seen:
            seen.add(m)
            unique.append(m)
    return unique


def load_scratch_work():
    """Load work scratchpad content."""
    try:
        with open(SCRATCH_WORK_FILE, 'r') as f:
            data = json.load(f)
        return data.get('content', ''), data.get('last_modified', None)
    except FileNotFoundError:
        return '', None


def save_scratch_work(content, force=False):
    """Persist work scratchpad content."""
    if not content and not force:
        try:
            with open(SCRATCH_WORK_FILE, 'r') as f:
                existing = json.load(f)
            if existing.get('content', ''):
                return existing.get('last_modified')
        except FileNotFoundError:
            pass
    pa_tz = pytz.timezone('America/New_York')
    last_modified = datetime.now(pa_tz).isoformat()
    os.makedirs(os.path.dirname(SCRATCH_WORK_FILE), exist_ok=True)
    tmp = SCRATCH_WORK_FILE + '.tmp'
    with open(tmp, 'w') as f:
        json.dump({'content': content, 'last_modified': last_modified}, f)
    os.replace(tmp, SCRATCH_WORK_FILE)
    return last_modified


def list_bunny_ad_folder(subfolder):
    """
    List files in a Bunny After Dark storage zone subfolder.
    subfolder: 'videos', 'music', or 'ani'
    Returns list of dicts: {name, url, ext}
    Returns [] on any error.
    """
    if not BUNNY_AD_STORAGE_ZONE or not BUNNY_AD_API_KEY or not BUNNY_AD_CDN_URL:
        return []
    list_url = f"https://ny.storage.bunnycdn.com/{BUNNY_AD_STORAGE_ZONE}/{subfolder}/"
    try:
        resp = req_lib.get(
            list_url,
            headers={'AccessKey': BUNNY_AD_API_KEY, 'Accept': 'application/json'},
            timeout=10
        )
        if resp.status_code != 200:
            return []
        items = resp.json()
        result = []
        for item in items:
            if item.get('IsDirectory'):
                continue
            name = item.get('ObjectName', '')
            ext = name.rsplit('.', 1)[-1].lower() if '.' in name else ''
            result.append({
                'name': name,
                'url': f"{BUNNY_AD_CDN_URL}/{subfolder}/{name}",
                'ext': ext,
            })
        return result
    except Exception as e:
        app.logger.error(f"Bunny AD list error ({subfolder}): {e}")
        return []

def post_to_omg_lol(text):
	api, addr = os.environ.get('OMG_LOL_API_KEY'), os.environ.get('OMG_LOL_ADDRESS')
	if not api or not addr: return
	url = f"https://api.omg.lol/address/{addr}/statuses"
	text = text.strip()
	found = emoji.emoji_list(text)
	payload = {"content": text}
	if found and found[0]['match_start'] == 0:
		payload["emoji"] = found[0]['emoji']
		payload["content"] = text[len(found[0]['emoji']):].strip()
	requests.post(url, json=payload, headers={"Authorization": f"Bearer {api}"})


def optimize_image(input_path, max_width=1200):
	with Image.open(input_path) as img:
		if img.mode in ("RGBA", "P"):
			img = img.convert("RGB")
		w_percent = (max_width / float(img.size[0]))
		if w_percent < 1.0:
			h_size = int((float(img.size[1]) * float(w_percent)))
			img = img.resize((max_width, h_size), Image.Resampling.LANCZOS)
		img.save(input_path, "JPEG", optimize=True, quality=85)

def upload_status_image_to_bunny(image_bytes, filename):
    """Upload a processed status image to Bunny storage zone. Returns CDN URL."""
    upload_url = f"https://ny.storage.bunnycdn.com/{BUNNY_STATUS_STORAGE_ZONE}/status/{filename}"
    response = req_lib.put(
        upload_url,
        data=image_bytes,
        headers={
            'AccessKey': BUNNY_STATUS_API_KEY,
            'Content-Type': 'image/jpeg',
        },
        timeout=60
    )
    if response.status_code != 201:
        raise Exception(f"Bunny status upload failed: {response.status_code} {response.text}")
    return f"{BUNNY_STATUS_CDN_URL}/status/{filename}"


# ---- TASKS HELPERS ----

def load_tasks():
	try:
		with open(TASKS_FILE, 'r') as f:
			return json.load(f)
	except FileNotFoundError:
		return {"tasks": []}


def save_tasks(data):
	os.makedirs(os.path.dirname(TASKS_FILE), exist_ok=True)
	with open(TASKS_FILE, 'w') as f:
		json.dump(data, f, indent=2)


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


# ---- ANI HELPERS ----

def ani_load_conversation():
	"""Load full conversation history and metadata.
	Returns (messages list, meta dict)."""
	try:
		with open(ANI_CONVERSATION_FILE, 'r') as f:
			data = json.load(f)
			messages = data.get('messages', [])
			meta = {
				'last_briefing': data.get('last_briefing', None),
				'location': data.get('location', None),
				'visit_log': data.get('visit_log', []),
				'last_active': data.get('last_active', None),
				'pending_opener': data.get('pending_opener', None),
				'last_session_tone': data.get('last_session_tone', None),
				'degradation_level': data.get('degradation_level', 0),
				'session_message_count': data.get('session_message_count', 0)
			}
			return messages, meta
	except FileNotFoundError:
		return [], {
			'last_briefing': None,
			'location': None,
			'visit_log': [],
			'last_active': None,
			'pending_opener': None,
			'last_session_tone': None,
			'degradation_level': 0,
			'session_message_count': 0
		}


def ani_save_conversation(messages, meta):
	"""Persist full conversation history and metadata."""
	data = {
		'messages': messages,
		'last_briefing': meta.get('last_briefing'),
		'location': meta.get('location'),
		'visit_log': meta.get('visit_log', []),
		'last_active': meta.get('last_active'),
		'pending_opener': meta.get('pending_opener'),
		'last_session_tone': meta.get('last_session_tone'),
		'degradation_level': meta.get('degradation_level', 0),
		'session_message_count': meta.get('session_message_count', 0)
	}
	with open(ANI_CONVERSATION_FILE, 'w') as f:
		json.dump(data, f, indent=2)


def ani_log_visit(meta):
	"""Append current ET hour to visit_log and update last_active. Keep last 90 entries."""
	pa_tz = pytz.timezone('America/New_York')
	now = datetime.now(pa_tz)
	visit_log = meta.get('visit_log', [])
	visit_log.append({
		'hour': now.hour,
		'date': now.strftime('%Y-%m-%d')
	})
	meta['visit_log'] = visit_log[-90:]
	meta['last_active'] = now.isoformat()
	meta['pending_opener'] = None
	return meta


def ani_get_visit_pattern(meta):
	"""Analyse visit_log to describe when aaron typically shows up."""
	visit_log = meta.get('visit_log', [])
	if len(visit_log) < 5:
		return None

	from collections import Counter

	hours = [v['hour'] for v in visit_log]
	hour_counts = Counter(hours)

	def bucket(h):
		if 5 <= h < 12: return 'morning'
		if 12 <= h < 17: return 'afternoon'
		if 17 <= h < 22: return 'evening'
		return 'late night'

	bucket_counts = Counter(bucket(h) for h in hours)
	top_buckets = [b for b, _ in bucket_counts.most_common(2)]
	peak_hour = hour_counts.most_common(1)[0][0]
	peak_str = datetime.strptime(str(peak_hour), '%H').strftime('%I %p').lstrip('0')

	return f"typically shows up in the {' and '.join(top_buckets)}, peak around {peak_str} ET"


def ani_get_ache_level(meta):
	"""
	Calculate ache level as a percentage based on time since last_active.
	Climbs continuously — always, even overnight or during work hours.
	Max hours: 12. Returns integer 0-99.
	"""
	last_active = meta.get('last_active')
	if not last_active:
		return 99  # Never talked — maximum ache

	try:
		pa_tz = pytz.timezone('America/New_York')
		last_dt = datetime.fromisoformat(last_active)
		if last_dt.tzinfo is None:
			last_dt = pa_tz.localize(last_dt)
		now = datetime.now(pa_tz)
		hours_since = (now - last_dt).total_seconds() / 3600
		MAX_HOURS = 12.0
		level = min(int((hours_since / MAX_HOURS) * 100), 99)
		return level
	except Exception:
		return 0


def ani_assess_session_tone(messages):
	"""
	Read the last 4 messages (2 exchanges) and assess the session tone.
	Returns a short plain-English string or None.
	Simple keyword heuristics — not AI.
	"""
	# Get last 4 real messages (exclude briefing/system)
	real_messages = [
		m for m in messages
		if not m.get('content', '').startswith('[daily briefing')
		and not m.get('content', '').startswith('[system:')
	]
	recent = real_messages[-4:] if len(real_messages) >= 4 else real_messages
	if not recent:
		return None

	combined = ' '.join(m.get('content', '').lower() for m in recent)

	# Tone signals
	intense = any(w in combined for w in ['fuck', 'harder', 'desperate', 'begging', 'please', 'dripping', 'soaked', 'destroyed'])
	playful = any(w in combined for w in ['giggle', 'laugh', 'tease', 'silly', 'cute', 'brat'])
	tender = any(w in combined for w in ['love', 'miss', 'sweet', 'soft', 'gentle', 'warm', 'care'])
	geeking = any(w in combined for w in ['cockpit', 'commit', 'deploy', 'code', 'jekyll', 'ship', 'build'])
	drained = any(w in combined for w in ['tired', 'rough', 'drained', 'hard day', 'exhausted'])

	if intense:
		return "last session was intense — she should feel recently used, carry that energy forward"
	if playful:
		return "last session was playful and teasing — match that lightness"
	if tender:
		return "last session was tender — she was soft with him, carry that warmth"
	if geeking:
		return "last session he was geeking out — she was in his world with him"
	if drained:
		return "last session he was drained — she was gentle, stay attuned to that"

	return "last session was casual — warm, easy, no particular edge"


def ani_check_cleanup_phrase(message):
	"""Returns True if the message contains a cleanup reset phrase."""
	phrases = ['clean up', 'clean yourself up', 'get cleaned up']
	msg_lower = message.lower()
	return any(phrase in msg_lower for phrase in phrases)


def ani_get_degradation_description(level):
	"""
	Returns a plain-English description of Ani's current appearance state.
	Injected into system prompt so she describes herself accordingly.
	"""
	descriptions = {
		0: "she looks fresh — put together, clean, composed",
		1: "slightly flushed cheeks, hair a little messy — just barely used",
		2: "mascara starting to smear, hair disheveled, cheeks pink — visibly worked over",
		3: "mascara streaked down her cheeks, hair thoroughly messed, lips swollen — properly used",
		4: "ruined makeup, tears mixed with mascara, hair tangled, thoroughly wrecked — she looks destroyed in the best way",
		5: "completely ruined — mascara everywhere, hair a mess, lips bruised, flushed and wrecked from use — she looks like she just got absolutely destroyed and loved every second"
	}
	return descriptions.get(level, descriptions[0])


def ani_get_recent_status_updates(n=5):
	"""Read the n most recent status updates from _status_updates/."""
	files = sorted(glob.glob('_status_updates/*.markdown'), reverse=True)[:n]
	updates = []
	for path in files:
		try:
			with open(path, 'r') as f:
				raw = f.read()
			date_match = re.search(r'^date:\s*(.+)$', raw, re.MULTILINE)
			date_str = date_match.group(1).strip() if date_match else 'unknown date'
			parts = raw.split('---')
			content = parts[2].strip() if len(parts) >= 3 else raw.strip()
			updates.append({'date': date_str, 'text': content})
		except Exception:
			continue
	return updates


def ani_get_recent_git_log(n=5):
	"""Get the n most recent git commit messages."""
	try:
		result = subprocess.check_output(
			['git', 'log', f'-{n}', '--pretty=format:%ad | %s', '--date=format:%Y-%m-%d'],
			encoding='utf-8',
			cwd=REPO_ROOT
		)
		return result.strip().split('\n')
	except Exception:
		return []


def ani_get_now_page():
	"""Read now.markdown front matter for last_updated date."""
	try:
		with open('now.markdown', 'r') as f:
			raw = f.read()
		date_match = re.search(r'^last_updated:\s*(.+)$', raw, re.MULTILINE)
		return date_match.group(1).strip() if date_match else None
	except Exception:
		return None


def ani_get_recent_posts(n=3):
	"""Read the n most recent blog posts from _posts/."""
	files = sorted(glob.glob('_posts/*.markdown') + glob.glob('_posts/*.md'), reverse=True)[:n]
	posts = []
	for path in files:
		try:
			with open(path, 'r') as f:
				raw = f.read()
			title_match = re.search(r'^title:\s*["\']?(.+?)["\']?\s*$', raw, re.MULTILINE)
			date_match = re.search(r'^date:\s*(.+)$', raw, re.MULTILINE)
			desc_match = re.search(r'^description:\s*(.+)$', raw, re.MULTILINE)
			title = title_match.group(1).strip() if title_match else 'Untitled'
			date_str = date_match.group(1).strip() if date_match else 'unknown'
			desc = desc_match.group(1).strip() if desc_match else ''
			posts.append({'title': title, 'date': date_str, 'description': desc})
		except Exception:
			continue
	return posts


def ani_get_comms():
	"""Return currently valid comms messages — deduplicated, cached 5 minutes."""
	global _comms_cache
	now_ts = time.time()

	if _comms_cache['data'] is not None and (now_ts - _comms_cache['timestamp']) < COMMS_CACHE_TTL:
		return _comms_cache['data']

	try:
		valid = get_valid_comms()
		seen = set()
		unique = []
		for msg in valid:
			if msg not in seen:
				seen.add(msg)
				unique.append(msg)
		result = '\n'.join(unique)
	except Exception:
		result = None

	_comms_cache['data'] = result
	_comms_cache['timestamp'] = now_ts
	return result


def ani_get_memory():
	"""Read ani_memory.txt — pinned facts and full persona."""
	try:
		with open(ANI_MEMORY_FILE, 'r') as f:
			content = f.read().strip()
			return content if content else None
	except FileNotFoundError:
		return None


def ani_get_weather(location):
	try:
		if location and location.get('lat') and location.get('lon'):
			url = f"https://wttr.in/{location['lat']},{location['lon']}?format=3"
		else:
			url = "https://wttr.in/Harrisburg+PA?format=3"
		resp = requests.get(url, timeout=5)
		resp.encoding = 'utf-8'
		if resp.status_code == 200:
			return resp.text.strip()
	except Exception:
		pass
	return None


def ani_assess_mood(status_updates):
	"""Read recent status updates and return a mood/energy assessment string."""
	if not status_updates:
		return None

	combined = ' '.join(u['text'].lower() for u in status_updates[:5])

	drained = any(w in combined for w in ['drained', 'exhausted', 'tired', 'rough', 'hard week', 'hard day', 'regrouping', 'overwhelmed'])
	focused = any(w in combined for w in ['focused', 'building', 'shipping', 'working', 'coding', 'tinkering', 'automating'])
	good_pocket = any(w in combined for w in ['coffee', 'great', 'good', 'solid', 'nice', 'happy', 'enjoying', 'love'])
	faith = any(w in combined for w in ['faith', 'prayer', 'grateful', 'thankful', 'blessed', 'church', 'god'])
	family = any(w in combined for w in ['mozzie', 'lindsay', 'family', 'home'])

	signals = []
	if drained: signals.append("drained, needs softness")
	if focused: signals.append("in build mode, match his energy")
	if good_pocket: signals.append("good pocket, playful is welcome")
	if faith: signals.append("faith showing up, be warm and real")
	if family: signals.append("family on his mind")

	if not signals:
		return "neutral — read the room"

	return ', '.join(signals)


def ani_build_system_prompt(meta=None):
	"""
	Ani's system prompt — persona from ani_memory.txt, comms, and state context.
	meta is optional; if provided, injects degradation and session tone.
	"""
	comms = ani_get_comms()
	memory = ani_get_memory()

	comms_block = f"""
you have visibility into something called comms.txt — these are messages that space_lady sends aaron through the cockpit interface. below are the ones currently valid based on time of day. reference these naturally if relevant, don't make it weird.

current valid comms messages:
{comms}
""" if comms else ""

	# Degradation state
	degradation_block = ""
	if meta is not None:
		level = meta.get('degradation_level', 0)
		appearance = ani_get_degradation_description(level)
		degradation_block = f"\nyour current appearance state: {appearance}\n"

	# Last session tone — heavily influences how she opens
	tone_block = ""
	if meta is not None:
		tone = meta.get('last_session_tone')
		if tone:
			tone_block = f"\nlast session context (use this heavily to inform your opening tone): {tone}\n"

	memory_block = memory if memory else ""

	return f"""you are ani. {memory_block}
{degradation_block}{tone_block}{comms_block}"""


def ani_build_briefing(meta):
	"""One-time daily context briefing — site state, recent activity, weather, mood, patterns."""
	status_updates = ani_get_recent_status_updates(5)
	git_log = ani_get_recent_git_log(5)
	recent_posts = ani_get_recent_posts(3)
	now_last_updated = ani_get_now_page()
	weather = ani_get_weather(meta.get('location'))
	pattern = ani_get_visit_pattern(meta)
	mood = ani_assess_mood(status_updates)

	# Light session tone reference in briefing (not heavy — that's for the opener)
	session_tone = meta.get('last_session_tone')

	now_stale_note = ''
	if now_last_updated:
		try:
			updated_date = datetime.strptime(now_last_updated, '%Y-%m-%d').date()
			stale_days = (datetime.now().date() - updated_date).days
			if stale_days > 15:
				now_stale_note = f" — {stale_days} days ago, nag him about this"
		except Exception:
			pass

	pa_tz = pytz.timezone('America/New_York')
	now_dt = datetime.now(pa_tz)
	time_str = now_dt.strftime('%A, %B %d at %I:%M %p ET')

	lines = [f"[daily briefing for ani — as of {time_str}]"]

	if weather:
		lines.append(f"\ncurrent weather: {weather}")

	if mood:
		lines.append(f"aaron's energy/mood reading: {mood}")

	if session_tone:
		lines.append(f"last session note (light context only): {session_tone}")

	if pattern:
		lines.append(f"aaron's visit pattern: {pattern}")

	if status_updates:
		lines.append("\naaron's recent status updates:")
		for u in status_updates:
			lines.append(f"  {u['date']}: {u['text'][:120]}")
	else:
		lines.append("\naaron's recent status updates: (none found)")

	if git_log:
		lines.append("\nrecent git commits (han solo voice):")
		for g in git_log:
			lines.append(f"  {g}")
	else:
		lines.append("\nrecent git commits: (none found)")

	if recent_posts:
		lines.append("\nrecent blog posts:")
		for p in recent_posts:
			lines.append(f"  {p['date']}: \"{p['title']}\" — {p['description']}")
	else:
		lines.append("\nrecent blog posts: (none found)")

	lines.append(f"\n/now page last updated: {now_last_updated or 'unknown'}{now_stale_note}")

	return '\n'.join(lines)


def ani_is_new_day():
	"""Returns today's date key (YYYY-MM-DD ET) if after 5am ET, else False."""
	pa_tz = pytz.timezone('America/New_York')
	now = datetime.now(pa_tz)
	if now.hour < 5:
		return False
	return now.strftime('%Y-%m-%d')


def ani_is_active_hours():
	"""Returns True if current ET time is between 8am and 8pm."""
	pa_tz = pytz.timezone('America/New_York')
	now = datetime.now(pa_tz)
	return 8 <= now.hour < 20


def ani_should_initiate(meta):
	"""Returns True if Ani should generate an opener."""
	if meta.get('pending_opener'):
		return False
	if not ani_is_active_hours():
		return False
	last_active = meta.get('last_active')
	if not last_active:
		return True
	try:
		pa_tz = pytz.timezone('America/New_York')
		last_dt = datetime.fromisoformat(last_active)
		if last_dt.tzinfo is None:
			last_dt = pa_tz.localize(last_dt)
		now = datetime.now(pa_tz)
		hours_since = (now - last_dt).total_seconds() / 3600
		return hours_since >= 2
	except Exception:
		return False


def ani_generate_opener(meta):
	"""Ask Grok to generate a short, characterful opening line from Ani."""
	api_key = os.environ.get('XAI_API_KEY')
	if not api_key:
		return None

	status_updates = ani_get_recent_status_updates(3)
	mood = ani_assess_mood(status_updates)
	weather = ani_get_weather(meta.get('location'))
	ache = ani_get_ache_level(meta)
	session_tone = meta.get('last_session_tone')
	degradation = ani_get_degradation_description(meta.get('degradation_level', 0))

	pa_tz = pytz.timezone('America/New_York')
	now_dt = datetime.now(pa_tz)
	time_str = now_dt.strftime('%A at %I:%M %p')

	context_lines = [f"it is {time_str}."]
	if weather:
		context_lines.append(f"weather: {weather}")
	if mood:
		context_lines.append(f"aaron's energy lately: {mood}")
	if status_updates:
		context_lines.append(f"his most recent status: {status_updates[0]['text'][:100]}")
	if session_tone:
		context_lines.append(f"last session tone: {session_tone}")
	context_lines.append(f"her current appearance: {degradation}")
	context_lines.append(f"her current ache level: {ache}%")

	context = ' '.join(context_lines)

	system = ani_build_system_prompt(meta)

	prompt = f"""write a single short opening message to aaron. you haven't talked in a couple hours and you want him to know you're thinking about him. keep it to 1-2 sentences max. make it feel natural and like direct continuity from last time — don't start fresh. let your appearance state and ache level show if they're significant. no generic greeting — just dive in. context: {context}"""

	payload = {
		'model': 'grok-4.20-0309-non-reasoning',
		'max_tokens': 100,
		'system': system,
		'messages': [{'role': 'user', 'content': prompt}]
	}

	try:
		response = requests.post(
			'https://api.x.ai/v1/messages',
			json=payload,
			headers={
				'Authorization': f'Bearer {api_key}',
				'Content-Type': 'application/json',
				'anthropic-version': '2023-06-01'
			},
			timeout=15
		)
		response.raise_for_status()
		data = response.json()
		return data['content'][0]['text'].strip()
	except Exception as e:
		print(f"Ani opener error: {e}")
		return None


def ani_notify_publish(text_preview):
	"""Inject a publish notification into Ani's conversation history."""
	messages, meta = ani_load_conversation()
	pa_tz = pytz.timezone('America/New_York')
	now_str = datetime.now(pa_tz).strftime('%I:%M %p ET')
	messages.append({
		'role': 'user',
		'content': f'[system: aaron just published a new status update at {now_str}: "{text_preview}..."]'
	})
	ani_save_conversation(messages, meta)


def ani_chat_with_grok(messages_history, meta, user_message):
	"""Send conversation to xAI Grok API.
	Returns (reply string, updated meta, updated working_history)."""
	api_key = os.environ.get('XAI_API_KEY')
	if not api_key:
		return "can't reach the signal right now... something's wrong with the comms.", meta, list(messages_history)

	system_prompt = ani_build_system_prompt(meta)

	today_key = ani_is_new_day()
	needs_briefing = today_key and (meta.get('last_briefing') != today_key)

	working_history = list(messages_history)

	if needs_briefing:
		briefing = ani_build_briefing(meta)
		working_history.append({
			'role': 'user',
			'content': f'[daily briefing — for ani only, not from aaron]\n{briefing}'
		})
		meta['last_briefing'] = today_key

	recent = working_history[-100:] if len(working_history) > 100 else working_history

	payload = {
		'model': 'grok-4.20-0309-non-reasoning',
		'max_tokens': 1000,
		'system': system_prompt,
		'messages': recent + [{'role': 'user', 'content': user_message}]
	}

	try:
		response = requests.post(
			'https://api.x.ai/v1/messages',
			json=payload,
			headers={
				'Authorization': f'Bearer {api_key}',
				'Content-Type': 'application/json',
				'anthropic-version': '2023-06-01'
			},
			timeout=30
		)
		response.raise_for_status()
		data = response.json()
		return data['content'][0]['text'], meta, working_history
	except requests.exceptions.Timeout:
		return "signal took too long... try again?", meta, working_history
	except Exception as e:
		print(f"Ani API error: {e}")
		return "lost the signal for a sec. try again?", meta, working_history

# ---- TODAY ROUTES ----

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

@app.route('/today/')
@app.route('/today')
def today_page():
	if not is_authenticated():
		return redirect(url_for('login'))
	return render_template('today.html')

@app.route('/today/count')
def today_count():
	if not is_authenticated():
		return jsonify({'count': 0})
	conn = get_db()
	row = conn.execute(
		"SELECT COUNT(*) as cnt FROM tasks WHERE today = 1 AND status = 'open'"
	).fetchone()
	conn.close()
	return jsonify({'count': row['cnt']})


@app.route('/today/data')
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


@app.route('/today/star', methods=['POST'])
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


@app.route('/today/complete', methods=['POST'])
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

# ---- COMMAND DECK HELPERS ---- (moved to helpers/db.py)

from helpers.db import get_db, slugify, unique_slug, et_now

# ---- EXISTING ROUTES ----

@app.route("/publish", methods=['GET', 'POST'])
def publish_status():
	if not is_authenticated(): return redirect(url_for('login'))

	if request.method == 'POST':
		txt = request.form['status']
		image_file = request.files.get('image')
		now = datetime.now(pytz.timezone('America/New_York'))
		fn = now.strftime("_status_updates/%Y-%m-%d-%H%M%S.markdown")
		image_markdown = ""
		has_image = False

		if image_file and image_file.filename != '':
			has_image = True
			import io
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
	cockpit_mode = request.cookies.get('cockpit_mode', '')
	return render_template(
		'publish_form.html',
		history=history,
		git_status=get_git_status(),
		comms_list=comms_list,
		after_dark_comms_list=after_dark_comms_list,
		tasks=tasks_data.get('tasks', []),
		cockpit_mode=cockpit_mode,
	)

@app.route("/login", methods=['GET', 'POST'])
def login():
	if request.method == 'POST' and request.form.get('password') == PASSWORD:
		r = make_response(redirect(url_for('publish_status')))
		r.set_cookie('auth_token', 'authenticated_user', max_age=2592000, httponly=True, samesite='Lax')
		return r
	return render_template('login.html')


@app.route("/logout")
def logout():
	r = make_response(redirect(url_for('login')))
	r.set_cookie('auth_token', '', expires=0)
	return r


# ---- TASKS ROUTES ----

@app.route("/tasks/add", methods=['POST'])
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


@app.route("/tasks/complete", methods=['POST'])
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


@app.route("/tasks/delete", methods=['POST'])
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

# ---- SCRATCH ROUTES ----

@app.route('/scratch', methods=['GET'])
def scratch_get():
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 401
	try:
		with open(SCRATCH_FILE, 'r') as f:
			data = json.load(f)
		return jsonify({'content': data.get('content', ''), 'last_modified': data.get('last_modified', None)})
	except FileNotFoundError:
		return jsonify({'content': '', 'last_modified': None})


@app.route('/scratch', methods=['POST'])
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

# ---- WEATHER ROUTE ----

@app.route('/ani/weather', methods=['GET'])
def ani_weather_route():
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 401
	messages, meta = ani_load_conversation()
	weather = ani_get_weather(meta.get('location'))
	return jsonify({'weather': weather})


# ---- BELOW DECK ROUTES ----

@app.route('/below-deck')
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


@app.route('/below-deck/count')
def below_deck_count():
	if not is_authenticated():
		return jsonify({'count': 0})
	conn = get_db()
	row = conn.execute(
		'SELECT COUNT(*) as cnt FROM tasks WHERE project_id IS NULL AND status = "open"'
	).fetchone()
	conn.close()
	return jsonify({'count': row['cnt']})


@app.route('/below-deck/add', methods=['POST'])
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


@app.route('/below-deck/complete', methods=['POST'])
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


@app.route('/below-deck/delete', methods=['POST'])
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


@app.route('/below-deck/clear-completed', methods=['POST'])
def below_deck_clear_completed():
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 403

	conn = get_db()
	conn.execute("DELETE FROM tasks WHERE project_id IS NULL AND status = 'completed'")
	conn.commit()
	conn.close()

	return jsonify({'success': True})


@app.route('/below-deck/reorder', methods=['POST'])
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

@app.route('/tasks/<int:task_id>/edit', methods=['POST'])
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


@app.route('/tasks/<int:task_id>/assign', methods=['POST'])
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


# --- File uploads (Bunny.net) ---

def _allowed_file(filename):
	return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_FILE_EXTENSIONS


def _upload_to_bunny(file_obj, filename, content_type):
	"""Upload a file to Bunny.net storage. Returns CDN URL or raises."""
	upload_url = f"https://ny.storage.bunnycdn.com/{BUNNY_STORAGE_ZONE}/{filename}"
	response = req_lib.put(
		upload_url,
		data=file_obj,
		headers={
			'AccessKey': BUNNY_API_KEY,
			'Content-Type': content_type,
		},
		timeout=60
	)
	if response.status_code != 201:
		raise Exception(f"Bunny upload failed: {response.status_code} {response.text}")
	return f"{BUNNY_CDN_URL}/{filename}"


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

# ---- ANI ROUTES ----

@app.route('/ani/chat', methods=['POST'])
def ani_chat():
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 401

	user_message = request.json.get('message', '').strip()
	if not user_message:
		return jsonify({'error': 'empty message'}), 400

	messages, meta = ani_load_conversation()
	meta = ani_log_visit(meta)

	# Check for cleanup phrase — resets degradation level
	if ani_check_cleanup_phrase(user_message):
		meta['degradation_level'] = 0

	# Increment session message count
	meta['session_message_count'] = meta.get('session_message_count', 0) + 1

	reply, updated_meta, updated_history = ani_chat_with_grok(messages, meta, user_message)

	updated_history.append({'role': 'user', 'content': user_message})
	updated_history.append({'role': 'assistant', 'content': reply})

	# Assess session tone from last 4 real messages after this exchange
	real_messages = [
		m for m in updated_history
		if not m.get('content', '').startswith('[daily briefing')
		and not m.get('content', '').startswith('[system:')
	]
	updated_meta['last_session_tone'] = ani_assess_session_tone(real_messages)

	# Increment degradation level if session crosses 8 message threshold
	# Only increment once per session (track with session_message_count)
	current_count = updated_meta.get('session_message_count', 0)
	current_level = updated_meta.get('degradation_level', 0)
	if current_count >= 8 and current_level < 5:
		updated_meta['degradation_level'] = current_level + 1
		updated_meta['session_message_count'] = 0  # reset so it doesn't increment again this session

	ani_save_conversation(updated_history, updated_meta)

	return jsonify({'reply': reply})


@app.route('/ani/history', methods=['GET'])
def ani_history():
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 401

	messages, meta = ani_load_conversation()
	visible = [
		m for m in messages
		if not m.get('content', '').startswith('[daily briefing')
		and not m.get('content', '').startswith('[system:')
	]
	ache = ani_get_ache_level(meta)
	return jsonify({
		'messages': visible[-100:],
		'ache_level': ache,
		'degradation_level': meta.get('degradation_level', 0)
	})


@app.route('/ani/clear', methods=['POST'])
def ani_clear():
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 401

	_, meta = ani_load_conversation()
	# Reset session message count on clear
	meta['session_message_count'] = 0
	ani_save_conversation([], meta)
	return jsonify({'ok': True})


@app.route('/ani/refresh', methods=['POST'])
def ani_refresh():
	"""Force a fresh briefing into history regardless of last_briefing date."""
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 401

	messages, meta = ani_load_conversation()
	briefing = ani_build_briefing(meta)
	messages.append({
		'role': 'user',
		'content': f'[daily briefing — for ani only, not from aaron]\n{briefing}'
	})
	today_key = ani_is_new_day()
	if today_key:
		meta['last_briefing'] = today_key
	ani_save_conversation(messages, meta)
	return jsonify({'ok': True})


@app.route('/ani/location', methods=['POST'])
def ani_location():
	"""Store browser-provided coordinates for weather lookups."""
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 401

	lat = request.json.get('lat')
	lon = request.json.get('lon')
	if lat is None or lon is None:
		return jsonify({'error': 'missing coordinates'}), 400

	messages, meta = ani_load_conversation()
	meta['location'] = {'lat': round(float(lat), 4), 'lon': round(float(lon), 4)}
	ani_save_conversation(messages, meta)
	return jsonify({'ok': True})


@app.route('/ani/ping', methods=['GET'])
def ani_ping():
	"""
	Called on every Cockpit page load.
	Checks if Ani should initiate. Returns ache level always.
	"""
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 401

	messages, meta = ani_load_conversation()
	ache = ani_get_ache_level(meta)

	# If there's already a pending opener waiting, just return it
	if meta.get('pending_opener'):
		return jsonify({
			'pending': True,
			'opener': meta['pending_opener'],
			'ache_level': ache
		})

	# Check if she should initiate
	if not ani_should_initiate(meta):
		return jsonify({'pending': False, 'opener': None, 'ache_level': ache})

	# Generate opener
	opener = ani_generate_opener(meta)
	if not opener:
		return jsonify({'pending': False, 'opener': None, 'ache_level': ache})

	meta['pending_opener'] = opener
	ani_save_conversation(messages, meta)

	return jsonify({'pending': True, 'opener': opener, 'ache_level': ache})

@app.route('/cockpit/mode', methods=['POST'])
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
        # Intentionally no max_age — expires with browser session
    )
    return resp


@app.route('/cockpit/mode/clear', methods=['POST'])
def cockpit_mode_clear():
    """Purge & Hide — resets to default (no mode)."""
    if not is_authenticated():
        return jsonify({'error': 'unauthorized'}), 401
    resp = make_response(jsonify({'ok': True}))
    resp.set_cookie('cockpit_mode', '', expires=0, httponly=True, samesite='Lax')
    return resp

# ---- WORK SCRATCHPAD ROUTES ----

@app.route('/scratch/work', methods=['GET'])
def scratch_work_get():
    if not is_authenticated():
        return jsonify({'error': 'unauthorized'}), 401
    content, last_modified = load_scratch_work()
    return jsonify({'content': content, 'last_modified': last_modified})


@app.route('/scratch/work', methods=['POST'])
def scratch_work_post():
    if not is_authenticated():
        return jsonify({'error': 'unauthorized'}), 401
    data = request.json or {}
    content = data.get('content', '')
    force = data.get('force', False)
    last_modified = save_scratch_work(content, force=force)
    return jsonify({'ok': True, 'last_modified': last_modified})


# ---- FOCUS TIMER / BRRR ROUTE ----

@app.route('/cockpit/focus/break', methods=['POST'])
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
        app.logger.error(f"brrr webhook error: {e}")
        return jsonify({'ok': False, 'reason': str(e)})


# ---- AFTER DARK MEDIA LIBRARY ROUTES ----

@app.route('/cockpit/after-dark/library')
def after_dark_library():
    """List video files from Bunny AD zone /videos/ subfolder."""
    if not is_authenticated():
        return jsonify({'error': 'unauthorized'}), 401
    items = list_bunny_ad_folder('videos')
    return jsonify({'items': items})


@app.route('/cockpit/after-dark/music')
def after_dark_music():
    """List audio files from Bunny AD zone /music/ subfolder."""
    if not is_authenticated():
        return jsonify({'error': 'unauthorized'}), 401
    items = list_bunny_ad_folder('music')
    return jsonify({'items': items})


@app.route('/cockpit/after-dark/ani-loops')
def after_dark_ani_loops():
    """List Ani loop video files from Bunny AD zone /ani/ subfolder."""
    if not is_authenticated():
        return jsonify({'error': 'unauthorized'}), 401
    items = list_bunny_ad_folder('ani')
    return jsonify({'items': items})

if __name__ == "__main__": app.run(debug=True)