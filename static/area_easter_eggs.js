/* area_easter_eggs.js
 *
 * Per-area easter eggs for Corporate / PennDOT / FDOT (§0a.3).
 * Activated by the body[data-area="..."] attribute set on area pages
 * and on sub-project pages whose parent area is one of these.
 *
 * Universal rules (§0a.3):
 *   - All animations <1s, position:absolute, pointer-events:none — never block clicks.
 *   - Frequencies 1-in-20 to 1-in-30 — surprise lands instead of going numb.
 *   - prefers-reduced-motion respected via CSS (animations collapse to instant or skip).
 *
 * All copy + frequencies live as constants below so tuning is one place.
 */
(function () {
	'use strict';

	if (window.AreaEasterEggsLoaded) return;
	window.AreaEasterEggsLoaded = true;

	var area = document.body && document.body.getAttribute('data-area');
	if (!area) return;

	// Skip animations entirely when reduced motion is preferred (CSS already
	// neutralises animations, but JS-driven inserts can be skipped too)
	var reducedMotion = window.matchMedia
		&& window.matchMedia('(prefers-reduced-motion: reduce)').matches;

	var FREQ = {
		corporate_stamp: 20,    // 1-in-N page loads, a card gets a CARGO/CLASSIFIED stamp
		fdot_palm:       30,    // 1-in-N area-page loads, palm tree drifts across
	};

	var STAMPS_CORPORATE = ['cd-cargo-stamp', 'cd-classified-stamp'];

	function rand(n) { return Math.floor(Math.random() * n); }

	// ---- Corporate: CARGO / CLASSIFIED stamp on a random sub-project card ----
	function maybeCorporateStamp() {
		if (reducedMotion) return;
		if (rand(FREQ.corporate_stamp) !== 0) return;
		var cards = document.querySelectorAll('.cd-subproject-card');
		if (!cards.length) return;
		var card = cards[rand(cards.length)];
		card.classList.add(STAMPS_CORPORATE[rand(STAMPS_CORPORATE.length)]);
	}

	// ---- Corporate: ✓ INVENTORIED flash on first task creation in a sub-project ----
	// Hook: command_deck_project.html dispatches a 'cd-task-created' event after a
	// successful task add. We listen and emit a brief overlay above the task list.
	function bindInventoriedFlash() {
		document.addEventListener('cd-task-created-first', function (ev) {
			var anchor = ev.detail && ev.detail.anchor;
			if (!anchor || reducedMotion) return;
			anchor.style.position = anchor.style.position || 'relative';
			var flash = document.createElement('div');
			flash.className = 'cd-inventoried-flash';
			flash.textContent = '✓ INVENTORIED';
			anchor.appendChild(flash);
			setTimeout(function () { if (flash.parentNode) flash.parentNode.removeChild(flash); }, 700);
		});
	}

	// ---- PennDOT: MILE MARKER N flash every 10th time entry on this area ----
	function maybePenndotMileMarker() {
		var lifetimeAttr = document.body.getAttribute('data-lifetime-entries');
		if (lifetimeAttr == null) return;  // only on area page
		var n = parseInt(lifetimeAttr, 10) || 0;
		if (n <= 0 || n % 10 !== 0) return;
		if (reducedMotion) return;
		var marker = document.createElement('div');
		marker.className = 'cd-mile-marker';
		marker.textContent = 'MILE MARKER ' + n;
		document.body.appendChild(marker);
		setTimeout(function () { if (marker.parentNode) marker.parentNode.removeChild(marker); }, 1600);
	}

	// ---- FDOT: hurricane-season pill (Jun 1 – Nov 30) ----
	function maybeFdotHurricanePill() {
		var now = new Date();
		var month = now.getMonth() + 1; // 1-12
		var inSeason = month >= 6 && month <= 11;
		if (!inSeason) return;
		var titleEl = document.querySelector('.cd-area-page-title-text')
			|| document.querySelector('.cd-area-page-title');
		if (!titleEl) return;
		var pill = document.createElement('span');
		pill.className = 'cd-fdot-hurricane-pill';
		pill.title = 'Atlantic hurricane season runs Jun 1 – Nov 30';
		pill.textContent = '🌀 SEASON ACTIVE';
		titleEl.parentNode.appendChild(pill);
	}

	// ---- FDOT: console.log signature ----
	function fdotConsoleSignature() {
		try {
			console.log(
				'%cFlorida Man arrives at the workstation. — aaronaiken.me',
				'color:#e07050;font-style:italic;font-family:serif;font-size:13px;'
			);
		} catch (e) { /* no-op */ }
	}

	// ---- FDOT: 1-in-N — palm tree silhouette drifts across area card ----
	function maybeFdotPalm() {
		if (reducedMotion) return;
		// Only on the area page (where the area-page-header exists)
		if (!document.querySelector('.cd-area-page-header')) return;
		if (rand(FREQ.fdot_palm) !== 0) return;
		var palm = document.createElement('div');
		palm.className = 'cd-fdot-palm';
		palm.setAttribute('aria-hidden', 'true');
		palm.textContent = '🌴';
		document.body.appendChild(palm);
		setTimeout(function () { if (palm.parentNode) palm.parentNode.removeChild(palm); }, 1300);
	}

	// ---- Dispatch ----

	if (area === 'corporate') {
		maybeCorporateStamp();
		bindInventoriedFlash();
	} else if (area === 'penndot') {
		maybePenndotMileMarker();
	} else if (area === 'fdot') {
		maybeFdotHurricanePill();
		fdotConsoleSignature();
		maybeFdotPalm();
	}
})();
