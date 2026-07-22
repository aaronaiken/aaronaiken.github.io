/* 48pages notebook — cockpit "side-door" client (slip + fullscreen skeleton).
   Self-contained module: talks to /notebook/page, /notebook/slip, and /below-deck/add.
   Kept liftable — when 48pages ships, swap these fetch targets for its /v1/* API and
   nothing else changes. Full INKWELL UI (iA render, scraps, ROLL/FILE/TEAR, cabinet,
   live Below Deck on the right page) lands in the next phase. */
(function () {
	'use strict';

	var PAGE_URL = '/notebook/page';
	var SLIP_URL = '/notebook/slip';
	var BELOW_ADD_URL = '/below-deck/add';

	// PG n/48 label — a page is "used" the moment any ink lands on it (ceil, min 1).
	function fmtGauge(b) {
		if (!b) return 'PG 0/48';
		var used = b.pages_used || 0;
		var pg = used <= 0 ? 0 : Math.max(1, Math.ceil(used));
		return 'PG ' + Math.min(pg, b.page_budget) + '/' + b.page_budget;
	}

	// ---------- SLIP (on /publish) ----------
	function initSlip() {
		var slip = document.getElementById('nb-slip-input');
		if (!slip) return;
		var gauge = document.getElementById('nb-slip-gauge');
		var spineFill = document.getElementById('nb-slip-spine-fill');
		var flash = document.getElementById('nb-slip-flash');
		var DRAFT_KEY = 'cockpit-nb-slip-draft';

		// Restore any unflushed draft so a refresh never loses keystrokes.
		try { var d = localStorage.getItem(DRAFT_KEY); if (d) slip.value = d; } catch (e) {}

		function paintBudget(b) {
			if (gauge) gauge.textContent = fmtGauge(b);
			if (spineFill && b) {
				spineFill.style.height = Math.round((b.fill || 0) * 100) + '%';
				spineFill.classList.toggle('is-triage', !!b.triage);
			}
		}
		function loadBudget() {
			fetch(PAGE_URL).then(function (r) { return r.json(); })
				.then(function (d) { paintBudget(d.budget); }).catch(function () {});
		}
		loadBudget();

		function saveDraft() { try { localStorage.setItem(DRAFT_KEY, slip.value); } catch (e) {} }
		function clearDraft() { try { localStorage.removeItem(DRAFT_KEY); } catch (e) {} }

		function showFlash(msg) {
			if (!flash) return;
			flash.textContent = msg;
			flash.classList.add('is-on');
			setTimeout(function () { flash.classList.remove('is-on'); }, 1800);
		}

		function fileToPage() {
			var text = slip.value.replace(/\n+$/, '').trim();
			if (!text) { slip.value = ''; clearDraft(); return; }
			fetch(SLIP_URL, {
				method: 'POST', headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ text: text })
			}).then(function (r) { return r.json(); })
				.then(function (d) {
					slip.value = ''; clearDraft();
					paintBudget(d.budget);
					showFlash('FILED TO PAGE ✓');
				}).catch(function () { showFlash('offline — kept on the slip'); });
		}

		function rollToBelowDeck() {
			var text = slip.value.trim();
			if (!text) return;
			var title = text.split('\n').map(function (s) { return s.trim(); })
				.filter(Boolean).join(' / ');
			var body = new URLSearchParams(); body.set('title', title);
			fetch(BELOW_ADD_URL, {
				method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
				body: body.toString()
			}).then(function (r) { return r.json(); })
				.then(function () { slip.value = ''; clearDraft(); showFlash('ROLLED TO BELOW DECK ↩'); })
				.catch(function () { showFlash('offline — kept on the slip'); });
		}

		slip.addEventListener('input', saveDraft);
		slip.addEventListener('keydown', function (e) {
			// Ctrl/Cmd+Enter → roll straight to Below Deck.
			if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
				e.preventDefault(); rollToBelowDeck(); return;
			}
			// Enter on an already-blank trailing line (the "Enter Enter" gesture) → file to page.
			// Shift+Enter always inserts a newline, so multi-line slips are still possible.
			if (e.key === 'Enter' && !e.shiftKey && !e.ctrlKey && !e.metaKey) {
				var v = slip.value;
				var caretAtEnd = slip.selectionStart === v.length && slip.selectionEnd === v.length;
				if (caretAtEnd && /\n\s*$/.test(v) && v.trim()) {
					e.preventDefault(); fileToPage(); return;
				}
			}
		});
	}

	// ---------- FULLSCREEN INKWELL (on /notebook) ----------
	function initFullscreen() {
		var page = document.getElementById('nb-page-input');
		if (!page) return;
		var gaugeLabel = document.getElementById('nb-page-gauge');
		var gaugeFill = document.getElementById('nb-gauge-fill');
		var status = document.getElementById('nb-page-status');
		var banner = document.getElementById('nb-triage-banner');
		var scrapBar = document.getElementById('nb-scrap-bar');
		var scrapWhat = document.getElementById('nb-scrap-what');
		var pageWrap = document.getElementById('nb-fs-page');
		var bdList = document.getElementById('nb-bd-list');
		var bdInput = document.getElementById('nb-bd-input');
		var saveTimer = null, lastBudget = null;

		function paint(b) {
			if (!b) return;
			lastBudget = b;
			if (gaugeLabel) gaugeLabel.textContent = fmtGauge(b);
			if (gaugeFill) {
				gaugeFill.style.height = Math.round((b.fill || 0) * 100) + '%';
				gaugeFill.classList.toggle('is-triage', !!b.triage);
			}
			if (pageWrap) pageWrap.classList.toggle('is-triage', !!b.triage);
			if (banner) banner.classList.toggle('is-on', !!b.triage);
		}
		function flash(msg) { if (status) status.textContent = msg; }
		function saveNow() {
			fetch(PAGE_URL, {
				method: 'POST', headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ content: page.value, force: true })
			}).then(function (r) { return r.json(); })
				.then(function (d) { paint(d.budget); flash('saved'); })
				.catch(function () { flash('offline'); });
		}
		function scheduleSave() { flash('saving…'); clearTimeout(saveTimer); saveTimer = setTimeout(saveNow, 1500); }

		// The scrap the caret sits in = the block between the surrounding blank lines.
		function currentBlock() {
			var v = page.value, pos = page.selectionStart;
			var start = v.lastIndexOf('\n\n', pos - 1);
			start = start === -1 ? 0 : start + 2;
			var endRel = v.indexOf('\n\n', pos);
			var end = endRel === -1 ? v.length : endRel;
			return { start: start, end: end, text: v.slice(start, end).replace(/^\s+|\s+$/g, '') };
		}
		function refreshScrapBar() {
			var t = currentBlock().text;
			if (scrapWhat) scrapWhat.textContent = t ? (t.split('\n')[0].slice(0, 42) + (t.length > 42 ? '…' : '')) : '—';
			if (scrapBar) scrapBar.classList.toggle('is-on', !!t);
		}
		function removeBlock(blk) {
			var v = page.value;
			var before = v.slice(0, blk.start).replace(/\n+$/, '');
			var after = v.slice(blk.end).replace(/^\n+/, '');
			page.value = before && after ? before + '\n\n' + after : before + after;
			page.selectionStart = page.selectionEnd = Math.min(before.length, page.value.length);
		}

		window.nbTearCurrent = function () {
			var blk = currentBlock(); if (!blk.text) return;
			removeBlock(blk); saveNow(); refreshScrapBar(); flash('torn');
		};
		window.nbRollCurrent = function () {
			var blk = currentBlock(); if (!blk.text) return;
			var title = blk.text.split('\n').map(function (s) { return s.trim(); }).filter(Boolean).join(' / ');
			var body = new URLSearchParams(); body.set('title', title);
			fetch(BELOW_ADD_URL, { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body: body.toString() })
				.then(function (r) { return r.json(); })
				.then(function () { removeBlock(blk); saveNow(); refreshScrapBar(); loadBelowDeck(); flash('rolled ↩'); })
				.catch(function () { flash('offline'); });
		};

		page.addEventListener('input', function () { scheduleSave(); refreshScrapBar(); });
		page.addEventListener('click', refreshScrapBar);
		page.addEventListener('keyup', refreshScrapBar);
		page.addEventListener('keydown', function (e) {
			// Soft-block once the page is full: Enter/navigation/delete still work, new characters don't.
			if (lastBudget && lastBudget.full && e.key.length === 1 && !e.ctrlKey && !e.metaKey && !e.altKey) {
				e.preventDefault(); flash('PAGE FULL — file, roll, or tear'); return;
			}
			if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') { e.preventDefault(); window.nbRollCurrent(); }
		});

		// ---- right page: live Below Deck (same store as /below-deck) ----
		function esc(s) { var d = document.createElement('div'); d.textContent = s == null ? '' : s; return d.innerHTML; }
		function loadBelowDeck() {
			if (!bdList) return;
			fetch('/below-deck/list').then(function (r) { return r.json(); }).then(function (d) {
				var html = '';
				(d.open || []).forEach(function (t) {
					html += '<li class="nb-bd-item" data-id="' + t.id + '">'
						+ '<button class="nb-bd-check" onclick="nbBdComplete(' + t.id + ')" title="Complete"></button>'
						+ '<span class="nb-bd-title">' + esc(t.title) + '</span>'
						+ '<button class="nb-bd-del" onclick="nbBdDelete(' + t.id + ')" title="Delete">✕</button></li>';
				});
				if (!(d.open || []).length) html += '<li class="nb-bd-empty">clear deck.</li>';
				(d.completed || []).slice(0, 6).forEach(function (t) {
					html += '<li class="nb-bd-item is-done"><span class="nb-bd-check done">✓</span>'
						+ '<span class="nb-bd-title">' + esc(t.title) + '</span></li>';
				});
				bdList.innerHTML = html;
			}).catch(function () {});
		}
		function bdPost(url, id, cb) {
			var body = new URLSearchParams(); body.set('id', id);
			fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body: body.toString() })
				.then(function () { if (cb) cb(); }).catch(function () {});
		}
		window.nbBdAdd = function () {
			if (!bdInput) return;
			var title = bdInput.value.trim(); if (!title) return;
			var body = new URLSearchParams(); body.set('title', title);
			fetch(BELOW_ADD_URL, { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body: body.toString() })
				.then(function (r) { return r.json(); }).then(function () { bdInput.value = ''; loadBelowDeck(); }).catch(function () {});
		};
		window.nbBdComplete = function (id) { bdPost('/below-deck/complete', id, loadBelowDeck); };
		window.nbBdDelete = function (id) { bdPost('/below-deck/delete', id, loadBelowDeck); };

		// initial paint
		loadBelowDeck();
		refreshScrapBar();
		fetch(PAGE_URL).then(function (r) { return r.json(); }).then(function (d) { paint(d.budget); }).catch(function () {});
	}

	// ---------- MEDIA RAILS (home stack) ----------
	function railShown(id) {
		var e = document.getElementById(id);
		return !!e && getComputedStyle(e).display !== 'none';
	}
	var RAIL_MAP = { yt: 'yt-player', music: 'ad-music-player', video: 'ad-player' };
	function nbReflectRails() {
		Object.keys(RAIL_MAP).forEach(function (k) {
			var st = document.getElementById('rail-' + k + '-state');
			if (!st) return;
			var shown = railShown(RAIL_MAP[k]);
			st.textContent = shown ? '● SHOWING' : '— HIDDEN';
			var rail = document.getElementById('rail-' + k);
			if (rail) rail.classList.toggle('is-live', shown);
		});
	}
	window.nbMediaRail = function (kind) {
		if (kind === 'yt' && window.ytPlayerToggle) window.ytPlayerToggle();
		else if (kind === 'music' && window.adMusicPlayerToggle) window.adMusicPlayerToggle();
		else if (kind === 'video' && window.adPlayerToggle) window.adPlayerToggle();
		nbReflectRails();
	};

	// Expand action for the slip's ⤢ button + Ctrl+Shift+N.
	window.nbOpenFullscreen = function () { window.location.href = '/notebook'; };

	document.addEventListener('DOMContentLoaded', function () {
		initSlip();
		initFullscreen();
		if (document.getElementById('media-rails')) nbReflectRails();
		document.addEventListener('keydown', function (e) {
			// Ctrl+Shift+N → notebook fullscreen (browser may reserve this; ⤢ is the sure path).
			if ((e.ctrlKey || e.metaKey) && e.shiftKey && (e.key === 'N' || e.key === 'n')) {
				e.preventDefault(); window.nbOpenFullscreen();
			}
			// Esc closes the fullscreen back to the cockpit.
			if (e.key === 'Escape' && document.getElementById('nb-page-input')) {
				window.location.href = '/publish';
			}
		});
	});
})();
