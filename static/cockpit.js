		let cockpitAudioCtx;
		const cockpit = document.getElementById('main-cockpit');
		const tx = document.getElementById('status-input');
		const secretDisplay = document.getElementById('secret-comm');
		const charCount = document.getElementById('char-count');

		// ---- HUD ----
		function updateHUD() {
			const length = tx.value.length;
			charCount.innerText = length;
			const intensity = Math.min(length / 280, 1);
			tx.style.boxShadow = `0 0 ${intensity * 24}px rgba(212,136,10,${intensity * 0.35})`;
			if (length > 250) {
				tx.classList.add('redline');
				charCount.style.color = "#cc3322";
			} else {
				tx.classList.remove('redline');
				charCount.style.color = "var(--muted)";
			}
			// Save draft to localStorage on every keystroke
			if (tx.value.trim()) {
				localStorage.setItem('cockpit-draft', tx.value);
			} else {
				localStorage.removeItem('cockpit-draft');
			}
		}

		// ---- DRAFT RESTORE ----
		function initDraft() {
			const draft = localStorage.getItem('cockpit-draft');
			if (draft) {
				tx.value = draft;
				updateHUD();
				const msg = document.getElementById('draft-restored-msg');
				msg.style.display = 'block';
				setTimeout(() => {
					msg.style.transition = 'opacity 1s ease';
					msg.style.opacity = '0';
					setTimeout(() => { msg.style.display = 'none'; msg.style.opacity = '1'; }, 1000);
				}, 2500);
			}
		}

		// Clear draft on successful publish
		document.getElementById('status-form').addEventListener('submit', () => {
			localStorage.removeItem('cockpit-draft');
		});

		// ---- WEATHER ----
		function initWeather() {
			const display = document.getElementById('weather-display');
			if (!display) return;
			// Paint cached value immediately so the SHIELDS area isn't blank
			// while we wait on the network (or while wttr.in is flaky).
			const cached = localStorage.getItem('cockpit_weather_last');
			if (cached) display.textContent = '· ' + cached;
			fetch('/ani/weather')
				.then(r => r.json())
				.then(data => {
					if (!data.weather) return; // keep cached value on null
					// wttr.in format: "City: ☀️ +72°F"
					let w = data.weather;
					if (w.includes(':')) w = w.split(':').slice(1).join(':').trim();
					w = w.replace(/Â/g, '').replace(/\s+/g, ' ').trim();
					display.textContent = '· ' + w;
					localStorage.setItem('cockpit_weather_last', w);
				})
				.catch(() => {}); // keep cached value on fetch error
		}

		// ---- BELOW DECK BADGE ----
		function initBelowDeckBadge() {
			fetch('/below-deck/count')
				.then(r => r.json())
				.then(data => {
					const count = data.count || 0;
					const badge = document.getElementById('below-deck-badge');
					const dot = document.getElementById('below-deck-dot');
					if (count === 0) {
						badge.style.display = 'none';
						return;
					}
					badge.style.display = 'inline-flex';
					badge.style.alignItems = 'center';
					if (count <= 3) {
						dot.style.background = '#4dbb6a';
						dot.style.color = '#4dbb6a';
					} else if (count <= 6) {
						dot.style.background = '#d4880a';
						dot.style.color = '#d4880a';
					} else {
						dot.style.background = '#cc3322';
						dot.style.color = '#cc3322';
					}
				})
				.catch(() => {});
		}

		// ---- SHIELD ----
		function updateSignalIntegrity() {
			const start = Date.now();
			fetch('/static/comms.txt', { method: 'HEAD', cache: 'no-store' })
				.then(() => {
					const latency = Date.now() - start;
					const fill = document.getElementById('shield-fill');
					let integrity = Math.max(10, 100 - (latency / 5));
					fill.style.width = integrity + '%';
					const scanSpeed = Math.max(2, (latency / 50));
					document.body.style.setProperty('--scan-speed', `${scanSpeed}s`);
					if (latency > 300) {
						fill.style.background = '#cc3322';
						document.body.style.filter = "contrast(1.2) brightness(0.8)";
					} else {
						fill.style.background = integrity < 50 ? '#d4880a' : '#4dbb6a';
						document.body.style.filter = "none";
					}
				});
		}

		setInterval(updateSignalIntegrity, 30000);
		updateSignalIntegrity();

		// ---- SECRET COMMS ----
		const availableComms = window.COCKPIT_COMMS || [];

		function showSecret() {
			window.getSelection().removeAllRanges();
			if ("vibrate" in navigator) navigator.vibrate([30, 80]);
			playCockpitSound('transmission');

			let msg = availableComms[Math.floor(Math.random() * availableComms.length)];
			if (Math.random() < 0.3) { msg = msg.replace(/Aaron/gi, "Daddy"); }

			const textTarget = document.getElementById('secret-text');
			textTarget.innerText = msg;
			const cursor = document.createElement('span');
			cursor.className = 'terminal-cursor';
			textTarget.appendChild(cursor);

			secretDisplay.style.display = 'flex';
			setTimeout(() => { secretDisplay.style.opacity = "1"; }, 10);
			setTimeout(() => {
				window.addEventListener('click', closeSecret, { once: true });
				window.addEventListener('touchstart', closeSecret, { once: true });
			}, 300);
		}

		function closeSecret() {
			secretDisplay.style.opacity = "0";
			setTimeout(() => { secretDisplay.style.display = 'none'; }, 500);
		}

		let secretTimer;
		function startSecret() { secretTimer = setTimeout(showSecret, 1500); }
		function endSecret() { clearTimeout(secretTimer); }
		function triggerDesktopSecret() { showSecret(); }

		// ---- ANI PILL HANDLERS ----
		let aniPressTimer = null;

		function startAni(e) {
			e.preventDefault();
			aniPressTimer = setTimeout(function() {
				aniPressTimer = null;
				aniToggle();
			}, 600);
		}

		function endAni(e) {
			e.preventDefault();
			if (aniPressTimer) {
				clearTimeout(aniPressTimer);
				aniPressTimer = null;
			}
		}

		// ---- TEXT HELPERS ----
		function wrapText(before, after) {
			const start = tx.selectionStart, end = tx.selectionEnd;
			const selected = tx.value.substring(start, end);
			tx.value = tx.value.substring(0, start) + before + selected + after + tx.value.substring(end);
			updateHUD(); tx.focus();
			tx.setSelectionRange(start + before.length, start + before.length + selected.length);
		}

		async function smartURL() {
			const start = tx.selectionStart, end = tx.selectionEnd;
			const selected = tx.value.substring(start, end) || "link text";
			try {
				const clipboard = await navigator.clipboard.readText();
				tx.value = tx.value.substring(0, start) + `[${selected}](${clipboard})` + tx.value.substring(end);
			} catch (e) { wrapText('[', '](url)'); }
			updateHUD();
		}

		function insertText(val) {
			playChirp(440, 'sine');
			tx.value += (tx.value.length > 0 && !tx.value.endsWith(' ') ? ' ' : '') + val;
			updateHUD(); tx.focus();
		}

		function insertGratefulLog() {
			const now = new Date();
			const opts = { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric', timeZone: 'America/New_York' };
			const dateStr = now.toLocaleDateString('en-US', opts);
			// Pull the current weather icon from the cockpit header.
			// `#weather-display` renders like "· ☀️ +57°F" — strip the bullet and grab
			// everything before the temp sign. Fall back to ☀️ if it hasn't loaded yet.
			let icon = '☀️';
			const wd = document.getElementById('weather-display');
			if (wd && wd.textContent) {
				const m = wd.textContent.replace(/^[·\s]+/, '').match(/^([^+\-0-9]+)/);
				if (m && m[1].trim()) icon = m[1].trim();
			}
			const template = `${icon} **Grateful Log for ${dateStr}**\n1. \n2. \n3. `;
			if (tx.value.trim().length > 0) {
				if (!confirm("Replace current draft with grateful-log template?")) return;
			}
			tx.value = template;
			updateHUD();
			tx.focus();
			// Place caret at end (right after "1. ") so he can start typing item 1.
			const caret = template.indexOf('1. ') + 3;
			tx.setSelectionRange(caret, caret);
		}

		// Markdown shortcuts on the status textarea: Cmd/Ctrl+B / +I / +K
		tx.addEventListener('keydown', (e) => {
			if (!(e.metaKey || e.ctrlKey) || e.altKey) return;
			const k = e.key.toLowerCase();
			if (k === 'b') { e.preventDefault(); wrapText('**', '**'); }
			else if (k === 'i') { e.preventDefault(); wrapText('*', '*'); }
			else if (k === 'k') { e.preventDefault(); smartURL(); }
		});

		function toggleTheme() {}

		// ---- HYPERSPACE SUBMIT ----
		let cockpitSubmitting = false;
		document.getElementById('status-form').addEventListener('submit', (e) => {
			e.preventDefault();
			// Guard: drop repeat submits (double-tap, Enter spam) once one is
			// already in flight — prevents accidental duplicate transmissions.
			if (cockpitSubmitting) return;
			// Guard: a status needs text or an image. Never transmit a blank
			// post — an empty <content> breaks the Atom feed for micro.blog.
			// Mirrors the server-side check in blueprints/cockpit.py.
			const txt = document.getElementById('status-input').value.trim();
			const hasImage = document.getElementById('image-upload').files.length > 0;
			if (!txt && !hasImage) {
				const input = document.getElementById('status-input');
				input.placeholder = 'Nothing to transmit — add text or an image.';
				input.focus();
				return;
			}
			cockpitSubmitting = true;
			const btn = document.getElementById('publish-btn');
			if (btn) btn.disabled = true;
			if ("vibrate" in navigator) navigator.vibrate([30, 50, 30]);
			cockpit.classList.add('hyperspace');
			setTimeout(() => e.target.submit(), 450);
		});

		// ---- SOUNDS ----
		function playCockpitSound(type) {
			if (!cockpitAudioCtx) cockpitAudioCtx = new (window.AudioContext || window.webkitAudioContext)();
			if (cockpitAudioCtx.state === 'suspended') cockpitAudioCtx.resume();
			const osc = cockpitAudioCtx.createOscillator();
			const gain = cockpitAudioCtx.createGain();
			osc.connect(gain);
			gain.connect(cockpitAudioCtx.destination);
			const now = cockpitAudioCtx.currentTime;
			if (type === 'transmission') {
				osc.type = 'square';
				osc.frequency.setValueAtTime(1600, now);
				osc.frequency.exponentialRampToValueAtTime(440, now + 0.15);
				const osc2 = cockpitAudioCtx.createOscillator();
				const gain2 = cockpitAudioCtx.createGain();
				osc2.type = 'sine';
				osc2.frequency.setValueAtTime(880, now);
				osc2.frequency.exponentialRampToValueAtTime(110, now + 0.2);
				osc2.connect(gain2); gain2.connect(cockpitAudioCtx.destination);
				gain2.gain.setValueAtTime(0.05, now);
				gain2.gain.exponentialRampToValueAtTime(0.0001, now + 0.2);
				osc2.start(now); osc2.stop(now + 0.2);
				gain.gain.setValueAtTime(0.05, now);
				gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.15);
			} else if (type === 'payload') {
				osc.type = 'triangle';
				osc.frequency.setValueAtTime(150, now);
				osc.frequency.exponentialRampToValueAtTime(40, now + 0.15);
				gain.gain.setValueAtTime(0.15, now);
			} else if (type === 'success') {
				osc.type = 'sine';
				osc.frequency.setValueAtTime(440, now);
				osc.frequency.setValueAtTime(880, now + 0.08);
				gain.gain.setValueAtTime(0.1, now);
			}
			gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.2);
			osc.start(now); osc.stop(now + 0.2);
		}

		function playChirp(freq, type) {
			if (!cockpitAudioCtx) cockpitAudioCtx = new (window.AudioContext || window.webkitAudioContext)();
			if (cockpitAudioCtx.state === 'suspended') cockpitAudioCtx.resume();
			const o = cockpitAudioCtx.createOscillator();
			const g = cockpitAudioCtx.createGain();
			o.type = type; o.frequency.value = freq;
			o.connect(g); g.connect(cockpitAudioCtx.destination);
			g.gain.setValueAtTime(0.04, cockpitAudioCtx.currentTime);
			g.gain.exponentialRampToValueAtTime(0.0001, cockpitAudioCtx.currentTime + 0.08);
			o.start(); o.stop(cockpitAudioCtx.currentTime + 0.08);
		}

		// ---- PAYLOAD ----
		function updatePayloadStatus() {
			const fileInput = document.getElementById('image-upload');
			const label = document.getElementById('payload-label');
			const status = document.getElementById('payload-name');
			if (fileInput.files.length > 0) {
				label.style.borderColor = 'var(--secret-neon)';
				label.style.color = 'var(--secret-neon)';
				label.innerText = 'PAYLOAD READY';
				status.style.display = 'inline';
				status.style.animation = 'blink 0.5s step-end 3';
				document.getElementById('alt-text-row').style.display = 'flex';
			}
		}

		// Ask Claude to suggest alt text for the attached image. Fills the input;
		// you review/edit before publishing. Nothing auto-applies.
		function suggestAltText() {
			const fileInput = document.getElementById('image-upload');
			const input = document.getElementById('alt-text-input');
			const btn = document.getElementById('alt-suggest-btn');
			if (!fileInput.files.length) return;
			const fd = new FormData();
			fd.append('image', fileInput.files[0]);
			btn.disabled = true;
			btn.textContent = '✨ …';
			fetch('/publish/alt-suggest', { method: 'POST', body: fd })
				.then(r => r.json())
				.then(data => {
					if (!data.ok || !data.alt) throw new Error(data.error || 'failed');
					input.value = data.alt;
					input.focus();
					btn.textContent = '✨ SUGGEST';
					btn.disabled = false;
				})
				.catch(() => {
					btn.textContent = 'RETRY';
					btn.disabled = false;
				});
		}

		// ---- TASKS ----
		let _lastCompletedTitle = '';
		let _lastCompletedId = '';

		function addTask() {
			const input = document.getElementById('task-input');
			const btn = document.getElementById('task-add-btn');
			const title = input.value.trim();
			if (!title) return;
			input.value = '';
			btn.disabled = true;
			btn.textContent = 'LOGGING...';
			btn.className = 'tasks-add-btn is-working';
			playChirp(660, 'square');
			const fd = new FormData();
			fd.append('title', title);
			fetch('/tasks/add', { method: 'POST', body: fd })
				.then(r => r.json())
				.then(data => {
					if (!data.ok) throw new Error(data.error);
					prependTaskItem(data.task);
					removeEmptyMsg();
					playChirp(880, 'sine');
					btn.textContent = 'LOGGED ✓';
					btn.className = 'tasks-add-btn is-success';
					setTimeout(() => {
						btn.textContent = '+ LOG';
						btn.className = 'tasks-add-btn';
						btn.disabled = false;
						input.focus();
					}, 1800);
				})
				.catch(() => {
					input.value = title;
					playChirp(220, 'sawtooth');
					btn.textContent = 'FAILED — TRY AGAIN';
					btn.className = 'tasks-add-btn is-error';
					setTimeout(() => {
						btn.textContent = '+ LOG';
						btn.className = 'tasks-add-btn';
						btn.disabled = false;
						input.focus();
					}, 2500);
				});
		}

		function completeTask(id, title) {
			const li = document.querySelector(`.task-item[data-id="${id}"]`);
			if (!li) return;
			playChirp(550, 'sine');
			_lastCompletedTitle = title;
			_lastCompletedId = id;
			const fd = new FormData();
			fd.append('id', id);
			fetch('/tasks/complete', { method: 'POST', body: fd })
				.then(r => r.json())
				.then(data => {
					if (!data.ok) throw new Error(data.error);
					li.classList.add('is-complete');
					li.querySelector('.task-check').textContent = '✓';
					li.querySelector('.task-check').style.cursor = 'default';
					li.querySelector('.task-check').onclick = null;
					showLogPrompt();
					playChirp(880, 'sine');
				})
				.catch(() => playChirp(220, 'sawtooth'));
		}

		function deleteTask(id) {
			const li = document.querySelector(`.task-item[data-id="${id}"]`);
			if (!li) return;
			const fd = new FormData();
			fd.append('id', id);
			fetch('/tasks/delete', { method: 'POST', body: fd })
				.then(r => r.json())
				.then(data => {
					if (!data.ok) throw new Error(data.error);
					li.style.opacity = '0';
					li.style.transition = 'opacity 0.3s';
					setTimeout(() => li.remove(), 300);
					playChirp(330, 'triangle');
				})
				.catch(() => playChirp(220, 'sawtooth'));
		}

		function prependTaskItem(task) {
			const list = document.getElementById('tasks-list');
			const li = document.createElement('li');
			li.className = 'task-item';
			li.dataset.id = task.id;
			li.dataset.title = task.title;
			li.dataset.blog = '';
			li.innerHTML = `
				<button class="task-check" onclick="completeTask('${task.id}', '${task.title.replace(/'/g, "\\'")}')" title="Mark complete"></button>
				<span class="task-title">${escapeHtml(task.title)}<a class="task-post-link" target="_blank" rel="noopener" title="Linked blog post" hidden>post ↗</a></span>
				<button class="task-link" onclick="linkTaskBlog('${task.id}')" title="Link a blog post">🔗</button>
				<button class="task-delete" onclick="deleteTask('${task.id}')" title="Delete">✕</button>
			`;
			const divider = list.querySelector('.tasks-divider');
			divider ? list.insertBefore(li, divider) : list.prepend(li);
		}

		function removeEmptyMsg() {
			const msg = document.getElementById('tasks-empty-msg');
			if (msg) msg.remove();
		}

		function showLogPrompt() {
			document.getElementById('task-log-prompt').classList.add('visible');
		}

		function dismissLogPrompt() {
			document.getElementById('task-log-prompt').classList.remove('visible');
			_lastCompletedTitle = '';
		}

		function logAsStatus() {
			const statusInput = document.getElementById('status-input');
			statusInput.value = `✅ Shipped: ${_lastCompletedTitle}`;
			// Tell the backend to auto-link this task to the status update once published.
			const lt = document.getElementById('link-task-id');
			if (lt) lt.value = _lastCompletedId || '';
			updateHUD();
			statusInput.focus();
			dismissLogPrompt();
			statusInput.scrollIntoView({ behavior: 'smooth', block: 'center' });
		}

		function logAsBlogDraft() {
			const draft = `---\ntitle: "${_lastCompletedTitle}"\ndate: ${new Date().toISOString().split('T')[0]}\nlayout: post\nauthor: aaron\nshipped_from: "${_lastCompletedTitle}"\n---\n\n`;
			navigator.clipboard.writeText(draft)
				.then(() => {
					const btn = document.querySelector('.task-log-btn:nth-child(2)');
					if (btn) { btn.textContent = 'COPIED ✓'; setTimeout(() => btn.textContent = 'BLOG DRAFT', 2000); }
				})
				.catch(() => {});
			dismissLogPrompt();
		}

		// Link a published blog post to a Mission Log task (task → post). The
		// reverse link (the public "shipped from" note on the post) comes from
		// the post's `shipped_from` front-matter — pre-filled by BLOG DRAFT for
		// new posts; add it by hand on an existing post.
		function linkTaskBlog(id) {
			const li = document.querySelector(`.task-item[data-id="${id}"]`);
			const current = li ? (li.dataset.blog || '') : '';
			const url = prompt('Published URL for this task — blog post or status update (blank to unlink):', current);
			if (url === null) return; // cancelled
			const trimmed = url.trim();
			const fd = new FormData();
			fd.append('id', id);
			fd.append('blog_url', trimmed);
			fetch('/tasks/link-blog', { method: 'POST', body: fd })
				.then(r => r.json())
				.then(data => {
					if (!data.ok) throw new Error(data.error || 'failed');
					if (li) {
						li.dataset.blog = trimmed;
						li.classList.toggle('has-blog', !!trimmed);
						const link = li.querySelector('.task-post-link');
						if (link) {
							link.href = trimmed;
							if (trimmed) link.removeAttribute('hidden');
							else link.setAttribute('hidden', '');
						}
					}
					playChirp(trimmed ? 880 : 440, 'sine');
				})
				.catch(() => playChirp(220, 'sawtooth'));
		}

		function logLinkPost() {
			if (_lastCompletedId) linkTaskBlog(_lastCompletedId);
			dismissLogPrompt();
		}

		function escapeHtml(str) {
			return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
		}

		document.getElementById('task-input').addEventListener('keydown', (e) => {
			if (e.key === 'Enter') { e.preventDefault(); addTask(); }
		});

		updateHUD();
		initDraft();
		initWeather();
		initBelowDeckBadge();

		// ---- RESTORE MISSION LOG COLLAPSE STATE ----
		if (localStorage.getItem('cockpit-tasks-collapsed') === '1') {
			document.getElementById('tasks-body').classList.add('is-collapsed');
			document.getElementById('tasks-arrow').classList.add('is-collapsed');
		}
		if (localStorage.getItem('cockpit-comms-collapsed') === '1') {
			var _cb = document.getElementById('comms-body'), _ca = document.getElementById('comms-arrow');
			if (_cb) _cb.classList.add('is-collapsed');
			if (_ca) _ca.classList.add('is-collapsed');
		}
		if (localStorage.getItem('cockpit-quickinsert-collapsed') === '1') {
			var _qb = document.getElementById('quickinsert-body'), _qa = document.getElementById('quickinsert-arrow');
			if (_qb) _qb.classList.add('is-collapsed');
			if (_qa) _qa.classList.add('is-collapsed');
		}
		if (localStorage.getItem('cockpit-focus') === '1') {
			document.body.classList.add('cockpit-focus');
			var _fb = document.getElementById('focus-btn');
			if (_fb) _fb.classList.add('is-active');
		}
		if (localStorage.getItem('cockpit-nav-newtab') === '1' && typeof applyNavNewTab === 'function') {
			applyNavNewTab(true);
		}

		// ---- COLLAPSIBLE ----
		function toggleTasks() {
			const body = document.getElementById('tasks-body');
			const arrow = document.getElementById('tasks-arrow');
			const isCollapsed = arrow.classList.contains('is-collapsed');
			body.classList.toggle('is-collapsed');
			arrow.classList.toggle('is-collapsed');
			localStorage.setItem('cockpit-tasks-collapsed', isCollapsed ? '0' : '1');
		}

		function toggleComms() {
			const body = document.getElementById('comms-body');
			const arrow = document.getElementById('comms-arrow');
			if (!body || !arrow) return;
			const isCollapsed = arrow.classList.contains('is-collapsed');
			body.classList.toggle('is-collapsed');
			arrow.classList.toggle('is-collapsed');
			localStorage.setItem('cockpit-comms-collapsed', isCollapsed ? '0' : '1');
		}

		function toggleQuickInsert() {
			const body = document.getElementById('quickinsert-body');
			const arrow = document.getElementById('quickinsert-arrow');
			if (!body || !arrow) return;
			const isCollapsed = arrow.classList.contains('is-collapsed');
			body.classList.toggle('is-collapsed');
			arrow.classList.toggle('is-collapsed');
			localStorage.setItem('cockpit-quickinsert-collapsed', isCollapsed ? '0' : '1');
		}

		// Focus mode — collapse everything but the transmission box (a lightweight 'work mode').
		function toggleFocus() {
			const on = document.body.classList.toggle('cockpit-focus');
			const btn = document.getElementById('focus-btn');
			if (btn) btn.classList.toggle('is-active', on);
			localStorage.setItem('cockpit-focus', on ? '1' : '0');
		}

		// ============================================================
		// LAYOUT PRESETS + SETTINGS
		// ============================================================
		var COCKPIT_SECTIONS = [
			{ key: 'quickinsert', body: 'quickinsert-body', arrow: 'quickinsert-arrow', store: 'cockpit-quickinsert-collapsed', label: 'Quick Insert' },
			{ key: 'comms',       body: 'comms-body',       arrow: 'comms-arrow',        store: 'cockpit-comms-collapsed',       label: 'Comms Log' },
			{ key: 'tasks',       body: 'tasks-body',       arrow: 'tasks-arrow',         store: 'cockpit-tasks-collapsed',        label: 'Mission Log' },
			{ key: 'scratch',     body: 'scratch-body',     arrow: 'scratch-arrow',       store: 'cockpit-scratch-collapsed',      label: 'Scratch' }
		];

		function cockpitSetSectionCollapsed(sec, collapsed) {
			var b = document.getElementById(sec.body), a = document.getElementById(sec.arrow);
			if (b) b.classList.toggle('is-collapsed', collapsed);
			if (a) a.classList.toggle('is-collapsed', collapsed);
			localStorage.setItem(sec.store, collapsed ? '1' : '0');
		}
		function cockpitSetFocus(on) {
			document.body.classList.toggle('cockpit-focus', on);
			var btn = document.getElementById('focus-btn');
			if (btn) btn.classList.toggle('is-active', on);
			localStorage.setItem('cockpit-focus', on ? '1' : '0');
		}

		// Built-ins. Section values: 1 = collapsed, 0 = open.
		var BUILTIN_PRESETS = {
			'Write':   { focus: true },
			'Triage':  { focus: false, quickinsert: 1, comms: 0, tasks: 0, scratch: 1 },
			'Full':    { focus: false, quickinsert: 0, comms: 0, tasks: 0, scratch: 0 },
			'Minimal': { focus: false, quickinsert: 1, comms: 1, tasks: 1, scratch: 1 }
		};

		function applyPreset(cfg) {
			if (!cfg) return;
			cockpitSetFocus(!!cfg.focus);
			COCKPIT_SECTIONS.forEach(function (sec) {
				if (cfg[sec.key] !== undefined) cockpitSetSectionCollapsed(sec, cfg[sec.key] === 1 || cfg[sec.key] === true);
			});
		}
		function getCurrentLayout() {
			var cfg = { focus: document.body.classList.contains('cockpit-focus') };
			COCKPIT_SECTIONS.forEach(function (sec) {
				var b = document.getElementById(sec.body);
				cfg[sec.key] = (b && b.classList.contains('is-collapsed')) ? 1 : 0;
			});
			return cfg;
		}
		function loadUserPresets() { try { return JSON.parse(localStorage.getItem('cockpit-presets') || '[]'); } catch (e) { return []; } }
		function saveUserPresets(list) { try { localStorage.setItem('cockpit-presets', JSON.stringify(list)); } catch (e) {} }
		function getAllPresets() {
			var built = Object.keys(BUILTIN_PRESETS).map(function (n) { return { name: n, config: BUILTIN_PRESETS[n], builtin: true }; });
			return built.concat(loadUserPresets());
		}
		function deleteUserPreset(name) {
			saveUserPresets(loadUserPresets().filter(function (x) { return x.name !== name; }));
			settingsRenderPresets();
		}

		// ---- Open-in-new-tab nav (keeps this tab + the player alive when you jump into an app) ----
		function applyNavNewTab(on) {
			document.querySelectorAll('a.cockpit__ctrl-btn, #below-deck-badge a').forEach(function (a) {
				if (on) a.setAttribute('target', '_blank'); else a.removeAttribute('target');
			});
			var b = document.getElementById('settings-navtab-btn');
			if (b) b.textContent = 'Open nav links in new tabs: ' + (on ? 'ON' : 'OFF');
		}
		function toggleNavNewTab() {
			var on = localStorage.getItem('cockpit-nav-newtab') !== '1';
			localStorage.setItem('cockpit-nav-newtab', on ? '1' : '0');
			applyNavNewTab(on);
		}

		// ---- Settings overlay ----
		function settingsOpen() {
			var o = document.getElementById('settings-overlay');
			if (o) {
				o.classList.add('is-open');
				settingsRenderPresets();
				applyNavNewTab(localStorage.getItem('cockpit-nav-newtab') === '1');
			}
		}
		function settingsClose() {
			var o = document.getElementById('settings-overlay');
			if (o) o.classList.remove('is-open');
		}
		function settingsSaveCurrent() {
			var name = prompt('Name this layout:');
			if (!name) return;
			name = name.trim().slice(0, 24);
			if (!name || BUILTIN_PRESETS[name]) { alert('Pick a different name (not a built-in).'); return; }
			var list = loadUserPresets().filter(function (x) { return x.name !== name; });
			list.push({ name: name, config: getCurrentLayout() });
			saveUserPresets(list);
			settingsRenderPresets();
		}
		function settingsRenderPresets() {
			var list = document.getElementById('settings-preset-list');
			if (!list) return;
			list.innerHTML = '';
			getAllPresets().forEach(function (p) {
				var row = document.createElement('div');
				row.className = 'settings-preset-row';
				var apply = document.createElement('button');
				apply.className = 'settings-preset-apply';
				apply.textContent = p.name + (p.builtin ? '' : ' ·');
				apply.title = 'Apply this layout';
				apply.onclick = function () { applyPreset(p.config); };
				row.appendChild(apply);
				if (!p.builtin) {
					var del = document.createElement('button');
					del.className = 'settings-preset-del';
					del.textContent = '✕';
					del.title = 'Delete preset';
					del.onclick = function (e) { e.stopPropagation(); deleteUserPreset(p.name); };
					row.appendChild(del);
				}
				list.appendChild(row);
			});
		}

		// ---- Paste (or drop) an image straight into the transmission box → attaches it ----
		(function () {
			var box = document.getElementById('status-input');
			if (!box) return;
			function attach(file) {
				try {
					var dt = new DataTransfer();
					dt.items.add(file);
					var input = document.getElementById('image-upload');
					input.files = dt.files;
					if (typeof updatePayloadStatus === 'function') updatePayloadStatus();
				} catch (e) {}
			}
			box.addEventListener('paste', function (e) {
				var items = (e.clipboardData || {}).items || [];
				for (var i = 0; i < items.length; i++) {
					if (items[i].type && items[i].type.indexOf('image') === 0) {
						var f = items[i].getAsFile();
						if (f) { attach(f); e.preventDefault(); break; }
					}
				}
			});
			box.addEventListener('dragover', function (e) { e.preventDefault(); });
			box.addEventListener('drop', function (e) {
				var files = (e.dataTransfer || {}).files || [];
				if (files.length && files[0].type.indexOf('image') === 0) { attach(files[0]); e.preventDefault(); }
			});
		})();

