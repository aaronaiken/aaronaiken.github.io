/* command_deck_tabs.js
 * Work / Personal tab switcher + per-tab search filter.
 * Shared by command_deck_dashboard.html and command_deck_projects.html.
 *
 * Markup contract:
 *   <div class="cd-tabs"><button class="cd-tab" data-tab="work">…</button>…</div>
 *   <div class="cd-tab-pane" data-tab="work">…</div>
 *   <div class="cd-tab-pane" data-tab="personal" hidden>…</div>
 *   <input class="cd-tab-search" data-tab="work" />          (optional, per pane)
 *   <div class="cd-tab-empty" data-tab-empty="work" hidden>…</div> (optional, per pane)
 *   Searchable cards within a pane carry data-search="lower-cased text".
 *
 * Persistence: localStorage['commandDeckTab']. Default: 'work'.
 * Spec §4.2.
 */
(function () {
	'use strict';

	if (window.CommandDeckTabsLoaded) return;
	window.CommandDeckTabsLoaded = true;

	var STORAGE_KEY = 'commandDeckTab';
	var DEFAULT_TAB = 'work';

	var tabs = document.querySelectorAll('.cd-tab');
	var panes = document.querySelectorAll('.cd-tab-pane');
	if (!tabs.length || !panes.length) return;

	function getActive() {
		try {
			var v = localStorage.getItem(STORAGE_KEY);
			return v === 'work' || v === 'personal' ? v : DEFAULT_TAB;
		} catch (e) { return DEFAULT_TAB; }
	}
	function setActive(name) {
		try { localStorage.setItem(STORAGE_KEY, name); } catch (e) {}
	}

	function activate(name) {
		tabs.forEach(function (t) {
			var on = t.getAttribute('data-tab') === name;
			t.setAttribute('aria-selected', on ? 'true' : 'false');
		});
		panes.forEach(function (p) {
			p.hidden = p.getAttribute('data-tab') !== name;
		});
		// Reset search inputs in the newly-shown pane (per spec §8: "Clears on tab switch")
		var input = document.querySelector('.cd-tab-search[data-tab="' + name + '"]');
		if (input) {
			input.value = '';
			applyFilter(name, '');
		}
		setActive(name);
	}

	function applyFilter(tabName, query) {
		var pane = document.querySelector('.cd-tab-pane[data-tab="' + tabName + '"]');
		if (!pane) return;
		var q = (query || '').trim().toLowerCase();
		var cards = pane.querySelectorAll('[data-search]');
		var matched = 0;
		cards.forEach(function (card) {
			var hay = card.getAttribute('data-search') || '';
			var match = !q || hay.indexOf(q) !== -1;
			card.style.display = match ? '' : 'none';
			if (match) matched++;
		});
		var emptyEl = document.querySelector('.cd-tab-empty[data-tab-empty="' + tabName + '"]');
		if (emptyEl) emptyEl.hidden = !(q && matched === 0);
	}

	tabs.forEach(function (t) {
		t.addEventListener('click', function () {
			activate(t.getAttribute('data-tab'));
		});
	});

	document.querySelectorAll('.cd-tab-search').forEach(function (input) {
		var name = input.getAttribute('data-tab');
		input.addEventListener('input', function () { applyFilter(name, input.value); });
	});

	activate(getActive());
})();
