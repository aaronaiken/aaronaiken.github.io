// command_deck_nav.js
// Phase 2.3 polish — MORE ▾ overflow menu in the CD header nav.
// Two jobs:
//   1. Mark the MORE trigger active when we're on a route that lives
//      inside the menu (currently /reports + /templates). Also marks
//      the matching <a> inside the menu so it pops when revealed.
//   2. Close any open <details.cd-nav-more> when the user clicks
//      outside it. <details> handles toggle + ESC for free; we just
//      add the outside-click behavior.

(function () {
	'use strict';

	var path = window.location.pathname;
	var menuRoutes = ['/command-deck/reports', '/command-deck/templates'];
	var underMenu = menuRoutes.some(function (r) { return path.indexOf(r) === 0; });

	if (underMenu) {
		document.querySelectorAll('.cd-nav-more-trigger').forEach(function (s) {
			s.classList.add('active');
		});
		document.querySelectorAll('.cd-nav-more-menu a').forEach(function (a) {
			var href = (a.getAttribute('href') || '').replace(/\/$/, '');
			if (href && path.indexOf(href) === 0) a.classList.add('active');
		});
	}

	document.addEventListener('click', function (ev) {
		document.querySelectorAll('details.cd-nav-more[open]').forEach(function (d) {
			if (!d.contains(ev.target)) d.removeAttribute('open');
		});
	});
})();
