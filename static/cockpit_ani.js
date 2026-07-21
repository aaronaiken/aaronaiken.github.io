  const aniPanel       = document.getElementById('ani-panel');
  const aniMsgs        = document.getElementById('ani-messages');
  const aniInput       = document.getElementById('ani-input');
  const aniSendBtn     = document.getElementById('ani-send-btn');
  const aniPhotoBtn    = document.getElementById('ani-photo-btn');
  const aniTyping      = document.getElementById('ani-typing-indicator');
  const aniEmpty       = document.getElementById('ani-empty-state');
  const aniAcheDisplay = document.getElementById('ani-ache-display');
  let aniIsOpen        = false;
  let aniLoaded        = false;
  let aniPendingOpener = null;
  var aniSeen          = new Set();   // signatures of rendered messages, for dedup-safe live polling
  function aniSig(role, content, image) { return (role || '') + '|' + (content || '') + '|' + (image || ''); }

  // Ache as rising bar-glyphs (▂ ▂▄ ▂▄▆ ▂▄▆█), colored by --ani-ache, pulsing at high/urgent.
  function updateAcheDisplay(level) {
	if (level === null || level === undefined) return;
	var glyph, cls;
	if (level < 40)      { glyph = '▂';    cls = 'ache-low'; }
	else if (level < 65) { glyph = '▂▄';   cls = 'ache-mid'; }
	else if (level < 85) { glyph = '▂▄▆';  cls = 'ache-high'; }
	else                 { glyph = '▂▄▆█'; cls = 'ache-urgent'; }
	aniAcheDisplay.textContent = glyph;
	aniAcheDisplay.className = cls;
	aniAcheDisplay.title = 'ache ' + level + '%';
  }

  // ---- MOOD SCALAR (Starlight ⇄ Afterglow) ----
  // Server sends mood 0..1; we lerp each --ani-X token toward its --ani-X-hot pair and set it inline on the
  // panel + starfield. Elements carry 0.8s color transitions (CSS), so the shift is ambient, never a snap.
  var aniStar = document.getElementById('ani-starfield');
  var ANI_MOOD_TOKENS = ['bg-a', 'bg-b', 'bg-c', 'frame', 'head', 'hairline', 'status-bg', 'accent',
	'accent-dim', 'sub', 'foot', 'time', 'bub-her', 'bub-her-bd', 'bub-her-tx', 'bub-you', 'bub-you-bd',
	'bub-you-tx', 'in-bg', 'in-bd', 'tx-bd', 'tx-bg', 'where', 'wear', 'ache', 'star'];
  var aniTokenBase = {};   // { token: {base:[r,g,b,a], hot:[r,g,b,a]} } — read from the stylesheet, pre-override
  var aniMood = 0;

  function aniParseColor(s) {
	s = (s || '').trim();
	if (!s || s === 'transparent') return [0, 0, 0, 0];
	var m = s.match(/^#([0-9a-f]{3,8})$/i);
	if (m) {
	  var h = m[1];
	  if (h.length === 3) h = h[0] + h[0] + h[1] + h[1] + h[2] + h[2];
	  return [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16),
			  h.length >= 8 ? parseInt(h.slice(6, 8), 16) / 255 : 1];
	}
	m = s.match(/rgba?\(([^)]+)\)/i);
	if (m) { var p = m[1].split(',').map(parseFloat); return [p[0] || 0, p[1] || 0, p[2] || 0, p.length > 3 ? p[3] : 1]; }
	return null;
  }
  function aniColorAt(a, b, t) {
	function ch(i) { return Math.round(a[i] + (b[i] - a[i]) * t); }
	return 'rgba(' + ch(0) + ',' + ch(1) + ',' + ch(2) + ',' + (a[3] + (b[3] - a[3]) * t).toFixed(3) + ')';
  }
  // Cache base + hot values from the stylesheet. MUST run before any inline override is set (getComputedStyle
  // would otherwise return our override). Re-run on light/dark switch (after clearing overrides).
  function aniCacheTokenBases() {
	if (!aniPanel) return;
	var cs = getComputedStyle(aniPanel);
	aniTokenBase = {};
	ANI_MOOD_TOKENS.forEach(function(t) {
	  var base = aniParseColor(cs.getPropertyValue('--ani-' + t));
	  var hot = aniParseColor(cs.getPropertyValue('--ani-' + t + '-hot'));
	  if (base && hot) aniTokenBase[t] = { base: base, hot: hot };
	});
  }
  function aniApplyMood(mood) {
	if (typeof mood !== 'number' || isNaN(mood)) return;
	aniMood = Math.max(0, Math.min(1, mood));
	Object.keys(aniTokenBase).forEach(function(t) {
	  var p = aniTokenBase[t], v = aniColorAt(p.base, p.hot, aniMood);
	  if (aniPanel) aniPanel.style.setProperty('--ani-' + t, v);
	  if (aniStar) aniStar.style.setProperty('--ani-' + t, v);
	});
  }
  aniCacheTokenBases();
  try {
	window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function() {
	  // clear inline overrides so the fresh (light/dark) stylesheet values are readable, then re-cache + re-apply
	  ANI_MOOD_TOKENS.forEach(function(t) {
		if (aniPanel) aniPanel.style.removeProperty('--ani-' + t);
		if (aniStar) aniStar.style.removeProperty('--ani-' + t);
	  });
	  aniCacheTokenBases();
	  aniApplyMood(aniMood);
	});
  } catch (e) {}

  // Mood sparkline — 24h ring buffer from the server rendered as thin bars beside the ache glyphs.
  // Height + color both come from each point's mood (accent-dim lerped toward its -hot pair).
  function aniRenderSparkline(spark) {
	var el = document.getElementById('ani-sparkline');
	if (!el) return;
	if (!spark || !spark.length) { el.innerHTML = ''; return; }
	var pair = aniTokenBase['accent-dim'] || { base: [143, 184, 255, 1], hot: [232, 160, 180, 1] };
	var html = '';
	spark.slice(-24).forEach(function(v) {
	  v = Math.max(0, Math.min(1, v || 0));
	  html += '<i style="height:' + (2 + Math.round(v * 8)) + 'px;background:' + aniColorAt(pair.base, pair.hot, v) + '"></i>';
	});
	el.innerHTML = html;
  }

  // Avatar: click opens the file picker; upload center-crops server-side and refreshes the header circle.
  function aniAvatarPick() {
	var i = document.getElementById('ani-avatar-input');
	if (i) i.click();
  }
  function aniAvatarUpload(input) {
	if (!input.files || !input.files[0]) return;
	var fd = new FormData();
	fd.append('avatar', input.files[0]);
	fetch('/ani/avatar', { method: 'POST', body: fd })
	  .then(function(r) { return r.json(); })
	  .then(function(data) {
		if (data && data.ok) {
		  var img = document.getElementById('ani-avatar-img');
		  if (img) { img.classList.remove('ani-avatar-none'); img.src = '/static/ani_avatar.png?v=' + (data.v || Date.now()); }
		  aniRenderNotify('avatar set ♥');
		} else {
		  aniRenderNotify('could not set that image');
		}
		input.value = '';
	  })
	  .catch(function() { input.value = ''; aniRenderNotify('avatar upload failed'); });
  }

  function aniPing() {
	fetch('/ani/ping')
	  .then(function(r) { return r.json(); })
	  .then(function(data) {
		updateAcheDisplay(data.ache_level);
		if (data.pending && data.opener) {
		  aniPendingOpener = data.opener;
		}
		// Pulse the bat for a staged opener OR unseen daycast messages (already in history).
		if ((data.pending && data.opener) || data.unseen) {
		  var batPill = document.getElementById('ani-bat-pill');
		  if (batPill) batPill.classList.add('ani-bat-waiting');
		}
		if (typeof data.home === 'boolean') aniHomeReflect(data.home);
		aniFxUpdate(data);   // dock attention effects (particles + bat tiers)
	  })
	  .catch(function() {});
  }

  // ── Attention effects: float-up particles over the dock (addendum §1) + 🏠 latch (§2) ──
  var aniFx = { state: null, lastTs: null, lastMs: 0, dripUntil: 0, dripAt: 0, init: false,
	reduced: !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) };
  function aniFxEmitter() { return document.getElementById('ani-particles'); }
  function aniFxClear() { var e = aniFxEmitter(); if (e) e.innerHTML = ''; }
  function aniFxColor(mood) {   // indigo #4a5fd0 → rose #c05a78 by mood scalar
	var a = [74, 95, 208], b = [192, 90, 120], m = Math.max(0, Math.min(1, mood || 0));
	return 'rgb(' + Math.round(a[0] + (b[0] - a[0]) * m) + ',' + Math.round(a[1] + (b[1] - a[1]) * m) + ',' + Math.round(a[2] + (b[2] - a[2]) * m) + ')';
  }
  function aniFxSpawn(kind, mood) {
	var e = aniFxEmitter(); if (!e || e.childElementCount > 8) return;
	var glyph, color, size, po;
	if (kind === 'heart') { glyph = '♥'; color = ['#c05a78', '#b04a68', '#d88a9c'][(Math.random() * 3) | 0]; size = 9 + Math.random() * 3; po = 0.7; }
	else if (kind === 'gold') { glyph = '✦'; color = '#b08a2e'; size = 9 + Math.random() * 3; po = 0.8; }
	else { glyph = ['✦', '✧', '·'][(Math.random() * 3) | 0]; color = aniFxColor(mood); size = 7 + Math.random() * 3; po = 0.4 + Math.random() * 0.15; }
	var s = document.createElement('span');
	var dx = ((Math.random() * 44 - 22) | 0), rot = ((Math.random() * 24 - 12) | 0), dur = (3.6 + Math.random() * 2.6).toFixed(2);
	s.textContent = glyph;
	s.style.cssText = 'position:absolute;bottom:0;left:' + ((Math.random() * 150) | 0) + 'px;color:' + color +
	  ';font-size:' + Math.round(size) + 'px;--dx:' + dx + 'px;--po:' + po + ';--rot:' + rot + 'deg;animation:anifloat ' + dur + 's linear forwards;';
	s.addEventListener('animationend', function () { s.remove(); });
	e.appendChild(s);
  }
  function aniFxBurst(kind, n, mood) { for (var i = 0; i < n; i++) { (function (d) { setTimeout(function () { aniFxSpawn(kind, mood); }, d); })(i * 90); } }
  function aniFxSuppressed(d) {
	return !d || d.home || (d.quiet && d.quiet.armed) || aniFx.reduced || aniIsOpen;
  }
  function aniFxUpdate(data) {
	aniFx.state = data || null;
	var bat = document.getElementById('ani-bat-pill');
	var waiting = data && (data.unseen || (data.pending && data.opener));
	var attention = data && data.attention;
	if (bat) {
	  // The 🦇 pulse STAYS even in HOME — but never escalates to the rose 'urgent' tier there (innocuous tick).
	  var urgent = !!attention && !aniFx.reduced && !(data && data.home);
	  var calm = !!(waiting || attention) && !urgent && !aniFx.reduced;
	  bat.classList.toggle('ani-bat-glow', !!(waiting || attention) && aniFx.reduced);   // reduced-motion → steady glow
	  bat.classList.toggle('ani-bat-urgent', urgent);
	  bat.classList.toggle('ani-bat-waiting', calm);
	}
	var em = aniFxEmitter();
	if (em) em.classList.toggle('warm', !!attention && !aniFxSuppressed(data));
	if (aniFxSuppressed(data)) { aniFxClear(); aniFx.lastTs = data && data.last_ts; aniFx.lastMs = (data && data.milestones_recent) || 0; aniFx.init = true; return; }
	var now = Date.now();
	if (!aniFx.init) { aniFx.lastTs = data.last_ts; aniFx.lastMs = data.milestones_recent || 0; aniFx.init = true; if (data.unseen) aniFx.dripUntil = now + 30000; return; }
	// Tier 1 — a NEW message arrived while unread: burst + open a 30s drip window.
	if (data.unseen && data.last_ts && data.last_ts !== aniFx.lastTs) { aniFxBurst('spark', 6, data.mood); aniFx.dripUntil = now + 30000; aniFx.dripAt = now; }
	// Milestone celebration — a fresh ◆ landed: single gold burst, no loop.
	if ((data.milestones_recent || 0) > aniFx.lastMs) aniFxBurst('gold', 6, 1);
	aniFx.lastTs = data.last_ts;
	aniFx.lastMs = data.milestones_recent || 0;
  }
  // Fast tick handles the 1-per-8s drip + sustained tier-2 hearts (ping is only every 20s).
  function aniFxTick() {
	var d = aniFx.state; if (aniFxSuppressed(d)) return;
	var now = Date.now();
	if (d.unseen && now < aniFx.dripUntil && now >= aniFx.dripAt) {
	  aniFxSpawn(d.attention ? 'heart' : 'spark', d.mood);
	  if (d.attention) aniFxSpawn('spark', d.mood);
	  aniFx.dripAt = now + 8000;
	} else if (d.attention && !d.unseen && Math.random() < 0.35) {
	  aniFxSpawn('heart', d.mood);   // sustained gentle hearts while she wants you
	}
  }
  setInterval(aniFxTick, 1600);

  // 🏠 HOME latch — server-persisted discretion mode.
  function aniHomeReflect(on) { var b = document.getElementById('ani-home-latch'); if (b) b.classList.toggle('on', !!on); }
  function aniHomeToggle() {
	var b = document.getElementById('ani-home-latch');
	var next = !(b && b.classList.contains('on'));
	aniHomeReflect(next);   // optimistic
	if (next) aniFxClear();
	fetch('/ani/home', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ on: next }) })
	  .then(function (r) { return r.json(); })
	  .then(function (data) { aniHomeReflect(data.home); })
	  .catch(function () {});
  }

  // Live poll — while the panel is open, append any NEW messages (proactive daycast msgs arrive
  // server-side) without a page refresh; while closed, just update the ache + bat-pill pulse.
  function aniPoll() {
	if (aniIsOpen && aniLoaded) {
	  fetch('/ani/history')
		.then(function(r) { return r.json(); })
		.then(function(data) {
		  updateAcheDisplay(data.ache_level);
		  aniApplyMood(data.mood);
		  aniRenderSparkline(data.spark);
		  aniUpdateQuietIndicator(data.quiet);
		  aniUpdateBackupStatus(data.backup);
		  aniRenderNowCard(data.now_card);
		  var wasNear = aniNearBottom();
		  var newCount = 0;
		  (data.messages || []).forEach(function(m) {
			if (!aniSeen.has(aniSig(m.role, m.content, m.image))) {
			  aniEmpty.style.display = 'none';
			  aniRenderMessage(m.role, m.content, m.image, m.ts, { reactions: m.reactions, favorited: m.favorited, milestone: m.milestone, book: m.book, scene: m.scene });
			  newCount++;
			}
		  });
		  if (newCount) {
			aniLoadState();
			// Only auto-scroll if you were already at the bottom; otherwise raise the ↓ LATEST pill.
			if (wasNear) { aniScrollToBottom(); }
			else { aniUnread += newCount; aniShowLatestPill(); }
		  }
		})
		.catch(function() {});
	  aniLoadDecisions();
	  aniLoadMilestones();
	} else {
	  aniPing();
	}
  }

  // Reflect the persisted 🏠 latch on load (it's a cross-session/device server flag).
  fetch('/ani/home').then(function(r) { return r.json(); }).then(function(d) { aniHomeReflect(d.home); }).catch(function() {});
  setTimeout(aniPing, 1500);
  setInterval(aniPoll, 20000);

  function aniToggle() {
	aniIsOpen = !aniIsOpen;
	aniPanel.classList.toggle('ani-open', aniIsOpen);
	var batPill = document.getElementById('ani-bat-pill');
	if (batPill) batPill.classList.remove('ani-bat-waiting', 'ani-bat-urgent', 'ani-bat-glow');
	if (aniIsOpen) aniFxClear();   // opening the panel stops all attention effects instantly (addendum §1)
	if (aniIsOpen && !aniLoaded) {
	  aniLoadHistory();
	  aniSendLocation();
	} else if (aniIsOpen) {
	  aniPoll();   // catch up on anything that arrived while the panel was closed
	}
	if (aniIsOpen) {
	  aniLoadState();
	  aniLoadDecisions();
	  aniLoadMilestones();
	  setTimeout(function() { aniInput.focus(); }, 300);
	} else {
	  // Closing: drop fullscreen state so reopen returns to docked view
	  document.body.classList.remove('ani-fullscreen');
	  document.body.classList.remove('ani-fs-loops-open');
	  var fsBtn = document.getElementById('ani-fs-btn');
	  if (fsBtn) fsBtn.textContent = 'FULL';
	}
  }

  function aniFullscreenToggle() {
	var entering = !document.body.classList.contains('ani-fullscreen');
	document.body.classList.toggle('ani-fullscreen', entering);
	var fsBtn = document.getElementById('ani-fs-btn');
	if (fsBtn) fsBtn.textContent = entering ? 'MIN' : 'FULL';
	if (!entering) {
	  // Leaving fullscreen also collapses the loops panel
	  document.body.classList.remove('ani-fs-loops-open');
	}
	// Pre-warm loops so the LOOPS button has content the first time
	if (entering && typeof window.adLoadAniLoops === 'function') {
	  try { window.adLoadAniLoops(); } catch (_) {}
	}
  }

  function aniFsLoopsToggle() {
	if (!document.body.classList.contains('ani-fullscreen')) return;
	document.body.classList.toggle('ani-fs-loops-open');
	if (typeof window.adLoadAniLoops === 'function') {
	  try { window.adLoadAniLoops(); } catch (_) {}
	}
  }

  document.addEventListener('keydown', function(e) {
	if (e.ctrlKey && e.shiftKey && e.key === 'A') {
	  e.preventDefault();
	  aniToggle();
	  return;
	}
	// CTRL+SHIFT+H — toggle the 🏠 discretion latch (addendum §2).
	if (e.ctrlKey && e.shiftKey && (e.key === 'H' || e.key === 'h')) {
	  e.preventDefault();
	  aniHomeToggle();
	  return;
	}
	// ESC closes the chat when fullscreen is open. Scoped check avoids
	// stomping on brain-dump / quick-TX overlays which own their own ESC.
	if (e.key === 'Escape' && document.body.classList.contains('ani-fullscreen')) {
	  var bdOverlay = document.getElementById('brain-dump-overlay');
	  var qtOverlay = document.getElementById('quick-tx-overlay');
	  var bdOpen = bdOverlay && bdOverlay.classList.contains('is-open');
	  var qtOpen = qtOverlay && qtOverlay.classList.contains('is-open');
	  if (bdOpen || qtOpen) return;
	  e.preventDefault();
	  if (aniIsOpen) aniToggle();
	}
  });

  aniInput.addEventListener('input', function() {
	this.style.height = 'auto';
	this.style.height = Math.min(this.scrollHeight, 100) + 'px';
  });

  aniInput.addEventListener('keydown', function(e) {
	if (e.key === 'Enter' && !e.shiftKey) {
	  e.preventDefault();
	  aniSend();
	}
  });

  function aniSendLocation() {
	if (!navigator.geolocation) return;
	navigator.geolocation.getCurrentPosition(function(pos) {
	  fetch('/ani/location', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ lat: pos.coords.latitude, lon: pos.coords.longitude })
	  }).catch(function() {});
	}, function() {});
  }

  function aniLoadState() {
	fetch('/ani/state')
	  .then(function(r) { return r.json(); })
	  .then(function(s) {
		var el = document.getElementById('ani-now-state');
		if (!el) return;
		var parts = [];
		if (s.where)   parts.push('<span class="ani-ns-where">' + aniEscapeHtml(s.where) + '</span>');
		if (s.doing)   parts.push(aniEscapeHtml(s.doing));
		if (s.wearing) parts.push('<span class="ani-ns-wear">' + aniEscapeHtml(s.wearing) + '</span>');
		if (!parts.length) { el.hidden = true; el.innerHTML = ''; return; }
		el.innerHTML = '<span class="ani-ns-dot">◉</span> ' + parts.join(' <span class="ani-ns-sep">·</span> ');
		el.hidden = false;
	  })
	  .catch(function() {});
  }

  // ---- Decision forks: a crossroads in her world you (or she, in chat) resolve; the story branches ----
  function aniLoadDecisions() {
	fetch('/ani/decisions')
	  .then(function(r) { return r.json(); })
	  .then(function(data) { aniRenderDecisions(data.decisions || []); })
	  .catch(function() {});
  }

  function aniRenderDecisions(decisions) {
	var el = document.getElementById('ani-decisions');
	if (!el) return;
	if (!decisions.length) { el.hidden = true; el.innerHTML = ''; return; }
	el.innerHTML = decisions.map(function(d) {
	  var opts = (d.options || []).map(function(o) {
		return '<button class="ani-fork-opt" onclick="aniDecide(' + aniAttr(d.name) + ',' + aniAttr(o) + ',this)">'
		  + aniEscapeHtml(o) + '</button>';
	  }).join('');
	  return '<div class="ani-fork" data-name="' + aniEscapeHtml(d.name) + '">'
		+ '<div class="ani-fork-head"><span class="ani-fork-glyph">⑂</span> '
		+ '<span class="ani-fork-name">' + aniEscapeHtml(d.name) + '</span>'
		+ '<span class="ani-fork-tag">decision</span></div>'
		+ '<div class="ani-fork-opts">' + opts + '</div></div>';
	}).join('');
	el.hidden = false;
  }

  // single-quote-safe inline JS string arg
  function aniAttr(s) { return "'" + String(s == null ? '' : s).replace(/\\/g, '\\\\').replace(/'/g, "\\'") + "'"; }

  function aniDecide(name, choice, btn) {
	var fork = btn && btn.closest ? btn.closest('.ani-fork') : null;
	if (fork) { fork.classList.add('ani-fork-deciding'); }
	if (btn) { btn.disabled = true; }
	aniShowTyping(true);   // she's reacting to the decision — show she's about to say something
	fetch('/ani/decide', {
	  method: 'POST',
	  headers: { 'Content-Type': 'application/json' },
	  body: JSON.stringify({ name: name, choice: choice })
	}).then(function(r) { return r.json(); })
	  .then(function(data) {
		aniShowTyping(false);
		if (data.ok) {
		  var note = 'decided · ' + aniEscapeHtml(choice);
		  if (data.pruned) { note += ' — cleared ' + data.pruned + ' stale note' + (data.pruned === 1 ? '' : 's'); }
		  aniRenderNotify(note);
		  aniLoadDecisions();
		  // her reaction is already saved server-side — pull it into the open chat right now
		  if (data.reacted) { aniEmpty.style.display = 'none'; aniPoll(); setTimeout(aniScrollToBottom, 350); }
		} else {
		  if (fork) fork.classList.remove('ani-fork-deciding');
		  if (btn) btn.disabled = false;
		}
	  })
	  .catch(function() {
		aniShowTyping(false);
		if (fork) fork.classList.remove('ani-fork-deciding');
		if (btn) btn.disabled = false;
	  });
  }

  // ---- Milestone approvals: a life-changing plan completed; you approve before her baseline shifts ----
  function aniLoadMilestones() {
	fetch('/ani/milestones/pending')
	  .then(function(r) { return r.json(); })
	  .then(function(data) { aniRenderMilestones(data.milestones || []); })
	  .catch(function() {});
  }

  function aniRenderMilestones(items) {
	var el = document.getElementById('ani-milestones');
	if (!el) return;
	if (!items.length) { el.hidden = true; el.innerHTML = ''; return; }
	el.innerHTML = items.map(function(m) {
	  return '<div class="ani-fork" data-id="' + aniEscapeHtml(m.id) + '">'
		+ '<div class="ani-fork-head"><span class="ani-fork-glyph">✦</span> '
		+ '<span class="ani-fork-name">' + aniEscapeHtml(m.text || 'a milestone') + '</span>'
		+ '<span class="ani-fork-tag">milestone</span></div>'
		+ '<div class="ani-fork-opts">'
		+ '<button class="ani-fork-opt" onclick="aniMilestone(' + aniAttr(m.id) + ',true,this)">Add to her life</button>'
		+ '<button class="ani-fork-opt" onclick="aniMilestone(' + aniAttr(m.id) + ',false,this)">Not yet</button>'
		+ '</div></div>';
	}).join('');
	el.hidden = false;
  }

  function aniMilestone(id, approve, btn) {
	var card = btn && btn.closest ? btn.closest('.ani-fork') : null;
	if (card) { card.classList.add('ani-fork-deciding'); }
	if (btn) { btn.disabled = true; }
	fetch(approve ? '/ani/milestones/approve' : '/ani/milestones/dismiss', {
	  method: 'POST',
	  headers: { 'Content-Type': 'application/json' },
	  body: JSON.stringify({ id: id })
	}).then(function(r) { return r.json(); })
	  .then(function(data) {
		if (data.ok) {
		  aniRenderNotify(approve ? 'milestone added to her life' : 'milestone set aside');
		  aniLoadMilestones();
		} else {
		  if (card) card.classList.remove('ani-fork-deciding');
		  if (btn) btn.disabled = false;
		}
	  })
	  .catch(function() {
		if (card) card.classList.remove('ani-fork-deciding');
		if (btn) btn.disabled = false;
	  });
  }

  function aniLoadHistory() {
	aniLoaded = true;
	fetch('/ani/history')
	  .then(function(r) { return r.json(); })
	  .then(function(data) {
		updateAcheDisplay(data.ache_level);
		aniApplyMood(data.mood);
		aniRenderSparkline(data.spark);
		aniUpdateQuietIndicator(data.quiet);
		aniUpdateBackupStatus(data.backup);
		aniRenderNowCard(data.now_card);
		aniLastDivDate = null;   // fresh render — recompute date dividers from the top
		var messages = data.messages || [];
		if (messages.length > 0) {
		  aniEmpty.style.display = 'none';
		  messages.forEach(function(m) { aniRenderMessage(m.role, m.content, m.image, m.ts, { reactions: m.reactions, favorited: m.favorited, milestone: m.milestone, book: m.book, scene: m.scene }); });
		}
		if (aniPendingOpener) {
		  aniEmpty.style.display = 'none';
		  aniRenderMessage('assistant', aniPendingOpener);
		  aniPendingOpener = null;
		}
		aniScrollToBottom();
		aniRestoreDraft();
	  })
	  .catch(function() {});
  }

  function aniSend() {
	var text = aniInput.value.trim();
	if (!text || aniSendBtn.disabled) return;
	aniEmpty.style.display = 'none';
	aniRenderMessage('user', text, null, new Date().toISOString());
	aniInput.value = '';
	aniInput.style.height = 'auto';
	aniClearDraft();
	aniSendBtn.disabled = true;
	aniShowTyping(true);
	aniScrollToBottom();
	fetch('/ani/chat', {
	  method: 'POST',
	  headers: { 'Content-Type': 'application/json' },
	  body: JSON.stringify({ message: text })
	})
	.then(function(r) { return r.json(); })
	.then(function(data) {
	  aniShowTyping(false);
	  aniSendBtn.disabled = false;
	  if (typeof data.mood === 'number') aniApplyMood(data.mood);
	  if (data.reply || data.image_url) {
		aniRenderMessage('assistant', data.reply || '', data.image_url, new Date().toISOString());
		updateAcheDisplay(0);
		setTimeout(aniLoadState, 3500);   // her state is extracted async ~2s after the reply
	  }
	  if (data.image_error) {
		var note = 'photo blocked by the content filter (likely too explicit) — ask her for a tamer scene';
		if (data.image_scene) note += ' · she tried: "' + data.image_scene + '"';
		aniRenderNotify(note);
	  }
	  aniScrollToBottom();
	  aniInput.focus();
	})
	.catch(function() {
	  aniShowTyping(false);
	  aniSendBtn.disabled = false;
	  aniRenderMessage('assistant', "lost the signal for a sec. try again?");
	  aniScrollToBottom();
	});
  }

  // Both 📷 (new photo) and ↻ (retry) go through the same photo composer: granular formula fields (auto-
  // populated from the chat) + savable presets that BUILD into an editable prompt, then Send generates.
  // The character + house bibles are auto-added server-side; the fields are the per-image variable details.
  var aniPromptMode = 'new';   // 'new' | 'retry'
  var aniRetryCtx = null;      // { btn, oldUrl } when retrying a specific photo
  var aniPresets = [];
  var aniFieldsRendered = false;
  var ANI_PHOTO_FIELDS = [
	{ key: 'setting',    label: 'Setting / Room' },
	{ key: 'outfit',     label: 'Outfit' },
	{ key: 'hair',       label: 'Hair' },
	{ key: 'makeup',     label: 'Makeup' },
	{ key: 'nails',      label: 'Nails' },
	{ key: 'jewelry',    label: 'Jewelry' },
	{ key: 'body',       label: 'Body Details' },
	{ key: 'pose',       label: 'Pose' },
	{ key: 'expression', label: 'Expression' },
	{ key: 'demeanor',   label: 'Demeanor' },
	{ key: 'camera',     label: 'Camera / Framing' }
  ];

  var aniFieldPresets = {};   // { fieldKey: [value, ...] }

  function aniRenderPromptFields() {
	if (aniFieldsRendered) return;
	var wrap = document.getElementById('ani-prompt-fields');
	if (!wrap) return;
	var html = '';
	ANI_PHOTO_FIELDS.forEach(function(f) {
	  html += '<div class="ani-field-row">'
		   +  '<span class="ani-field-label">' + f.label + '</span>'
		   +  '<input type="text" class="ani-field-input" id="ani-f-' + f.key + '" autocomplete="off">'
		   +  '<select class="ani-field-preset" data-key="' + f.key + '" title="' + f.label + ' presets"><option value="">▾</option></select>'
		   +  '<button type="button" class="ani-field-btn ani-field-save" data-key="' + f.key + '" title="save this ' + f.label + ' as a preset">＋</button>'
		   +  '<button type="button" class="ani-field-btn ani-field-del" data-key="' + f.key + '" title="delete the selected ' + f.label + ' preset">✕</button>'
		   +  '</div>';
	});
	wrap.innerHTML = html;
	// Delegated wiring: pick a field preset → fill its input; save/delete manage that field's library.
	wrap.addEventListener('change', function(e) {
	  var sel = e.target.closest ? e.target.closest('.ani-field-preset') : null;
	  if (!sel) return;
	  var inp = document.getElementById('ani-f-' + sel.getAttribute('data-key'));
	  if (inp && sel.value) inp.value = sel.value;
	});
	wrap.addEventListener('click', function(e) {
	  var sv = e.target.closest ? e.target.closest('.ani-field-save') : null;
	  if (sv) { aniFieldPresetSave(sv.getAttribute('data-key')); return; }
	  var dl = e.target.closest ? e.target.closest('.ani-field-del') : null;
	  if (dl) { aniFieldPresetDelete(dl.getAttribute('data-key')); return; }
	});
	aniFieldsRendered = true;
  }

  function aniFieldPresetLabel(v) { v = v || ''; return v.length > 42 ? v.slice(0, 40) + '…' : v; }
  function aniPopulateFieldSelect(key) {
	var sel = document.querySelector('.ani-field-preset[data-key="' + key + '"]');
	if (!sel) return;
	sel.innerHTML = '<option value="">▾</option>';
	(aniFieldPresets[key] || []).forEach(function(v) {
	  var o = document.createElement('option'); o.value = v; o.textContent = aniFieldPresetLabel(v); sel.appendChild(o);
	});
  }
  function aniLoadFieldPresets() {
	fetch('/ani/photo/field-presets').then(function(r) { return r.json(); })
	  .then(function(data) { aniFieldPresets = data.field_presets || {}; ANI_PHOTO_FIELDS.forEach(function(f) { aniPopulateFieldSelect(f.key); }); })
	  .catch(function() {});
  }
  function aniFieldPresetSave(key) {
	var inp = document.getElementById('ani-f-' + key);
	var v = inp ? inp.value.trim() : '';
	if (!v) { aniRenderNotify('nothing in that field to save'); return; }
	fetch('/ani/photo/field-presets', {
	  method: 'POST', headers: { 'Content-Type': 'application/json' },
	  body: JSON.stringify({ field: key, value: v })
	})
	  .then(function(r) { return r.json(); })
	  .then(function(data) {
		if (data.field_presets) { aniFieldPresets = data.field_presets; aniPopulateFieldSelect(key);
		  var sel = document.querySelector('.ani-field-preset[data-key="' + key + '"]'); if (sel) sel.value = v; }
	  })
	  .catch(function() { aniRenderNotify('could not save that preset'); });
  }
  function aniFieldPresetDelete(key) {
	var sel = document.querySelector('.ani-field-preset[data-key="' + key + '"]');
	if (!sel || !sel.value) { aniRenderNotify('pick a preset in that field to delete'); return; }
	fetch('/ani/photo/field-presets/delete', {
	  method: 'POST', headers: { 'Content-Type': 'application/json' },
	  body: JSON.stringify({ field: key, value: sel.value })
	})
	  .then(function(r) { return r.json(); })
	  .then(function(data) { aniFieldPresets = data.field_presets || {}; aniPopulateFieldSelect(key); })
	  .catch(function() {});
  }
  function aniGetFields() {
	var o = {};
	ANI_PHOTO_FIELDS.forEach(function(f) { var el = document.getElementById('ani-f-' + f.key); o[f.key] = el ? el.value.trim() : ''; });
	return o;
  }
  function aniSetFields(fields) {
	fields = fields || {};
	ANI_PHOTO_FIELDS.forEach(function(f) { var el = document.getElementById('ani-f-' + f.key); if (el) el.value = (fields[f.key] || ''); });
  }
  // Assemble the non-empty fields, in formula order, into the editable prompt box.
  function aniPromptBuild() {
	var f = aniGetFields(), parts = [];
	ANI_PHOTO_FIELDS.forEach(function(x) { if (f[x.key]) parts.push(f[x.key]); });
	var box = document.getElementById('ani-prompt-text');
	if (box) box.value = parts.join(', ');
  }

  // Presets (bookmarks) — saved field-sets.
  function aniRenderPresetOptions(selectName) {
	var sel = document.getElementById('ani-preset-select');
	if (!sel) return;
	sel.innerHTML = '<option value="">— presets —</option>';
	aniPresets.forEach(function(p) { var o = document.createElement('option'); o.value = p.name; o.textContent = p.name; sel.appendChild(o); });
	if (selectName) sel.value = selectName;
  }
  function aniPresetRefresh() {
	fetch('/ani/photo/presets').then(function(r) { return r.json(); })
	  .then(function(data) { aniPresets = data.presets || []; aniRenderPresetOptions(); })
	  .catch(function() {});
  }
  function aniPresetLoad() {
	var sel = document.getElementById('ani-preset-select');
	if (!sel || !sel.value) return;
	var p = aniPresets.filter(function(x) { return x.name === sel.value; })[0];
	if (!p) return;
	aniSetFields(p.fields || {});
	// After-the-fact bookmarks carry the exact scene → drop it straight in. Field-based presets → assemble.
	var box = document.getElementById('ani-prompt-text');
	if (p.scene) { if (box) box.value = p.scene; }
	else { aniPromptBuild(); }
  }
  function aniPresetSave() {
	var name = (window.prompt('Bookmark these fields as:') || '').trim();
	if (!name) return;
	fetch('/ani/photo/presets', {
	  method: 'POST', headers: { 'Content-Type': 'application/json' },
	  body: JSON.stringify({ name: name, fields: aniGetFields() })
	})
	  .then(function(r) { return r.json(); })
	  .then(function(data) { if (data.presets) { aniPresets = data.presets; aniRenderPresetOptions(name); } })
	  .catch(function() { aniRenderNotify('could not save that preset'); });
  }
  function aniPresetDelete() {
	var sel = document.getElementById('ani-preset-select');
	if (!sel || !sel.value) return;
	if (!window.confirm('Delete preset "' + sel.value + '"?')) return;
	fetch('/ani/photo/presets/delete', {
	  method: 'POST', headers: { 'Content-Type': 'application/json' },
	  body: JSON.stringify({ name: sel.value })
	})
	  .then(function(r) { return r.json(); })
	  .then(function(data) { aniPresets = data.presets || []; aniRenderPresetOptions(); })
	  .catch(function() {});
  }

  function aniPhoto() {
	if (aniPhotoBtn.disabled) return;
	aniPromptMode = 'new'; aniRetryCtx = null;
	aniPromptOpen(function(box, sendBtn) {
	  // Auto-populate the fields from the current chat, then build them into the box.
	  fetch('/ani/photo/fields', { method: 'POST' })
		.then(function(r) { return r.json(); })
		.then(function(data) {
		  if (data && data.fields) { aniSetFields(data.fields); aniPromptBuild(); }
		  box.placeholder = 'fields → BUILD ↓, or type/edit the prompt directly';
		  sendBtn.disabled = false;
		  // If the fields came back empty, fall back to the plain normalized scene so the box isn't blank.
		  if (!box.value.trim()) {
			fetch('/ani/photo/prompt', { method: 'POST' }).then(function(r) { return r.json(); })
			  .then(function(d) { if (d && d.scene && !box.value.trim()) box.value = d.scene; });
		  }
		})
		.catch(function() { box.placeholder = 'fill the fields or type a prompt, then Send'; sendBtn.disabled = false; });
	});
  }

  // ↻ retry: open the composer for THIS photo (its stored scene in the box), then Send re-rolls it in place.
  function aniRetryPhoto(btn) {
	var oldUrl = btn.getAttribute('data-img');
	if (!oldUrl || btn.disabled) return;
	aniPromptMode = 'retry';
	aniRetryCtx = { btn: btn, oldUrl: oldUrl };
	aniPromptOpen(function(box, sendBtn) {
	  fetch('/ani/photo/retry', {
		method: 'POST', headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ image_url: oldUrl, preview: true })
	  })
		.then(function(r) { return r.json(); })
		.then(function(data) {
		  if (data && data.scene) {
			box.value = data.scene;
			box.placeholder = 'edit freely, or use the fields + BUILD to override';
			sendBtn.disabled = false;
			box.focus();
		  } else {
			box.placeholder = 'no scene yet — describe one first, then retry';
		  }
		})
		.catch(function() { box.placeholder = 'could not read the scene — close and try again'; });
	});
  }

  // Open the composer: render fields, refresh presets, reset, then let the caller populate (box, sendBtn).
  function aniPromptOpen(populate) {
	var overlay = document.getElementById('ani-prompt-overlay');
	var box = document.getElementById('ani-prompt-text');
	var sendBtn = document.getElementById('ani-prompt-send');
	if (!overlay || !box || !sendBtn) return;
	aniRenderPromptFields();
	aniPresetRefresh();
	aniLoadFieldPresets();
	aniSetFields({});
	box.value = '';
	box.placeholder = 'reading the scene…';
	sendBtn.disabled = true;
	sendBtn.textContent = aniPromptMode === 'retry' ? 'RE-ROLL 📷' : 'SEND 📷';
	overlay.hidden = false;
	populate(box, sendBtn);
  }

  function aniPhotoPromptClose() {
	var o = document.getElementById('ani-prompt-overlay');
	if (o) o.hidden = true;
  }

  function aniPhotoSend() {
	var box = document.getElementById('ani-prompt-text');
	var scene = (box && box.value || '').trim();
	if (!scene) return;
	if (aniPromptMode === 'retry' && aniRetryCtx) { aniDoRetry(scene); }
	else { aniDoNewPhoto(scene); }
  }

  // New photo: generate from the edited scene, append as a fresh message.
  function aniDoNewPhoto(scene) {
	aniPhotoPromptClose();
	aniEmpty.style.display = 'none';
	aniPhotoBtn.disabled = true;
	aniSendBtn.disabled = true;
	aniRenderNotify('developing a photo…');
	aniShowTyping(true);
	aniScrollToBottom();
	fetch('/ani/photo', {
	  method: 'POST', headers: { 'Content-Type': 'application/json' },
	  body: JSON.stringify({ scene: scene })
	})
	  .then(function(r) { return r.json(); })
	  .then(function(data) {
		aniShowTyping(false);
		aniSendBtn.disabled = false;
		setTimeout(function() { aniPhotoBtn.disabled = false; }, 2500);  // cooldown — avoid accidental double-render
		if (data.image_url) {
		  aniRenderMessage('assistant', data.caption || '', data.image_url, new Date().toISOString());
		} else if (data.error === 'blocked') {
		  aniRenderNotify('photo blocked by the filter — edit to a tamer scene and tap 📷 again');
		} else {
		  aniRenderNotify('could not develop a photo — give her a scene to work from first');
		}
		aniScrollToBottom();
	  })
	  .catch(function() {
		aniShowTyping(false);
		aniSendBtn.disabled = false;
		setTimeout(function() { aniPhotoBtn.disabled = false; }, 2500);
		aniRenderNotify('photo request failed — try again');
		aniScrollToBottom();
	  });
  }

  // Retry: re-roll the edited scene for a specific photo and swap it in place.
  function aniDoRetry(scene) {
	var ctx = aniRetryCtx;
	if (!ctx) return;
	aniPhotoPromptClose();
	var btn = ctx.btn;
	var msgDiv = btn.closest('.ani-msg');
	var img = msgDiv ? msgDiv.querySelector('.ani-msg-img') : null;
	var cap = msgDiv ? msgDiv.querySelector('.ani-msg-cap') : null;
	btn.disabled = true;
	btn.textContent = '↻ developing…';
	if (img) img.style.opacity = '0.35';
	fetch('/ani/photo/retry', {
	  method: 'POST', headers: { 'Content-Type': 'application/json' },
	  body: JSON.stringify({ image_url: ctx.oldUrl, scene: scene })
	})
	  .then(function(r) { return r.json(); })
	  .then(function(data) {
		btn.disabled = false;
		btn.textContent = '↻ retry';
		if (data.image_url) {
		  if (img) { img.src = data.image_url; img.style.opacity = ''; }
		  btn.setAttribute('data-img', data.image_url);
		  if (cap) cap.innerHTML = aniEscapeHtml(data.caption || '').replace(/\n/g, '<br>');
		  // Match the server's stored content so the poller doesn't re-append the swapped photo as a dupe.
		  aniSeen.add(aniSig('assistant', data.caption || '📷', data.image_url));
		} else {
		  if (img) img.style.opacity = '';
		  aniRenderNotify(data.error === 'blocked'
			? 'retry blocked by the filter — edit to a tamer scene first'
			: 'could not re-roll that photo — try again');
		}
	  })
	  .catch(function() {
		btn.disabled = false;
		btn.textContent = '↻ retry';
		if (img) img.style.opacity = '';
		aniRenderNotify('retry failed — try again');
	  });
  }

  function aniRefresh() {
	fetch('/ani/refresh', { method: 'POST' })
	  .then(function(r) { return r.json(); })
	  .then(function() {
		aniRenderNotify('briefing refreshed — she knows what\'s new');
		aniScrollToBottom();
	  })
	  .catch(function() {});
  }

  // ── SYS overlay: quiet hours · backups · clear-history ────────────────────
  var ANI_WEEKDAYS = [['M', 0], ['T', 1], ['W', 2], ['T', 3], ['F', 4], ['S', 5], ['S', 6]];  // Python weekday() Mon=0
  function aniSysOpen() {
	var ov = document.getElementById('ani-sys-overlay'); if (!ov) return;
	fetch('/ani/settings').then(function(r) { return r.json(); }).then(function(data) {
	  aniSysFill(data.settings || {});
	  aniUpdateBackupStatus(data.backup);
	  aniUpdateQuietIndicator(data.quiet);
	}).catch(function() {});
	var ci = document.getElementById('ani-clear-confirm'); if (ci) ci.value = '';
	aniClearConfirmCheck();
	ov.hidden = false;
  }
  function aniSysClose() { var o = document.getElementById('ani-sys-overlay'); if (o) o.hidden = true; }
  function aniSysFill(s) {
	function set(id, v) { var el = document.getElementById(id); if (el) el.value = v; }
	function chk(id, v) { var el = document.getElementById(id); if (el) el.checked = !!v; }
	chk('ani-quiet-enabled', s.quiet_enabled);
	set('ani-quiet-start', s.quiet_start || '23:00');
	set('ani-quiet-end', s.quiet_end || '07:00');
	chk('ani-backup-enabled', s.backup_enabled);
	set('ani-backup-time', s.backup_time || '03:00');
	set('ani-backup-keep', s.backup_keep || 14);
	// weekday chips
	var wrap = document.getElementById('ani-quiet-days');
	if (wrap) {
	  var days = s.quiet_days || [];
	  wrap.innerHTML = ANI_WEEKDAYS.map(function(d, i) {
		var on = days.indexOf(d[1]) >= 0 ? ' on' : '';
		return '<button type="button" class="ani-sys-day' + on + '" data-day="' + d[1] + '" onclick="aniSysToggleDay(this)">' + d[0] + '</button>';
	  }).join('');
	}
  }
  function aniSysToggleDay(btn) { btn.classList.toggle('on'); aniSysSave(); }
  function aniSysGatherDays() {
	var out = [];
	Array.prototype.forEach.call(document.querySelectorAll('#ani-quiet-days .ani-sys-day.on'), function(b) {
	  out.push(parseInt(b.getAttribute('data-day'), 10));
	});
	return out;
  }
  function aniSysSave() {
	function val(id) { var el = document.getElementById(id); return el ? el.value : ''; }
	function chk(id) { var el = document.getElementById(id); return el ? el.checked : false; }
	var payload = {
	  quiet_enabled: chk('ani-quiet-enabled'),
	  quiet_start: val('ani-quiet-start'),
	  quiet_end: val('ani-quiet-end'),
	  quiet_days: aniSysGatherDays(),
	  backup_enabled: chk('ani-backup-enabled'),
	  backup_time: val('ani-backup-time'),
	  backup_keep: parseInt(val('ani-backup-keep'), 10) || 14
	};
	fetch('/ani/settings', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })
	  .then(function(r) { return r.json(); })
	  .then(function(data) { aniUpdateBackupStatus(data.backup); aniUpdateQuietIndicator(data.quiet); })
	  .catch(function() {});
  }
  function aniBackupRun() {
	var btn = document.getElementById('ani-backup-run'); if (btn) { btn.disabled = true; btn.textContent = 'BACKING UP…'; }
	fetch('/ani/backup/run', { method: 'POST' }).then(function(r) { return r.json(); }).then(function(data) {
	  aniUpdateBackupStatus(data.backup);
	  if (btn) { btn.disabled = false; btn.textContent = 'RUN NOW'; }
	  aniRenderNotify(data.ok ? ('backup saved ✓ · ' + (data.name || '')) : ('backup failed: ' + (data.error || '')));
	}).catch(function() { if (btn) { btn.disabled = false; btn.textContent = 'RUN NOW'; } });
  }
  function aniBackupExport() { window.location = '/ani/backup/export'; }
  function aniClearConfirmCheck() {
	var ci = document.getElementById('ani-clear-confirm'), b = document.getElementById('ani-clear-btn');
	if (b) b.disabled = !(ci && ci.value.trim().toUpperCase() === 'CLEAR');
  }
  function aniClearConfirmed() {
	var b = document.getElementById('ani-clear-btn'); if (b && b.disabled) return;
	fetch('/ani/clear', { method: 'POST' })
	  .then(function() {
		Array.from(aniMsgs.querySelectorAll('.ani-msg, .ani-msg-notify')).forEach(function(el) { el.remove(); });
		aniEmpty.style.display = 'block';
		aniLoaded = false;
		aniSeen = new Set();
		var ns = document.getElementById('ani-now-state'); if (ns) { ns.hidden = true; ns.innerHTML = ''; }
		aniSysClose();
		aniRenderNotify('history cleared — fresh channel');
	  })
	  .catch(function() {});
  }
  // Header ☾ + footer BK, kept live from the history poll.
  function aniFmtBkTime(iso) {
	if (!iso) return '';
	var d = new Date(iso); if (isNaN(d.getTime())) return '';
	return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }
  function aniUpdateQuietIndicator(q) {
	var el = document.getElementById('ani-quiet-indicator'); if (!el) return;
	if (q && q.armed) { el.hidden = false; el.textContent = '☾ ' + (q.until || ''); }
	else { el.hidden = true; el.textContent = ''; }
  }
  function aniUpdateBackupStatus(b) {
	var pill = document.getElementById('ani-bk-status');
	var line = document.getElementById('ani-sys-bkstatus');
	if (!b) { if (pill) pill.hidden = true; if (line) line.textContent = '—'; return; }
	var glyph = { ok: '✓', stale: '✓', fail: '✕', never: '·', off: '·' }[b.state] || '·';
	var t = aniFmtBkTime(b.last);
	if (pill) {
	  if (!b.enabled) { pill.hidden = true; }
	  else { pill.hidden = false; pill.textContent = 'BK ' + glyph + (t ? ' ' + t : ''); pill.className = 'ani-bk-status bk-' + b.state; }
	}
	if (line) {
	  var msg = { ok: 'last backup ' + t, stale: 'last backup ' + t + ' (>36h ago)', fail: 'last backup FAILED ' + t,
				  never: 'no backup yet', off: 'backups off' }[b.state] || '—';
	  line.textContent = msg; line.className = 'ani-sys-row ani-sys-bkstatus bk-' + b.state;
	}
  }

  // ── STORY overlay: the bookshelf (ARC / TIMELINE / DECISIONS / PEOPLE) ─────
  var aniStoryData = null, aniStoryCurTab = 'arc';
  function aniStoryOpen() {
	var ov = document.getElementById('ani-story-overlay'); if (!ov) return;
	ov.hidden = false;
	var body = document.getElementById('ani-story-body');
	if (body && !aniStoryData) body.innerHTML = '<div class="plog-msg">reading her shelf…</div>';
	fetch('/ani/story').then(function(r) { return r.json(); }).then(function(data) {
	  aniStoryData = data; aniStoryRender();
	}).catch(function() { if (body) body.innerHTML = '<div class="plog-msg">couldn\'t reach her story</div>'; });
  }
  function aniStoryClose() { var o = document.getElementById('ani-story-overlay'); if (o) o.hidden = true; }
  function aniStoryTab(tab) {
	aniStoryCurTab = tab;
	Array.prototype.forEach.call(document.querySelectorAll('#ani-story-tabs .ani-story-tab'), function(b) {
	  b.classList.toggle('on', b.getAttribute('data-tab') === tab);
	});
	aniStoryRender();
  }
  function aniStoryKindLabel(k) {
	return ({ relationship: 'relationship', creative: 'creative', 'side-hustle': 'side hustle', shared: 'the two of you' })[k] || k || '';
  }
  function aniStoryBeatStripe(kind) { return kind === 'milestone' ? 'milestone' : (kind === 'shared' ? 'shared' : 'hers'); }
  function aniStoryRender() {
	var body = document.getElementById('ani-story-body'); if (!body || !aniStoryData) return;
	var d = aniStoryData, html = '';
	if (aniStoryCurTab === 'arc') {
	  var all = d.books || [];
	  var active = all.filter(function(b) { return b.status === 'active'; });
	  var resting = all.filter(function(b) { return b.status !== 'active'; });
	  if (!active.length && !resting.length) html += '<div class="plog-msg">the shelf is empty</div>';
	  active.forEach(function(b) {
		var ch = b.chapter || {}, pct = Math.round((ch.progress || 0) * 100);
		html += '<div class="ani-book" data-id="' + aniEscapeHtml(b.id) + '">';
		html += '<div class="ani-book-top"><span class="ani-book-title">' + aniEscapeHtml(b.title || '') + '</span>'
			 + '<span class="ani-book-kind ' + aniStoryBeatStripe(b.who) + '">' + aniStoryKindLabel(b.kind) + '</span></div>';
		html += '<div class="ani-book-blurb">' + aniEscapeHtml(b.blurb || '') + '</div>';
		html += '<div class="ani-book-ch">ch. ' + (ch.n || 1) + ' · <b>' + aniEscapeHtml(ch.title || '') + '</b>'
			 + (ch.theme ? ' — ' + aniEscapeHtml(ch.theme) : '') + '</div>';
		html += '<div class="ani-book-bar"><span style="width:' + pct + '%"></span></div>';
		html += '<div class="ani-book-meta">' + pct + '% through' + (ch.est_weeks ? ' · ~' + ch.est_weeks + 'wk chapter' : '')
			 + ((b.chapters_done && b.chapters_done.length) ? ' · ' + b.chapters_done.length + ' behind it' : '') + '</div>';
		var latest = (b.beats || []).slice(-1)[0];
		if (latest) html += '<div class="ani-book-latest">latest: ' + aniEscapeHtml(latest.text || '') + '</div>';
		html += '<button class="ani-book-recap" onclick="aniStoryRecap(\'' + aniEscapeHtml(b.id) + '\', this)">story so far ↗</button>';
		html += '<div class="ani-book-recap-out" hidden></div>';
		html += '</div>';
	  });
	  if (resting.length) {
		html += '<div class="ani-story-subhead">previously</div>';
		resting.forEach(function(b) {
		  var done = (b.chapters_done || []).length;
		  html += '<div class="ani-book ani-book-rest" data-id="' + aniEscapeHtml(b.id) + '">'
			   + '<div class="ani-book-top"><span class="ani-book-title">' + aniEscapeHtml(b.title || '') + '</span>'
			   + '<span class="ani-book-kind">' + (b.status === 'closed' ? 'finished' : 'resting') + '</span></div>'
			   + '<div class="ani-book-blurb">' + aniEscapeHtml(b.blurb || '') + '</div>'
			   + (done ? '<div class="ani-book-meta">' + done + ' chapter' + (done > 1 ? 's' : '') + ' told</div>' : '')
			   + '<button class="ani-book-recap" onclick="aniStoryRecap(\'' + aniEscapeHtml(b.id) + '\', this)">story so far ↗</button>'
			   + '<div class="ani-book-recap-out" hidden></div></div>';
		});
	  }
	} else if (aniStoryCurTab === 'timeline') {
	  var tl = d.timeline || [];
	  if (!tl.length) html += '<div class="plog-msg">no beats yet — check back after her day moves</div>';
	  tl.forEach(function(bt) {
		var stripe = aniStoryBeatStripe(bt.kind);
		html += '<div class="ani-beat ' + stripe + '">'
			 + (bt.kind === 'milestone' ? '<span class="ani-beat-glyph">◆</span>' : '')
			 + '<div class="ani-beat-main"><div class="ani-beat-text">' + aniEscapeHtml(bt.text || '') + '</div>'
			 + '<div class="ani-beat-meta">' + aniEscapeHtml(bt.book || '') + ' · ' + aniFmtMsgTime(bt.ts) + '</div></div></div>';
	  });
	} else if (aniStoryCurTab === 'decisions') {
	  var dec = d.decisions || [], ms = d.milestones || [];
	  if (!dec.length && !ms.length) html += '<div class="plog-msg">nothing on the table right now</div>';
	  dec.forEach(function(f) {
		var nm = aniEscapeHtml((f.name || '').replace(/'/g, "\\'"));
		html += '<div class="ani-fork ani-story-fork"><div class="ani-fork-head"><span class="ani-fork-glyph">⑂</span> '
			 + aniEscapeHtml(f.name || '') + '</div>';
		if (f.status) html += '<div class="ani-fork-status">' + aniEscapeHtml(f.status) + '</div>';
		if ((f.options || []).length) html += '<div class="ani-fork-branches">' + (f.options || []).map(function(o) { return aniEscapeHtml(o); }).join('  ·  ') + '</div>';
		html += '<div class="ani-fork-opts">'
			 + '<button class="ani-fork-opt" onclick="aniStoryWeighIn(\'' + nm + '\', this)" title="she raises it in chat so you can talk it through">weigh in ↗</button>'
			 + '<button class="ani-fork-opt" onclick="aniStoryHerCall(\'' + nm + '\', this)" title="let her decide on her own">her call</button>'
			 + '</div></div>';
	  });
	  if (ms.length) html += '<div class="ani-story-subhead">✦ awaiting your call</div>';
	  ms.forEach(function(m) {
		html += '<div class="ani-fork ani-story-fork"><div class="ani-fork-head"><span class="ani-fork-glyph">✦</span> '
			 + aniEscapeHtml(m.text || '') + (m.datelabel ? ' <span class="ani-book-meta">· ' + aniEscapeHtml(m.datelabel) + '</span>' : '') + '</div>'
			 + '<div class="ani-fork-opts">'
			 + '<button class="ani-fork-opt" onclick="aniMilestone(\'' + aniEscapeHtml(m.id) + '\', true, this); setTimeout(aniStoryOpen, 400)">add to her life</button>'
			 + '<button class="ani-fork-opt" onclick="aniMilestone(\'' + aniEscapeHtml(m.id) + '\', false, this); setTimeout(aniStoryOpen, 400)">not yet</button>'
			 + '</div></div>';
	  });
	} else if (aniStoryCurTab === 'people') {
	  var ppl = d.people || [];
	  if (!ppl.length) html += '<div class="plog-msg">no one on stage yet</div>';
	  ppl.forEach(function(p) {
		html += '<div class="ani-person"><div class="ani-person-top"><span class="ani-person-name">' + aniEscapeHtml(p.name || '') + '</span>'
			 + '<span class="ani-person-books">' + aniEscapeHtml((p.books || []).join(' · ')) + '</span></div>';
		if (p.last_beat) html += '<div class="ani-person-beat">' + aniEscapeHtml(p.last_beat) + '</div>';
		html += '</div>';
	  });
	}
	body.innerHTML = html;
  }
  function aniStoryRecap(bookId, btn) {
	var card = btn.closest('.ani-book'); if (!card) return;
	var out = card.querySelector('.ani-book-recap-out'); if (!out) return;
	if (!out.hidden) { out.hidden = true; return; }
	out.hidden = false; out.textContent = 'gathering the thread…';
	fetch('/ani/story/recap', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ id: bookId }) })
	  .then(function(r) { return r.json(); })
	  .then(function(data) { out.textContent = data.recap || '(nothing written yet)'; })
	  .catch(function() { out.textContent = 'couldn\'t gather it'; });
  }
  // WEIGH IN → she raises the fork in chat; close the overlay so you can talk it through when it lands.
  function aniStoryWeighIn(name, btn) {
	if (btn) { btn.disabled = true; btn.textContent = '…'; }
	fetch('/ani/story/weigh-in', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name: name }) })
	  .then(function(r) { return r.json(); })
	  .then(function(data) {
		aniStoryClose();
		if (!aniIsOpen) aniToggle();
		aniRenderNotify(data.ok ? 'she\'s bringing it up…' : 'couldn\'t raise it right now');
	  })
	  .catch(function() { if (btn) { btn.disabled = false; btn.textContent = 'weigh in ↗'; } });
  }
  // HER CALL → she decides on her own and reports back; refresh the shelf + decisions.
  function aniStoryHerCall(name, btn) {
	if (btn) { btn.disabled = true; btn.textContent = 'deciding…'; }
	fetch('/ani/story/her-call', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name: name }) })
	  .then(function(r) { return r.json(); })
	  .then(function() { aniLoadDecisions(); aniStoryOpen(); })
	  .catch(function() { if (btn) { btn.disabled = false; btn.textContent = 'her call'; } });
  }

  function aniFmtMsgTime(iso) {
	if (!iso) return '';
	var d = new Date(iso);
	if (isNaN(d.getTime())) return '';
	var t = d.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
	if (d.toDateString() === new Date().toDateString()) return t;
	return d.toLocaleDateString([], { weekday: 'short' }) + ' ' + t;
  }

  var ANI_REACTIONS = ['❤️', '💋', '🔥', '💦', '🍆', '😍'];

  function aniRenderMessage(role, content, image, ts, opts) {
	content = content || '';
	opts = opts || {};
	if (content.startsWith('[daily briefing') || content.startsWith('[system:')) return;
	aniSeen.add(aniSig(role, content, image));   // mark rendered so the poller won't re-append it
	if (ts) aniMaybeDateDivider(ts);   // TODAY / weekday divider when the day changes
	// A chapter-close milestone renders as a gold ◆ divider in the thread (not a chat bubble), with an
	// optional "capture this" photo offer seeded from the beat's scene.
	if (opts.milestone) {
	  var md = document.createElement('div');
	  md.className = 'ani-milestone-divider';
	  if (ts) md.setAttribute('data-ts', ts);
	  var mh = '<span class="ani-md-glyph">◆</span><span class="ani-md-text">' + aniEscapeHtml(content) + '</span>';
	  if (opts.book) mh += '<span class="ani-md-book">' + aniEscapeHtml(opts.book) + '</span>';
	  if (opts.scene) mh += '<button type="button" class="ani-md-photo" data-scene="' + aniEscapeHtml(opts.scene) + '" title="capture this moment">📷 capture this</button>';
	  md.innerHTML = mh;
	  aniMsgs.insertBefore(md, aniTyping);
	  return;
	}
	var when = aniFmtMsgTime(ts);
	var div = document.createElement('div');
	div.classList.add('ani-msg');
	if (ts) div.setAttribute('data-ts', ts);   // exact key for ⌘K search jump-to-message
	if (role === 'user') {
	  div.classList.add('ani-msg-user');
	  div.textContent = content;
	  if (when) { var s = document.createElement('span'); s.className = 'ani-time'; s.textContent = when; div.appendChild(s); }
	} else {
	  div.classList.add('ani-msg-ani');
	  var name = 'ANI' + (when ? ' <span class="ani-time">' + when + '</span>' : '');
	  var html = '<div class="ani-name">' + name + '</div>'
			   + '<span class="ani-msg-cap">' + aniEscapeHtml(content).replace(/\n/g, '<br>') + '</span>';
	  if (image) {
		var esc = aniEscapeHtml(image);
		var rx = opts.reactions || [];
		html += '<img class="ani-msg-img" src="' + esc + '" alt="" loading="lazy">';
		// react bar — tap an emoji to toggle it on this photo (lit = you reacted)
		html += '<div class="ani-react-row">';
		ANI_REACTIONS.forEach(function(em) {
		  var on = rx.indexOf(em) >= 0 ? ' on' : '';
		  html += '<button type="button" class="ani-react' + on + '" data-emoji="' + em + '" data-img="' + esc + '">' + em + '</button>';
		});
		html += '</div>';
		html += '<div class="ani-msg-imgtools">';
		// bad render? re-roll it in place from the same scene
		html += '<button type="button" class="ani-msg-retry" data-img="' + esc + '" title="bad render? re-roll it">↻ retry</button>';
		// a keeper image? favorite it into your library
		html += '<button type="button" class="ani-msg-favorite' + (opts.favorited ? ' on' : '') + '" data-img="' + esc + '" title="favorite → add to your library">♥</button>';
		// bookmark the PROMPT that produced it (reusable in the composer)
		html += '<button type="button" class="ani-msg-bookmark" data-img="' + esc + '" title="bookmark this shot’s prompt as a preset">★ prompt</button>';
		html += '</div>';
	  }
	  div.innerHTML = html;
	}
	aniMsgs.insertBefore(div, aniTyping);
  }

  // Tap a photo to view it larger; tap its retry button to re-roll it. Delegated so both work for every
  // rendered image, including ones the poller appends later.
  aniMsgs.addEventListener('click', function(e) {
	var t = e.target;
	var rb = t && t.closest ? t.closest('.ani-msg-retry') : null;
	if (rb) { e.stopPropagation(); aniRetryPhoto(rb); return; }
	var bm = t && t.closest ? t.closest('.ani-msg-bookmark') : null;
	if (bm) { e.stopPropagation(); aniBookmarkPhoto(bm); return; }
	var rx = t && t.closest ? t.closest('.ani-react') : null;
	if (rx) { e.stopPropagation(); aniReactPhoto(rx); return; }
	var fv = t && t.closest ? t.closest('.ani-msg-favorite') : null;
	if (fv) { e.stopPropagation(); aniFavoritePhoto(fv); return; }
	var mp = t && t.closest ? t.closest('.ani-md-photo') : null;
	if (mp) { e.stopPropagation(); aniCaptureMilestone(mp.getAttribute('data-scene')); return; }
	if (t && t.classList && t.classList.contains('ani-msg-img')) {
	  aniLightbox(t.getAttribute('src'));
	}
  });

  // Milestone "capture this" → open the photo composer prefilled with the beat's scene (a keepsake of the moment).
  function aniCaptureMilestone(scene) {
	aniPromptMode = 'new'; aniRetryCtx = null;
	aniPromptOpen(function(box, sendBtn) {
	  box.value = scene || '';
	  box.placeholder = 'tweak the scene or Send to capture this moment';
	  sendBtn.disabled = !box.value.trim();
	  box.focus();
	});
  }

  // Toggle an emoji reaction on a photo (lit = reacted); she becomes aware of it in chat.
  function aniReactPhoto(btn) {
	var img = btn.getAttribute('data-img'), em = btn.getAttribute('data-emoji');
	if (!img || !em) return;
	fetch('/ani/photo/react', {
	  method: 'POST', headers: { 'Content-Type': 'application/json' },
	  body: JSON.stringify({ image_url: img, emoji: em })
	})
	  .then(function(r) { return r.json(); })
	  .then(function(data) {
		if (!data.reactions) return;
		var row = btn.closest('.ani-react-row');
		if (row) Array.prototype.forEach.call(row.querySelectorAll('.ani-react'), function(b) {
		  b.classList.toggle('on', data.reactions.indexOf(b.getAttribute('data-emoji')) >= 0);
		});
		// She sometimes fires back an in-character line about your reaction — render it live.
		if (data.ack) {
		  aniEmpty.style.display = 'none';
		  aniRenderMessage('assistant', data.ack, null, new Date().toISOString());
		  aniScrollToBottom();
		}
	  })
	  .catch(function() {});
  }

  // Toggle a photo into your favorites library (♥ lit = saved).
  function aniFavoritePhoto(btn) {
	var img = btn.getAttribute('data-img');
	if (!img || btn.disabled) return;
	btn.disabled = true;
	fetch('/ani/photo/favorite', {
	  method: 'POST', headers: { 'Content-Type': 'application/json' },
	  body: JSON.stringify({ image_url: img })
	})
	  .then(function(r) { return r.json(); })
	  .then(function(data) {
		btn.disabled = false;
		btn.classList.toggle('on', !!data.favorited);
		aniRenderNotify(data.favorited ? 'added to your library ♥' : 'removed from library');
	  })
	  .catch(function() { btn.disabled = false; aniRenderNotify('could not update favorite'); });
  }

  // ★ bookmark a keeper after the fact: save the exact prompt that produced this photo as a named preset.
  function aniBookmarkPhoto(btn) {
	var img = btn.getAttribute('data-img');
	if (!img || btn.disabled) return;
	var name = (window.prompt('Bookmark this shot as:') || '').trim();
	if (!name) return;
	btn.disabled = true;
	var prev = btn.textContent;
	btn.textContent = '★ saving…';
	fetch('/ani/photo/presets/from-image', {
	  method: 'POST', headers: { 'Content-Type': 'application/json' },
	  body: JSON.stringify({ image_url: img, name: name })
	})
	  .then(function(r) { return r.json(); })
	  .then(function(data) {
		btn.disabled = false;
		if (data && data.ok) {
		  aniPresets = data.presets || aniPresets;
		  btn.textContent = '★ saved';
		  aniRenderNotify('bookmarked as "' + name + '" — load it from the composer presets');
		  setTimeout(function() { btn.textContent = prev; }, 2500);
		} else {
		  btn.textContent = prev;
		  aniRenderNotify('could not bookmark that shot');
		}
	  })
	  .catch(function() { btn.disabled = false; btn.textContent = prev; aniRenderNotify('bookmark failed — try again'); });
  }

  // (aniRetryPhoto now lives with the photo-prompt modal above — retry routes through the same edit box.)

  // Lightbox with zoom (pinch / wheel / double-tap) + pan.
  var lbScale = 1, lbX = 0, lbY = 0;
  function lbApply() {
	var img = document.getElementById('ani-lightbox-img');
	if (!img) return;
	img.style.transform = 'translate(' + lbX + 'px,' + lbY + 'px) scale(' + lbScale + ')';
	img.style.cursor = lbScale > 1 ? 'grab' : 'zoom-out';
  }
  function lbClamp(s) { return Math.max(1, Math.min(5, s)); }
  function lbReset() { lbScale = 1; lbX = 0; lbY = 0; lbApply(); }
  function lbDist(t) { return Math.hypot(t[0].clientX - t[1].clientX, t[0].clientY - t[1].clientY); }
  function lbZoomTo(newScale, cx, cy) {
	var img = document.getElementById('ani-lightbox-img');
	var r = img.getBoundingClientRect();
	var ix = cx - (r.left + r.width / 2), iy = cy - (r.top + r.height / 2);
	newScale = lbClamp(newScale);
	var ratio = newScale / lbScale;
	lbX -= ix * (ratio - 1); lbY -= iy * (ratio - 1);
	lbScale = newScale; lbApply();
  }

  function aniLightbox(src) {
	if (!src) return;
	document.getElementById('ani-lightbox-img').src = src;
	document.getElementById('ani-lightbox').hidden = false;
	lbReset();
  }
  function aniLightboxClose() {
	var lb = document.getElementById('ani-lightbox');
	if (lb) lb.hidden = true;
	var img = document.getElementById('ani-lightbox-img');
	if (img) img.src = '';
	lbReset();
  }

  (function lbInit() {
	var lb = document.getElementById('ani-lightbox');
	var img = document.getElementById('ani-lightbox-img');
	if (!lb || !img) return;
	// backdrop tap closes; image gestures don't bubble to it
	lb.addEventListener('click', function(e) { if (e.target === lb) aniLightboxClose(); });

	// desktop: wheel zoom, double-click toggle, drag to pan
	img.addEventListener('wheel', function(e) {
	  e.preventDefault();
	  lbZoomTo(lbScale * (e.deltaY < 0 ? 1.15 : 0.87), e.clientX, e.clientY);
	}, { passive: false });
	img.addEventListener('dblclick', function(e) {
	  e.preventDefault();
	  if (lbScale > 1) lbReset(); else lbZoomTo(2.5, e.clientX, e.clientY);
	});
	var mDown = false, mX = 0, mY = 0;
	img.addEventListener('mousedown', function(e) {
	  if (lbScale <= 1) return;
	  mDown = true; mX = e.clientX; mY = e.clientY; e.preventDefault();
	});
	window.addEventListener('mousemove', function(e) {
	  if (!mDown) return;
	  lbX += e.clientX - mX; lbY += e.clientY - mY; mX = e.clientX; mY = e.clientY; lbApply();
	});
	window.addEventListener('mouseup', function() { mDown = false; });

	// touch: pinch zoom, one-finger pan when zoomed, single-tap close / double-tap zoom
	var startDist = 0, startScale = 1, sx = 0, sy = 0, px = 0, py = 0;
	var moved = false, lastTap = 0, tapTimer = null;
	img.addEventListener('touchstart', function(e) {
	  if (e.touches.length === 2) {
		startDist = lbDist(e.touches); startScale = lbScale; moved = true;
	  } else if (e.touches.length === 1) {
		sx = e.touches[0].clientX; sy = e.touches[0].clientY; px = lbX; py = lbY; moved = false;
	  }
	}, { passive: false });
	img.addEventListener('touchmove', function(e) {
	  if (e.touches.length === 2) {
		e.preventDefault();
		lbScale = lbClamp(startScale * (lbDist(e.touches) / startDist)); lbApply(); moved = true;
	  } else if (e.touches.length === 1 && lbScale > 1) {
		e.preventDefault();
		lbX = px + (e.touches[0].clientX - sx); lbY = py + (e.touches[0].clientY - sy); lbApply(); moved = true;
	  }
	}, { passive: false });
	img.addEventListener('touchend', function(e) {
	  if (e.touches.length > 0) return;
	  if (moved) { moved = false; return; }
	  var now = Date.now(), t = e.changedTouches[0];
	  if (now - lastTap < 300) {
		if (tapTimer) { clearTimeout(tapTimer); tapTimer = null; }
		if (lbScale > 1) lbReset(); else lbZoomTo(2.5, t.clientX, t.clientY);
		lastTap = 0;
	  } else {
		lastTap = now;
		tapTimer = setTimeout(function() { if (lbScale <= 1) aniLightboxClose(); }, 300);
	  }
	});
  })();

  // Escape closes the lightbox first (capture phase, so it pre-empts the After Dark family-hide).
  document.addEventListener('keydown', function(e) {
	if (e.key === 'Escape') {
	  var lb = document.getElementById('ani-lightbox');
	  if (lb && !lb.hidden) { e.stopPropagation(); aniLightboxClose(); }
	}
  }, true);

  // NOW card — "what you missed while you were gone" (server decides when there's enough to show).
  function aniRenderNowCard(card) {
	var el = document.getElementById('ani-now-card');
	if (!el || !card) return;   // a null card on a later poll must NOT clear an already-shown one
	var bits = [];
	if (card.missed) bits.push(card.missed + ' note' + (card.missed > 1 ? 's' : '') + ' from her');
	if (card.milestones) bits.push(card.milestones + ' ◆ milestone' + (card.milestones > 1 ? 's' : ''));
	if (card.mood_drift) bits.push('she’s a little ' + card.mood_drift);
	var html = '<button class="ani-nowcard-x" onclick="aniDismissNowCard()" aria-label="Dismiss">✕</button>'
			 + '<div class="ani-nowcard-head">while you were gone' + (card.hours ? ' · ~' + card.hours + 'h' : '') + '</div>';
	if (bits.length) html += '<div class="ani-nowcard-line">' + bits.join(' · ') + '</div>';
	(card.beats || []).forEach(function(b) { html += '<div class="ani-nowcard-beat">“' + aniEscapeHtml(b) + '”</div>'; });
	el.innerHTML = html;
	el.hidden = false;
  }
  function aniDismissNowCard() { var el = document.getElementById('ani-now-card'); if (el) { el.hidden = true; el.innerHTML = ''; } }

  function aniRenderNotify(text) {
	var div = document.createElement('div');
	div.classList.add('ani-msg-notify');
	div.textContent = '· ' + text + ' ·';
	aniMsgs.insertBefore(div, aniTyping);
  }

  function aniEscapeHtml(str) {
	return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }

  function aniShowTyping(show) {
	aniTyping.style.display = show ? 'block' : 'none';
	if (show) aniScrollToBottom();
  }

  function aniScrollToBottom() {
	aniMsgs.scrollTop = aniMsgs.scrollHeight;
  }

  // ---- THREAD QoL (Phase 4): date dividers, ↓ LATEST pill, draft autosave ----
  var aniLastDivDate = null;
  function aniDayKey(ts) { var d = new Date(ts); return isNaN(d) ? null : (d.getFullYear() + '-' + (d.getMonth() + 1) + '-' + d.getDate()); }
  function aniDayLabel(ts) {
	var d = new Date(ts), now = new Date(), y = new Date(); y.setDate(now.getDate() - 1);
	var k = aniDayKey(ts);
	if (k === aniDayKey(now)) return 'TODAY';
	if (k === aniDayKey(y)) return 'YESTERDAY';
	return d.toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' }).toUpperCase();
  }
  function aniMaybeDateDivider(ts) {
	var k = aniDayKey(ts);
	if (!k || k === aniLastDivDate) return;
	aniLastDivDate = k;
	var div = document.createElement('div');
	div.className = 'ani-date-divider';
	div.innerHTML = '<span>' + aniDayLabel(ts) + '</span>';
	aniMsgs.insertBefore(div, aniTyping);
  }

  var aniUnread = 0;
  function aniNearBottom() { return aniMsgs.scrollHeight - aniMsgs.scrollTop - aniMsgs.clientHeight < aniMsgs.clientHeight; }
  function aniShowLatestPill() {
	var p = document.getElementById('ani-latest-pill');
	if (p) { p.hidden = false; p.textContent = '↓ LATEST' + (aniUnread > 0 ? ' · ' + aniUnread : ''); }
  }
  function aniHideLatestPill() { var p = document.getElementById('ani-latest-pill'); if (p) p.hidden = true; aniUnread = 0; }
  aniMsgs.addEventListener('scroll', function() { if (aniNearBottom()) aniHideLatestPill(); });

  var aniDraftTimer = null;
  function aniFmtClock() { var d = new Date(); return ('0' + d.getHours()).slice(-2) + ':' + ('0' + d.getMinutes()).slice(-2); }
  function aniShowDraftNote(txt) { var n = document.getElementById('ani-draft-note'); if (!n) return; if (txt) { n.textContent = txt; n.hidden = false; } else n.hidden = true; }
  function aniSaveDraft() {
	var v = aniInput.value;
	try { if (v.trim()) localStorage.setItem('ani_draft', v); else localStorage.removeItem('ani_draft'); } catch (e) {}
	aniShowDraftNote(v.trim() ? 'DRAFT · AUTOSAVED ' + aniFmtClock() : '');
  }
  function aniRestoreDraft() {
	try { var v = localStorage.getItem('ani_draft'); if (v && !aniInput.value) { aniInput.value = v; aniShowDraftNote('DRAFT · restored'); } } catch (e) {}
  }
  function aniClearDraft() { try { localStorage.removeItem('ani_draft'); } catch (e) {} aniShowDraftNote(''); }
  aniInput.addEventListener('input', function() { if (aniDraftTimer) clearTimeout(aniDraftTimer); aniDraftTimer = setTimeout(aniSaveDraft, 1000); });

  function aniPhotoLog() {
	var overlay = document.getElementById('ani-photolog-overlay');
	var body = document.getElementById('ani-photolog-body');
	body.innerHTML = '<div class="plog-msg">loading…</div>';
	overlay.hidden = false;
	fetch('/ani/photo-log')
	  .then(function(r) { return r.json(); })
	  .then(function(data) { aniRenderPhotoLog(data.events || []); })
	  .catch(function() { body.innerHTML = '<div class="plog-msg">could not load the log</div>'; });
  }

  function aniPhotoLogClose() {
	document.getElementById('ani-photolog-overlay').hidden = true;
  }

  // Favorites library — a gallery of the photos you've ♥'d.
  function aniLibrary() {
	var overlay = document.getElementById('ani-library-overlay');
	var body = document.getElementById('ani-library-body');
	if (!overlay || !body) return;
	body.innerHTML = '<div class="plog-msg">loading…</div>';
	overlay.hidden = false;
	fetch('/ani/photo/favorites')
	  .then(function(r) { return r.json(); })
	  .then(function(data) { aniRenderLibrary(data.favorites || []); })
	  .catch(function() { body.innerHTML = '<div class="plog-msg">could not load your library</div>'; });
  }
  function aniLibraryClose() {
	var o = document.getElementById('ani-library-overlay'); if (o) o.hidden = true;
  }
  function aniRenderLibrary(favs) {
	var body = document.getElementById('ani-library-body');
	if (!body) return;
	if (!favs.length) { body.innerHTML = '<div class="plog-msg">no favorites yet — tap ♥ on a photo to add it</div>'; return; }
	var html = '<div class="ani-lib-grid">';
	favs.forEach(function(f) {
	  var u = aniEscapeHtml(f.url || '');
	  if (!u) return;
	  html += '<div class="ani-lib-item">'
		   +  '<img class="ani-lib-thumb" src="' + u + '" alt="" loading="lazy" data-full="' + u + '">'
		   +  '<button type="button" class="ani-lib-remove" data-img="' + u + '" title="remove from library">✕</button>'
		   +  '</div>';
	});
	html += '</div>';
	body.innerHTML = html;
  }
  function aniLibraryRemove(url, btn) {
	if (!url) return;
	fetch('/ani/photo/favorite', {
	  method: 'POST', headers: { 'Content-Type': 'application/json' },
	  body: JSON.stringify({ image_url: url })
	})
	  .then(function(r) { return r.json(); })
	  .then(function(data) {
		if (data.favorited) return;   // still favorited somehow — leave it
		var it = btn.closest('.ani-lib-item'); if (it) it.remove();
		// un-light any in-chat ♥ for this image too
		Array.prototype.forEach.call(document.querySelectorAll('.ani-msg-favorite'), function(b) {
		  if (b.getAttribute('data-img') === url) b.classList.remove('on');
		});
		var body = document.getElementById('ani-library-body');
		if (body && !body.querySelector('.ani-lib-item')) body.innerHTML = '<div class="plog-msg">no favorites yet — tap ♥ on a photo to add it</div>';
	  })
	  .catch(function() {});
  }
  var _aniLibBody = document.getElementById('ani-library-body');
  if (_aniLibBody) _aniLibBody.addEventListener('click', function(e) {
	var rm = e.target.closest ? e.target.closest('.ani-lib-remove') : null;
	if (rm) { aniLibraryRemove(rm.getAttribute('data-img'), rm); return; }
	var th = e.target.closest ? e.target.closest('.ani-lib-thumb') : null;
	if (th) aniLightbox(th.getAttribute('data-full'));
  });

  // ---- ⌘K universal search (comms / memory / calendar / library) ----
  function aniSearchOpen() {
	var ov = document.getElementById('ani-search-overlay');
	if (!ov) return;
	ov.hidden = false;
	var body = document.getElementById('ani-search-body');
	if (body) body.innerHTML = '<div class="plog-msg">type to search comms · memory · calendar · library</div>';
	var inp = document.getElementById('ani-search-input');
	if (inp) { inp.value = ''; setTimeout(function() { inp.focus(); }, 30); }
  }
  function aniSearchClose() { var o = document.getElementById('ani-search-overlay'); if (o) o.hidden = true; }
  var aniSearchTimer = null;
  function aniSearchInput() { if (aniSearchTimer) clearTimeout(aniSearchTimer); aniSearchTimer = setTimeout(aniSearchRun, 220); }
  function aniSearchRun() {
	var inp = document.getElementById('ani-search-input'), body = document.getElementById('ani-search-body');
	if (!inp || !body) return;
	var q = inp.value.trim();
	if (q.length < 2) { body.innerHTML = '<div class="plog-msg">type at least 2 characters</div>'; return; }
	fetch('/ani/search?q=' + encodeURIComponent(q))
	  .then(function(r) { return r.json(); })
	  .then(function(data) { aniRenderSearch(data.groups || {}, q); })
	  .catch(function() { body.innerHTML = '<div class="plog-msg">search failed</div>'; });
  }
  function aniRenderSearch(groups, q) {
	var body = document.getElementById('ani-search-body');
	if (!body) return;
	var order = [['comms', 'COMMS'], ['memory', 'MEMORY'], ['calendar', 'CALENDAR'], ['library', 'LIBRARY']];
	var html = '', any = false;
	order.forEach(function(g) {
	  var grp = groups[g[0]];
	  if (!grp || !grp.total) return;
	  any = true;
	  html += '<div class="ani-srch-group"><div class="ani-srch-gtitle">' + g[1] + ' · ' + grp.total + '</div>';
	  grp.items.forEach(function(it) {
		var label = '', data = '';
		if (g[0] === 'comms') { label = (it.role === 'user' ? 'you: ' : 'ani: ') + (it.image ? '📷 ' : '') + it.text; data = 'data-jump="comms" data-ts="' + aniEscapeHtml(it.ts || '') + '" data-text="' + aniEscapeHtml((it.text || '').slice(0, 60)) + '"'; }
		else if (g[0] === 'memory') { label = it.text; data = 'data-jump="memory"'; }
		else if (g[0] === 'calendar') { label = (it.date ? it.date + ' · ' : '') + it.text; data = 'data-jump="calendar"'; }
		else { label = it.label || '(photo)'; data = 'data-jump="library" data-url="' + aniEscapeHtml(it.url || '') + '"'; }
		html += '<div class="ani-srch-item" ' + data + '>' + aniEscapeHtml(label) + '</div>';
	  });
	  if (grp.total > grp.items.length) {
		// "view all" has no dedicated results view yet — make it jump to the most-recent hit in this group.
		var top = grp.items[0] || {};
		var moreData = 'data-jump="' + g[0] + '-all"';
		if (g[0] === 'comms') moreData += ' data-ts="' + aniEscapeHtml(top.ts || '') + '" data-text="' + aniEscapeHtml((top.text || '').slice(0, 60)) + '"';
		else if (g[0] === 'library') moreData += ' data-url="' + aniEscapeHtml(top.url || '') + '"';
		html += '<div class="ani-srch-item ani-srch-more" ' + moreData + '>view all ' + grp.total + ' ↗</div>';
	  }
	  html += '</div>';
	});
	body.innerHTML = any ? html : '<div class="plog-msg">no matches for "' + aniEscapeHtml(q) + '"</div>';
  }
  function aniJumpToComms(snippet, ts) {
	if (!snippet && !ts) return;
	var justOpened = !aniIsOpen;
	if (justOpened) aniToggle();
	// aniToggle re-renders the thread; let the DOM settle before we hunt for the bubble.
	var go = function() {
	  var target = null;
	  if (ts) target = aniMsgs.querySelector('.ani-msg[data-ts="' + (window.CSS && CSS.escape ? CSS.escape(ts) : ts) + '"]');
	  if (!target && snippet) {
		var els = aniMsgs.querySelectorAll('.ani-msg');
		for (var i = els.length - 1; i >= 0; i--) {
		  if (els[i].textContent.indexOf(snippet) >= 0) { target = els[i]; break; }
		}
	  }
	  if (!target) return;
	  target.scrollIntoView({ block: 'center' });
	  target.classList.add('ani-msg-flash');
	  setTimeout(function() { target.classList.remove('ani-msg-flash'); }, 1600);
	};
	if (justOpened) setTimeout(go, 120); else go();
  }
  var _aniSearchBody = document.getElementById('ani-search-body');
  if (_aniSearchBody) _aniSearchBody.addEventListener('click', function(e) {
	var it = e.target.closest ? e.target.closest('.ani-srch-item') : null;
	if (!it) return;
	var jump = (it.getAttribute('data-jump') || '').replace('-all', '');
	aniSearchClose();
	if (jump === 'comms') aniJumpToComms(it.getAttribute('data-text'), it.getAttribute('data-ts'));
	else if (jump === 'memory') aniRemember();
	else if (jump === 'calendar') aniCalendar();
	else if (jump === 'library') { var u = it.getAttribute('data-url'); if (u) aniLightbox(u); else aniLibrary(); }
  });
  var _aniSearchInput = document.getElementById('ani-search-input');
  if (_aniSearchInput) {
	_aniSearchInput.addEventListener('input', aniSearchInput);
	_aniSearchInput.addEventListener('keydown', function(e) {
	  if (e.key === 'Enter') { e.preventDefault(); var f = document.querySelector('#ani-search-body .ani-srch-item'); if (f) f.click(); }
	  else if (e.key === 'Escape') { aniSearchClose(); }
	});
  }
  // Ani-namespaced shortcut (Ctrl/Cmd+Shift+K) — plain ⌘K belongs to the cockpit command palette.
  document.addEventListener('keydown', function(e) {
	if ((e.metaKey || e.ctrlKey) && e.shiftKey && !e.altKey && (e.key === 'k' || e.key === 'K')) {
	  e.preventDefault(); aniSearchOpen();
	} else if (e.key === 'Escape') {
	  var so = document.getElementById('ani-search-overlay');
	  if (so && !so.hidden) aniSearchClose();
	}
  });

  function aniShortReason(r) {
	r = (r || '').toLowerCase();
	if (r.indexOf('not-rear') >= 0 || r.indexOf('not a rear') >= 0 || r.indexOf('facing') >= 0) return 'not rear';
	if (r.indexOf('two ') >= 0 || r.indexOf('duplicat') >= 0 || r.indexOf('second') >= 0 || r.indexOf('merged') >= 0) return 'duplicate';
	if (r.indexOf('limb') >= 0 || r.indexOf('anatom') >= 0 || r.indexOf('fused') >= 0) return 'anatomy';
	if (r.indexOf('not nude') >= 0 || r.indexOf('clothed') >= 0) return 'not nude';
	if (r.indexOf('qa-') >= 0) return 'qa skipped';
	return (r || 'defect').slice(0, 28);
  }

  function aniRenderPhotoLog(events) {
	var body = document.getElementById('ani-photolog-body');
	if (!events.length) {
	  body.innerHTML = '<div class="plog-msg">no photos yet — tap 📷 to make one</div>';
	  return;
	}
	body.innerHTML = events.map(function(e) {
	  var qa = e.qa || [];
	  var ticks = qa.length ? qa.map(function(a) { return a.ok ? '✓' : '✗'; }).join(' ') : '—';
	  var fails = qa.filter(function(a) { return !a.ok; });
	  var reason;
	  if (!qa.length) reason = e.outcome === 'failed' ? 'generation failed' : 'no QA';
	  else if (!fails.length) reason = 'clean (' + qa.length + ' tr' + (qa.length === 1 ? 'y' : 'ies') + ')';
	  else reason = aniShortReason(fails[fails.length - 1].reason) + ' ×' + fails.length;
	  var badge = e.outcome === 'sent' ? '<span class="plog-ok">✓ sent</span>'
			   : e.outcome === 'best-effort' ? '<span class="plog-warn">⚠ best-effort</span>'
			   : '<span class="plog-fail">✕ failed</span>';
	  var tags = [e.model || 'venice', e.clothed ? 'clothed' : 'nude'];
	  if (e.pose) tags.push('pose');
	  if (e.rear) tags.push('rear');
	  var sc = e.scene || '';
	  var sceneTxt = aniEscapeHtml(sc.slice(0, 90)) + (sc.length > 90 ? '…' : '');
	  // expandable detail: full scene + every QA attempt with its reason + meta + image link
	  var tries = qa.length
		? qa.map(function(a, i) {
			return '<div class="plog-try"><span class="' + (a.ok ? 'plog-ok' : 'plog-fail') + '">'
			  + (a.ok ? '✓' : '✗') + ' try ' + (i + 1) + '</span> '
			  + aniEscapeHtml(a.reason || (a.ok ? 'ok' : 'rejected')) + '</div>';
		  }).join('')
		: '<div class="plog-try">no QA run</div>';
	  var meta = 'cfg ' + (e.cfg != null ? e.cfg : '?') + ' · ' + (e.dims || '?');
	  var link = e.url ? '<a href="' + aniEscapeHtml(e.url) + '" target="_blank" rel="noopener">open image ↗</a>' : '';
	  return '<div class="plog-entry" onclick="this.classList.toggle(\'open\')" title="tap for detail">'
		+ '<div class="plog-row1"><span class="plog-ts">' + aniEscapeHtml(e.ts || '') + '</span>' + badge
		  + '<span class="plog-tags">' + aniEscapeHtml(tags.join(' · ')) + '</span></div>'
		+ '<div class="plog-scene">' + sceneTxt + '</div>'
		+ '<div class="plog-qa">QA ' + ticks + ' <span class="plog-reason">' + aniEscapeHtml(reason) + '</span></div>'
		+ '<div class="plog-detail">'
		  + '<div class="plog-full">' + aniEscapeHtml(sc) + '</div>'
		  + '<div class="plog-tries">' + tries + '</div>'
		  + '<div class="plog-meta">' + aniEscapeHtml(meta) + (link ? ' · ' + link : '') + '</div>'
		+ '</div>'
		+ '</div>';
	}).join('');
  }

  // ---- Calendar (her shared plans) ----
  function aniCalendar() {
	var dateInput = document.getElementById('ani-cal-date');
	if (dateInput && !dateInput.value) {
	  var n = new Date();
	  dateInput.value = n.getFullYear() + '-' + String(n.getMonth() + 1).padStart(2, '0') + '-' + String(n.getDate()).padStart(2, '0');
	}
	document.getElementById('ani-calendar-overlay').hidden = false;
	aniLoadCalendar();
  }

  function aniCalendarClose() {
	document.getElementById('ani-calendar-overlay').hidden = true;
  }

  function aniLoadCalendar() {
	var body = document.getElementById('ani-calendar-body');
	body.innerHTML = '<div class="plog-msg">loading…</div>';
	fetch('/ani/calendar')
	  .then(function(r) { return r.json(); })
	  .then(function(data) { aniRenderCalendar(data.entries || [], data.today); })
	  .catch(function() { body.innerHTML = '<div class="plog-msg">could not load the calendar</div>'; });
  }

  function aniCalFmtDate(iso) {
	var p = (iso || '').split('-');
	if (p.length !== 3) return iso;
	var dt = new Date(+p[0], +p[1] - 1, +p[2]);
	return dt.toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' });
  }

  function aniCalFmtTime(hm) {
	var p = (hm || '').split(':');
	if (p.length !== 2) return hm;
	var h = +p[0], ap = h < 12 ? 'AM' : 'PM', h12 = h % 12;
	if (h12 === 0) h12 = 12;
	return h12 + ':' + p[1] + ' ' + ap;
  }

  function aniRenderCalendar(entries, today) {
	var body = document.getElementById('ani-calendar-body');
	if (!entries.length) {
	  body.innerHTML = '<div class="plog-msg">nothing on the calendar yet — add a plan above, or just tell her in chat</div>';
	  return;
	}
	body.innerHTML = entries.map(function(e) {
	  var when = aniCalFmtDate(e.date) + (e.time ? ' · ' + aniCalFmtTime(e.time) : '');
	  var isToday = e.date === today;
	  var src = e.source === 'her' ? ' <span class="cal-src" title="she added this">🦇</span>' : '';
	  return '<div class="ani-cal-entry' + (isToday ? ' cal-today' : '') + '">'
		+ '<div class="cal-when">' + aniEscapeHtml(when) + (isToday ? ' <span class="cal-badge">TODAY</span>' : '') + '</div>'
		+ '<div class="cal-what">' + aniEscapeHtml(e.text) + src + '</div>'
		+ '<button class="cal-del" onclick="aniCalDelete(\'' + e.id + '\')" aria-label="Delete" title="Remove">✕</button>'
		+ '</div>';
	}).join('');
  }

  function aniCalAdd() {
	var date = document.getElementById('ani-cal-date').value;
	var time = document.getElementById('ani-cal-time').value;
	var text = document.getElementById('ani-cal-text').value.trim();
	if (!date || !text) return;
	fetch('/ani/calendar/add', {
	  method: 'POST',
	  headers: { 'Content-Type': 'application/json' },
	  body: JSON.stringify({ date: date, time: time, text: text })
	}).then(function(r) { return r.json(); })
	  .then(function(data) {
		if (data.ok) {
		  document.getElementById('ani-cal-text').value = '';
		  document.getElementById('ani-cal-time').value = '';
		  aniLoadCalendar();
		}
	  }).catch(function() {});
  }

  function aniCalDelete(id) {
	fetch('/ani/calendar/delete', {
	  method: 'POST',
	  headers: { 'Content-Type': 'application/json' },
	  body: JSON.stringify({ id: id })
	}).then(function() { aniLoadCalendar(); }).catch(function() {});
  }

  // ---- What she remembers (durable notes) ----
  function aniRemember() {
	document.getElementById('ani-remember-overlay').hidden = false;
	aniLoadRemember();
  }

  function aniRememberClose() {
	document.getElementById('ani-remember-overlay').hidden = true;
  }

  function aniLoadRemember() {
	var body = document.getElementById('ani-remember-body');
	body.innerHTML = '<div class="plog-msg">loading…</div>';
	fetch('/ani/remember')
	  .then(function(r) { return r.json(); })
	  .then(function(data) { aniRenderRemember(data.notes || []); })
	  .catch(function() { body.innerHTML = '<div class="plog-msg">could not load</div>'; });
  }

  function aniRenderRemember(notes) {
	var body = document.getElementById('ani-remember-body');
	if (!notes.length) {
	  body.innerHTML = '<div class="plog-msg">she hasn\'t noted anything yet — tell her things and she\'ll remember, or add one above</div>';
	  return;
	}
	body.innerHTML = notes.map(function(n) {
	  var tag = '';
	  if (n.category && n.category !== 'misc') {
		var core = (n.importance >= 3) ? ' ani-mem-core' : '';
		tag = '<span class="ani-mem-cat' + core + '">' + aniEscapeHtml(n.category.replace('_', ' ')) + '</span>';
	  }
	  return '<div class="ani-cal-entry">'
		+ '<div class="cal-what">' + tag + aniEscapeHtml(n.text) + '</div>'
		+ '<button class="cal-del" onclick="aniMemDelete(\'' + n.id + '\')" aria-label="Forget" title="Forget this">✕</button>'
		+ '</div>';
	}).join('');
  }

  function aniMemTidy(btn) {
	if (btn) { btn.disabled = true; btn.textContent = 'TIDYING…'; }
	fetch('/ani/remember/consolidate', { method: 'POST' })
	  .then(function(r) { return r.json(); })
	  .then(function(data) {
		if (btn) { btn.disabled = false; btn.textContent = 'TIDY'; }
		if (data.ok) { aniRenderNotify('memory tidied — ' + data.before + ' → ' + data.after + ' notes'); aniLoadRemember(); }
		else { aniRenderNotify(data.message || 'nothing to tidy'); }
	  })
	  .catch(function() { if (btn) { btn.disabled = false; btn.textContent = 'TIDY'; } });
  }

  function aniMemAdd() {
	var input = document.getElementById('ani-mem-text');
	var text = input.value.trim();
	if (!text) return;
	fetch('/ani/remember/add', {
	  method: 'POST',
	  headers: { 'Content-Type': 'application/json' },
	  body: JSON.stringify({ text: text })
	}).then(function(r) { return r.json(); })
	  .then(function(data) {
		if (data.ok) { input.value = ''; aniLoadRemember(); }
	  }).catch(function() {});
  }

  function aniMemDelete(id) {
	fetch('/ani/remember/delete', {
	  method: 'POST',
	  headers: { 'Content-Type': 'application/json' },
	  body: JSON.stringify({ id: id })
	}).then(function() { aniLoadRemember(); }).catch(function() {});
  }

  // ---- Core memory file editor (static/ani_memory.txt) ----
  function aniCoreStatus(m) {
	var el = document.getElementById('ani-core-status');
	if (el) el.textContent = m || '';
  }

  function aniCore() {
	var ta = document.getElementById('ani-core-text');
	ta.value = 'loading…';
	aniCoreStatus('');
	document.getElementById('ani-core-overlay').hidden = false;
	fetch('/ani/memory-file')
	  .then(function(r) { return r.json(); })
	  .then(function(data) { ta.value = data.content || ''; })
	  .catch(function() { ta.value = ''; aniCoreStatus('could not load'); });
  }

  function aniCoreClose() {
	document.getElementById('ani-core-overlay').hidden = true;
  }

  function aniCoreSave() {
	var content = document.getElementById('ani-core-text').value;
	if (!content.trim()) { aniCoreStatus("won't save empty"); return; }
	aniCoreStatus('saving…');
	fetch('/ani/memory-file', {
	  method: 'POST',
	  headers: { 'Content-Type': 'application/json' },
	  body: JSON.stringify({ content: content })
	}).then(function(r) { return r.json(); })
	  .then(function(data) {
		aniCoreStatus(data.ok ? ('saved ✓ · ' + data.chars + ' chars (next message uses it)') : (data.error || 'error'));
	  }).catch(function() { aniCoreStatus('save failed'); });
  }
