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
		  var batPill = document.getElementById('ani-bat-pill');
		  if (batPill) batPill.classList.add('ani-bat-waiting');
		}
	  })
	  .catch(function() {});
  }

  setTimeout(aniPing, 1500);

  function aniToggle() {
	aniIsOpen = !aniIsOpen;
	aniPanel.classList.toggle('ani-open', aniIsOpen);
	var batPill = document.getElementById('ani-bat-pill');
	if (batPill) batPill.classList.remove('ani-bat-waiting');
	if (aniIsOpen && !aniLoaded) {
	  aniLoadHistory();
	  aniSendLocation();
	}
	if (aniIsOpen) {
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

  function aniLoadHistory() {
	aniLoaded = true;
	fetch('/ani/history')
	  .then(function(r) { return r.json(); })
	  .then(function(data) {
		updateAcheDisplay(data.ache_level);
		var messages = data.messages || [];
		if (messages.length > 0) {
		  aniEmpty.style.display = 'none';
		  messages.forEach(function(m) { aniRenderMessage(m.role, m.content, m.image); });
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
	aniRenderMessage('user', text);
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
		aniRenderMessage('assistant', data.reply || '', data.image_url);
		updateAcheDisplay(0);
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

  function aniPhoto() {
	if (aniPhotoBtn.disabled) return;
	aniEmpty.style.display = 'none';
	aniPhotoBtn.disabled = true;
	aniSendBtn.disabled = true;
	aniRenderNotify('developing a photo…');
	aniShowTyping(true);
	aniScrollToBottom();
	fetch('/ani/photo', { method: 'POST' })
	  .then(function(r) { return r.json(); })
	  .then(function(data) {
		aniShowTyping(false);
		aniPhotoBtn.disabled = false;
		aniSendBtn.disabled = false;
		if (data.image_url) {
		  aniRenderMessage('assistant', '', data.image_url);
		} else if (data.error === 'blocked') {
		  aniRenderNotify('photo blocked by the filter — describe a tamer scene and tap 📷 again');
		} else {
		  aniRenderNotify('could not develop a photo — give her a scene to work from first');
		}
		aniScrollToBottom();
	  })
	  .catch(function() {
		aniShowTyping(false);
		aniPhotoBtn.disabled = false;
		aniSendBtn.disabled = false;
		aniRenderNotify('photo request failed — try again');
		aniScrollToBottom();
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
	  })
	  .catch(function() {});
  }

  function aniRenderMessage(role, content, image) {
	content = content || '';
	if (content.startsWith('[daily briefing') || content.startsWith('[system:')) return;
	var div = document.createElement('div');
	div.classList.add('ani-msg');
	if (role === 'user') {
	  div.classList.add('ani-msg-user');
	  div.textContent = content;
	} else {
	  div.classList.add('ani-msg-ani');
	  var html = '<div class="ani-name">ANI</div>' + aniEscapeHtml(content).replace(/\n/g, '<br>');
	  if (image) html += '<img class="ani-msg-img" src="' + aniEscapeHtml(image) + '" alt="" loading="lazy">';
	  div.innerHTML = html;
	}
	aniMsgs.insertBefore(div, aniTyping);
  }

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
