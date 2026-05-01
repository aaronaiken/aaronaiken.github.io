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
			fetch('/ani/weather')
				.then(r => r.json())
				.then(data => {
					if (data.weather) {
						const display = document.getElementById('weather-display');
						// wttr.in format: "City: ☀️ +72°F"
						// Strip location prefix, keep conditions + temp
						let w = data.weather;
						if (w.includes(':')) w = w.split(':').slice(1).join(':').trim();
						// Remove any stray encoding artifacts
						w = w.replace(/Â/g, '').replace(/\s+/g, ' ').trim();
						display.textContent = '· ' + w;
					}
				})
				.catch(() => {});
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

		function toggleTheme() {}

		// ---- HYPERSPACE SUBMIT ----
		document.getElementById('status-form').addEventListener('submit', (e) => {
			if ("vibrate" in navigator) navigator.vibrate([30, 50, 30]);
			cockpit.classList.add('hyperspace');
			setTimeout(() => e.target.submit(), 450);
			e.preventDefault();
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
			}
		}

		// ---- TASKS ----
		let _lastCompletedTitle = '';

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
			li.innerHTML = `
				<button class="task-check" onclick="completeTask('${task.id}', '${task.title.replace(/'/g, "\\'")}')" title="Mark complete"></button>
				<span class="task-title">${escapeHtml(task.title)}</span>
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
			updateHUD();
			statusInput.focus();
			dismissLogPrompt();
			statusInput.scrollIntoView({ behavior: 'smooth', block: 'center' });
		}

		function logAsBlogDraft() {
			const draft = `---\ntitle: "${_lastCompletedTitle}"\ndate: ${new Date().toISOString().split('T')[0]}\nlayout: post\nauthor: aaron\n---\n\n`;
			navigator.clipboard.writeText(draft)
				.then(() => {
					const btn = document.querySelector('.task-log-btn:nth-child(2)');
					if (btn) { btn.textContent = 'COPIED ✓'; setTimeout(() => btn.textContent = 'BLOG DRAFT', 2000); }
				})
				.catch(() => {});
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

		// ---- COLLAPSIBLE ----
		function toggleTasks() {
			const body = document.getElementById('tasks-body');
			const arrow = document.getElementById('tasks-arrow');
			const isCollapsed = arrow.classList.contains('is-collapsed');
			body.classList.toggle('is-collapsed');
			arrow.classList.toggle('is-collapsed');
			localStorage.setItem('cockpit-tasks-collapsed', isCollapsed ? '0' : '1');
		}

