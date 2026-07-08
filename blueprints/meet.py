"""
meet — a homemade video meeting inside the Cockpit.

You start a meeting from `/meet` (authed); it mints an unguessable room and a
guest link anyone can open (no auth) to join with a name. Media is peer-to-peer
WebRTC (a mesh — good for a small 2–4 person call); Flask is only the SIGNALING
relay, done over short HTTP polling since PythonAnywhere has no WebSockets.

Reliability across locked-down networks comes from TURN, configured via env:
  - Cloudflare Realtime TURN:  COCKPIT_CF_TURN_KEY_ID + COCKPIT_CF_TURN_TOKEN
  - or a static TURN server:   COCKPIT_TURN_URL + COCKPIT_TURN_USER + COCKPIT_TURN_CRED
Without either it falls back to public STUN (fine for testing / same-network).

Ephemeral room + signal state lives in its own tiny SQLite file (gitignored);
stale participants are pruned on every poll.
"""
import os
import json
import secrets
import sqlite3
from datetime import datetime, timezone, timedelta

import requests
from flask import Blueprint, request, jsonify, render_template, redirect, url_for

from helpers.auth import is_authenticated

meet_bp = Blueprint('meet', __name__)

MEET_DB = os.environ.get('COCKPIT_MEET_DB',
                         os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'meet.db'))
STALE_SECONDS = 25   # drop a participant we haven't heard from in this long


def _now():
    return datetime.now(timezone.utc)


def _iso():
    return _now().isoformat()


def _db():
    db = sqlite3.connect(MEET_DB)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA busy_timeout = 3000")
    db.executescript("""
        CREATE TABLE IF NOT EXISTS rooms (id TEXT PRIMARY KEY, created_at TEXT);
        CREATE TABLE IF NOT EXISTS participants (
            room_id TEXT, peer_id TEXT, name TEXT, last_seen TEXT,
            PRIMARY KEY (room_id, peer_id));
        CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_id TEXT, to_peer TEXT, from_peer TEXT, kind TEXT, payload TEXT, created_at TEXT);
    """)
    for col in ('label', 'scheduled_at'):   # additive; safe to re-run
        try:
            db.execute("ALTER TABLE rooms ADD COLUMN %s TEXT" % col)
        except sqlite3.OperationalError:
            pass
    return db


def _prune(db, room_id):
    cutoff = (_now().timestamp() - STALE_SECONDS)
    rows = db.execute("SELECT peer_id, last_seen FROM participants WHERE room_id=?", (room_id,)).fetchall()
    for r in rows:
        try:
            ts = datetime.fromisoformat(r['last_seen']).timestamp()
        except Exception:
            ts = 0
        if ts < cutoff:
            db.execute("DELETE FROM participants WHERE room_id=? AND peer_id=?", (room_id, r['peer_id']))
            db.execute("DELETE FROM signals WHERE room_id=? AND (to_peer=? OR from_peer=?)",
                       (room_id, r['peer_id'], r['peer_id']))


def _roster(db, room_id, exclude=None):
    rows = db.execute("SELECT peer_id, name FROM participants WHERE room_id=? ORDER BY last_seen", (room_id,)).fetchall()
    return [{'id': r['peer_id'], 'name': r['name']} for r in rows if r['peer_id'] != exclude]


# ---- pages ----

def _rooms_with_counts(db):
    rows = db.execute("SELECT * FROM rooms ORDER BY COALESCE(NULLIF(scheduled_at, ''), created_at) DESC").fetchall()
    out = []
    for r in rows:
        n = db.execute("SELECT COUNT(*) AS c FROM participants WHERE room_id=?", (r['id'],)).fetchone()['c']
        out.append({'id': r['id'], 'label': (r['label'] or '').strip(),
                    'scheduled_at': (r['scheduled_at'] or '').strip(),
                    'created_at': r['created_at'], 'count': n})
    return out


@meet_bp.route('/meet')
def meet_home():
    """Host lobby (authed) — create a link now, join now or at meeting time."""
    if not is_authenticated():
        return redirect(url_for('cockpit.login'))
    db = _db()
    # tidy: drop rooms older than 48h + any orphaned state, so the store doesn't grow forever
    cutoff = (_now() - timedelta(hours=48)).isoformat()
    db.execute("DELETE FROM rooms WHERE created_at < ?", (cutoff,))
    db.execute("DELETE FROM participants WHERE room_id NOT IN (SELECT id FROM rooms)")
    db.execute("DELETE FROM signals WHERE room_id NOT IN (SELECT id FROM rooms)")
    db.commit()
    rooms = _rooms_with_counts(db)
    db.close()
    return render_template('meet_home.html', rooms=rooms)


@meet_bp.route('/meet/new', methods=['POST'])
def meet_new():
    """Create a room (optionally named + scheduled). Does NOT join — shows the link."""
    if not is_authenticated():
        return redirect(url_for('cockpit.login'))
    room_id = secrets.token_urlsafe(6)
    label = (request.form.get('label') or '').strip()[:80]
    when = (request.form.get('when') or '').strip()[:40]
    db = _db()
    db.execute("INSERT INTO rooms (id, created_at, label, scheduled_at) VALUES (?,?,?,?)",
               (room_id, _iso(), label, when))
    db.commit()
    db.close()
    return redirect(url_for('meet.meet_created', room_id=room_id))


@meet_bp.route('/meet/created/<room_id>')
def meet_created(room_id):
    if not is_authenticated():
        return redirect(url_for('cockpit.login'))
    db = _db()
    room = db.execute("SELECT * FROM rooms WHERE id=?", (room_id,)).fetchone()
    db.close()
    if not room:
        return render_template('meet_gone.html'), 404
    return render_template('meet_created.html', room_id=room_id,
                           label=(room['label'] or '').strip(), when=(room['scheduled_at'] or '').strip())


@meet_bp.route('/meet/<room_id>/delete', methods=['POST'])
def meet_delete(room_id):
    if not is_authenticated():
        return redirect(url_for('cockpit.login'))
    db = _db()
    db.execute("DELETE FROM rooms WHERE id=?", (room_id,))
    db.execute("DELETE FROM participants WHERE room_id=?", (room_id,))
    db.execute("DELETE FROM signals WHERE room_id=?", (room_id,))
    db.commit()
    db.close()
    return redirect(url_for('meet.meet_home'))


@meet_bp.route('/meet/r/<room_id>')
def meet_room(room_id):
    """The room — host reaches it authed; guests just open the link and enter a name."""
    db = _db()
    room = db.execute("SELECT id FROM rooms WHERE id=?", (room_id,)).fetchone()
    db.close()
    if not room:
        return render_template('meet_gone.html'), 404
    return render_template('meet_room.html', room_id=room_id, is_host=bool(request.args.get('host')))


# ---- ICE / TURN config ----

@meet_bp.route('/meet/ice')
def meet_ice():
    """ICE servers for the browsers. Cloudflare TURN if configured, else static TURN, else STUN-only."""
    stun = {'urls': ['stun:stun.l.google.com:19302', 'stun:stun.cloudflare.com:3478']}

    key_id = os.environ.get('COCKPIT_CF_TURN_KEY_ID')
    token = os.environ.get('COCKPIT_CF_TURN_TOKEN')
    if key_id and token:
        try:
            r = requests.post(
                f'https://rtc.live.cloudflare.com/v1/turn/keys/{key_id}/credentials/generate',
                headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
                json={'ttl': 3600}, timeout=6)
            if r.ok:
                ice = r.json().get('iceServers')
                if ice:
                    return jsonify({'iceServers': ice if isinstance(ice, list) else [ice]})
        except Exception as e:
            print(f"[meet] CF TURN mint failed: {e}")

    turn_url = os.environ.get('COCKPIT_TURN_URL')
    if turn_url:
        return jsonify({'iceServers': [stun, {
            'urls': turn_url,
            'username': os.environ.get('COCKPIT_TURN_USER', ''),
            'credential': os.environ.get('COCKPIT_TURN_CRED', ''),
        }]})

    return jsonify({'iceServers': [stun]})


# ---- signaling (public: anyone with the room link) ----

@meet_bp.route('/meet/r/<room_id>/join', methods=['POST'])
def meet_join(room_id):
    body = request.json or {}
    peer_id = (body.get('peer_id') or '').strip()
    name = (body.get('name') or 'guest').strip()[:40] or 'guest'
    if not peer_id:
        return jsonify({'error': 'peer_id required'}), 400
    db = _db()
    if not db.execute("SELECT 1 FROM rooms WHERE id=?", (room_id,)).fetchone():
        db.close()
        return jsonify({'error': 'no such room'}), 404
    db.execute("""INSERT INTO participants (room_id, peer_id, name, last_seen) VALUES (?,?,?,?)
                  ON CONFLICT(room_id, peer_id) DO UPDATE SET name=excluded.name, last_seen=excluded.last_seen""",
               (room_id, peer_id, name, _iso()))
    _prune(db, room_id)
    db.commit()
    peers = _roster(db, room_id, exclude=peer_id)
    db.close()
    return jsonify({'peers': peers, 'self': peer_id})


@meet_bp.route('/meet/r/<room_id>/poll', methods=['POST'])
def meet_poll(room_id):
    body = request.json or {}
    peer_id = (body.get('peer_id') or '').strip()
    if not peer_id:
        return jsonify({'error': 'peer_id required'}), 400
    db = _db()
    db.execute("UPDATE participants SET last_seen=? WHERE room_id=? AND peer_id=?", (_iso(), room_id, peer_id))
    _prune(db, room_id)
    sigs = db.execute("SELECT id, from_peer, kind, payload FROM signals WHERE room_id=? AND to_peer=? ORDER BY id",
                      (room_id, peer_id)).fetchall()
    ids = [s['id'] for s in sigs]
    out = [{'from': s['from_peer'], 'kind': s['kind'], 'payload': json.loads(s['payload'])} for s in sigs]
    if ids:
        db.execute("DELETE FROM signals WHERE id IN (%s)" % ",".join("?" * len(ids)), ids)
    db.commit()
    peers = _roster(db, room_id, exclude=peer_id)
    db.close()
    return jsonify({'peers': peers, 'signals': out})


@meet_bp.route('/meet/r/<room_id>/signal', methods=['POST'])
def meet_signal(room_id):
    body = request.json or {}
    to_peer = (body.get('to') or '').strip()
    from_peer = (body.get('from') or '').strip()
    kind = (body.get('kind') or '').strip()
    payload = body.get('payload')
    if not (to_peer and from_peer and kind):
        return jsonify({'error': 'bad signal'}), 400
    db = _db()
    db.execute("INSERT INTO signals (room_id, to_peer, from_peer, kind, payload, created_at) VALUES (?,?,?,?,?,?)",
               (room_id, to_peer, from_peer, kind, json.dumps(payload), _iso()))
    db.commit()
    db.close()
    return jsonify({'ok': True})


@meet_bp.route('/meet/r/<room_id>/leave', methods=['POST'])
def meet_leave(room_id):
    body = request.json or {}
    peer_id = (body.get('peer_id') or '').strip()
    db = _db()
    db.execute("DELETE FROM participants WHERE room_id=? AND peer_id=?", (room_id, peer_id))
    db.execute("DELETE FROM signals WHERE room_id=? AND (to_peer=? OR from_peer=?)", (room_id, peer_id, peer_id))
    db.commit()
    db.close()
    return jsonify({'ok': True})
