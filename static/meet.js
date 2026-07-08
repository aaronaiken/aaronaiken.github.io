/* meet.js — a small WebRTC mesh for a 2-4 person call.
   Flask relays signaling over HTTP polling; media is peer-to-peer. To avoid
   glare in the mesh, the peer with the lexicographically-GREATER id is the
   initiator for each pair (it offers; the other answers). Screen share swaps
   the outgoing video track via replaceTrack — no renegotiation needed. */
(function () {
  var ROOM = window.MEET.room;
  var PEER_ID = Math.random().toString(36).slice(2) + Date.now().toString(36);
  var API = '/meet/r/' + encodeURIComponent(ROOM);

  var localStream = null;      // camera + mic
  var camTrack = null;         // the live camera video track (kept for un-share)
  var screenStream = null;     // active screen capture, if any
  var iceServers = [{ urls: ['stun:stun.l.google.com:19302'] }];
  var peers = {};              // peerId -> { pc, name, tile, pendingCandidates:[] }
  var name = 'guest';
  var polling = false;

  var el = function (id) { return document.getElementById(id); };
  var status = function (t) { var s = el('status'); if (s) s.textContent = t || ''; };

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
    return v;
  }
  function removeTile(id) {
    var t = el('tile-' + id);
    if (t) t.remove();
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
    return entry;
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
      (res.signals || []).forEach(function (s) {
        if (s.kind === 'offer') onOffer(s.from, null, s.payload);
        else if (s.kind === 'answer') onAnswer(s.from, s.payload);
        else if (s.kind === 'candidate') onCandidate(s.from, s.payload);
      });
      reconcile(res.peers || []);
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
      el('screen-btn').classList.add('on');
      track.onended = stopScreen;   // user hit the browser's "stop sharing"
    });
  }
  function stopScreen() {
    if (screenStream) { screenStream.getTracks().forEach(function (t) { t.stop(); }); screenStream = null; }
    replaceOutgoingVideo(camTrack);
    var lv = localVideoEl(); if (lv) lv.srcObject = localStream;
    el('screen-btn').classList.remove('on');
  }

  // ---------- controls ----------
  function wireControls() {
    el('mic-btn').onclick = function () {
      var t = localStream.getAudioTracks()[0]; if (!t) return;
      t.enabled = !t.enabled;
      this.classList.toggle('off', !t.enabled);
    };
    el('cam-btn').onclick = function () {
      if (!camTrack) return;
      camTrack.enabled = !camTrack.enabled;
      this.classList.toggle('off', !camTrack.enabled);
    };
    el('screen-btn').onclick = function () {
      if (screenStream) stopScreen(); else startScreen().catch(function () {});
    };
    el('copy-btn').onclick = function () {
      var link = location.origin + '/meet/r/' + encodeURIComponent(ROOM);
      navigator.clipboard.writeText(link).then(function () {
        var b = el('copy-btn'); b.classList.add('on');
        setTimeout(function () { b.classList.remove('on'); }, 1200);
      });
    };
    el('leave-btn').onclick = leave;
    window.addEventListener('pagehide', leave);
  }

  function leave() {
    polling = false;
    Object.keys(peers).forEach(dropPeer);
    if (localStream) localStream.getTracks().forEach(function (t) { t.stop(); });
    navigator.sendBeacon
      ? navigator.sendBeacon(API + '/leave', new Blob([JSON.stringify({ peer_id: PEER_ID })], { type: 'application/json' }))
      : api('/leave', { peer_id: PEER_ID });
  }

  // ---------- join ----------
  function begin() {
    Promise.all([
      navigator.mediaDevices.getUserMedia({ video: true, audio: true }),
      fetch('/meet/ice').then(function (r) { return r.json(); }).catch(function () { return null; })
    ]).then(function (arr) {
      localStream = arr[0];
      camTrack = localStream.getVideoTracks()[0];
      if (arr[1] && arr[1].iceServers) iceServers = arr[1].iceServers;

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
      el('gate-error').textContent = 'need camera + mic access to join. (' + (err && err.name || 'error') + ')';
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
