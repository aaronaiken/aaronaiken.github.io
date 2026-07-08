/* meet.js — a small WebRTC mesh for a 2-4 person call.
   Flask relays signaling over HTTP polling; media is peer-to-peer. To avoid
   glare in the mesh, the peer with the lexicographically-GREATER id is the
   initiator for each pair (it offers; the other answers). Screen share swaps
   the outgoing video track via replaceTrack — no renegotiation needed. */
(function () {
  var ROOM = window.MEET.room;
  // stable per-room identity (survives a reload so your notes section + mesh spot stay yours)
  var PEER_ID = (function () {
    var rnd = function () { return Math.random().toString(36).slice(2) + Date.now().toString(36); };
    try {
      var k = 'meet-peer-' + ROOM, v = sessionStorage.getItem(k);
      if (!v) { v = rnd(); sessionStorage.setItem(k, v); }
      return v;
    } catch (e) { return rnd(); }
  })();
  var API = '/meet/r/' + encodeURIComponent(ROOM);

  var localStream = null;      // camera + mic
  var camTrack = null;         // the live camera video track (kept for un-share)
  var screenStream = null;     // active screen capture, if any
  var myScreen = false;        // am I currently screen-sharing (broadcast to peers)
  var peerScreen = {};         // peerId -> bool (are THEY screen-sharing → contain, not crop)
  var blurOn = false, blurReady = false;   // background blur (local, sender-side)
  var seg = null, blurVideo = null, blurCanvas = null, blurCtx = null, blurStream = null, blurTrack = null;
  var iceServers = [{ urls: ['stun:stun.l.google.com:19302'] }];
  var peers = {};              // peerId -> { pc, name, tile, pendingCandidates:[] }
  var name = 'guest';
  var polling = false;
  var latestNotes = [];        // shared-notes sections from everyone (from /poll)
  var noteSaveT = null, lastOthers = '';

  var el = function (id) { return document.getElementById(id); };
  var status = function (t) { var s = el('status'); if (s) s.textContent = t || ''; };
  // null-safe click wiring — a missing element (e.g. stale cached HTML) must never crash the join
  function wire(id, fn) { var e = el(id); if (e) e.onclick = fn; }

  function api(path, body) {
    return fetch(API + path, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    }).then(function (r) { return r.json(); });
  }
  function sendSignal(to, kind, payload) {
    return api('/signal', { to: to, from: PEER_ID, kind: kind, payload: payload });
  }

  // ---------- tiles ----------
  function makeTile(id, label, isLocal) {
    var wrap = document.createElement('div');
    wrap.className = 'tile';
    wrap.id = 'tile-' + id;
    var v = document.createElement('video');
    v.autoplay = true; v.playsInline = true;
    if (isLocal) v.muted = true;
    var tag = document.createElement('div');
    tag.className = 'tag';
    tag.textContent = label;
    wrap.appendChild(v); wrap.appendChild(tag);
    el('grid').appendChild(wrap);
    relayout();
    return v;
  }
  function removeTile(id) {
    var t = el('tile-' + id);
    if (t) t.remove();
    relayout();
  }

  // presentation layout: when anyone's screen-sharing, that tile fills the stage and every
  // camera shrinks into a strip on top; otherwise it's the equal grid.
  function relayout() {
    var strip = el('filmstrip'), grid = el('grid'), stage = el('stage');
    if (!strip || !grid || !stage) return;
    var tiles = Array.prototype.slice.call(document.querySelectorAll('.tile'));
    var presenting = tiles.some(function (t) { return t.classList.contains('is-screen'); });
    stage.classList.toggle('presenting', presenting);
    tiles.forEach(function (t) {
      var target = (presenting && !t.classList.contains('is-screen')) ? strip : grid;
      if (t.parentNode !== target) target.appendChild(t);
    });
  }

  // ---------- peer connections ----------
  function ensurePeer(id, pname) {
    if (peers[id]) { if (pname) peers[id].name = pname; return peers[id]; }
    var pc = new RTCPeerConnection({ iceServers: iceServers });
    var video = makeTile(id, pname || 'guest', false);
    var remoteStream = new MediaStream();
    video.srcObject = remoteStream;

    var entry = { pc: pc, name: pname || 'guest', video: video, stream: remoteStream, pending: [], haveRemote: false };
    peers[id] = entry;

    localStream.getTracks().forEach(function (t) { pc.addTrack(t, localStream); });

    pc.onicecandidate = function (e) {
      if (e.candidate) sendSignal(id, 'candidate', e.candidate);
    };
    pc.ontrack = function (e) {
      remoteStream.addTrack(e.track);
    };
    pc.onconnectionstatechange = function () {
      if (pc.connectionState === 'failed' || pc.connectionState === 'closed') dropPeer(id);
    };
    applyScreenClass(id);                                   // apply any screen state already known
    if (myScreen) sendSignal(id, 'screen', { on: true });  // tell a late joiner I'm sharing
    return entry;
  }

  // a peer's tile shows CONTAIN (whole screen, letterboxed) while they screen-share, else COVER (crop for faces)
  function applyScreenClass(id) {
    var t = el('tile-' + id);
    if (t) t.classList.toggle('is-screen', !!peerScreen[id]);
    relayout();
  }
  function broadcastScreen() {
    Object.keys(peers).forEach(function (id) { sendSignal(id, 'screen', { on: myScreen }); });
  }

  function dropPeer(id) {
    var p = peers[id];
    if (!p) return;
    try { p.pc.close(); } catch (e) {}
    removeTile(id);
    delete peers[id];
  }

  // deterministic: greater id initiates
  function amInitiator(otherId) { return PEER_ID > otherId; }

  function startOffer(id, pname) {
    var p = ensurePeer(id, pname);
    p.pc.createOffer().then(function (offer) {
      return p.pc.setLocalDescription(offer);
    }).then(function () {
      sendSignal(id, 'offer', p.pc.localDescription);
    }).catch(function (e) { console.warn('offer failed', e); });
  }

  function onOffer(id, pname, sdp) {
    var p = ensurePeer(id, pname);
    p.pc.setRemoteDescription(new RTCSessionDescription(sdp)).then(function () {
      p.haveRemote = true;
      flushCandidates(p);
      return p.pc.createAnswer();
    }).then(function (ans) {
      return p.pc.setLocalDescription(ans);
    }).then(function () {
      sendSignal(id, 'answer', p.pc.localDescription);
    }).catch(function (e) { console.warn('answer failed', e); });
  }

  function onAnswer(id, sdp) {
    var p = peers[id];
    if (!p) return;
    p.pc.setRemoteDescription(new RTCSessionDescription(sdp)).then(function () {
      p.haveRemote = true;
      flushCandidates(p);
    }).catch(function (e) { console.warn('setRemote(answer) failed', e); });
  }

  function onCandidate(id, cand) {
    var p = peers[id];
    if (!p) return;
    if (!p.haveRemote) { p.pending.push(cand); return; }
    p.pc.addIceCandidate(new RTCIceCandidate(cand)).catch(function () {});
  }
  function flushCandidates(p) {
    p.pending.forEach(function (c) { p.pc.addIceCandidate(new RTCIceCandidate(c)).catch(function () {}); });
    p.pending = [];
  }

  // ---------- roster reconciliation ----------
  function reconcile(roster) {
    var live = {};
    roster.forEach(function (r) {
      live[r.id] = true;
      if (!peers[r.id] && amInitiator(r.id)) startOffer(r.id, r.name);   // I call them
      else if (peers[r.id] && r.name) peers[r.id].name = r.name;
    });
    Object.keys(peers).forEach(function (id) { if (!live[id]) dropPeer(id); });
  }

  // ---------- polling loop ----------
  function poll() {
    if (!polling) return;
    api('/poll', { peer_id: PEER_ID }).then(function (res) {
      if (res.error) { status(res.error); return; }
      if (res.ended) { stopMedia(); showEnd('ended'); return; }
      (res.signals || []).forEach(function (s) {
        if (s.kind === 'offer') onOffer(s.from, null, s.payload);
        else if (s.kind === 'answer') onAnswer(s.from, s.payload);
        else if (s.kind === 'candidate') onCandidate(s.from, s.payload);
        else if (s.kind === 'screen') { peerScreen[s.from] = !!(s.payload && s.payload.on); applyScreenClass(s.from); }
      });
      reconcile(res.peers || []);
      latestNotes = res.notes || [];
      renderOtherNotes(latestNotes);
      var n = (res.peers || []).length;
      status(n === 0 ? 'waiting for others… share the link' : (n + 1) + ' in the room');
    }).catch(function () {}).then(function () {
      if (polling) setTimeout(poll, 1000);
    });
  }

  // ---------- screen share ----------
  function replaceOutgoingVideo(track) {
    Object.keys(peers).forEach(function (id) {
      var sender = peers[id].pc.getSenders().find(function (s) { return s.track && s.track.kind === 'video'; });
      if (sender) sender.replaceTrack(track);
    });
  }
  function localVideoEl() {
    var t = el('tile-local'); return t ? t.querySelector('video') : null;
  }
  function startScreen() {
    return navigator.mediaDevices.getDisplayMedia({ video: true, audio: false }).then(function (s) {
      screenStream = s;
      var track = s.getVideoTracks()[0];
      replaceOutgoingVideo(track);
      var lv = localVideoEl(); if (lv) lv.srcObject = s;
      var lt = el('tile-local'); if (lt) lt.classList.add('is-screen');   // show my whole screen, not cropped
      relayout();
      var sb = el('screen-btn'); if (sb) sb.classList.add('on');
      myScreen = true; broadcastScreen();                                 // peers switch my tile to contain
      track.onended = stopScreen;   // user hit the browser's "stop sharing"
    });
  }
  function stopScreen() {
    if (screenStream) { screenStream.getTracks().forEach(function (t) { t.stop(); }); screenStream = null; }
    replaceOutgoingVideo(currentCamTrack());
    var lv = localVideoEl(); if (lv) lv.srcObject = (blurOn && blurStream) ? blurStream : localStream;
    var lt = el('tile-local'); if (lt) lt.classList.remove('is-screen');
    relayout();
    var sb = el('screen-btn'); if (sb) sb.classList.remove('on');
    myScreen = false; broadcastScreen();
  }

  // ---------- background blur (MediaPipe segmentation, all local + sender-side) ----------
  function currentCamTrack() { return (blurOn && blurTrack) ? blurTrack : camTrack; }

  // blur only works where MediaPipe + canvas.captureStream do — not iOS Safari (incl. iPad, which
  // reports itself as a Mac, caught via maxTouchPoints). Used to hide the button on unsupported devices.
  function blurSupported() {
    if (typeof SelfieSegmentation === 'undefined') return false;
    if (typeof document.createElement('canvas').captureStream !== 'function') return false;
    var ios = /iP(hone|od|ad)/.test(navigator.userAgent) ||
              (navigator.maxTouchPoints > 1 && /Mac/.test(navigator.platform || ''));
    return !ios;
  }

  function onSegResults(results) {
    if (!blurCtx) return;
    var w = results.image.width, h = results.image.height;
    if (blurCanvas.width !== w) blurCanvas.width = w;
    if (blurCanvas.height !== h) blurCanvas.height = h;
    var c = blurCtx;
    c.save();
    c.clearRect(0, 0, w, h);
    c.drawImage(results.segmentationMask, 0, 0, w, h);
    c.globalCompositeOperation = 'source-in';        // keep camera only where the person is
    c.drawImage(results.image, 0, 0, w, h);
    c.globalCompositeOperation = 'destination-over';  // put the blurred frame behind
    c.filter = 'blur(12px)';
    c.drawImage(results.image, 0, 0, w, h);
    c.restore();
    if (blurOn && !blurReady && !screenStream) {       // first good frame → go live
      blurReady = true;
      replaceOutgoingVideo(blurTrack);
      var lv = localVideoEl(); if (lv) lv.srcObject = blurStream;
      var bb = el('blur-btn'); if (bb) { bb.classList.remove('loading'); bb.classList.add('on'); }
      status('');
    }
  }

  function ensureBlur() {
    if (seg) return true;
    if (typeof SelfieSegmentation === 'undefined') return false;   // library didn't load
    try {
      blurVideo = document.createElement('video');
      blurVideo.muted = true; blurVideo.playsInline = true; blurVideo.srcObject = localStream;
      blurVideo.play().catch(function () {});
      blurCanvas = document.createElement('canvas'); blurCanvas.width = 640; blurCanvas.height = 480;
      blurCtx = blurCanvas.getContext('2d');
      seg = new SelfieSegmentation({ locateFile: function (f) {
        return 'https://cdn.jsdelivr.net/npm/@mediapipe/selfie_segmentation/' + f;
      } });
      seg.setOptions({ modelSelection: 1 });
      seg.onResults(onSegResults);
      blurStream = blurCanvas.captureStream && blurCanvas.captureStream(24);   // unsupported on some iOS
      blurTrack = blurStream && blurStream.getVideoTracks()[0];
      if (!blurTrack) { seg = null; return false; }
      return true;
    } catch (e) {
      console.warn('[meet] blur init failed:', e);
      seg = null; blurStream = null; blurTrack = null;
      return false;
    }
  }

  function pump() {
    if (!blurOn || !seg) return;
    seg.send({ image: blurVideo }).catch(function () {}).then(function () {
      if (blurOn) setTimeout(pump, 40);   // ~25fps, and don't over-queue
    });
  }

  function revertBlur(msg) {
    blurOn = false; blurReady = false;
    replaceOutgoingVideo(camTrack);
    var lv = localVideoEl(); if (lv) lv.srcObject = localStream;
    var bb = el('blur-btn'); if (bb) bb.classList.remove('on', 'loading');
    if (msg) status(msg);
  }

  function toggleBlur() {
    if (screenStream) { status('stop screen share to blur'); return; }
    if (blurOn) { revertBlur(''); return; }
    if (!ensureBlur()) { status('blur isn’t supported on this device'); return; }
    blurOn = true; blurReady = false;
    var b = el('blur-btn'); if (b) b.classList.add('loading');
    status('starting blur…');
    pump();
    // if no blurred frame arrives (e.g. iOS Safari can't run the pipeline), give up gracefully
    setTimeout(function () { if (blurOn && !blurReady) revertBlur('blur isn’t supported on this device'); }, 6000);
  }

  // ---------- controls ----------
  function wireControls() {
    wire('mic-btn', function () {
      var t = localStream.getAudioTracks()[0]; if (!t) return;
      t.enabled = !t.enabled;
      this.classList.toggle('off', !t.enabled);
    });
    wire('cam-btn', function () {
      if (!camTrack) return;
      camTrack.enabled = !camTrack.enabled;
      this.classList.toggle('off', !camTrack.enabled);
    });
    wire('screen-btn', function () {
      if (screenStream) stopScreen(); else startScreen().catch(function () {});
    });
    if (blurSupported()) wire('blur-btn', toggleBlur);
    else { var _bb = el('blur-btn'); if (_bb) _bb.style.display = 'none'; }
    wire('copy-btn', function () {
      var link = location.origin + '/meet/r/' + encodeURIComponent(ROOM);
      navigator.clipboard.writeText(link).then(function () {
        var b = el('copy-btn'); b.classList.add('on');
        setTimeout(function () { b.classList.remove('on'); }, 1200);
      });
    });
    wire('leave-btn', onLeaveClick);
    wireNotes();
    wire('ended-copy', function () {
      var b = el('ended-copy');
      navigator.clipboard.writeText(el('ended-notes').value).then(function () {
        b.textContent = 'COPIED ✓'; setTimeout(function () { b.textContent = 'COPY NOTES'; }, 1300);
      });
    });
    window.addEventListener('pagehide', beaconLeave);
  }

  function stopMedia() {
    polling = false;
    blurOn = false;
    Object.keys(peers).forEach(dropPeer);
    if (screenStream) screenStream.getTracks().forEach(function (t) { t.stop(); });
    if (blurStream) blurStream.getTracks().forEach(function (t) { t.stop(); });
    if (seg && seg.close) { try { seg.close(); } catch (e) {} }
    if (localStream) localStream.getTracks().forEach(function (t) { t.stop(); });
  }
  function beaconLeave() {
    if (navigator.sendBeacon) {
      navigator.sendBeacon(API + '/leave', new Blob([JSON.stringify({ peer_id: PEER_ID })], { type: 'application/json' }));
    } else {
      api('/leave', { peer_id: PEER_ID });
    }
  }
  function onLeaveClick() {
    stopMedia();
    beaconLeave();
    if (window.MEET.isHost) api('/close', {}).catch(function () {});   // host leaving ends it for everyone
    showEnd(window.MEET.isHost ? 'closed' : 'left');
  }

  // ---------- shared notes (everyone sees everyone's; each edits only their own section) ----------
  var NOTES_KEY = 'meet-notes-' + ROOM;

  function saveNoteSoon() {
    clearTimeout(noteSaveT);
    noteSaveT = setTimeout(function () {
      var ta = el('notes-text');
      api('/note', { peer_id: PEER_ID, name: name, body: ta ? ta.value : '' }).catch(function () {});
    }, 500);
  }

  function renderOtherNotes(notes) {
    var box = el('notes-others'); if (!box) return;
    var others = (notes || []).filter(function (n) { return n.peer_id !== PEER_ID; });
    var sig = JSON.stringify(others);
    if (sig === lastOthers) return;   // unchanged → don't re-render (avoids flicker while others type)
    lastOthers = sig;
    box.innerHTML = '';
    others.forEach(function (n) {
      if (!(n.body || '').trim()) return;
      var sec = document.createElement('div'); sec.className = 'note-section';
      var who = document.createElement('div'); who.className = 'note-who'; who.textContent = n.name || 'guest';
      var b = document.createElement('div'); b.className = 'note-body'; b.textContent = n.body;
      sec.appendChild(who); sec.appendChild(b); box.appendChild(sec);
    });
  }

  function combinedNotes() {   // everyone's notes, for the end-screen copy
    var parts = [];
    var ta = el('notes-text');
    if (ta && ta.value.trim()) parts.push('you:\n' + ta.value.trim());
    latestNotes.forEach(function (n) {
      if (n.peer_id === PEER_ID || !(n.body || '').trim()) return;
      parts.push((n.name || 'guest') + ':\n' + n.body.trim());
    });
    return parts.join('\n\n');
  }

  function wireNotes() {
    var ta = el('notes-text');
    if (ta) ta.value = localStorage.getItem(NOTES_KEY) || '';
    if (ta && ta.value.trim()) saveNoteSoon();   // push a restored note so the room sees it
    wire('notes-btn', function () { var p = el('notes-panel'); if (p) p.classList.toggle('hidden'); if (ta) ta.focus(); });
    wire('notes-close', function () { var p = el('notes-panel'); if (p) p.classList.add('hidden'); });
    if (ta) ta.addEventListener('input', function () {
      localStorage.setItem(NOTES_KEY, ta.value);
      saveNoteSoon();
      var s = el('notes-saved'); if (s) { s.textContent = 'saved'; clearTimeout(ta._t); ta._t = setTimeout(function () { s.textContent = ''; }, 900); }
    });
    wire('notes-copy', function () {
      var b = el('notes-copy');
      navigator.clipboard.writeText(combinedNotes()).then(function () { b.textContent = 'copied ✓'; setTimeout(function () { b.textContent = 'copy all'; }, 1000); });
    });
  }

  // ---------- end screen ----------
  function showEnd(mode) {   // 'left' guest left · 'closed' host ended · 'ended' host ended (guest POV)
    var titles = { left: "you've left the meeting", closed: 'meeting ended', ended: 'the meeting ended' };
    el('stage').classList.add('hidden');
    el('name-gate').classList.add('hidden');
    var et = el('ended-title'); if (et) et.textContent = titles[mode] || 'meeting ended';
    var en = el('ended-notes'); if (en) en.value = combinedNotes();
    var rejoin = el('ended-rejoin');
    if (rejoin) {
      if (mode === 'left') { rejoin.classList.remove('hidden'); rejoin.href = location.pathname; }
      else rejoin.classList.add('hidden');
    }
    var nw = el('ended-new'); if (nw) nw.classList.toggle('hidden', !window.MEET.isHost);
    var end = el('ended'); if (end) end.classList.remove('hidden');
  }

  // ---------- join ----------
  function begin() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      el('gate-error').textContent = 'this browser blocks camera/mic here (needs https).';
      return;
    }
    navigator.mediaDevices.getUserMedia({ video: true, audio: true }).then(function (stream) {
      localStream = stream;
      camTrack = localStream.getVideoTracks()[0];
      return fetch('/meet/ice').then(function (r) { return r.json(); }).catch(function () { return null; });
    }).then(function (ice) {
      if (ice && ice.iceServers) iceServers = ice.iceServers;
      el('name-gate').classList.add('hidden');
      el('stage').classList.remove('hidden');
      var lv = makeTile('local', name + ' (you)', true);
      lv.srcObject = localStream;
      wireControls();
      polling = true;
      return api('/join', { peer_id: PEER_ID, name: name });
    }).then(function (res) {
      if (res && res.peers) reconcile(res.peers);
      poll();
    }).catch(function (err) {
      console.error('[meet] join failed:', err);
      var permission = err && (err.name === 'NotAllowedError' || err.name === 'NotFoundError' || err.name === 'NotReadableError');
      el('gate-error').textContent = permission
        ? 'need camera + mic access to join. (' + err.name + ')'
        : 'could not start: ' + (err && (err.message || err.name) || 'unknown error');
      el('name-gate').classList.remove('hidden');
      el('stage').classList.add('hidden');
    });
  }

  function onJoinClick() {
    name = (el('name-input').value || '').trim().slice(0, 40) || 'guest';
    el('gate-error').textContent = '';
    begin();
  }

  el('join-btn').onclick = onJoinClick;
  el('name-input').addEventListener('keydown', function (e) { if (e.key === 'Enter') onJoinClick(); });
  el('name-input').focus();
})();
