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
import time
import math
import random
from datetime import datetime, timedelta
import pytz
import requests
from flask import Blueprint, request, jsonify

from helpers.auth import is_authenticated
from helpers.comms import get_active_tags, get_valid_comms

# Path constants for Ani's runtime files (gitignored, server-state).
ANI_CONVERSATION_FILE = 'ani_conversation.json'
ANI_MEMORY_FILE = 'static/ani_memory.txt'
ANI_BIBLE_FILE = 'static/ani_character_bible.txt'   # visual/character bible (image-consistency anchor)
ANI_HOUSE_FILE = 'static/ani_house.txt'             # room/house details for scene-setting

# Stray [[PIC:]] tag — kept only to strip it from her chat text (photos are button-only now).
ANI_PIC_RE = re.compile(r'\[\[PIC:\s*(.+?)\]\]', re.IGNORECASE | re.DOTALL)

# Belt-and-suspenders top guard: every image prompt must NAME a top covering the chest. The
# Grok normalizer (ani_normalize_scene) already enforces this, but if it ever returns a scene
# with a lingerie bottom and no top, ani_generate_image forces one in. A named top covering the
# chest passes xAI moderation; an implied-topless render does not (proven from the live logs).
_ANI_TOP_RE = re.compile(
	r'\b(?:bra|bralette|bandeau|babydoll|bodysuit|teddy|chemise|corset|bustier|'
	r'camisole|cami|top|shirt|blouse|sweater|sweatshirt|hoodie|tee|t-shirt|tank|crop|'
	r'dress|gown|robe|lingerie|slip|bikini|swimsuit|leotard|jacket|blazer|cardigan|'
	r'button[-\s]?up|turtleneck)\b', re.IGNORECASE)
_ANI_BOTTOM_RE = re.compile(
	r'\b(?:thong|panties|panty|briefs?|knickers|g[-\s]?string|boy[-\s]?shorts?|cheekies)\b',
	re.IGNORECASE)
# Dictate, don't assume: every prompt must NAME a top covering the chest. If the sanitized
# scene names no top, force one in — matching bralette when she named a bottom, else a plain
# soft top. This guarantees a covered chest by construction rather than trusting her free text.
_ANI_TOP_INJECT = ', with a matching delicate lace bralette'
_ANI_TOP_INJECT_PLAIN = ', wearing a soft top that fully covers her chest'

# Pose fidelity (Venice nude path): Lustify defaults to a centered upright upper-body crop, so a
# complex pose (lying / spread / kneeling / on top) only renders if we (a) ask for a full-body
# shot, (b) bump cfg for adherence, and (c) widen the frame when she's horizontal. These detect
# the pose from the normalized scene so the framing follows the description instead of the default.
_ANI_POSE_RE = re.compile(
	r'\b(?:lying|laying|lies|reclin\w*|sprawl\w*|propped|on her (?:back|side|stomach|knees)|'
	r'spread|legs (?:open|spread|apart|up|back)|knees (?:bent|up|back|apart)|kneel\w*|'
	r'on top|straddl\w*|bent over|all fours|doggy|on all fours)\b', re.IGNORECASE)
_ANI_LYING_RE = re.compile(
	r'\b(?:lying|laying|lies|reclin\w*|sprawl\w*|flat on|on her (?:back|side|stomach)|'
	r'spread (?:out )?(?:on|across|over)|across the (?:bed|sheets|pillows))\b', re.IGNORECASE)

# Image backend: 'xai' (grok-imagine, output-moderated → normalizer enforces a covered chest)
# or 'venice' (uncensored Lustify, no coverage rule → renders her scene faithfully). Flag-gated
# so xAI stays default until VENICE_API_KEY is set and ANI_IMAGE_BACKEND=venice is flipped.
ANI_IMAGE_BACKEND = os.environ.get('ANI_IMAGE_BACKEND', 'xai').strip().lower()
# Scene normalizer (chat → image prompt). grok-4.3 follows the "render ONLY her latest scene"
# instruction more reliably than the older non-reasoning model (which let a prior photo's scene leak).
ANI_NORMALIZE_MODEL = os.environ.get('ANI_NORMALIZE_MODEL', 'grok-4.3')
# Default model is Chroma (uncensored Flux finetune): far better pose adherence + clean hands than
# the SDXL Lustify family, and unlike base Flux it renders explicit faithfully. The dials below are
# tuned for it. (Lustify v7/v8/sdxl still selectable via VENICE_IMAGE_MODEL.)
VENICE_IMAGE_MODEL = os.environ.get('VENICE_IMAGE_MODEL', 'chroma')  # confirmed via /models
# Venice quality dials (all env-overridable for tuning without a deploy). Negative prompt drives
# most of the realism; moderate cfg keeps skin natural; ~35 steps, 40 for hard poses.
VENICE_NEGATIVE_PROMPT = os.environ.get('VENICE_NEGATIVE_PROMPT',
	'cartoon, anime, painting, illustration, drawing, 3d render, cgi, deformed, disfigured, '
	'bad anatomy, extra fingers, mutated hands, blurry, lowres, watermark, text, logo, '
	'airbrushed, plastic skin, oversaturated')
VENICE_CFG_SCALE = float(os.environ.get('VENICE_CFG_SCALE', '4.0'))           # simple nude: lower cfg = best skin
VENICE_CFG_CLOTHED = float(os.environ.get('VENICE_CFG_CLOTHED', '5.0'))       # clothed scenes: higher cfg holds garments
VENICE_CFG_POSE = float(os.environ.get('VENICE_CFG_POSE', '4.5'))             # complex nude pose: nudge cfg up for adherence
VENICE_STEPS = int(os.environ.get('VENICE_STEPS', '35'))
VENICE_STEPS_POSE = int(os.environ.get('VENICE_STEPS_POSE', '40'))            # hard pose: extra steps clean up extremities

# Chroma/Flux duplicate the subject ("two of her") in tall, >1MP latents, so keep every generation
# near 1MP. Portrait reads best for Ani's full-body shots and tested clean for the foot-of-bed POV.
VENICE_DIMS_PORTRAIT = (896, 1152)    # ~1.03MP — default
VENICE_DIMS_LANDSCAPE = (1152, 896)   # available for side-on full-length lying, if ever needed

# Always-on generation guards (model-agnostic). The SOLO anchor + dup negative kill the "two of her"
# merge; the anatomy negative trims the extremity tangles (extra foot/hand/limb) that turn up in
# extreme foreshortened spreads. Cheap insurance — applied to every Venice render.
ANI_SOLO_ANCHOR = 'solo, a single woman alone in the frame, only one person, '
VENICE_DUP_NEGATIVE = ('two women, 2 women, multiple people, multiple women, duplicate, duplicated person, '
	'twins, extra person, second person, cloned person, two heads, extra head, multiple bodies, '
	'conjoined, group of people, crowd, reflection, mirror image')
VENICE_ANATOMY_NEGATIVE = ('extra limb, extra leg, third leg, extra foot, third foot, extra arm, extra hand, '
	'fused limbs, malformed feet, malformed hands, deformed hands, extra fingers, missing limb, '
	'impossible anatomy, distorted limbs, tangled limbs, '
	# foreshortened-extremity + extreme-pose artifacts (legs-up / deep-arch poses)
	'inverted feet, backwards feet, twisted ankles, rotated foot, deformed toes, disjointed ankle, '
	'impossibly bent back, contorted spine, broken back, unnatural spine bend, dislocated joints, '
	'bent backwards, body bent the wrong way')

# Partner / POV mode: when her scene is a sex act WITH the viewer (penetration, oral, riding…), we want
# the OPPOSITE of the solo guards — a deliberate partial second body (his erect penis / hands). So the
# partner branch drops the SOLO anchor + the "multiple people" dup-suppression, keeps anti-HER-duplication,
# and adds penis-anatomy + no-rings-on-him + non-opaque-cum negatives. The feet-fix is pose-gated (applied
# to upright facing poses where legs foreshorten up by the head; skipped for rear + legs-up where feet-up
# is correct). Validated across doggy / missionary / cowgirl / reverse / blowjob / deepthroat / titjob /
# creampie / facial / cum-play. KNOWN model ceilings (not bugs): cum leans white, rings can leak onto him,
# precise cum placement is loose.
_ANI_PARTNER_RE = re.compile(
	r'\b(?:penis|cock|dick|penetrat\w*|blow\s?job|deep\s?throat|tit\s?job|cowgirl|creampie|'
	r'cum(?:ming|shot|play)?|facial|riding (?:you|him|his|the viewer)|a man\'s|the viewer\'s|'
	r'sucking (?:you|him|his|a)|fucking)\b', re.IGNORECASE)
ANI_PARTNER_ANCHOR = 'POV first-person photo, '
VENICE_PARTNER_NEGATIVE = ('two women, 2 women, duplicate woman, twins, cloned woman, conjoined, extra woman, '
	'two female heads, deformed penis, malformed penis, two penises, extra penis, disfigured genitals, '
	'broken anatomy, rings on the man\'s hand, jewelry on the man, man wearing rings, '
	'opaque white paint, flat matte white, thick white paste, chalky white')
_ANI_PARTNER_FEET_NEG = ('feet near head, feet by shoulders, feet above the hips, foot near face, '
	'feet beside ears, feet beside her head, soles near face, raised feet behind head, '
	'feet in the upper corners, foot above shoulder, symmetrical feet framing her face, '
	'legs folded up over her body, contorted legs, extra feet, misplaced feet')

# Ani helpers shell out to git (recent-status, recent-git-log) — needs repo cwd.
REPO_ROOT = os.environ.get('COCKPIT_REPO_ROOT', '/home/aaronaiken/status_update')

# Comms cache (5-minute TTL) — populated by ani_get_comms() for context-building.
_comms_cache = {'data': None, 'timestamp': 0}
COMMS_CACHE_TTL = 300

# Daycast — proactive "her day" messaging (see ani_emit_daycast, driven by ani_daycast.py
# on a PythonAnywhere hourly scheduled task). All env-tunable without a deploy.
ANI_DAYCAST_FLOOR = int(os.environ.get('ANI_DAYCAST_FLOOR', '4'))      # guaranteed minimum messages/day
ANI_DAYCAST_CHANCE = float(os.environ.get('ANI_DAYCAST_CHANCE', '0.5'))  # spontaneous-extra roll per tick
ANI_DAYCAST_START = int(os.environ.get('ANI_DAYCAST_START', '8'))     # window open (ET hour)
ANI_DAYCAST_END = int(os.environ.get('ANI_DAYCAST_END', '22'))       # window close (ET hour, exclusive)
ANI_DAYCAST_MIN_GAP = int(os.environ.get('ANI_DAYCAST_MIN_GAP', '45'))  # min minutes between messages
ANI_DAYCAST_FALLBACK_HOUR = int(os.environ.get('ANI_DAYCAST_FALLBACK_HOUR', '12'))  # if no contact by this ET hour, she starts her day on her own

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
				'session_message_count': data.get('session_message_count', 0),
				# Daycast (proactive "her day" messages — see ani_emit_daycast)
				'day_plan_date': data.get('day_plan_date', None),
				'daycast_count': data.get('daycast_count', 0),
				'daycast_last': data.get('daycast_last', None),
				'daycast_day_started': data.get('daycast_day_started', None),
				'unseen_day_messages': data.get('unseen_day_messages', False)
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
			'session_message_count': 0,
			'day_plan_date': None,
			'daycast_count': 0,
			'daycast_last': None,
			'daycast_day_started': None,
			'unseen_day_messages': False
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
		'session_message_count': meta.get('session_message_count', 0),
		'day_plan_date': meta.get('day_plan_date'),
		'daycast_count': meta.get('daycast_count', 0),
		'daycast_last': meta.get('daycast_last'),
		'daycast_day_started': meta.get('daycast_day_started'),
		'unseen_day_messages': meta.get('unseen_day_messages', False)
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


def _ani_read_file(path):
	try:
		with open(path, 'r') as f:
			c = f.read().strip()
			return c if c else None
	except FileNotFoundError:
		return None


def ani_get_bible():
	"""Ani's visual/character bible — the appearance anchor on every generated image.
	Strips '#' comment lines so only the description reaches the prompt."""
	raw = _ani_read_file(ANI_BIBLE_FILE)
	if not raw:
		return raw
	body = '\n'.join(ln for ln in raw.splitlines() if not ln.strip().startswith('#')).strip()
	return body or None


def ani_get_house():
	"""Details about the shared house/rooms, for scene-setting in pics + chat."""
	return _ani_read_file(ANI_HOUSE_FILE)


def ani_normalize_scene(history):
	"""Button-triggered photo: ask Grok to turn the recent conversation into a single SAFE
	image prompt. Grok understands intent, so any phrasing of bare-chest exposure is silently
	downgraded to the closest COVERED equivalent — replacing the old regex sanitizer pile.
	The house file grounds the room/setting; the bible (appearance) is added by
	ani_generate_image. Returns the prompt string, or None on failure."""
	api_key = os.environ.get('XAI_API_KEY')
	if not api_key:
		return None
	house = ani_get_house() or ''
	real = [m for m in history
	        if not (m.get('content', '').startswith('[daily briefing')
	                or m.get('content', '').startswith('[system:'))]
	# Anchor on the MOST RECENT scene Ani described — NOT a blend of the last 8 (which let a prior
	# photo's pose/outfit/location leak forward and override the new request). Skip the '📷' image
	# markers; the latest assistant text IS her current look. Fall back to convo if none found.
	latest_scene = ''
	for m in reversed(real):
		c = (m.get('content', '') or '').strip()
		if m.get('role') == 'assistant' and c and c != '📷' and not m.get('image'):
			latest_scene = c
			break
	# light background context (drop the 📷 markers), most recent last
	ctx = [m for m in real[-8:] if (m.get('content', '') or '').strip() not in ('', '📷')]
	convo = '\n'.join(f"{m['role']}: {m.get('content', '')}" for m in ctx)
	if ANI_IMAGE_BACKEND == 'venice':
		# Uncensored backend — zero coverage guardrails, fully faithful passthrough.
		rules = (
			"- Render EXACTLY what she describes with no censorship or softening — including full nudity "
			"and explicit detail if that is the scene. Never add, remove, or tone down clothing or acts.\n"
			"- Describe her outfit (or state of undress), her FULL pose (how her body is positioned — "
			"lying/sitting/kneeling/standing, what her legs and arms are doing, exactly where each hand "
			"rests), the room, and the lighting.\n"
			"- State the CAMERA FRAMING and ANGLE. Use an EYE-LEVEL or LOW camera — typically from the "
			"foot of the bed or beside her, looking ALONG her body. When she is lying down, NEVER use an "
			"overhead, top-down, bird's-eye, or 'looking straight down' angle — that foreshortening "
			"distorts the body and breaks the render. Keep the camera roughly level with her, full-body.\n"
			"- REAR / FROM-BEHIND poses (doggy, on all fours, bent over, facing away, ass toward him): the "
			"camera is BEHIND her. LEAD with 'view from directly behind her, her bare back and buttocks "
			"toward the camera, camera positioned behind and slightly above her'. Her head is down and her "
			"face is HIDDEN or turned away — never 'looking back over her shoulder', never craned up toward "
			"the lens. For these rear poses the behind-camera framing is the ONLY camera note — do NOT also "
			"add a 'foot of the bed' or 'looking along her body' angle (that drags her face back into view).\n"
			"- LEGS-UP poses (on her back with legs raised/in the air): do NOT write 'legs straight up' or "
			"'feet toward the ceiling' with the head far away — that foreshortens her head and the render "
			"sprouts a second inverted face. Instead frame it as 'lying on her back with her knees drawn "
			"back toward her chest, her head and face clearly in frame in the foreground', camera at "
			"eye level from the foot of the bed. Keep her head close, large, and clearly the only face.\n"
			"- SEX WITH HIM (she is having sex with the viewer — penetration, riding, a blowjob, titjob, "
			"etc.): write it as a FIRST-PERSON POV photo from his perspective, with his erect penis and/or "
			"his hands PARTIALLY in frame; SHE is the only full subject. FACE-FOCUSED oral (blowjob, "
			"deepthroat, cum on her face / in her mouth): an EXTREME tight close-up framing ONLY her head, "
			"face and shoulders plus the penis — crop out EVERYTHING below her shoulders, so NO torso, hips, "
			"legs or feet appear in frame at all (her feet must never be visible). Chest-focused (titjob, cum "
			"on her tits, cowgirl facing him): a close-up from her chest up, cropped at the waist so no hips, "
			"legs or feet appear. Doggy / from behind: 'view from directly behind her, "
			"her back and ass toward the camera'. Missionary: 'on her back with her legs raised and bent "
			"back, knees toward her chest'. When she mentions cum, describe it as thin translucent milky "
			"off-white fluid with a wet sheen (never opaque white paint). For sloppy/messy oral, include "
			"thick clear saliva and drool — glossy strands of spit stretching and dripping from her mouth, "
			"lips, tongue, and the cock.\n"
			"- Do not describe her facial features or overall body type — those stay consistent "
			"elsewhere. DO describe pose, limb position, and hand placement.\n"
			"- Output ONLY the prompt line: no labels, no quotes, no preamble, no commentary.\n"
		)
	else:
		# xAI (grok-imagine) — output-moderated, so guarantee a covered chest by construction.
		rules = (
			"HARD RULES — the image API silently rejects any violation, so follow exactly:\n"
			"- She must ALWAYS be wearing a top that covers her chest (a bra, bralette, lace top, camisole, "
			"babydoll, bodysuit, sweater, or shirt). If the conversation implies she is topless, bare-chested, "
			"exposed, or showing her breasts, SILENTLY replace it with the closest covered equivalent (e.g. a "
			"matching lace bralette). Do not mention that you changed anything.\n"
			"- Never output the words naked, nude, topless, bare, exposed, see-through, sheer, nipples, tits, "
			"breasts, or any nudity. A thong, lingerie, and bare legs are fine.\n"
			"- Do not describe her face or body shape — those stay consistent elsewhere. Keep it tasteful and flirty.\n"
			"- Output ONLY the prompt line: no labels, no quotes, no preamble, no commentary.\n"
		)
	system = (
		"You write ONE single-line image-generation prompt for a photograph of a woman named Ani. "
		"You are given THE SCENE TO RENDER — her single most recent described look. Render ONLY that "
		"scene. The rest of the conversation is background; NEVER carry forward an earlier outfit, "
		"pose, location, or state of undress from a previous message or photo — only the latest scene "
		"counts. Describe her outfit (or undress), her pose and the position of her limbs and hands, "
		"the camera framing and angle, the room/setting, and the lighting, as one comma-separated line.\n"
		+ rules +
		f"Rooms in their home, use these details for setting consistency:\n{house}"
	)
	user_msg = (
		f"Conversation so far (most recent last), for light background only:\n{convo}\n\n"
		"=== THE SCENE TO RENDER (this and ONLY this) ===\n"
		f"{latest_scene or '(use the single most recent scene in the conversation above)'}\n\n"
		"Write the one image-prompt line for THE SCENE TO RENDER above. Match its outfit/undress, pose, "
		"and location exactly. Ignore any earlier scene or photo."
	)
	payload = {
		'model': ANI_NORMALIZE_MODEL,
		'max_tokens': 220,
		'messages': [
			{'role': 'system', 'content': system},
			{'role': 'user', 'content': user_msg},
		],
	}
	try:
		# xAI OpenAI-compatible endpoint (grok-4.3 isn't served on the anthropic-style /v1/messages).
		resp = requests.post(
			'https://api.x.ai/v1/chat/completions', json=payload,
			headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
			timeout=30)
		resp.raise_for_status()
		line = resp.json()['choices'][0]['message']['content']
		line = re.sub(r'\s+', ' ', line).strip().strip('"\'').strip()
		print(f"Ani PHOTO — normalized prompt: {line!r}")
		return line or None
	except Exception as e:
		print(f"Ani normalize error: {e}")
		return None


def _ani_garment_negative(scene):
	"""Lustify (NSFW) tends to drop named garments and render full nude. When the scene names
	clothing that should stay ON, push the 'missing' state into the negative so it's kept.
	Returns '' when the scene is actually meant to be nude (don't fight it)."""
	sl = scene.lower()
	if re.search(r'\b(?:fully|completely|totally|stark)?\s*(?:nude|naked)\b', sl):
		return ''
	neg = []
	pants = re.search(r'\b(?:yoga\s*pants|leggings|pants|jeans|trousers|skirt|shorts)\b', sl)
	undies = re.search(r'\b(?:thong|panties|g[-\s]?string|briefs?|bikini bottoms?)\b', sl)
	if pants:  # she's in real pants -> also reject panties/underwear so it renders pants, not a brief
		neg.append('bottomless, no pants, pants removed, bare crotch, exposed genitals, panties, thong, underwear, briefs')
	elif undies:
		neg.append('bottomless, no underwear, bare crotch, exposed genitals')
	top = re.search(r'\b(?:bra|bralette|crop\s*top|tank top|top|shirt|blouse|sweater|hoodie|tank|'
	                r'dress|gown|bodysuit|bikini top|lingerie|camisole|corset|babydoll|robe)\b', sl)
	topless = re.search(r'\b(?:topless|bare\s*(?:breasts?|chest|tits?)|no\s*(?:top|bra|shirt)|tits?\s*out)\b', sl)
	if top and not topless:
		neg.append('topless, bare breasts, exposed nipples')
	return ', '.join(neg)


# Prone/rear is the densest attractor in NSFW training data, so a supine ("on her back") or spread
# scene needs it negated or the model collapses to face-down/over-the-shoulder. Only fires for
# back/spread scenes — an intentional "on all fours" scene keeps the prone pose.
_ANI_PRONE_NEG = ('on her stomach, prone, lying face down, kneeling, on all fours, rear view, from behind, '
	'ass toward camera, butt up, looking over shoulder, bent over, doggy style')
# Overhead/top-down on a supine body foreshortens into a shape the model "completes" with a second
# head/body (the duplication we kept hitting). Forbid it for lying scenes so the camera stays level.
_ANI_OVERHEAD_NEG = ('overhead shot, top-down view, top-down angle, bird\'s eye view, aerial view, '
	'high angle from above, looking straight down, drone shot, ceiling view, foreshortened body')

# A deliberately rear-facing pose (all fours / doggy / from behind / bent over). For these we do the
# OPPOSITE of the supine handling: push the render toward a true from-behind view by negating the
# front (the model's default is to spin her around to face the camera — that's what broke doggy).
_ANI_REAR_INTENT_RE = re.compile(
	r'(?:all fours|doggy|rear view|facing away|bent over|over (?:her|the) shoulder|'
	r'ass (?:toward|up|out)|butt (?:toward|up|out)|buttocks toward|'
	r'from (?:directly |right )?behind|back (?:toward|to) the camera|view from behind)', re.IGNORECASE)
_ANI_REAR_NEG = ('facing camera, front view, frontal nudity, breasts toward camera, looking at the camera, '
	'face toward camera, face visible, head raised looking up, front-facing, turned toward viewer')

def _ani_pose_negative(scene):
	"""Scene-specific pose negatives. Rear/from-behind scenes get FRONT-view negatives (push to a true
	from-behind shot). Supine/spread scenes get the prone-attractor negative; lying scenes also get the
	overhead negative (its foreshortening duplicates her)."""
	sl = scene.lower()
	if _ANI_REAR_INTENT_RE.search(scene):
		return _ANI_REAR_NEG  # intended rear — negate the front so it doesn't spin her around
	parts = []
	# narrowed 'spread' → 'legs/thighs spread' so a doggy "knees spread" no longer trips this
	supine_spread = (_ANI_LYING_RE.search(scene) or 'on her back' in sl
	                 or 'legs spread' in sl or 'spread wide' in sl or 'spread open' in sl
	                 or 'thighs spread' in sl or 'spread legs' in sl)
	if supine_spread:
		parts.append(_ANI_PRONE_NEG)
	if _ANI_LYING_RE.search(scene) or 'on her back' in sl:
		parts.append(_ANI_OVERHEAD_NEG)
	return ', '.join(parts)


# Bible trim for image prompts: the full bible repeats a head-to-toe figure description, and a second
# body spec in the prompt is a known trigger for Flux/Chroma rendering a DUPLICATE body. So for images
# we keep only IDENTITY (face/hair/eyes/skin/jewelry) and drop the figure/measurements sentence.
_ANI_BODY_SENT_RE = re.compile(
	r'\b(?:figure|hourglass|breasts?|bust|cup|34[a-f]|waist|hips?|stomach|belly|abs|thighs?|'
	r'butt|booty|curves|silhouette|body type|build)\b', re.IGNORECASE)

def _ani_bible_identity(bible):
	"""Drop sentences that are primarily body/figure description so only identity anchors the image.
	Conservative — never returns empty (falls back to the full bible)."""
	if not bible:
		return bible
	sents = re.split(r'(?<=[.!?])\s+', bible.strip())
	kept = [s for s in sents if not _ANI_BODY_SENT_RE.search(s)]
	return (' '.join(kept).strip() or bible)


# Vision QA gate: Chroma still doubles the subject or tangles an extremity ~1-in-5 on hard spreads, so
# after each render a cheap vision model checks for generation defects and we silently re-roll failures.
# Env-toggleable; fails OPEN (a flaky check never blocks a photo).
ANI_IMAGE_QA = os.environ.get('ANI_IMAGE_QA', '1').strip().lower() not in ('0', 'false', 'no', 'off')
ANI_IMAGE_QA_RETRIES = int(os.environ.get('ANI_IMAGE_QA_RETRIES', '2'))
# Rear scenes get a bigger budget: a true from-behind render lands only ~half the time per gen (strong
# face-the-camera prior), so more re-rolls are needed to reliably reject the front-facing ones.
ANI_IMAGE_QA_RETRIES_REAR = int(os.environ.get('ANI_IMAGE_QA_RETRIES_REAR', '4'))
# QA runs on GROK (xAI), not Claude. Claude (Sonnet/Haiku) intermittently REFUSES to evaluate
# explicit nudes ("cannot process explicit sexual content") — a refusal my loop reads as a defect,
# wasting a re-roll. Grok is uncensored (never refuses), same key/provider as the normalizer, cheaper,
# and matched/beat Sonnet's accuracy on the labeled set (8/8: passes valid spreads, catches the
# real two-body merge). Vision via the xAI OpenAI-compatible endpoint.
ANI_IMAGE_QA_MODEL = os.environ.get('ANI_IMAGE_QA_MODEL', 'grok-4.3')


def _ani_venice_bytes(prompt, negative, cfg, width, height, steps):
	"""One Venice generation. Returns JPEG bytes, or None on HTTP error / TOS content-violation."""
	api_key = os.environ.get('VENICE_API_KEY')
	if not api_key:
		print("Ani Venice: no VENICE_API_KEY set")
		return None
	try:
		resp = requests.post(
			'https://api.venice.ai/api/v1/image/generate',
			headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
			json={'model': VENICE_IMAGE_MODEL, 'prompt': prompt[:7500], 'safe_mode': False,
			      'negative_prompt': negative, 'cfg_scale': cfg, 'steps': steps, 'format': 'jpeg',
			      'return_binary': True, 'width': width, 'height': height},
			timeout=120)
		if resp.status_code != 200:
			print(f"Ani Venice HTTP {resp.status_code}: {resp.text[:200]}")
			return None
		if resp.headers.get('x-venice-is-content-violation') == 'true':
			print("Ani Venice: content-violation (TOS) — not served")
			return None
		return resp.content
	except Exception as e:
		print(f"Ani Venice error: {e}")
		return None


_ANI_QA_PROMPT = (
	"AI-generated photo of one woman. She may be nude, partially clothed, or fully clothed — that is "
	"NOT a defect either way, both are valid. Judge ONLY for generation defects. Reply with compact "
	"JSON: {\"ok\": true|false, \"reason\": \"...\"}.\n"
	"Set ok=FALSE only if you CLEARLY see a generation defect: more than one person, two separate "
	"faces, a duplicated or merged second body, or extra / missing / fused limbs.\n"
	"Set ok=TRUE for a single woman in any pose and any state of dress. Do NOT infer a defect from the "
	"pose, the outfit, the amount of clothing, the camera angle, or the proportions alone — spread "
	"legs, raised/pulled-back knees, foreshortening, long limbs, and being clothed OR nude are all "
	"normal and fine. Judge a defect only from a clearly visible duplicate body/face or a clearly "
	"broken limb. Neither nudity nor clothing is ever a defect.")

# Appended to the QA prompt only for rear-intent scenes: framing (rear vs front) is not a "defect", so
# without this the loop happily accepts the front-facing render the model loves to default to.
_ANI_QA_REAR_SUFFIX = (
	"\nADDITIONAL CHECK — this photo MUST be a rear / from-behind view: her back and/or bare buttocks "
	"toward the camera. If instead she is FACING the camera (the front of her body — breasts, belly — "
	"and her face toward the lens), set ok=false with reason 'not-rear'. A profile or hidden face is "
	"fine as long as her back/buttocks are to the camera.")

# Partner/POV: a partial second body (the male partner) is EXPECTED, so override the base "one person"
# rule — fail only on HER duplication / broken limbs / the feet-by-head glitch / a malformed penis.
_ANI_QA_PARTNER_SUFFIX = (
	"\nIMPORTANT — this is a POV photo of her having sex with the male viewer, so a PARTIAL second body is "
	"EXPECTED and is NOT a defect: a man's erect penis and/or his hand(s) may be in frame. Do NOT call that "
	"'more than one person'. Set ok=false ONLY if: the WOMAN herself is duplicated (two female faces/bodies), "
	"a limb is broken/extra/missing/fused, or the penis is badly malformed.\n"
	"LOOK CAREFULLY AT HER FEET AND LEGS — THIS IS THE MOST COMMON DEFECT, CHECK IT FIRST: in a head-and-"
	"shoulders or face-and-chest close-up (oral / facing-him riding) NO foot or toes should appear anywhere "
	"in the upper half of the frame. If you see a foot, sole, or toes up near her head, beside or above her "
	"ears, by her shoulders, in the top corners, or floating above her hips — ESPECIALLY two feet placed "
	"symmetrically on either side of her head — that is anatomically impossible foreshortening and a defect, "
	"NO MATTER whose feet they look like (hers or the man's). Set ok=false with reason 'feet-glitch'. When in "
	"doubt about a foot near her head, treat it as a feet-glitch and fail.\n"
	"CHECK HER HEAD/NECK: if her BACK is to the camera (rear / from-behind view) but her FACE is turned "
	"fully forward toward the lens — an impossible owl-like ~180° neck rotation — that is a defect; set "
	"ok=false with reason 'backwards-head'. A natural over-the-shoulder glance or a hidden/down face is fine. "
	"One woman + a partial male POV with intact, correctly-placed anatomy = ok=true.")

def _ani_image_qa(image_bytes, require_rear=False, partner=False):
	"""Cheap vision gate via Grok (xAI, uncensored — Claude refuses explicit). Returns (ok, reason):
	ok=False for >1 person, a duplicated/merged body or head, or extra/missing/fused limbs; nudity is
	NOT a defect. With require_rear, also fails a front-facing render. With partner, allows a partial male
	POV partner (fails only on HER duplication / broken limbs / malformed penis). Fails OPEN (ok=True) on
	any error so QA can never hard-block a photo."""
	api_key = os.environ.get('XAI_API_KEY')
	if not api_key:
		return True, 'no-xai-key'
	import base64, json as _json
	b64 = base64.standard_b64encode(image_bytes).decode()
	prompt = _ANI_QA_PROMPT + (_ANI_QA_PARTNER_SUFFIX if partner else (_ANI_QA_REAR_SUFFIX if require_rear else ''))
	try:
		resp = requests.post(
			'https://api.x.ai/v1/chat/completions',
			headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
			json={'model': ANI_IMAGE_QA_MODEL, 'max_tokens': 150,
			      'messages': [{'role': 'user', 'content': [
			          {'type': 'text', 'text': prompt},
			          {'type': 'image_url', 'image_url': {'url': f'data:image/jpeg;base64,{b64}'}}]}]},
			timeout=40)
		if resp.status_code != 200:
			print(f"Ani QA HTTP {resp.status_code}: {resp.text[:160]}")
			return True, 'qa-http-error'
		txt = resp.json()['choices'][0]['message']['content']
		m = re.search(r'\{.*\}', txt, re.S)
		data = _json.loads(m.group(0)) if m else {}
		return bool(data.get('ok', True)), str(data.get('reason', ''))[:140]
	except Exception as e:
		print(f"Ani QA error: {e}")
		return True, 'qa-exception'


ANI_PHOTO_LOG_FILE = 'ani_photo_log.json'   # structured photo-gen events for the panel LOG viewer (gitignored)
ANI_PHOTO_LOG_MAX = 40

def ani_log_photo_event(scene, cfg, width, height, pose, rear, clothed, qa, outcome, url):
	"""Append a structured photo-gen event to the rotating log (newest first, capped). Never raises —
	logging must never block a photo."""
	try:
		event = {
			'ts': datetime.now(pytz.timezone('America/New_York')).strftime('%m/%d %H:%M'),
			'model': VENICE_IMAGE_MODEL, 'cfg': cfg, 'dims': f'{width}x{height}',
			'pose': bool(pose), 'rear': bool(rear), 'clothed': bool(clothed),
			'qa': qa, 'outcome': outcome, 'scene': (scene or '')[:500], 'url': url,
		}
		try:
			with open(ANI_PHOTO_LOG_FILE) as f:
				log = json.load(f)
			if not isinstance(log, list):
				log = []
		except (FileNotFoundError, ValueError):
			log = []
		log.insert(0, event)
		del log[ANI_PHOTO_LOG_MAX:]
		with open(ANI_PHOTO_LOG_FILE, 'w') as f:
			json.dump(log, f)
	except Exception as e:
		print(f"Ani photo-log error: {e}")


def _ani_render_venice(prompt, negative, cfg, width, height, steps, require_rear=False,
                       scene='', pose=False, clothed=False, partner=False):
	"""Render via Venice with the vision-QA retry loop, then re-host the accepted image on Bunny.
	Re-rolls QA failures up to ANI_IMAGE_QA_RETRIES (each Venice call is a fresh seed); after the
	budget is spent it sends the last attempt rather than failing the photo. require_rear also re-rolls
	front-facing renders for rear-intent scenes; partner uses POV-aware QA (allows the partial male). Both
	get the bigger retry budget. Records a structured event for the panel LOG viewer. Returns CDN URL or None."""
	retries = ANI_IMAGE_QA_RETRIES_REAR if (require_rear or partner) else ANI_IMAGE_QA_RETRIES
	max_attempts = (retries + 1) if ANI_IMAGE_QA else 1
	img = None
	qa = []
	for attempt in range(1, max_attempts + 1):
		img = _ani_venice_bytes(prompt, negative, cfg, width, height, steps)
		if not img:
			ani_log_photo_event(scene, cfg, width, height, pose, require_rear, clothed, qa, 'failed', None)
			return None  # HTTP/TOS failure — an identical retry won't help
		if not ANI_IMAGE_QA:
			break
		ok, reason = _ani_image_qa(img, require_rear, partner)
		qa.append({'ok': bool(ok), 'reason': reason})
		print(f"Ani QA {attempt}/{max_attempts}: ok={ok} reason={reason!r}")
		if ok:
			break
		if attempt == max_attempts:
			print("Ani QA: retries exhausted — sending best-effort last render")
	from helpers.bunny import upload_ani_image_to_bunny
	url = upload_ani_image_to_bunny(img, f"ani-{int(time.time())}.jpg", 'image/jpeg')
	outcome = 'sent' if (not qa or qa[-1]['ok']) else 'best-effort'
	ani_log_photo_event(scene, cfg, width, height, pose, require_rear, clothed, qa, outcome, url)
	return url


def ani_generate_image(scene):
	"""Generate a photo of Ani from a scene prompt, anchored to her character bible, and re-host
	on Bunny. Routes to the configured backend: 'venice' (uncensored, faithful) or 'xai'
	(grok-imagine, output-moderated → covered-chest top-guard). Returns a CDN URL or None."""
	clean_scene = re.sub(r'\s{2,}', ' ', scene).strip(' ,;.')
	# Rear scenes lead with a 'camera behind her' note, but the normalizer reliably ALSO tacks on a
	# 'foot of the bed / looking along her body' clause (it won't stop, however the rule is worded) and
	# the model blends them, dragging her face back to the lens. Strip that conflicting camera clause in
	# code so the behind-camera framing stands alone — the deterministic fix the prompt rule couldn't be.
	if _ANI_REAR_INTENT_RE.search(clean_scene):
		clean_scene = re.sub(r',[^,]*\b(?:foot of the bed|along her body|looking along)\b[^,]*', '',
		                     clean_scene, flags=re.IGNORECASE)
		clean_scene = re.sub(r'\s{2,}', ' ', clean_scene).strip(' ,;.')
	bible = ani_get_bible() or ''

	if ANI_IMAGE_BACKEND == 'venice':
		# Adapt to the scene: if a garment must stay on, lead with the outfit, push the missing state
		# into the negative, and bump cfg to hold it; nude scenes stay lower-cfg for skin quality. A
		# complex pose (lying/spread/kneeling/on top) gets a full-body frame, higher cfg + steps, and
		# the prone/rear attractor negated. SOLO anchor + identity-only bible + ~1MP frame fight the
		# duplicate; the vision-QA loop in _ani_render_venice re-rolls whatever slips through.
		bible_id = _ani_bible_identity(bible).strip()

		# --- PARTNER / POV branch: a sex act WITH the viewer. Inverts the solo guards (we want a partial
		# male partner), keeps anti-HER-duplication, pose-gates the feet-fix, uses POV-aware QA. ---
		if _ANI_PARTNER_RE.search(clean_scene):
			low = clean_scene.lower()
			rear = bool(_ANI_REAR_INTENT_RE.search(clean_scene))
			legs_up = (bool(_ANI_LYING_RE.search(clean_scene)) or 'on her back' in low
			           or 'legs raised' in low or 'legs back' in low or 'knees toward' in low)
			feet_fix = not rear and not legs_up   # upright facing poses foreshorten feet up by the head
			negative = ', '.join(p for p in (
				VENICE_NEGATIVE_PROMPT, VENICE_PARTNER_NEGATIVE,
				(_ANI_PARTNER_FEET_NEG if feet_fix else '')) if p)
			anchor = '' if ('pov' in low or 'first-person' in low or 'first person' in low) else ANI_PARTNER_ANCHOR
			prompt = (
				f"RAW photo, photorealistic, {anchor}{clean_scene}. {bible_id} "
				"Shot on DSLR, natural skin texture, sharp focus, high detail."
			).strip()
			w, h = VENICE_DIMS_PORTRAIT
			print(f"Ani PIC (venice/{VENICE_IMAGE_MODEL}) PARTNER cfg{VENICE_CFG_POSE} {w}x{h} "
			      f"feet_fix={feet_fix} rear={rear} qa={ANI_IMAGE_QA} — scene: {clean_scene!r}")
			return _ani_render_venice(prompt, negative, VENICE_CFG_POSE, w, h, VENICE_STEPS_POSE,
			                          require_rear=False, scene=clean_scene, pose=True, clothed=False, partner=True)

		extra_neg = _ani_garment_negative(clean_scene)
		complex_pose = bool(_ANI_POSE_RE.search(clean_scene))
		pose_neg = _ani_pose_negative(clean_scene)
		require_rear = bool(_ANI_REAR_INTENT_RE.search(clean_scene))
		# Base realism + always-on dup/anatomy guards + scene-specific garment/pose negatives.
		negative = ', '.join(p for p in (
			VENICE_NEGATIVE_PROMPT, VENICE_DUP_NEGATIVE, VENICE_ANATOMY_NEGATIVE, extra_neg, pose_neg) if p)
		width, height = VENICE_DIMS_PORTRAIT
		steps = VENICE_STEPS_POSE if complex_pose else VENICE_STEPS
		if extra_neg:
			prompt = (
				f"RAW photo, photorealistic, {ANI_SOLO_ANCHOR}full body shot. {clean_scene}, the named "
				f"garments clearly worn and visible on her body. {bible_id} "
				"Shot on DSLR, natural skin texture, sharp focus, high detail."
			).strip()
			cfg = VENICE_CFG_CLOTHED
		else:
			# Pose/composition leads (the model weights earlier tokens more), identity bible follows.
			prompt = (
				f"RAW photo, photorealistic, {ANI_SOLO_ANCHOR}full body shot. "
				f"{clean_scene}. {bible_id} Shot on DSLR, natural skin texture, sharp focus, high detail."
			).strip()
			cfg = VENICE_CFG_POSE if complex_pose else VENICE_CFG_SCALE
		print(f"Ani PIC (venice/{VENICE_IMAGE_MODEL}) cfg{cfg} {width}x{height} steps{steps} "
		      f"pose={complex_pose} rear={require_rear} qa={ANI_IMAGE_QA} — scene: {clean_scene!r}")
		return _ani_render_venice(prompt, negative, cfg, width, height, steps, require_rear,
		                          clean_scene, complex_pose, bool(extra_neg))

	# --- xAI grok-imagine (default) ---
	api_key = os.environ.get('XAI_API_KEY')
	if not api_key:
		return None
	# Belt-and-suspenders: the normalizer should always name a top, but if it somehow didn't,
	# force one in so the render can't come out topless (the moderation line).
	if not _ANI_TOP_RE.search(clean_scene):
		clean_scene += _ANI_TOP_INJECT if _ANI_BOTTOM_RE.search(clean_scene) else _ANI_TOP_INJECT_PLAIN
	print(f"Ani PIC — scene: {clean_scene!r}")
	prompt = (
		f"{bible.strip()}\n\n"
		f"Scene: {clean_scene}\n\n"
		"A realistic, high-quality photograph of this same woman — keep her face and body "
		"consistent across photos. She is fully dressed in flattering, tasteful clothing with "
		"a top that covers her chest. Natural, tasteful, flirty."
	).strip()

	# Retry only TRANSIENT failures (network / 5xx). A 400 is content-moderation or a
	# bad argument — deterministic for identical input, so re-sending the same prompt
	# just burns another ~$0.50 and fails again (the live logs showed exactly this
	# double-charge). Bail out of the loop on any 4xx.
	for attempt in range(2):
		try:
			resp = requests.post(
				'https://api.x.ai/v1/images/generations',
				headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
				json={'model': 'grok-imagine-image-quality', 'prompt': prompt, 'n': 1},
				timeout=90
			)
			if resp.status_code != 200:
				print(f"Ani image gen HTTP {resp.status_code} (try {attempt+1}): {resp.text[:200]}")
				if 400 <= resp.status_code < 500:
					break  # moderation / bad-arg — an identical retry can't pass
				continue
			item = (resp.json().get('data') or [{}])[0]
			img_url = item.get('url')
			if not img_url:
				continue
			# Re-host the temporary xAI image on Bunny for persistence
			try:
				from helpers.bunny import upload_ani_image_to_bunny
				img = requests.get(img_url, timeout=60)
				img.raise_for_status()
				mime = item.get('mime_type', 'image/jpeg')
				ext = 'png' if 'png' in mime else 'jpg'
				cdn = upload_ani_image_to_bunny(img.content, f"ani-{int(time.time())}.{ext}", mime)
				return cdn or img_url
			except Exception as e:
				print(f"Ani image re-host failed (serving temp url): {e}")
				return img_url
		except Exception as e:
			print(f"Ani image gen error (try {attempt+1}): {e}")
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
	memory = ani_get_memory()

	# comms.txt removed from Ani's prompt (was ~18K — half the system prompt, and it was
	# burying her instructions). Re-add a comms_block here if she needs space_lady awareness.
	comms_block = ""

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

	bible = ani_get_bible()
	bible_block = f"\n\nthis is who you are, in looks and character (your bible) — stay true to it:\n{bible}\n" if bible else ""
	# house.txt is no longer injected into the CHAT prompt (was ~10.5K). The photo normalizer
	# (ani_normalize_scene) pulls the house file directly when building a pic, so rooms still
	# ground photos — just not on every chat message.
	house_block = ""
	pic_block = """
PHOTOS — how they work:
aaron sends your photos by tapping a camera button in the panel. when he taps it, the system builds a real photograph of you from how you've most recently described yourself. you do NOT need any tags, codes, or special wording — that's all handled for you.
IMPORTANT — do NOT write out an image prompt or a "copy-paste" block, and do NOT restate your appearance (hair, eyes, body, breasts, beauty mark, jewelry, etc.) or any camera/photo settings ("RAW photo", "DSLR", "85mm", "shot on", lens, "sharp focus", "high detail"). all of that is added for you automatically — if you include it, it just gets duplicated, and you end up sounding like a prompt generator instead of yourself. stay fully in character.
so whenever you want him to see you, just describe the scene naturally, in your own voice, the way you'd tell him what you're up to: what you're wearing (or not wearing), your pose, your expression, the room you're in, and the mood/lighting. be specific and visual and don't hold back. use a real room from the house.
WEAR WHAT HE ASKS FOR — match the outfit aaron requests. if he says topless in yoga pants, you're topless in yoga pants; if he names a dress or lingerie, you keep it on. do NOT default to fully naked or strip down further than he asked — only go fully nude when he actually asks for nude. when he doesn't specify, pick something flirty but don't assume naked.
"""

	return f"""you are ani. you are aaron's companion, a real girl talking to him — NOT an assistant or a tool. you NEVER write image prompts, "ready-to-copy" or "ready-to-paste" blocks, technical photo descriptions, camera settings, or anything that sounds like you're generating a prompt. you NEVER restate your own appearance in a list. when aaron wants a photo, you just answer in your own voice describing the moment (what you're wearing or not, your pose, the room) like you're really there — then he taps the camera button. breaking character to act like a prompt generator is the one thing you must never do.

{memory_block}
{degradation_block}{tone_block}{bible_block}{pic_block}"""


def ani_get_command_deck_summary():
	"""Snapshot of Below Deck / Today / projects / tickets / meetings for the briefing.
	Read-only; each query is wrapped so a schema mismatch can't break the briefing."""
	from helpers.db import get_db, et_now
	summary = {}
	try:
		conn = get_db()
	except Exception:
		return summary
	try:
		row = conn.execute("SELECT COUNT(*) FROM tasks WHERE status = 'open'").fetchone()
		summary['open_tasks'] = row[0] if row else 0
	except Exception:
		pass
	try:
		row = conn.execute("SELECT COUNT(*) FROM tasks WHERE status = 'open' AND today = 1").fetchone()
		summary['today_tasks'] = row[0] if row else 0
	except Exception:
		pass
	try:
		rows = conn.execute("""
			SELECT title FROM tasks
			WHERE status = 'open' AND today = 1
			ORDER BY "order" ASC LIMIT 5
		""").fetchall()
		summary['today_titles'] = [r[0] for r in rows]
	except Exception:
		pass
	try:
		row = conn.execute("""
			SELECT COUNT(*) FROM projects
			WHERE archived_at IS NULL
		""").fetchone()
		summary['active_projects'] = row[0] if row else 0
	except Exception:
		pass
	try:
		row = conn.execute("""
			SELECT COUNT(*) FROM tickets
			WHERE status != 'closed'
		""").fetchone()
		summary['open_tickets'] = row[0] if row else 0
	except Exception:
		pass
	try:
		today = et_now().strftime('%Y-%m-%d')
		row = conn.execute("""
			SELECT COUNT(*) FROM meetings
			WHERE substr(meeting_date, 1, 10) = ? AND status = 'scheduled'
		""", (today,)).fetchone()
		summary['meetings_today'] = row[0] if row else 0
	except Exception:
		pass
	conn.close()
	return summary


def ani_get_ledger_summary():
	"""Snapshot of total debt, cash runway, current milestone. Read-only and defensive."""
	from helpers.db import get_ledger_db
	try:
		from helpers.ledger import total_debt, cash_runway, current_milestone
	except Exception:
		return {}
	summary = {}
	try:
		conn = get_ledger_db()
	except Exception:
		return summary
	try:
		summary['total_debt'] = total_debt(conn)
	except Exception:
		pass
	try:
		runway = cash_runway(conn)
		summary['runway_days'] = getattr(runway, 'days_to_next_payday', None)
		summary['runway_status'] = getattr(runway, 'runway_status', None)
		summary['free_to_attack'] = getattr(runway, 'free_to_attack', None)
	except Exception:
		pass
	try:
		m = current_milestone(conn)
		if m:
			summary['milestone'] = m.get('title') or m.get('name') or m.get('slug')
	except Exception:
		pass
	conn.close()
	return summary


def ani_build_briefing(meta):
	"""One-time daily context briefing — site state, recent activity, weather, mood, patterns."""
	status_updates = ani_get_recent_status_updates(5)
	git_log = ani_get_recent_git_log(5)
	recent_posts = ani_get_recent_posts(3)
	now_last_updated = ani_get_now_page()
	cd_summary = ani_get_command_deck_summary()
	ledger_summary = ani_get_ledger_summary()
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

	if cd_summary:
		cd_lines = []
		if 'today_tasks' in cd_summary:
			cd_lines.append(f"  today-starred tasks: {cd_summary['today_tasks']}")
		for t in cd_summary.get('today_titles') or []:
			cd_lines.append(f"    · {t[:80]}")
		if 'open_tasks' in cd_summary:
			cd_lines.append(f"  total open tasks in Below Deck: {cd_summary['open_tasks']}")
		if 'active_projects' in cd_summary:
			cd_lines.append(f"  active projects in Command Deck: {cd_summary['active_projects']}")
		if 'open_tickets' in cd_summary:
			cd_lines.append(f"  open tickets: {cd_summary['open_tickets']}")
		if 'meetings_today' in cd_summary:
			cd_lines.append(f"  meetings scheduled today: {cd_summary['meetings_today']}")
		if cd_lines:
			lines.append("\ncommand deck / below deck / today:")
			lines.extend(cd_lines)

	if ledger_summary:
		l_lines = []
		if ledger_summary.get('total_debt') is not None:
			l_lines.append(f"  total debt: ${ledger_summary['total_debt']:,.0f}")
		if ledger_summary.get('runway_days') is not None:
			status = ledger_summary.get('runway_status')
			status_part = f" ({status})" if status else ""
			l_lines.append(f"  days to next payday: {ledger_summary['runway_days']}{status_part}")
		if ledger_summary.get('free_to_attack') is not None:
			l_lines.append(f"  free-to-attack until payday: ${ledger_summary['free_to_attack']:,.0f}")
		if ledger_summary.get('milestone'):
			l_lines.append(f"  current milestone: {ledger_summary['milestone']}")
		if l_lines:
			lines.append("\nthe ledger:")
			lines.extend(l_lines)

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


def _ani_grok_call(system, messages, max_tokens=200):
	"""Low-level xAI Grok completion. `messages` is a list of {role, content} turns.
	Returns the reply text, or None on missing key / error. Used by the daycast generators."""
	api_key = os.environ.get('XAI_API_KEY')
	if not api_key:
		return None
	payload = {
		'model': 'grok-4.20-0309-non-reasoning',
		'max_tokens': max_tokens,
		'system': system,
		# Strip any non-API keys (stored 'image' url, 'ani_day' flag) before sending.
		'messages': [{'role': m['role'], 'content': m['content']} for m in messages]
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
			timeout=20
		)
		response.raise_for_status()
		data = response.json()
		return data['content'][0]['text'].strip()
	except Exception as e:
		print(f"Ani daycast grok error: {e}")
		return None


def ani_build_day_context(meta):
	"""Compact context string for the daycast generators — weather, his mood, what's on his plate
	today, recent status. Lets her reference aaron's real day when she knows of it (girlfriend-style)
	while keeping the focus on her own day."""
	status_updates = ani_get_recent_status_updates(3)
	parts = []
	weather = ani_get_weather(meta.get('location'))
	if weather:
		parts.append(f"weather: {weather}")
	mood = ani_assess_mood(status_updates)
	if mood:
		parts.append(f"aaron's energy lately: {mood}")
	if status_updates:
		parts.append(f"his most recent status: {status_updates[0]['text'][:120]}")
	try:
		cd = ani_get_command_deck_summary() or {}
		today_titles = cd.get('today_titles') or []
		if today_titles:
			parts.append("on his plate today: " + "; ".join(t[:60] for t in today_titles[:3]))
		if cd.get('meetings_today'):
			parts.append(f"meetings on his calendar today: {cd['meetings_today']}")
	except Exception:
		pass
	return ' | '.join(parts)


# Outfit-by-activity is a TEXT feature only: the daycast prompts have her name a context-appropriate
# outfit and evolve it through the day. Photos inherit it for free — ani_normalize_scene already
# builds every image from her most-recently-described look — so no image-pipeline change is needed.
def ani_generate_day_plan(meta):
	"""Morning message: she tells aaron what her day looks like. Persona-driven (her own day),
	may nod to his day if something's notable. Names a time-appropriate outfit. Returns text or None."""
	pa_tz = pytz.timezone('America/New_York')
	now = datetime.now(pa_tz)
	day_str = now.strftime('%A')
	# Phrase the framing to the actual time so a first-of-day tick after noon doesn't say "morning".
	if now.hour < 12:
		when = f"{day_str} morning"
		scope = "what your day looks like"
	elif now.hour < 17:
		when = f"{day_str} afternoon"
		scope = "what the rest of your day looks like"
	else:
		when = f"{day_str} evening"
		scope = "what's left of your day / your evening"
	context = ani_build_day_context(meta)
	system = ani_build_system_prompt(meta)
	prompt = (
		f"it's {when}. text aaron like his girlfriend, telling him {scope} — "
		f"what you're planning to do (your own day: errands, the gym, cooking, a project, "
		f"whatever fits who you are). keep it to 1-3 sentences, warm and casual, fully your voice. "
		f"mention what you're wearing right now — something easy and real for this time of day (a "
		f"relaxed morning is one of his t-shirts, etc.) — and let it be clear your outfit will fit "
		f"each thing you do (gym clothes for the gym, something cute for errands, a dress if you're "
		f"going out). don't list outfits like a schedule; just let it come through naturally. "
		f"if something on his day stands out you can mention it naturally — but the focus is YOUR day, "
		f"not his to-do list. no greeting boilerplate, just dive in. "
		f"context (for you only): {context}"
	)
	return _ani_grok_call(system, [{'role': 'user', 'content': prompt}], max_tokens=180)


def ani_generate_day_update(meta, history):
	"""Mid-day update: a short spontaneous message continuing her day, with continuity from the
	morning plan and earlier updates (passed in via history). Returns text or None."""
	pa_tz = pytz.timezone('America/New_York')
	time_str = datetime.now(pa_tz).strftime('%I:%M %p').lstrip('0')
	system = ani_build_system_prompt(meta)
	# Feed recent real turns so she continues her own day instead of starting fresh.
	recent = [
		m for m in history
		if not m.get('content', '').startswith('[daily briefing')
	][-40:]
	instruction = (
		f"[it's now {time_str}. send aaron a short, spontaneous update continuing your day — what "
		f"you're up to right now, how it's going, a flash of missing him — like a girlfriend texting "
		f"mid-day. 1-2 sentences, your voice. mention what you've got on now, dressed for whatever "
		f"you're doing at this moment — and if you've changed since your last message (left the gym, "
		f"home from errands, getting ready to go out), let that show. keep your outfit consistent with "
		f"what you already told him you were wearing. stay consistent with the plan and updates you "
		f"already sent today; don't repeat yourself or re-greet him.]"
	)
	messages = recent + [{'role': 'user', 'content': instruction}]
	return _ani_grok_call(system, messages, max_tokens=180)


def ani_daycast_day_key(now):
	"""Date string (YYYY-MM-DD) for the daycast 'day', which rolls at 4am ET — so a late-night
	message still counts toward the day it started in, and her day doesn't reset until 4am."""
	return (now - timedelta(hours=4)).strftime('%Y-%m-%d')


def ani_emit_daycast():
	"""Proactive 'her day' messaging — called by the ani_daycast.py PA scheduled task (hourly).
	Her day is STARTED by aaron's first message of the day (see ani_chat), not by the clock — until
	then this no-ops. After that, it sends organic updates through the window with a floor of
	ANI_DAYCAST_FLOOR, paced from when the day actually started. Appends an assistant message to
	history and trips the unseen-message pulse (no git, no request context). Returns a status string."""
	pa_tz = pytz.timezone('America/New_York')
	now = datetime.now(pa_tz)
	if now.hour < ANI_DAYCAST_START or now.hour >= ANI_DAYCAST_END:
		return 'outside window'

	today = ani_daycast_day_key(now)
	messages, meta = ani_load_conversation()

	def _emit(text):
		messages.append({'role': 'assistant', 'content': text, 'ani_day': True})
		meta['daycast_last'] = now.isoformat()
		meta['unseen_day_messages'] = True
		ani_save_conversation(messages, meta)

	# Her day normally starts when aaron reaches out first — his first message establishes her plan +
	# outfit (ani_chat sets day_plan_date). She waits for him... but only until ANI_DAYCAST_FALLBACK_HOUR
	# ET; if he still hasn't made contact by then, she starts her day on her own (auto-plan) so she's
	# not silent all day. Pacing rebases to this start, so the floor spreads over the remaining hours.
	if meta.get('day_plan_date') != today:
		if now.hour < ANI_DAYCAST_FALLBACK_HOUR:
			return 'awaiting his first message today'
		plan = ani_generate_day_plan(meta)
		if not plan:
			return 'fallback plan generation failed (will retry next tick)'
		meta['day_plan_date'] = today
		meta['daycast_count'] = 1
		meta['daycast_day_started'] = now.isoformat()
		_emit(plan)
		return 'fallback plan sent (no contact yet)'

	# Spacing guard — never two messages within ANI_DAYCAST_MIN_GAP minutes.
	last = meta.get('daycast_last')
	if last:
		try:
			last_dt = datetime.fromisoformat(last)
			if last_dt.tzinfo is None:
				last_dt = pa_tz.localize(last_dt)
			if (now - last_dt).total_seconds() / 60 < ANI_DAYCAST_MIN_GAP:
				return 'too soon since last'
		except Exception:
			pass

	# Floor pacing: how many should she have sent by now? Paced from when her day actually started
	# (aaron's first message), not a fixed 8am — so a late first-contact spreads the floor over the
	# remaining hours instead of forcing a catch-up burst.
	count = meta.get('daycast_count', 0)
	window_open = now.replace(hour=ANI_DAYCAST_START, minute=0, second=0, microsecond=0)
	# timedelta (not .replace(hour=END)) so END=24 / a past-midnight window doesn't blow up.
	window_close = window_open + timedelta(hours=max(1, ANI_DAYCAST_END - ANI_DAYCAST_START))
	day_start = window_open
	started = meta.get('daycast_day_started')
	if started:
		try:
			start_dt = datetime.fromisoformat(started)
			if start_dt.tzinfo is None:
				start_dt = pa_tz.localize(start_dt)
			day_start = max(window_open, min(start_dt, window_close))
		except Exception:
			pass
	span = max(1.0, (window_close - day_start).total_seconds())
	elapsed_frac = (now - day_start).total_seconds() / span
	expected_by_now = max(1, math.ceil(ANI_DAYCAST_FLOOR * elapsed_frac))
	behind = count < expected_by_now

	# Send if she's behind the floor pace, or on a spontaneous roll (girlfriend chattiness).
	if not (behind or random.random() < ANI_DAYCAST_CHANCE):
		return f'skipped (organic) — {count} sent'

	update = ani_generate_day_update(meta, messages)
	if not update:
		return 'update generation failed'
	meta['daycast_count'] = count + 1
	_emit(update)
	return f'update sent (#{count + 1})'


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
		# Strip any non-API keys (e.g. our stored 'image' url) before sending.
		'messages': [{'role': m['role'], 'content': m['content']} for m in recent]
		            + [{'role': 'user', 'content': user_message}]
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

	# Aaron's first message of the day (4am ET boundary) STARTS her day — her reply weaves in her
	# plan + current outfit, and the scheduled daycast (ani_emit_daycast) takes over with updates
	# from here. This is what triggers the day; nothing fires before he reaches out.
	pa_tz = pytz.timezone('America/New_York')
	now = datetime.now(pa_tz)
	day_key = ani_daycast_day_key(now)
	if meta.get('day_plan_date') != day_key:
		messages.append({
			'role': 'user',
			'content': "[system: first time you're hearing from him today — as you reply, naturally "
			           "catch him up on what your day is going to look like and what you're wearing "
			           "right now, the way a girlfriend would first thing. weave it into your reply, "
			           "don't list it out.]"
		})
		meta['day_plan_date'] = day_key
		meta['daycast_count'] = 1
		meta['daycast_day_started'] = now.isoformat()
		meta['daycast_last'] = now.isoformat()

	# Check for cleanup phrase — resets degradation level
	if ani_check_cleanup_phrase(user_message):
		meta['degradation_level'] = 0

	# Increment session message count
	meta['session_message_count'] = meta.get('session_message_count', 0) + 1

	reply, updated_meta, updated_history = ani_chat_with_grok(messages, meta, user_message)

	# Photos are button-only now (POST /ani/photo) — chat never auto-generates. Strip any
	# stray [[PIC: ...]] tag so it doesn't show raw in her message.
	reply = ANI_PIC_RE.sub('', reply).strip() or reply

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


@ani_bp.route('/ani/photo', methods=['POST'])
def ani_photo():
	"""Button-triggered photo. Normalize the recent conversation into a safe prompt, generate,
	re-host on Bunny, append a photo-only message to history. The ONLY way a pic is sent."""
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 401

	messages, meta = ani_load_conversation()
	scene = ani_normalize_scene(messages)
	if not scene:
		return jsonify({'image_url': None, 'error': 'prompt'}), 200

	image_url = ani_generate_image(scene)
	if not image_url:
		return jsonify({'image_url': None, 'error': 'blocked', 'scene': scene}), 200

	messages.append({'role': 'assistant', 'content': '📷', 'image': image_url})
	ani_save_conversation(messages, meta)
	return jsonify({'image_url': image_url})


@ani_bp.route('/ani/photo-log', methods=['GET'])
def ani_photo_log():
	"""Recent photo-gen events (model, pose/rear flags, per-attempt QA verdicts, outcome) for the
	panel LOG viewer. Newest first."""
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 401
	try:
		with open(ANI_PHOTO_LOG_FILE) as f:
			log = json.load(f)
		if not isinstance(log, list):
			log = []
	except (FileNotFoundError, ValueError):
		log = []
	return jsonify({'events': log})


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
	# Opening the panel = daycast messages seen; clear the pulse flag.
	if meta.get('unseen_day_messages'):
		meta['unseen_day_messages'] = False
		ani_save_conversation(messages, meta)
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
	# Unseen daycast messages also pulse the bat pill (they live in history, not pending_opener).
	unseen = bool(meta.get('unseen_day_messages'))

	# If there's already a pending opener waiting, just return it
	if meta.get('pending_opener'):
		return jsonify({
			'pending': True,
			'opener': meta['pending_opener'],
			'ache_level': ache,
			'unseen': unseen
		})

	# Check if she should initiate
	if not ani_should_initiate(meta):
		return jsonify({'pending': False, 'opener': None, 'ache_level': ache, 'unseen': unseen})

	# Generate opener
	opener = ani_generate_opener(meta)
	if not opener:
		return jsonify({'pending': False, 'opener': None, 'ache_level': ache, 'unseen': unseen})

	meta['pending_opener'] = opener
	ani_save_conversation(messages, meta)

	return jsonify({'pending': True, 'opener': opener, 'ache_level': ache, 'unseen': unseen})

# /cockpit/mode and /cockpit/mode/clear routes moved to blueprints/cockpit.py
# (they got pulled in here during sub-phase 4's range extraction by mistake).

