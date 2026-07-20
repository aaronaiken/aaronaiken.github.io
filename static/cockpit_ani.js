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

  function updateAcheDisplay(level) {
	if (level === null || level === undefined) return;
	if (level < 20) {
	  aniAcheDisplay.textContent = '';
	  aniAcheDisplay.className = 'ache-low';
	} else {
	  aniAcheDisplay.textContent = '· ACHE ' + level + '%';
	  if (level < 40) aniAcheDisplay.className = 'ache-low';
	  else if (level < 65) aniAcheDisplay.className = 'ache-mid';
	  else if (level < 85) aniAcheDisplay.className = 'ache-high';
	  else aniAcheDisplay.className = 'ache-urgent';
	}
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
	  })
	  .catch(function() {});
  }

  // Live poll — while the panel is open, append any NEW messages (proactive daycast msgs arrive
  // server-side) without a page refresh; while closed, just update the ache + bat-pill pulse.
  function aniPoll() {
	if (aniIsOpen && aniLoaded) {
	  fetch('/ani/history')
		.then(function(r) { return r.json(); })
		.then(function(data) {
		  updateAcheDisplay(data.ache_level);
		  var appended = false;
		  (data.messages || []).forEach(function(m) {
			if (!aniSeen.has(aniSig(m.role, m.content, m.image))) {
			  aniEmpty.style.display = 'none';
			  aniRenderMessage(m.role, m.content, m.image, m.ts);
			  appended = true;
			}
		  });
		  if (appended) { aniLoadState(); aniScrollToBottom(); }
		})
		.catch(function() {});
	  aniLoadDecisions();
	  aniLoadMilestones();
	} else {
	  aniPing();
	}
  }

  setTimeout(aniPing, 1500);
  setInterval(aniPoll, 20000);

  function aniToggle() {
	aniIsOpen = !aniIsOpen;
	aniPanel.classList.toggle('ani-open', aniIsOpen);
	var batPill = document.getElementById('ani-bat-pill');
	if (batPill) batPill.classList.remove('ani-bat-waiting');
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
		var messages = data.messages || [];
		if (messages.length > 0) {
		  aniEmpty.style.display = 'none';
		  messages.forEach(function(m) { aniRenderMessage(m.role, m.content, m.image, m.ts); });
		}
		if (aniPendingOpener) {
		  aniEmpty.style.display = 'none';
		  aniRenderMessage('assistant', aniPendingOpener);
		  aniPendingOpener = null;
		}
		aniScrollToBottom();
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

  // Both 📷 (new photo) and ↻ (retry) go through the same see-and-edit modal: fetch the prompt, show it
  // editable, then Send generates with whatever you leave in the box. Mode decides what Send does.
  var aniPromptMode = 'new';   // 'new' | 'retry'
  var aniRetryCtx = null;      // { btn, oldUrl } when retrying a specific photo

  function aniPhoto() {
	if (aniPhotoBtn.disabled) return;
	aniPromptMode = 'new'; aniRetryCtx = null;
	aniPromptOpen(function() {
	  return fetch('/ani/photo/prompt', { method: 'POST' }).then(function(r) { return r.json(); });
	});
  }

  // ↻ retry: open the editable prompt for THIS photo (its stored scene), then Send re-rolls it in place.
  function aniRetryPhoto(btn) {
	var oldUrl = btn.getAttribute('data-img');
	if (!oldUrl || btn.disabled) return;
	aniPromptMode = 'retry';
	aniRetryCtx = { btn: btn, oldUrl: oldUrl };
	aniPromptOpen(function() {
	  return fetch('/ani/photo/retry', {
		method: 'POST', headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ image_url: oldUrl, preview: true })
	  }).then(function(r) { return r.json(); });
	});
  }

  // Open the modal and fill it via `fetcher` (a fn returning a promise of {scene}).
  function aniPromptOpen(fetcher) {
	var overlay = document.getElementById('ani-prompt-overlay');
	var box = document.getElementById('ani-prompt-text');
	var sendBtn = document.getElementById('ani-prompt-send');
	if (!overlay || !box || !sendBtn) return;
	box.value = '';
	box.placeholder = 'reading the scene…';
	sendBtn.disabled = true;
	sendBtn.textContent = aniPromptMode === 'retry' ? 'RE-ROLL 📷' : 'SEND 📷';
	overlay.hidden = false;
	fetcher()
	  .then(function(data) {
		if (data && data.scene) {
		  box.value = data.scene;
		  box.placeholder = 'the scene she photographs — edit freely';
		  sendBtn.disabled = false;
		  box.focus();
		} else {
		  box.placeholder = 'no scene yet — describe one to her first, then tap 📷';
		}
	  })
	  .catch(function() { box.placeholder = 'could not read the scene — close and try again'; });
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

  function aniClear() {
	if (!confirm('clear the whole history? this cannot be undone.')) return;
	fetch('/ani/clear', { method: 'POST' })
	  .then(function() {
		Array.from(aniMsgs.querySelectorAll('.ani-msg, .ani-msg-notify')).forEach(function(el) { el.remove(); });
		aniEmpty.style.display = 'block';
		aniLoaded = false;
		var ns = document.getElementById('ani-now-state'); if (ns) { ns.hidden = true; ns.innerHTML = ''; }
	  })
	  .catch(function() {});
  }

  function aniFmtMsgTime(iso) {
	if (!iso) return '';
	var d = new Date(iso);
	if (isNaN(d.getTime())) return '';
	var t = d.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
	if (d.toDateString() === new Date().toDateString()) return t;
	return d.toLocaleDateString([], { weekday: 'short' }) + ' ' + t;
  }

  function aniRenderMessage(role, content, image, ts) {
	content = content || '';
	if (content.startsWith('[daily briefing') || content.startsWith('[system:')) return;
	aniSeen.add(aniSig(role, content, image));   // mark rendered so the poller won't re-append it
	var when = aniFmtMsgTime(ts);
	var div = document.createElement('div');
	div.classList.add('ani-msg');
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
		html += '<img class="ani-msg-img" src="' + aniEscapeHtml(image) + '" alt="" loading="lazy">';
		// bad render? re-roll it in place — deletes this one, generates a new one from the same scene
		html += '<button type="button" class="ani-msg-retry" data-img="' + aniEscapeHtml(image) + '" title="bad render? re-roll it">↻ retry</button>';
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
	if (t && t.classList && t.classList.contains('ani-msg-img')) {
	  aniLightbox(t.getAttribute('src'));
	}
  });

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
