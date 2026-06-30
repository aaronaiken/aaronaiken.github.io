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
		}
		// Pulse the bat for a staged opener OR unseen daycast messages (already in history).
		if ((data.pending && data.opener) || data.unseen) {
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

  // Tap a photo to view it larger. Delegated so it works for every rendered image.
  aniMsgs.addEventListener('click', function(e) {
	var t = e.target;
	if (t && t.classList && t.classList.contains('ani-msg-img')) {
	  aniLightbox(t.getAttribute('src'));
	}
  });

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
	  return '<div class="ani-cal-entry">'
		+ '<div class="cal-what">' + aniEscapeHtml(n.text) + '</div>'
		+ '<button class="cal-del" onclick="aniMemDelete(\'' + n.id + '\')" aria-label="Forget" title="Forget this">✕</button>'
		+ '</div>';
	}).join('');
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
