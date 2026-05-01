"""Ani blueprint — private AI companion (xAI Grok). Slide-up panel UI lives in publish_form.html.

Routes: /ani/chat, /ani/history, /ani/clear, /ani/refresh, /ani/location, /ani/ping, /ani/weather
Internal helpers: ~24 ani_* functions (conversation persistence, ache tracking, briefing,
session-tone assessment, weather lookup, opener generation, Grok client).
"""
import os
import json
import subprocess
import glob
import re
from datetime import datetime, timedelta
import pytz
import requests
from flask import Blueprint, request, jsonify

from helpers.auth import is_authenticated
from helpers.comms import get_active_tags

# Path constants for Ani's runtime files (gitignored, server-state).
ANI_CONVERSATION_FILE = 'ani_conversation.json'
ANI_MEMORY_FILE = 'static/ani_memory.txt'

ani_bp = Blueprint('ani', __name__)


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


# ---- ROUTES ----

@ani_bp.route('/ani/weather', methods=['GET'])
def ani_weather_route():
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 401
	messages, meta = ani_load_conversation()
	weather = ani_get_weather(meta.get('location'))
	return jsonify({'weather': weather})


@ani_bp.route('/ani/chat', methods=['POST'])
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


@ani_bp.route('/ani/history', methods=['GET'])
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


@ani_bp.route('/ani/clear', methods=['POST'])
def ani_clear():
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 401

	_, meta = ani_load_conversation()
	# Reset session message count on clear
	meta['session_message_count'] = 0
	ani_save_conversation([], meta)
	return jsonify({'ok': True})


@ani_bp.route('/ani/refresh', methods=['POST'])
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


@ani_bp.route('/ani/location', methods=['POST'])
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


@ani_bp.route('/ani/ping', methods=['GET'])
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

@ani_bp.route('/cockpit/mode', methods=['POST'])
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


@ani_bp.route('/cockpit/mode/clear', methods=['POST'])
def cockpit_mode_clear():
    """Purge & Hide — resets to default (no mode)."""
    if not is_authenticated():
        return jsonify({'error': 'unauthorized'}), 401
    resp = make_response(jsonify({'ok': True}))
    resp.set_cookie('cockpit_mode', '', expires=0, httponly=True, samesite='Lax')
    return resp

