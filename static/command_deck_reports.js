// command_deck_reports.js — Phase 2 of time tracking.
// Drives the /command-deck/reports/ page: period nav, group toggle, entries
// rendering. Talks to /command-deck/reports/data — the endpoint returns all
// four totals shapes (by_area / by_project / by_day / by_timesheet) so
// switching the toggle is client-side only, no re-fetch.

(function () {
	'use strict';

	const PRESETS = ['today', 'this-week', 'this-month', 'custom'];
	const VALID_GROUPS = ['area', 'project', 'day', 'timesheet', 'category', 'mileage'];
	const TIMESHEET_DAY_CAP = 31;
	const MILEAGE_GROUP = 'mileage';

	const state = {
		preset: localStorage.getItem('reportsPeriod') || 'this-week',
		group: localStorage.getItem('reportsGroup') || 'area',
		start: null,   // 'YYYY-MM-DD' (custom mode only — server resolves for presets)
		end: null,     // 'YYYY-MM-DD' (custom mode only)
		data: null,    // last fetched payload
	};

	// ---- Date helpers ----

	function pad(n) { return String(n).padStart(2, '0'); }

	function fmtDate(d) {
		return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
	}

	function parseISODate(s) {
		const [y, m, d] = s.split('-').map(Number);
		return new Date(y, m - 1, d);
	}

	function startOfWeekSunday(d) {
		const day = d.getDay(); // Sun=0
		const result = new Date(d);
		result.setDate(d.getDate() - day);
		return result;
	}

	function addDays(d, n) {
		const r = new Date(d);
		r.setDate(d.getDate() + n);
		return r;
	}

	function startOfMonth(d) {
		return new Date(d.getFullYear(), d.getMonth(), 1);
	}

	function startOfNextMonth(d) {
		return new Date(d.getFullYear(), d.getMonth() + 1, 1);
	}

	function fmtSeconds(secs) {
		secs = Math.max(0, Math.round(secs || 0));
		const h = Math.floor(secs / 3600);
		const m = Math.floor((secs % 3600) / 60);
		if (h === 0 && m === 0) return secs > 0 ? '<1m' : '0:00';
		return `${h}:${pad(m)}`;
	}

	function fmtTime(iso) {
		// ISO UTC → HH:MM in viewer's local TZ. Browser handles ET conversion
		// since Aaron is in ET locally; on PA the server is whatever PA's TZ is.
		const dt = new Date(iso);
		return `${pad(dt.getHours())}:${pad(dt.getMinutes())}`;
	}

	function fmtDayLabel(iso) {
		const d = parseISODate(iso);
		const wk = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'][d.getDay()];
		return `${wk} ${d.getMonth() + 1}/${d.getDate()}`;
	}

	function fmtPeriodLabel() {
		if (!state.data) return '…';
		const start = parseISODate(state.data.meta.start);
		const end = addDays(parseISODate(state.data.meta.end), -1); // inclusive end for display
		const monthName = (m) => ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][m];
		if (state.preset === 'today') {
			return `${['Sun','Mon','Tue','Wed','Thu','Fri','Sat'][start.getDay()]} ${monthName(start.getMonth())} ${start.getDate()}, ${start.getFullYear()}`;
		}
		if (state.preset === 'this-month') {
			return `${monthName(start.getMonth())} ${start.getFullYear()}`;
		}
		// week / custom — show range
		if (start.getMonth() === end.getMonth()) {
			return `${monthName(start.getMonth())} ${start.getDate()} – ${end.getDate()}, ${start.getFullYear()}`;
		}
		return `${monthName(start.getMonth())} ${start.getDate()} – ${monthName(end.getMonth())} ${end.getDate()}, ${start.getFullYear()}`;
	}

	// ---- Period URL composition ----

	function buildQuery() {
		const params = new URLSearchParams();
		if (state.preset === 'custom' && state.start && state.end) {
			params.set('start', state.start);
			params.set('end', state.end);
		} else if (state.preset === 'custom') {
			// Custom selected but no dates yet — fall back to this-week
			params.set('period', 'this-week');
		} else {
			params.set('period', state.preset);
			if (state.start) params.set('start', state.start);
			if (state.end) params.set('end', state.end);
		}
		params.set('group', state.group);
		return params.toString();
	}

	// ---- Period nav (prev / next / jump) ----

	function shiftPeriod(direction) {
		// direction = -1 for prev, +1 for next.
		// Operate on the currently-rendered window, which the server returns
		// in meta.start / meta.end. Once shifted, we send explicit start/end
		// alongside the current preset so the server keeps the same shape.
		if (!state.data) return;
		const start = parseISODate(state.data.meta.start);
		const end = parseISODate(state.data.meta.end);

		if (state.preset === 'today' || state.preset === 'this-week' || state.preset === 'custom') {
			const days = Math.round((end - start) / 86400000);
			const newStart = addDays(start, direction * days);
			const newEnd = addDays(end, direction * days);
			state.start = fmtDate(newStart);
			state.end = fmtDate(newEnd);
		} else if (state.preset === 'this-month') {
			const ref = new Date(start.getFullYear(), start.getMonth() + direction, 1);
			state.start = fmtDate(startOfMonth(ref));
			state.end = fmtDate(startOfNextMonth(ref));
		}
		load();
	}

	function jumpToDate(iso) {
		if (!iso) return;
		const target = parseISODate(iso);
		if (state.preset === 'today') {
			state.start = iso;
			state.end = fmtDate(addDays(target, 1));
		} else if (state.preset === 'this-week' || state.preset === 'custom') {
			const sun = startOfWeekSunday(target);
			state.start = fmtDate(sun);
			state.end = fmtDate(addDays(sun, 7));
		} else if (state.preset === 'this-month') {
			state.start = fmtDate(startOfMonth(target));
			state.end = fmtDate(startOfNextMonth(target));
		}
		load();
	}

	// ---- Rendering ----

	function renderRollup() {
		const root = document.getElementById('reportsRollup');
		const data = state.data;
		const total = data.meta.totals_seconds || 0;

		if (!data.entries.length) {
			root.innerHTML = '';
			return;
		}

		let bucket;
		if (state.group === 'area') {
			bucket = data.totals.by_area;
			renderBucketRows(root, bucket, total, { label: 'area' });
		} else if (state.group === 'project') {
			bucket = data.totals.by_project;
			renderBucketRows(root, bucket, total, { label: 'project' });
		} else if (state.group === 'day') {
			renderDayRows(root, data.totals.by_day, total);
		} else if (state.group === 'timesheet') {
			renderTimesheet(root, data);
		} else if (state.group === 'category') {
			bucket = data.totals.by_category;
			renderBucketRows(root, bucket, total, { label: 'category' });
		}
	}

	function renderTimesheet(root, data) {
		const dayKeys = Object.keys(data.totals.by_day).sort();

		if (dayKeys.length > TIMESHEET_DAY_CAP) {
			root.innerHTML = `
				<div class="cd-reports-error">
					// Timesheet view is capped at ${TIMESHEET_DAY_CAP} days
					(this period spans ${dayKeys.length}). Switch to
					<button class="cd-reports-inline-link" data-switch-group="day">Day group</button>
					to see this range.
				</div>
			`;
			root.querySelector('.cd-reports-inline-link')
				.addEventListener('click', () => setGroup('day'));
			return;
		}

		const projects = Object.entries(data.totals.by_timesheet)
			.map(([id, info]) => ({ id, ...info }))
			.filter((p) => p.total > 0)
			.sort((a, b) => b.total - a.total);

		if (!projects.length) {
			root.innerHTML = '';
			return;
		}

		const header = `
			<thead>
				<tr>
					<th class="cd-timesheet-row-head">Project</th>
					${dayKeys.map((d) => `<th class="cd-num">${escapeHtml(timesheetDayHead(d))}</th>`).join('')}
					<th class="cd-num cd-timesheet-total-head">Total</th>
				</tr>
			</thead>
		`;

		const rows = projects.map((p) => {
			const stripe = p.area_color || 'var(--cd-amber-lo)';
			const cells = dayKeys.map((d) => {
				const secs = p.days[d] || 0;
				return `<td class="cd-num">${secs > 0 ? fmtSeconds(secs) : ''}</td>`;
			}).join('');
			return `
				<tr>
					<th scope="row" class="cd-timesheet-row-head">
						<span class="cd-reports-area-stripe" style="background:${stripe}"></span>
						${escapeHtml(p.title)}
						<span class="cd-reports-row-sub">${escapeHtml(p.area_title || '')}</span>
					</th>
					${cells}
					<td class="cd-num cd-timesheet-row-total">${fmtSeconds(p.total)}</td>
				</tr>
			`;
		}).join('');

		const footerCells = dayKeys.map((d) => {
			const secs = data.totals.by_day[d] || 0;
			return `<td class="cd-num">${secs > 0 ? fmtSeconds(secs) : ''}</td>`;
		}).join('');

		const totalSeconds = data.meta.totals_seconds || 0;

		root.innerHTML = `
			<div class="cd-timesheet-scroll">
				<table class="cd-timesheet-table">
					${header}
					<tbody>${rows}</tbody>
					<tfoot>
						<tr>
							<th scope="row" class="cd-timesheet-row-head">Daily total</th>
							${footerCells}
							<td class="cd-num cd-timesheet-row-total">${fmtSeconds(totalSeconds)}</td>
						</tr>
					</tfoot>
				</table>
			</div>
		`;
	}

	function timesheetDayHead(iso) {
		const d = parseISODate(iso);
		const wk = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'][d.getDay()];
		return `${wk} ${d.getMonth() + 1}/${d.getDate()}`;
	}

	function renderBucketRows(root, bucket, total, opts) {
		const rows = Object.entries(bucket)
			.map(([id, info]) => ({ id, ...info }))
			.filter((r) => r.seconds > 0)
			.sort((a, b) => b.seconds - a.seconds);

		if (!rows.length) {
			root.innerHTML = '';
			return;
		}

		const html = rows.map((r) => {
			const pct = total > 0 ? Math.round((r.seconds / total) * 100) : 0;
			const stripe = r.color || r.area_color || 'var(--cd-amber-lo)';
			const sub = (opts.label === 'project' && r.area_title)
				? `<span class="cd-reports-row-sub">${escapeHtml(r.area_title)}</span>`
				: '';
			return `
				<div class="cd-reports-row">
					<div class="cd-reports-row-stripe" style="background:${stripe}"></div>
					<div class="cd-reports-row-title">
						${escapeHtml(r.title || '—')}
						${sub}
					</div>
					<div class="cd-reports-row-bar">
						<div class="cd-reports-row-bar-fill" style="width:${pct}%; background:${stripe}"></div>
					</div>
					<div class="cd-reports-row-pct">${pct}%</div>
					<div class="cd-reports-row-duration cd-num">${fmtSeconds(r.seconds)}</div>
				</div>
			`;
		}).join('');
		root.innerHTML = html;
	}

	function renderDayRows(root, byDay, total) {
		const days = Object.entries(byDay).sort(); // ISO dates sort lexically
		const html = days.map(([day, secs]) => {
			const pct = total > 0 ? Math.round((secs / total) * 100) : 0;
			const fill = secs > 0 ? `width:${pct}%; background:var(--cd-amber);` : 'width:0;';
			return `
				<div class="cd-reports-row">
					<div class="cd-reports-row-stripe" style="background:var(--cd-amber-lo)"></div>
					<div class="cd-reports-row-title">${fmtDayLabel(day)}</div>
					<div class="cd-reports-row-bar">
						<div class="cd-reports-row-bar-fill" style="${fill}"></div>
					</div>
					<div class="cd-reports-row-pct">${pct}%</div>
					<div class="cd-reports-row-duration cd-num">${secs > 0 ? fmtSeconds(secs) : '—'}</div>
				</div>
			`;
		}).join('');
		root.innerHTML = html;
	}

	function renderEntries() {
		const tbody = document.getElementById('reportsEntriesBody');
		const data = state.data;
		if (!data.entries.length) {
			tbody.innerHTML = '<tr><td colspan="7" class="cd-reports-empty-cell">—</td></tr>';
			document.getElementById('reportsTotalDuration').textContent = '0:00';
			return;
		}

		const html = data.entries.map((e) => {
			const startLocal = fmtTime(e.started_at);
			const endLocal = fmtTime(e.ended_at);
			const day = fmtDayLabel(e.started_at.slice(0, 10));
			const stripe = e.area_color || 'var(--cd-amber-lo)';
			let context = '—';
			if (e.task_title) context = `task: ${escapeHtml(e.task_title)}`;
			else if (e.checklist_item_id) {
				// Phase 2.1: block-title as deliverable identity. Fall back
				// to plain "Checklist" when the block has no title.
				context = e.block_title
					? `Checklist: ${escapeHtml(e.block_title)}`
					: 'Checklist';
			}
			else if (e.meeting_id) {
				// Phase 5: meeting-scoped entry.
				context = e.meeting_title
					? `meeting: ${escapeHtml(e.meeting_title)}`
					: 'meeting';
			}
			else if (e.ticket_id) {
				// Tickets: TKT-NNNN (— title shown alongside if present)
				const tNum = e.ticket_number || ('TKT-' + e.ticket_id);
				context = e.ticket_title
					? `${tNum} — ${escapeHtml(e.ticket_title)}`
					: tNum;
			}
			const categoryCell = e.time_category_name
				? `<span class="cd-reports-cat-dot" style="background:${e.time_category_color || 'rgba(212,136,10,0.55)'}"></span>${escapeHtml(e.time_category_name)}`
				: '<span class="cd-text-dim">—</span>';
			const runningCls = e.running ? ' is-running' : '';
			const runningGlyph = e.running ? ' <span class="cd-reports-running-dot" title="still running"></span>' : '';
			// Click-to-edit on stopped entries; running entries stay static.
			const timeCell = e.running
				? `${startLocal} → ${endLocal}${runningGlyph}`
				: `<button type="button" class="cd-reports-time-edit" data-entry-id="${e.id}" data-started="${e.started_at}" data-ended="${e.ended_at}" title="Edit start/end time">${startLocal} → ${endLocal}</button>`;
			return `
				<tr class="cd-reports-entry${runningCls}" data-entry-id="${e.id}">
					<td>${day}</td>
					<td><span class="cd-reports-area-stripe" style="background:${stripe}"></span>${escapeHtml(e.area_title || '—')}</td>
					<td>${escapeHtml(e.project_title || '—')}</td>
					<td>${context}</td>
					<td>${categoryCell}</td>
					<td>${escapeHtml(e.description || '')}</td>
					<td>${timeCell}</td>
					<td class="cd-num">${fmtSeconds(e.duration_seconds)}</td>
				</tr>
			`;
		}).join('');
		tbody.innerHTML = html;

		document.getElementById('reportsTotalDuration').textContent = fmtSeconds(data.meta.totals_seconds);

		tbody.querySelectorAll('.cd-reports-time-edit').forEach((btn) => {
			btn.addEventListener('click', (ev) => {
				ev.stopPropagation();
				openTimeEditor(btn);
			});
		});
	}

	// Inline start/end time edit on stopped entries. Same UX as the
	// project-page today-list editor; here we re-fetch on save instead of
	// calling loadTodayTime().
	function _localTimeOf(iso) {
		if (!iso) return '';
		const d = new Date(iso);
		const pad = (n) => String(n).padStart(2, '0');
		return pad(d.getHours()) + ':' + pad(d.getMinutes());
	}
	function _combineLocalTime(originalIso, hhmm) {
		if (!hhmm) return null;
		const d = new Date(originalIso);
		const [h, m] = hhmm.split(':').map(Number);
		d.setHours(h, m, 0, 0);
		return d.toISOString();
	}
	function openTimeEditor(triggerBtn) {
		const entryId = triggerBtn.getAttribute('data-entry-id');
		const startedIso = triggerBtn.getAttribute('data-started');
		const endedIso = triggerBtn.getAttribute('data-ended');
		if (!startedIso || !endedIso) return;
		const wrap = document.createElement('span');
		wrap.className = 'cd-reports-time-editor';
		wrap.innerHTML =
			`<input type="time" class="cd-reports-time-input" data-which="start" value="${_localTimeOf(startedIso)}">` +
			`<span> – </span>` +
			`<input type="time" class="cd-reports-time-input" data-which="end" value="${_localTimeOf(endedIso)}">` +
			`<button type="button" class="cd-reports-time-save">SAVE</button>` +
			`<button type="button" class="cd-reports-time-cancel">CANCEL</button>`;
		triggerBtn.replaceWith(wrap);

		const cancel = () => load();
		const save = async () => {
			const sIn = wrap.querySelector('[data-which="start"]').value;
			const eIn = wrap.querySelector('[data-which="end"]').value;
			if (!sIn || !eIn) return;
			const newStarted = _combineLocalTime(startedIso, sIn);
			const newEnded = _combineLocalTime(endedIso, eIn);
			if (new Date(newEnded) < new Date(newStarted)) {
				alert('End must be after start.');
				return;
			}
			wrap.querySelector('.cd-reports-time-save').disabled = true;
			try {
				const r = await fetch(`/time/${entryId}/update`, {
					method: 'POST',
					headers: {'Content-Type': 'application/json'},
					body: JSON.stringify({started_at: newStarted, ended_at: newEnded}),
					credentials: 'same-origin',
				});
				if (r.ok) {
					load();
				} else {
					wrap.querySelector('.cd-reports-time-save').disabled = false;
					alert('Could not save.');
				}
			} catch (e) {
				wrap.querySelector('.cd-reports-time-save').disabled = false;
				alert('Could not save.');
			}
		};
		wrap.querySelector('.cd-reports-time-save').addEventListener('click', save);
		wrap.querySelector('.cd-reports-time-cancel').addEventListener('click', cancel);
		wrap.addEventListener('keydown', (ev) => {
			if (ev.key === 'Enter') { ev.preventDefault(); save(); }
			else if (ev.key === 'Escape') { ev.preventDefault(); cancel(); }
		});
		const firstInput = wrap.querySelector('[data-which="start"]');
		if (firstInput) firstInput.focus();
	}

	function renderHeader() {
		document.getElementById('reportsPeriodLabel').textContent = fmtPeriodLabel();

		document.querySelectorAll('.cd-reports-preset').forEach((b) => {
			b.classList.toggle('active', b.dataset.period === state.preset);
		});
		document.querySelectorAll('.cd-reports-group').forEach((b) => {
			b.classList.toggle('active', b.dataset.group === state.group);
		});
	}

	function renderPrivacyNote() {
		const note = document.getElementById('reportsPrivacyNote');
		const count = state.data?.meta?.hidden_private_count || 0;
		if (count > 0 && !state.data?.meta?.include_private) {
			document.getElementById('reportsPrivacyCount').textContent = count;
			note.hidden = false;
		} else {
			note.hidden = true;
		}
	}

	function renderEmpty() {
		const empty = document.getElementById('reportsEmpty');
		empty.hidden = (state.data && state.data.entries.length > 0);
	}

	function escapeHtml(s) {
		return String(s)
			.replace(/&/g, '&amp;')
			.replace(/</g, '&lt;')
			.replace(/>/g, '&gt;')
			.replace(/"/g, '&quot;');
	}

	// ---- Fetch + load ----

	async function load() {
		try {
			if (state.group === MILEAGE_GROUP) {
				await loadMileage();
				return;
			}
			const resp = await fetch(`/command-deck/reports/data?${buildQuery()}`);
			if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
			state.data = await resp.json();
			state.dataKind = 'time';
			renderHeader();
			renderEmpty();
			renderPrivacyNote();
			renderRollup();
			renderEntries();
		} catch (e) {
			console.error('reports load failed', e);
			document.getElementById('reportsRollup').innerHTML =
				`<div class="cd-reports-error">// failed to load report — ${escapeHtml(e.message)}</div>`;
		}
	}

	// Mileage view shares the period selector but pulls from a different
	// endpoint and has its own rollup + entries shape. We compute start/end
	// in JS (the time-reports endpoint normally resolves preset → dates on
	// the server, but the mileage endpoint just takes start/end directly).
	function resolveMileageDates() {
		const today = new Date();
		today.setHours(0, 0, 0, 0);
		if (state.start && state.end) {
			// state.end is exclusive in time-reports semantics; mileage filter
			// uses inclusive end. Subtract one day to flip it.
			const inclusive = addDays(parseISODate(state.end), -1);
			return { start: state.start, end: fmtDate(inclusive) };
		}
		if (state.preset === 'today') {
			return { start: fmtDate(today), end: fmtDate(today) };
		}
		if (state.preset === 'this-month') {
			const first = startOfMonth(today);
			const last = addDays(startOfNextMonth(today), -1);
			return { start: fmtDate(first), end: fmtDate(last) };
		}
		// default: this-week (Sun-Sat)
		const sun = startOfWeekSunday(today);
		const sat = addDays(sun, 6);
		return { start: fmtDate(sun), end: fmtDate(sat) };
	}

	async function loadMileage() {
		const dates = resolveMileageDates();
		const params = new URLSearchParams();
		if (dates.start) params.set('start', dates.start);
		if (dates.end) params.set('end', dates.end);
		// Privacy: the mileage endpoint defaults to excluding private projects;
		// the unlock state lives in localStorage same as time reports.
		if (localStorage.getItem('cdPrivateUnlocked') === '1') {
			params.set('include_private', '1');
		}
		const resp = await fetch(`/command-deck/mileage/data?${params.toString()}`, {
			credentials: 'same-origin',
		});
		if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
		const data = await resp.json();
		state.data = data;
		state.dataKind = 'mileage';
		// Inject meta.start/end so renderHeader's period label still works
		state.data.meta = state.data.meta || {};
		state.data.meta.start = dates.start;
		state.data.meta.end = fmtDate(addDays(parseISODate(dates.end), 1));  // exclusive for label math
		renderHeader();
		renderMileageEmpty(data);
		renderMileageRollup(data);
		renderMileageEntries(data);
	}

	function renderMileageEmpty(data) {
		const empty = document.getElementById('reportsEmpty');
		empty.hidden = (data.entries.length > 0);
		// Privacy note doesn't apply to mileage v1 (no hidden_private_count)
		document.getElementById('reportsPrivacyNote').hidden = true;
	}

	function fmtMiles(m) {
		const v = Math.round((m || 0) * 10) / 10;
		return v.toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 });
	}
	function fmtDollars(cents) {
		return '$' + (cents / 100).toLocaleString(undefined, {
			minimumFractionDigits: 2, maximumFractionDigits: 2,
		});
	}

	function renderMileageRollup(data) {
		const root = document.getElementById('reportsRollup');
		const totals = data.totals || {};
		if (!totals.count) {
			root.innerHTML = '';
			return;
		}
		// Project rollup — sorted by miles desc
		const rows = Object.values(totals.by_project || {})
			.sort((a, b) => b.miles - a.miles);
		const totalCents = totals.cents || 0;
		const totalMiles = totals.miles || 0;

		const html = `
			<div class="cd-reports-mileage-summary">
				<span>${totals.count} trip${totals.count === 1 ? '' : 's'}</span>
				<span>${fmtMiles(totalMiles)} mi</span>
				<span>${fmtDollars(totalCents)}</span>
				${totals.unsubmitted_cents > 0
					? `<span class="cd-mileage-summary-pending">${fmtMiles(totals.unsubmitted_miles)} mi · ${fmtDollars(totals.unsubmitted_cents)} pending</span>`
					: '<span class="cd-mileage-summary-clean">all submitted</span>'}
				<a href="/command-deck/mileage/" class="cd-btn ghost sm">OPEN MILEAGE</a>
				<button class="cd-btn sm" id="reportsMileageExport" type="button">EXPORT XLSX</button>
			</div>
			<table class="cd-reports-mileage-rollup">
				<thead>
					<tr><th>Project</th><th class="cd-num">Miles</th><th class="cd-num">$</th></tr>
				</thead>
				<tbody>
					${rows.map((r) => `
						<tr>
							<td>${escapeHtml(r.title || '(no project)')}</td>
							<td class="cd-num">${fmtMiles(r.miles)}</td>
							<td class="cd-num">${fmtDollars(r.cents)}</td>
						</tr>
					`).join('')}
				</tbody>
			</table>
		`;
		root.innerHTML = html;
		const expBtn = document.getElementById('reportsMileageExport');
		if (expBtn) expBtn.addEventListener('click', () => {
			const dates = resolveMileageDates();
			const qs = new URLSearchParams();
			if (dates.start) qs.set('start', dates.start);
			if (dates.end) qs.set('end', dates.end);
			if (localStorage.getItem('cdPrivateUnlocked') === '1') qs.set('include_private', '1');
			window.location.href = '/command-deck/mileage/export.xlsx?' + qs.toString();
		});
	}

	function renderMileageEntries(data) {
		const body = document.getElementById('reportsEntriesBody');
		// Replace the table headers when in mileage mode
		const thead = document.querySelector('.cd-reports-entries-table thead');
		thead.innerHTML = `
			<tr>
				<th>Date</th>
				<th>Project</th>
				<th>Trip</th>
				<th class="cd-num">Miles</th>
				<th class="cd-num">$</th>
				<th>Status</th>
				<th></th>
			</tr>`;
		const rows = data.entries.map((e) => {
			const trip = e.from_location && e.to_location
				? `${escapeHtml(e.from_location)} → ${escapeHtml(e.to_location)}${e.round_trip ? ' <span class="cd-mileage-roundtrip">↔</span>' : ''}`
				: escapeHtml(e.description || '');
			const status = e.is_submitted
				? '<span class="cd-mileage-status submitted">submitted</span>'
				: '<span class="cd-mileage-status pending">pending</span>';
			return `
				<tr data-id="${e.id}">
					<td>${escapeHtml(e.date)}</td>
					<td>${escapeHtml(e.project_title || '(no project)')}</td>
					<td class="cd-mileage-trip">${trip}</td>
					<td class="cd-num">${fmtMiles(e.miles)}</td>
					<td class="cd-num">${fmtDollars(e.reimbursement_cents)}</td>
					<td>${status}</td>
					<td><a class="cd-btn ghost sm" href="/command-deck/mileage/${e.id}/edit">EDIT</a></td>
				</tr>`;
		}).join('');
		body.innerHTML = rows || '<tr><td colspan="7" class="cd-reports-loading">No mileage in this range.</td></tr>';

		// Replace the existing time-totals tfoot
		const tfoot = document.querySelector('.cd-reports-entries-table tfoot tr');
		const totals = data.totals || {};
		tfoot.innerHTML = `
			<td colspan="3" class="cd-reports-total-label">Total</td>
			<td class="cd-num">${fmtMiles(totals.miles || 0)}</td>
			<td class="cd-num">${fmtDollars(totals.cents || 0)}</td>
			<td colspan="2"></td>
		`;
	}

	// ---- Wiring ----

	function setPreset(preset) {
		if (!PRESETS.includes(preset)) return;
		state.preset = preset;
		state.start = null;
		state.end = null;
		localStorage.setItem('reportsPeriod', preset);

		const customRow = document.getElementById('reportsCustom');
		if (customRow) customRow.hidden = (preset !== 'custom');

		// For custom, wait for the user to fill both inputs + click Apply
		// before we fetch — otherwise we'd render this-week's data under a
		// Custom-active toggle, which is confusing.
		if (preset === 'custom') {
			renderHeader();
			return;
		}
		load();
	}

	function applyCustomRange() {
		const startEl = document.getElementById('reportsCustomStart');
		const endEl = document.getElementById('reportsCustomEnd');
		if (!startEl.value || !endEl.value) return;
		if (startEl.value > endEl.value) return;
		state.start = startEl.value;
		// Server treats `end` as exclusive; the input is conceptually inclusive.
		const inclusive = parseISODate(endEl.value);
		state.end = fmtDate(addDays(inclusive, 1));
		load();
	}

	function resetEntriesTableChrome() {
		// Restore the time-mode thead/tfoot when leaving mileage mode.
		const thead = document.querySelector('.cd-reports-entries-table thead');
		thead.innerHTML = `
			<tr>
				<th>Day</th>
				<th>Area</th>
				<th>Project</th>
				<th>Scope</th>
				<th>Category</th>
				<th>Description</th>
				<th>Start → End</th>
				<th class="cd-num">Duration</th>
			</tr>`;
		const tfoot = document.querySelector('.cd-reports-entries-table tfoot tr');
		tfoot.innerHTML = `
			<td colspan="7" class="cd-reports-total-label">Total</td>
			<td class="cd-num" id="reportsTotalDuration">—</td>
		`;
	}

	function setGroup(group) {
		if (!VALID_GROUPS.includes(group)) return;
		const prevWasMileage = state.group === MILEAGE_GROUP;
		state.group = group;
		localStorage.setItem('reportsGroup', group);

		// Mileage mode pulls from a different endpoint; switching to/from it
		// requires a fresh fetch. The time tabs share one payload and just
		// re-render client-side.
		if (group === MILEAGE_GROUP || prevWasMileage) {
			if (prevWasMileage && group !== MILEAGE_GROUP) resetEntriesTableChrome();
			renderHeader();
			load();
			return;
		}
		renderHeader();
		renderRollup();
	}

	document.addEventListener('DOMContentLoaded', () => {
		document.getElementById('reportsPrev').addEventListener('click', () => shiftPeriod(-1));
		document.getElementById('reportsNext').addEventListener('click', () => shiftPeriod(+1));
		document.getElementById('reportsJump').addEventListener('change', (e) => jumpToDate(e.target.value));

		document.querySelectorAll('.cd-reports-preset').forEach((b) => {
			b.addEventListener('click', () => setPreset(b.dataset.period));
		});
		document.getElementById('reportsCustomApply').addEventListener('click', applyCustomRange);

		// Restore custom-row visibility when state.preset is already 'custom'
		if (state.preset === 'custom') {
			document.getElementById('reportsCustom').hidden = false;
		}
		document.querySelectorAll('.cd-reports-group').forEach((b) => {
			b.addEventListener('click', () => setGroup(b.dataset.group));
		});

		// Below Deck badge — same dot pattern as the dashboard.
		fetch('/below-deck/count').then((r) => r.json()).then((d) => {
			const el = document.getElementById('bdBadge');
			if (!el) return;
			const n = d.count || 0;
			if (n === 0) return;
			el.classList.add(n <= 3 ? 'green' : (n <= 6 ? 'amber' : 'red'));
		}).catch(() => {});

		load();
	});
})();
