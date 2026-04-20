from flask import Flask, request, render_template, make_response, redirect, url_for, jsonify
from werkzeug.utils import secure_filename
from PIL import Image
from datetime import datetime
import os, subprocess, pytz, requests, emoji, glob, json, time, re

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY')
PASSWORD = os.environ.get('FLASK_PASSWORD')

UPLOAD_FOLDER = '/home/aaronaiken/status_update/assets/img/status/'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

TASKS_FILE = 'assets/data/tasks.json'
SCRATCH_FILE = 'assets/data/scratch.json'
BELOW_DECK_FILE = 'assets/data/below_deck.json'
ANI_CONVERSATION_FILE = 'ani_conversation.json'
ANI_MEMORY_FILE = 'static/ani_memory.txt'
REPO_ROOT = '/home/aaronaiken/status_update'

# ---- COMMS CACHE ----
_comms_cache = {'data': None, 'timestamp': 0}
COMMS_CACHE_TTL = 300  # 5 minutes


# ---- AUTH ----

def is_authenticated():
    return request.cookies.get('auth_token') == 'authenticated_user'


# ---- GIT / COMMS HELPERS ----

def get_git_status():
    try:
        subprocess.run(["git", "fetch"], check=True, capture_output=True, timeout=5)
        status = subprocess.check_output(["git", "status", "-sb"], encoding='utf-8')
        if "ahead" in status:
            return "syncing"
        elif "behind" in status:
            return "offline"
        else:
            return "online"
    except Exception as e:
        print(f"Git Status Error: {e}")
        return False


def get_active_tags():
    pa_tz = pytz.timezone('America/New_York')
    now = datetime.now(pa_tz)

    print(f"DEBUG: Local PA Time is {now.strftime('%H:%M:%S')}")

    tags = ["ALL"]
    hour = now.hour

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


def perform_git_ops(filename):
    stash = subprocess.run(
        ["git", "stash"], capture_output=True, encoding='utf-8'
    )
    stashed = "No local changes" not in stash.stdout

    subprocess.run(["git", "pull", "--rebase", "origin", "main"], check=True)

    if stashed:
        subprocess.run(["git", "stash", "pop"], check=True)

    subprocess.run(["git", "add", "."], check=True)
    subprocess.run(["git", "commit", "-m", "update from cockpit"], check=True)
    subprocess.run(["git", "push", "origin", "main"], check=True)


def optimize_image(input_path, max_width=1200):
    with Image.open(input_path) as img:
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        w_percent = (max_width / float(img.size[0]))
        if w_percent < 1.0:
            h_size = int((float(img.size[1]) * float(w_percent)))
            img = img.resize((max_width, h_size), Image.Resampling.LANCZOS)
        img.save(input_path, "JPEG", optimize=True, quality=85)


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

    # ---- BELOW DECK HELPERS ----

def load_below_deck():
    try:
        with open(BELOW_DECK_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {"tasks": []}


def save_below_deck(data):
    os.makedirs(os.path.dirname(BELOW_DECK_FILE), exist_ok=True)
    with open(BELOW_DECK_FILE, 'w') as f:
        json.dump(data, f, indent=2)


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
            img_dir = "assets/img/status"
            os.makedirs(img_dir, exist_ok=True)
            img_name = secure_filename(image_file.filename)
            img_path_fs = os.path.join(img_dir, f"{now.strftime('%Y%m%d%H%M%S')}-{img_name}")
            image_file.save(img_path_fs)
            optimize_image(img_path_fs)
            image_markdown = f"\n\n![Status Image](/{img_path_fs})"

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
    history = [open(f).read().split("---")[-1].strip() for f in files]
    comms_list = get_valid_comms()
    tasks_data = load_tasks()
    return render_template(
        'publish_form.html',
        history=history,
        git_status=get_git_status(),
        comms_list=comms_list,
        tasks=tasks_data.get('tasks', [])
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
    content = request.json.get('content', '')
    pa_tz = pytz.timezone('America/New_York')
    last_modified = datetime.now(pa_tz).isoformat()
    os.makedirs(os.path.dirname(SCRATCH_FILE), exist_ok=True)
    with open(SCRATCH_FILE, 'w') as f:
        json.dump({'content': content, 'last_modified': last_modified}, f)
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

@app.route('/below-deck', methods=['GET'])
def below_deck():
    if not is_authenticated():
        return redirect(url_for('login'))
    data = load_below_deck()
    return render_template('below_deck.html', tasks=data.get('tasks', []))


@app.route('/below-deck/count', methods=['GET'])
def below_deck_count():
    if not is_authenticated():
        return jsonify({'error': 'unauthorized'}), 401
    data = load_below_deck()
    open_count = sum(1 for t in data.get('tasks', []) if t.get('status') == 'open')
    return jsonify({'count': open_count})


@app.route('/below-deck/add', methods=['POST'])
def below_deck_add():
    if not is_authenticated():
        return jsonify({'error': 'unauthorized'}), 401
    title = request.form.get('title', '').strip()
    if not title:
        return jsonify({'error': 'title required'}), 400
    data = load_below_deck()
    task = {
        'id': str(int(time.time() * 1000)),
        'title': title,
        'status': 'open',
        'created': datetime.now(pytz.timezone('America/New_York')).isoformat(),
        'order': 0
    }
    data['tasks'].insert(0, task)
    for i, t in enumerate(data['tasks']):
        t['order'] = i
    save_below_deck(data)
    return jsonify({'ok': True, 'task': task})


@app.route('/below-deck/complete', methods=['POST'])
def below_deck_complete():
    if not is_authenticated():
        return jsonify({'error': 'unauthorized'}), 401
    task_id = request.form.get('id', '').strip()
    if not task_id:
        return jsonify({'error': 'id required'}), 400
    data = load_below_deck()
    data['tasks'] = [t for t in data['tasks'] if t['id'] != task_id]
    save_below_deck(data)
    return jsonify({'ok': True})


@app.route('/below-deck/delete', methods=['POST'])
def below_deck_delete():
    if not is_authenticated():
        return jsonify({'error': 'unauthorized'}), 401
    task_id = request.form.get('id', '').strip()
    if not task_id:
        return jsonify({'error': 'id required'}), 400
    data = load_below_deck()
    data['tasks'] = [t for t in data['tasks'] if t['id'] != task_id]
    save_below_deck(data)
    return jsonify({'ok': True})


@app.route('/below-deck/reorder', methods=['POST'])
def below_deck_reorder():
    if not is_authenticated():
        return jsonify({'error': 'unauthorized'}), 401
    order = request.json.get('order', [])
    if not order:
        return jsonify({'error': 'order required'}), 400
    data = load_below_deck()
    task_map = {t['id']: t for t in data['tasks']}
    data['tasks'] = [task_map[tid] for tid in order if tid in task_map]
    for i, t in enumerate(data['tasks']):
        t['order'] = i
    save_below_deck(data)
    return jsonify({'ok': True})

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
    if current_count == 8 and current_level < 5:
        updated_meta['degradation_level'] = current_level + 1

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


if __name__ == "__main__": app.run(debug=True)