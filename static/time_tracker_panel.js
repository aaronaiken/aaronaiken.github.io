/* time_tracker_panel.js
 *
 * Cockpit floating timer panel — render, drag, picker, inline-create, Ctrl+K.
 * Spec: .kt/spec-time-tracking-phase-1.md §5.
 *
 * Subscribes to window.TimeTrackerCore for active-entry updates.
 * Exposes window.getTimerCmdItems() for the Ctrl+K palette in cockpit_modes.js.
 */
(function () {
	'use strict';

	if (window.TimeTrackerPanelLoaded) return;
	window.TimeTrackerPanelLoaded = true;

	var POS_KEY = 'timeTrackerPanelPos';
	var SAFE_INSET_PX = 100;

	var panel        = document.getElementById('ttp');
	if (!panel) return;
	var titlebar     = document.getElementById('ttp-titlebar');
	var summarySpan  = document.getElementById('ttp-summary');
	var groupsEl     = document.getElementById('ttp-groups');
	var formEl       = document.getElementById('ttp-form');
	var collapseBtn  = document.getElementById('ttp-collapse-btn');
	var closeBtn     = document.getElementById('ttp-close-btn');
	var newBtn       = document.getElementById('ttp-new-btn');
	var formArea     = document.getElementById('ttp-form-area');
	var formProject  = document.getElementById('ttp-form-project');
	var formDesc     = document.getElementById('ttp-form-desc');
	var formStart    = document.getElementById('ttp-form-start');
	var formCancel   = document.getElementById('ttp-form-cancel');
	var formNewWrap  = document.getElementById('ttp-form-new-title-wrap');
	var formNewTitle = document.getElementById('ttp-form-new-title');

	var state = {
		forced: false,
		collapsed: false,
		formOpen: false,
		formCreating: false,
		cachedProjects: null,
		activeEntries: [],
		editingId: null,
	};

	function escHtml(s) {
		var d = document.createElement('div');
		d.appendChild(document.createTextNode(s == null ? '' : String(s)));
		return d.innerHTML;
	}
	function fmt(secs) { return window.TimeTrackerCore.formatElapsed(secs); }

	// ---- Position persistence + off-screen guard ----

	function loadPos() {
		try {
			var raw = localStorage.getItem(POS_KEY);
			if (!raw) return null;
			var p = JSON.parse(raw);
			if (typeof p.x !== 'number' || typeof p.y !== 'number') return null;
			return p;
		} catch (e) { return null; }
	}
	function savePos() {
		var rect = panel.getBoundingClientRect();
		var data = { x: rect.left, y: rect.top, collapsed: state.collapsed };
		try { localStorage.setItem(POS_KEY, JSON.stringify(data)); } catch (e) {}
	}
	function applyPos(p) {
		if (!p) return;
		var w = panel.offsetWidth || 320;
		var h = panel.offsetHeight || 200;
		// Off-screen guard: at least SAFE_INSET_PX of panel must remain visible
		if (p.x + w < SAFE_INSET_PX ||
			p.x > window.innerWidth - SAFE_INSET_PX ||
			p.y + h < SAFE_INSET_PX ||
			p.y > window.innerHeight - SAFE_INSET_PX ||
			p.x < 0 || p.y < 0) {
			panel.style.left = '';
			panel.style.top = '';
			return;
		}
		panel.style.left = p.x + 'px';
		panel.style.top  = p.y + 'px';
		panel.style.right = 'auto';
		panel.style.bottom = 'auto';
	}

	// ---- Visibility ----

	function applyVisibility() {
		var shouldShow = state.forced || state.activeEntries.length > 0;
		panel.classList.toggle('ttp-open', shouldShow);
		panel.classList.toggle('ttp-collapsed', state.collapsed);
	}
	function show(forced) {
		if (forced) state.forced = true;
		applyVisibility();
	}
	function hide() {
		state.forced = false;
		state.formOpen = false;
		if (formEl) formEl.hidden = true;
		applyVisibility();
	}
	function toggleCollapse() {
		state.collapsed = !state.collapsed;
		applyVisibility();
		savePos();
	}

	// ---- Render active entries ----

	function renderActive(entries) {
		state.activeEntries = entries || [];
		var TTC = window.TimeTrackerCore;
		var totalSecs = state.activeEntries.reduce(function (a, e) { return a + TTC.elapsedSeconds(e); }, 0);

		if (summarySpan) {
			summarySpan.textContent = state.activeEntries.length === 0
				? ''
				: state.activeEntries.length + ' · ' + fmt(totalSecs);
		}

		// Group by area
		var groups = {};
		var order = [];
		state.activeEntries.forEach(function (e) {
			var key = e.area_id == null ? 'personal' : 'area-' + e.area_id;
			if (!groups[key]) {
				groups[key] = {
					name: e.area_title || 'Personal',
					color: e.area_color || '#d4880a',
					entries: [],
				};
				order.push(key);
			}
			groups[key].entries.push(e);
		});

		if (state.activeEntries.length === 0) {
			groupsEl.innerHTML = '<div class="ttp-empty">No active timers.</div>';
		} else {
			groupsEl.innerHTML = order.map(function (k) {
				var g = groups[k];
				return '<div class="ttp-group">' +
					'<div class="ttp-group-header" style="border-left-color:' + g.color + '">' + escHtml(g.name) + '</div>' +
					g.entries.map(function (e) {
						var elapsed = TTC.elapsedSeconds(e);
						var desc = e.description || e.project_title || '';
						var isEditing = state.editingId === e.id;
						return '<div class="ttp-row" data-id="' + e.id + '">' +
							'<span class="ttp-row-dot" style="background:' + g.color + '"></span>' +
							(isEditing
								? '<input class="ttp-row-desc-input" data-id="' + e.id + '" value="' + escHtml(desc) + '">'
								: '<span class="ttp-row-desc" data-id="' + e.id + '">' + escHtml(desc) + '</span>') +
							'<span class="ttp-row-elapsed">' + fmt(elapsed) + '</span>' +
							'<div class="ttp-row-actions">' +
								'<button class="ttp-row-stop" data-id="' + e.id + '" type="button">STOP</button>' +
								'<button class="ttp-row-delete" data-id="' + e.id + '" type="button" title="Delete">×</button>' +
							'</div>' +
						'</div>';
					}).join('') +
					'</div>';
			}).join('');
			bindRowActions();
			if (state.editingId != null) {
				var input = groupsEl.querySelector('.ttp-row-desc-input[data-id="' + state.editingId + '"]');
				if (input) { input.focus(); input.select(); }
			}
		}
		applyVisibility();
	}

	function bindRowActions() {
		groupsEl.querySelectorAll('.ttp-row-stop').forEach(function (b) {
			b.addEventListener('click', function () {
				b.disabled = true;
				window.TimeTrackerCore.stopTimer(b.getAttribute('data-id'));
			});
		});
		groupsEl.querySelectorAll('.ttp-row-delete').forEach(function (b) {
			b.addEventListener('click', function () {
				var id = b.getAttribute('data-id');
				if (!confirm('Delete this running timer? This cannot be undone.')) return;
				b.disabled = true;
				window.TimeTrackerCore.deleteTimer(id);
			});
		});
		groupsEl.querySelectorAll('.ttp-row-desc').forEach(function (el) {
			el.addEventListener('click', function () {
				state.editingId = parseInt(el.getAttribute('data-id'), 10);
				renderActive(state.activeEntries);
			});
		});
		groupsEl.querySelectorAll('.ttp-row-desc-input').forEach(function (input) {
			var id = input.getAttribute('data-id');
			var original = input.value;
			var done = false;
			function commit(save) {
				if (done) return;
				done = true;
				var v = input.value.trim();
				state.editingId = null;
				if (save && v !== original) {
					window.TimeTrackerCore.updateTimer(id, { description: v });
				} else {
					renderActive(state.activeEntries);
				}
			}
			input.addEventListener('blur', function () { commit(true); });
			input.addEventListener('keydown', function (e) {
				if (e.key === 'Enter') { e.preventDefault(); commit(true); }
				else if (e.key === 'Escape') { commit(false); }
			});
		});
	}

	// ---- New-timer form ----

	function fetchProjects() {
		return fetch('/time/projects', { credentials: 'same-origin' })
			.then(function (r) { return r.ok ? r.json() : { areas: [], personal: [] }; })
			.then(function (data) { state.cachedProjects = data; return data; })
			.catch(function () { return { areas: [], personal: [] }; });
	}
	function populateAreaPicker() {
		formArea.innerHTML = '';
		var data = state.cachedProjects || { areas: [], personal: [] };
		data.areas.forEach(function (a) {
			var opt = document.createElement('option');
			opt.value = 'area:' + a.id;
			opt.textContent = a.title;
			opt.dataset.areaSlug = a.slug;
			formArea.appendChild(opt);
		});
		if (data.personal && data.personal.length) {
			var opt = document.createElement('option');
			opt.value = 'personal';
			opt.textContent = '(Personal projects)';
			formArea.appendChild(opt);
		}
	}
	function populateProjectPicker() {
		formProject.innerHTML = '';
		var sel = formArea.value;
		var data = state.cachedProjects || { areas: [], personal: [] };
		if (sel === 'personal') {
			(data.personal || []).forEach(function (p) {
				var opt = document.createElement('option');
				opt.value = String(p.id);
				opt.textContent = p.title;
				formProject.appendChild(opt);
			});
		} else if (sel.indexOf('area:') === 0) {
			var areaId = parseInt(sel.split(':')[1], 10);
			var area = data.areas.find(function (a) { return a.id === areaId; });
			if (area) {
				(area.subprojects || []).forEach(function (p) {
					var opt = document.createElement('option');
					opt.value = String(p.id);
					opt.textContent = p.title;
					formProject.appendChild(opt);
				});
			}
			var createOpt = document.createElement('option');
			createOpt.value = '__create__';
			createOpt.textContent = '+ New sub-project under ' + (area ? area.title : 'this area');
			formProject.appendChild(createOpt);
		}
		handleProjectChange();
	}
	function handleProjectChange() {
		if (formProject.value === '__create__') {
			state.formCreating = true;
			if (formNewWrap) formNewWrap.hidden = false;
			if (formNewTitle) formNewTitle.focus();
		} else {
			state.formCreating = false;
			if (formNewWrap) formNewWrap.hidden = true;
		}
	}
	function openForm() {
		state.formOpen = true;
		state.forced = true;
		if (formEl) formEl.hidden = false;
		applyVisibility();
		fetchProjects().then(function () {
			populateAreaPicker();
			populateProjectPicker();
			if (formDesc) formDesc.focus();
		});
	}
	function closeForm() {
		state.formOpen = false;
		state.formCreating = false;
		if (formEl) formEl.hidden = true;
		if (formNewWrap) formNewWrap.hidden = true;
		applyVisibility();
	}
	function submitForm() {
		// §5.6 — don't fire actions before initial load resolves
		if (!window.TimeTrackerCore.isLoaded()) return;

		var description = (formDesc.value || '').trim();
		if (state.formCreating) {
			var areaSlug = formArea.options[formArea.selectedIndex].dataset.areaSlug;
			var newTitle = (formNewTitle.value || '').trim();
			if (!newTitle) { formNewTitle.focus(); return; }
			formStart.disabled = true;
			fetch('/command-deck/areas/' + areaSlug + '/subprojects/new', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				credentials: 'same-origin',
				body: JSON.stringify({ title: newTitle, tracking_enabled: true })
			})
				.then(function (r) { return r.json(); })
				.then(function (resp) {
					if (resp && resp.success) {
						return window.TimeTrackerCore.startTimer(resp.subproject.id, description);
					}
				})
				.then(function () {
					formStart.disabled = false;
					closeForm();
					fetchProjects();
				})
				.catch(function () { formStart.disabled = false; });
			return;
		}
		var pid = parseInt(formProject.value, 10);
		if (!pid) return;
		formStart.disabled = true;
		window.TimeTrackerCore.startTimer(pid, description).then(function (result) {
			formStart.disabled = false;
			if (result.ok) {
				formDesc.value = '';
				if (formNewTitle) formNewTitle.value = '';
				closeForm();
			} else if (result.status === 409) {
				alert('A timer is already running on that project.');
			}
		});
	}

	// ---- Drag ----

	var dragging = false, dragDX = 0, dragDY = 0;
	function onDragStart(e) {
		if (e.target.closest('button, input, select')) return;
		dragging = true;
		var rect = panel.getBoundingClientRect();
		var ev = e.touches ? e.touches[0] : e;
		dragDX = ev.clientX - rect.left;
		dragDY = ev.clientY - rect.top;
		panel.classList.add('ttp-dragging');
		document.addEventListener('mousemove', onDragMove);
		document.addEventListener('touchmove', onDragMove, { passive: false });
		document.addEventListener('mouseup', onDragEnd);
		document.addEventListener('touchend', onDragEnd);
		e.preventDefault();
	}
	function onDragMove(e) {
		if (!dragging) return;
		var ev = e.touches ? e.touches[0] : e;
		panel.style.left = (ev.clientX - dragDX) + 'px';
		panel.style.top  = (ev.clientY - dragDY) + 'px';
		panel.style.right = 'auto';
		panel.style.bottom = 'auto';
		if (e.cancelable) e.preventDefault();
	}
	function onDragEnd() {
		if (!dragging) return;
		dragging = false;
		panel.classList.remove('ttp-dragging');
		document.removeEventListener('mousemove', onDragMove);
		document.removeEventListener('touchmove', onDragMove);
		document.removeEventListener('mouseup', onDragEnd);
		document.removeEventListener('touchend', onDragEnd);
		savePos();
	}

	// ---- Init ----

	var savedPos = loadPos();
	if (savedPos) {
		state.collapsed = !!savedPos.collapsed;
		requestAnimationFrame(function () { applyPos(savedPos); });
	}

	if (titlebar)    titlebar.addEventListener('mousedown', onDragStart);
	if (titlebar)    titlebar.addEventListener('touchstart', onDragStart, { passive: false });
	if (collapseBtn) collapseBtn.addEventListener('click', toggleCollapse);
	if (closeBtn)    closeBtn.addEventListener('click', hide);
	if (newBtn)      newBtn.addEventListener('click', openForm);
	if (formCancel)  formCancel.addEventListener('click', closeForm);
	if (formStart)   formStart.addEventListener('click', submitForm);
	if (formArea)    formArea.addEventListener('change', populateProjectPicker);
	if (formProject) formProject.addEventListener('change', handleProjectChange);

	if (window.TimeTrackerCore) {
		window.TimeTrackerCore.subscribe(renderActive);
	}

	// ---- Ctrl+K palette entries (consumed by cockpit_modes.js) ----

	window.getTimerCmdItems = function () {
		var items = [];
		var entries = state.activeEntries;
		items.push({
			icon: '⏱',
			label: 'Start timer',
			hint: '',
			action: function () { show(true); openForm(); }
		});
		if (entries.length === 1) {
			items.push({
				icon: '■',
				label: 'Stop timer',
				hint: entries[0].project_title || entries[0].description || '',
				action: function () { window.TimeTrackerCore.stopTimer(entries[0].id); }
			});
		} else if (entries.length > 1) {
			items.push({
				icon: '■',
				label: 'Stop timer (open panel)',
				hint: entries.length + ' running',
				action: function () { show(true); }
			});
		}
		if (entries.length > 0) {
			items.push({
				icon: '✕',
				label: 'Stop all timers',
				hint: entries.length + ' running',
				action: function () {
					if (confirm('Stop all ' + entries.length + ' running timers?')) {
						window.TimeTrackerCore.stopAllTimers();
					}
				}
			});
			items.push({
				icon: '↻',
				label: 'Switch timer',
				hint: 'stop current, start new',
				action: function () {
					window.TimeTrackerCore.stopAllTimers().then(function () {
						show(true);
						openForm();
					});
				}
			});
		}
		return items;
	};
})();
