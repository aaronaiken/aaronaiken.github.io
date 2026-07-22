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

	// Shared page-meter (48 ticks) — used by both the home slip and the fullscreen.
	// A page is "used" the moment any ink lands on it (ceil, min 1); tick 38 = PG 39 triage.
	function buildTicks(container) {
		var ticks = [];
		if (container && !container.children.length) {
			for (var i = 0; i < 48; i++) {
				var t = document.createElement('div');
				t.className = 'nb-tick' + (i === 38 ? ' is-triage-mark' : '');
				container.appendChild(t); ticks.push(t);
			}
		}
		return ticks;
	}
	function pagesFilled(b) {
		var used = (b && b.pages_used) || 0;
		return used <= 0 ? 0 : Math.min(b.page_budget, Math.max(1, Math.ceil(used)));
	}
	function paintTicks(ticks, b) {
		var fill = pagesFilled(b);
		for (var i = 0; i < ticks.length; i++) {
			var f = i < fill;
			ticks[i].classList.toggle('is-filled', f);
			ticks[i].classList.toggle('past-triage', f && i >= 38);
		}
	}
	function readText(b) {
		if (!b) return 'PG 0/48 · 48 LEFT';
		var left = Math.max(0, b.page_budget - Math.ceil(b.pages_used || 0));
		return 'PG ' + pagesFilled(b) + '/' + b.page_budget + ' · ' + left + ' LEFT';
	}

	// ---------- SLIP (on /publish) ----------
	function initSlip() {
		var slip = document.getElementById('nb-slip-input');
		if (!slip) return;
		var gauge = document.getElementById('nb-slip-gauge');
		var meterTicks = document.getElementById('nb-slip-meter-ticks');
		var flash = document.getElementById('nb-slip-flash');
		var DRAFT_KEY = 'cockpit-nb-slip-draft';
		var slipTicks = buildTicks(meterTicks);

		// Restore any unflushed draft so a refresh never loses keystrokes.
		try { var d = localStorage.getItem(DRAFT_KEY); if (d) slip.value = d; } catch (e) {}

		function paintBudget(b) {
			if (!b) return;
			if (gauge) gauge.textContent = readText(b);
			paintTicks(slipTicks, b);
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
		var meter = document.getElementById('nb-meter');
		var meterTicks = document.getElementById('nb-meter-ticks');
		var status = document.getElementById('nb-page-status');
		var banner = document.getElementById('nb-triage-banner');
		var scrapBar = document.getElementById('nb-scrap-bar');
		var scrapWhat = document.getElementById('nb-scrap-what');
		var pageWrap = document.getElementById('nb-fs-page');
		var bdList = document.getElementById('nb-bd-list');
		var bdInput = document.getElementById('nb-bd-input');
		var saveTimer = null, lastBudget = null;

		var TICKS = buildTicks(meterTicks);

		function paint(b) {
			if (!b) return;
			lastBudget = b;
			if (gaugeLabel) gaugeLabel.textContent = readText(b);
			paintTicks(TICKS, b);
			if (meter) meter.classList.toggle('is-triage', !!b.triage);
			if (pageWrap) pageWrap.classList.toggle('is-triage', !!b.triage);
			if (banner) banner.classList.toggle('is-on', !!b.triage);
		}
		var lastSaved = null, saving = false;
		function agoStr(ms) {
			var s = Math.floor((Date.now() - ms) / 1000);
			if (s < 5) return 'JUST NOW';
			if (s < 60) return s + 'S AGO';
			var m = Math.floor(s / 60); if (m < 60) return m + 'M AGO';
			return Math.floor(m / 60) + 'H AGO';
		}
		function renderStatus() {
			if (!status) return;
			if (saving) { status.textContent = 'SAVING…'; return; }
			status.textContent = lastSaved ? ('SAVED · ' + agoStr(lastSaved)) : 'SAVED';
		}
		function flash(msg) { if (status) status.textContent = msg; }
		function saveNow() {
			saving = true; renderStatus();
			fetch(PAGE_URL, {
				method: 'POST', headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ content: page.value, force: true })
			}).then(function (r) { return r.json(); })
				.then(function (d) { paint(d.budget); saving = false; lastSaved = Date.now(); renderStatus(); })
				.catch(function () { saving = false; if (status) status.textContent = 'OFFLINE'; });
		}
		function scheduleSave() { saving = true; renderStatus(); clearTimeout(saveTimer); saveTimer = setTimeout(saveNow, 1500); }
		setInterval(renderStatus, 5000);

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
			if ((e.ctrlKey || e.metaKey) && e.shiftKey && (e.key === 'f' || e.key === 'F')) { e.preventDefault(); window.nbFileCurrent(); }
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

		// ---- cabinet (file / browse) ----
		var cab = document.getElementById('nb-cabinet');
		var cabCount = document.getElementById('nb-cab-count');
		var cabFiling = document.getElementById('nb-cab-filing');
		var cabBrowse = document.getElementById('nb-cab-browse');
		var filePreview = document.getElementById('nb-file-preview');
		var fileTitle = document.getElementById('nb-file-title');
		var fileTagsWrap = document.getElementById('nb-file-tags');
		var fileNewTag = document.getElementById('nb-file-newtag');
		var fileFrees = document.getElementById('nb-file-frees');
		var cabCards = document.getElementById('nb-cab-cards');
		var cabTagRail = document.getElementById('nb-cab-tagrail');
		var cabSearchInp = document.getElementById('nb-cab-search');
		var cabSortSel = document.getElementById('nb-cab-sort');
		var fileTags = [], fileBlock = null, cabActiveTag = '', cabAllTags = {}, cabItems = [];

		function estPages(text) {
			if (!text) return 0;
			var u = 0; text.split('\n').forEach(function (l) { u += Math.max(1, Math.ceil(l.length / 60)); });
			return u / 20;
		}
		function updateCabCount() {
			fetch('/notebook/cabinet').then(function (r) { return r.json(); })
				.then(function (d) { if (cabCount) cabCount.textContent = (d.items || []).length; cabAllTags = (d && d.tags) || cabAllTags; }).catch(function () {});
		}
		function openDrawer(mode) {
			if (!cab) return;
			cab.classList.add('is-open');
			cab.classList.toggle('is-filing', mode === 'file');
		}
		window.nbCabClose = function () { if (cab) cab.classList.remove('is-open', 'is-filing'); };

		// filing
		function renderFileTags() {
			if (!fileTagsWrap) return;
			var chosen = fileTags.map(function (t) {
				return '<span class="nb-file-tag is-on" onclick="nbFileDropTag(\'' + esc(t) + '\')">' + esc(t) + ' ×</span>';
			}).join('');
			var sugg = Object.keys(cabAllTags).filter(function (t) { return fileTags.indexOf(t) < 0; }).map(function (t) {
				return '<span class="nb-file-tag" onclick="nbFilePickTag(\'' + esc(t) + '\')">' + esc(t) + '</span>';
			}).join('');
			fileTagsWrap.innerHTML = chosen + sugg;
		}
		window.nbFilePickTag = function (t) { if (fileTags.indexOf(t) < 0) fileTags.push(t); renderFileTags(); };
		window.nbFileDropTag = function (t) { fileTags = fileTags.filter(function (x) { return x !== t; }); renderFileTags(); };
		window.nbFileAddTag = function () {
			if (!fileNewTag) return;
			var t = fileNewTag.value.trim().toLowerCase();
			if (t && fileTags.indexOf(t) < 0) fileTags.push(t);
			fileNewTag.value = ''; renderFileTags();
		};
		window.nbFileCurrent = function () {
			var blk = currentBlock(); if (!blk.text) return;
			fileBlock = blk; fileTags = [];
			if (filePreview) filePreview.textContent = blk.text;
			if (fileTitle) fileTitle.value = '';
			if (fileNewTag) fileNewTag.value = '';
			var p = estPages(blk.text);
			if (fileFrees) fileFrees.textContent = 'FREES ~' + (p < 1 ? '<1' : p.toFixed(1)) + (p >= 2 ? ' PAGES' : ' PAGE');
			fetch('/notebook/cabinet').then(function (r) { return r.json(); })
				.then(function (d) { cabAllTags = d.tags || {}; renderFileTags(); }).catch(function () { renderFileTags(); });
			openDrawer('file');
			if (fileTitle) setTimeout(function () { fileTitle.focus(); }, 60);
		};
		window.nbFileConfirm = function (keep) {
			if (!fileBlock) return;
			var body = { title: fileTitle ? fileTitle.value : '', body_md: fileBlock.text, tags: fileTags };
			fetch('/notebook/cabinet', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
				.then(function (r) { return r.json(); }).then(function (d) {
					if (d && d.ok) {
						if (!keep) { removeBlock(fileBlock); saveNow(); refreshScrapBar(); }
						fileBlock = null; window.nbCabClose(); updateCabCount(); flash(keep ? 'filed (kept)' : 'filed');
					}
				}).catch(function () { flash('offline'); });
		};

		// browse
		function ageStr(iso) {
			if (!iso) return '';
			try {
				var days = Math.floor((Date.now() - new Date(iso).getTime()) / 86400000);
				if (days < 1) return 'today';
				if (days < 7) return days + 'd';
				if (days < 31) return Math.floor(days / 7) + 'w';
				return Math.floor(days / 30) + 'mo';
			} catch (e) { return ''; }
		}
		window.nbCabToggle = function () {
			if (cab && cab.classList.contains('is-open') && !cab.classList.contains('is-filing')) { window.nbCabClose(); return; }
			openDrawer('browse'); window.nbCabRender();
		};
		window.nbCabTag = function (t) { cabActiveTag = (cabActiveTag === t ? '' : t); window.nbCabRender(); };
		window.nbCabSearch = function () { window.nbCabRender(); };
		window.nbCabRender = function () {
			if (!cabCards) return;
			var search = cabSearchInp ? cabSearchInp.value.trim() : '';
			var url = '/notebook/cabinet?search=' + encodeURIComponent(search) + '&tag=' + encodeURIComponent(cabActiveTag);
			fetch(url).then(function (r) { return r.json(); }).then(function (d) {
				var items = (d.items || []).slice(); cabAllTags = d.tags || {};
				var sort = cabSortSel ? cabSortSel.value : 'new';
				if (sort === 'old') items.reverse();
				else if (sort === 'az') items.sort(function (a, b) { return (a.title || '').localeCompare(b.title || ''); });
				cabItems = items;
				if (cabTagRail) {
					var allN = (cabCount && cabCount.textContent) || items.length;
					var rail = '<button class="nb-cab-drawer' + (cabActiveTag === '' ? ' is-on' : '') + '" onclick="nbCabTag(\'\')"><span>ALL</span><span class="nb-cab-dn">' + allN + '</span></button>';
					Object.keys(cabAllTags).sort().forEach(function (t) {
						rail += '<button class="nb-cab-drawer' + (cabActiveTag === t ? ' is-on' : '') + '" onclick="nbCabTag(\'' + esc(t) + '\')"'
							+ ' ondragover="event.preventDefault()" ondragenter="this.classList.add(\'drag-over\')" ondragleave="this.classList.remove(\'drag-over\')"'
							+ ' ondrop="nbCabDrop(event,\'' + esc(t) + '\')"><span>#' + esc(t) + '</span><span class="nb-cab-dn">' + cabAllTags[t] + '</span></button>';
					});
					cabTagRail.innerHTML = rail;
				}
				if (!items.length) { cabCards.innerHTML = '<div class="nb-cab-empty">nothing filed' + (search || cabActiveTag ? ' here' : ' yet') + '.</div>'; return; }
				cabCards.innerHTML = items.map(function (c) {
					var raw = (c.body_md || '').replace(/\n/g, ' ');
					var excerpt = raw.slice(0, 120) + (raw.length > 120 ? '…' : '');
					var tags = (c.tags || []).map(function (t) { return '<span class="nb-cab-ctag">#' + esc(t) + '</span>'; }).join('');
					return '<div class="nb-cab-card" draggable="true" data-id="' + c.id + '" ondragstart="nbCabDragStart(event,' + c.id + ')">'
						+ '<div class="nb-cab-card-top"><span class="nb-cab-ctitle">' + esc(c.title) + '</span><span class="nb-cab-cage">' + ageStr(c.filed).toUpperCase() + '</span></div>'
						+ '<div class="nb-cab-cexc">' + esc(excerpt) + '</div>'
						+ '<div class="nb-cab-cbottom"><div class="nb-cab-ctags">' + tags + '</div>'
						+ '<div class="nb-cab-cacts">'
						+ '<button onclick="nbCabToPage(' + c.id + ')" title="Return to page">↩ TO PAGE</button>'
						+ '<button onclick="nbCabRoll(' + c.id + ')" title="Roll to Below Deck">→ ROLL</button>'
						+ '<button onclick="nbCabCopy(' + c.id + ')" title="Copy text">⧉</button>'
						+ '<button onclick="nbCabShred(' + c.id + ')" title="Shred">⌦</button>'
						+ '</div></div></div>';
				}).join('');
			}).catch(function () {});
		};
		function cabItemById(id) { return cabItems.filter(function (c) { return c.id === id; })[0]; }
		// drag a card onto a drawer to add that tag (re-tag / re-file)
		window.nbCabDragStart = function (e, id) {
			try { e.dataTransfer.setData('text/plain', String(id)); e.dataTransfer.effectAllowed = 'copy'; } catch (x) {}
		};
		window.nbCabDrop = function (e, tag) {
			e.preventDefault();
			var el = e.currentTarget; if (el) el.classList.remove('drag-over');
			var id = parseInt(e.dataTransfer.getData('text/plain'), 10);
			var c = cabItemById(id); if (!c || !tag) return;
			var tags = (c.tags || []).slice();
			if (tags.indexOf(tag) < 0) tags.push(tag); else return;   // already in that drawer
			fetch('/notebook/cabinet/' + id + '/retag', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ tags: tags }) })
				.then(function () { flash('re-tagged'); window.nbCabRender(); }).catch(function () {});
		};
		window.nbCabToPage = function (id) {
			var c = cabItemById(id); if (!c) return;
			page.value = (page.value.replace(/\n+$/, '') + (page.value.trim() ? '\n\n' : '') + c.body_md).replace(/^\n+/, '');
			saveNow(); refreshScrapBar();
			fetch('/notebook/cabinet/' + id + '/delete', { method: 'POST' }).then(function () { updateCabCount(); window.nbCabRender(); }).catch(function () {});
			flash('returned to page');
		};
		window.nbCabRoll = function (id) {
			var c = cabItemById(id); if (!c) return;
			var b = new URLSearchParams(); b.set('title', c.title || (c.body_md || '').split('\n')[0]);
			fetch(BELOW_ADD_URL, { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body: b.toString() })
				.then(function () { loadBelowDeck(); flash('rolled ↩'); }).catch(function () {});
		};
		window.nbCabCopy = function (id) {
			var c = cabItemById(id); if (!c) return;
			try { navigator.clipboard.writeText(c.body_md || c.title || ''); flash('copied'); } catch (e) {}
		};
		window.nbCabShred = function (id) {
			if (!confirm('Shred this filed scrap? (gone for good)')) return;
			fetch('/notebook/cabinet/' + id + '/delete', { method: 'POST' })
				.then(function () { updateCabCount(); window.nbCabRender(); }).catch(function () {});
		};

		// initial paint
		loadBelowDeck();
		refreshScrapBar();
		updateCabCount();
		fetch(PAGE_URL).then(function (r) { return r.json(); }).then(function (d) { paint(d.budget); }).catch(function () {});
	}

	// ---------- MEDIA RAILS (home stack) ----------
	function railShown(id) {
		var e = document.getElementById(id);
		return !!e && getComputedStyle(e).display !== 'none';
	}
	var RAIL_MAP = { yt: 'yt-player', music: 'ad-music-player' };
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
		nbReflectRails();
	};

	// Expand action for the slip's ⤢ button + Ctrl+Shift+N.
	window.nbOpenFullscreen = function () { window.location.href = '/notebook'; };

	// Home latch on the notebook — same server flag as the cockpit (/ani/home).
	window.nbHomeToggle = function () {
		var b = document.getElementById('ani-home-latch'); if (!b) return;
		var next = !b.classList.contains('on');
		b.classList.toggle('on', next);
		fetch('/ani/home', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ on: next }) }).catch(function () {});
	};
	function nbHomeInit() {
		var b = document.getElementById('ani-home-latch'); if (!b) return;
		fetch('/ani/home').then(function (r) { return r.json(); })
			.then(function (d) { b.classList.toggle('on', !!(d && d.home)); }).catch(function () {});
	}

	document.addEventListener('DOMContentLoaded', function () {
		initSlip();
		initFullscreen();
		nbHomeInit();
		if (document.getElementById('media-rails')) nbReflectRails();
		document.addEventListener('keydown', function (e) {
			// Ctrl+Shift+N → notebook fullscreen (browser may reserve this; ⤢ is the sure path).
			if ((e.ctrlKey || e.metaKey) && e.shiftKey && (e.key === 'N' || e.key === 'n')) {
				e.preventDefault(); window.nbOpenFullscreen();
			}
			// Ctrl+Shift+C → toggle the cabinet drawer (fullscreen only).
			if ((e.ctrlKey || e.metaKey) && e.shiftKey && (e.key === 'C' || e.key === 'c') && document.getElementById('nb-cabinet')) {
				e.preventDefault(); if (window.nbCabToggle) window.nbCabToggle();
			}
			// Esc closes the cabinet if open, otherwise returns to the cockpit.
			if (e.key === 'Escape' && document.getElementById('nb-page-input')) {
				var cabEl = document.getElementById('nb-cabinet');
				if (cabEl && cabEl.classList.contains('is-open')) { if (window.nbCabClose) window.nbCabClose(); return; }
				window.location.href = '/publish';
			}
		});
	});
})();
