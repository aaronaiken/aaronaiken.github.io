
	// ============================================================
	// MODE STATE
	// Read from <body> class set server-side by Flask template.
	// Body class will be 'mode-work' or 'mode-after-dark' or ''.
	// ============================================================

	const COCKPIT_MODE = document.body.className.includes('mode-work')
		? 'work'
		: document.body.className.includes('mode-after-dark')
		? 'after-dark'
		: 'default';

	// Set mode dot state on load
	(function initModeDot() {
        const dot = document.getElementById('mode-dot');
        if (!dot) return;
        if (COCKPIT_MODE === 'work') {
            dot.classList.add('is-active-work');
            document.getElementById('scratch-body').classList.remove('is-collapsed');
            document.getElementById('scratch-arrow').classList.remove('is-collapsed');
            setTimeout(function() {
                scratchCurrentTab = 'desk';
                scratchInitWork();
            }, 300);
        }
        if (COCKPIT_MODE === 'after-dark') {
            dot.classList.add('is-active-after-dark');
            // Force scratch open
            document.getElementById('scratch-body').classList.remove('is-collapsed');
            document.getElementById('scratch-arrow').classList.remove('is-collapsed');
            // Reload scratch content after DOM settles
            setTimeout(function() {
                scratchInitHome();
            }, 300);
        }
    })();

	// ============================================================
	// MODE DOT + PIN
	// ============================================================

	const modeDot      = document.getElementById('mode-dot');
	const modePinInput = document.getElementById('mode-pin-input');
	let pinOpen = false;

	modeDot.addEventListener('click', function() {
		pinOpen = !pinOpen;
		modePinInput.classList.toggle('is-open', pinOpen);
		if (pinOpen) {
			modePinInput.value = '';
			setTimeout(() => modePinInput.focus(), 50);
		}
	});

	modePinInput.addEventListener('keydown', function(e) {
		if (e.key === 'Enter') {
			e.preventDefault();
			submitPin(this.value.trim());
		}
		if (e.key === 'Escape') {
			pinOpen = false;
			modePinInput.classList.remove('is-open');
			modePinInput.value = '';
		}
	});

	function submitPin(pin) {
		if (!pin) return;
		fetch('/cockpit/mode', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ pin: pin })
		})
		.then(r => r.json())
		.then(data => {
			modePinInput.value = '';
			pinOpen = false;
			modePinInput.classList.remove('is-open');
			if (data.match) {
				// Cookie is set server-side — reload to apply
				window.location.reload();
			}
			// Silent fail on no match — nothing happens
		})
		.catch(() => {
			modePinInput.value = '';
			pinOpen = false;
			modePinInput.classList.remove('is-open');
		});
	}

	// ============================================================
	// PURGE & HIDE — Escape held 1.5s
	// Clears mode cookie, reloads to default
	// ============================================================

	let escapeHoldTimer = null;
	let escapeHoldStart = null;
	const ESCAPE_HOLD_MS = 1500;

	document.addEventListener('keydown', function(e) {
		if (e.key === 'Escape') {
			// Close overlays first if any are open
			if (document.getElementById('quick-tx-overlay').classList.contains('is-open')) {
				quickTxClose();
				return;
			}
			if (document.getElementById('brain-dump-overlay').classList.contains('is-open')) {
				brainDumpClose();
				return;
			}
			if (document.getElementById('cmd-palette-overlay').classList.contains('is-open')) {
				cmdClose();
				return;
			}
			if (pinOpen) {
				pinOpen = false;
				modePinInput.classList.remove('is-open');
				modePinInput.value = '';
				return;
			}
			// Start hold timer for purge
			if (!escapeHoldTimer && COCKPIT_MODE !== 'default') {
				escapeHoldStart = Date.now();
				modeDot.style.transition = 'background 1.5s ease';
				modeDot.style.background = '#cc3322';
				escapeHoldTimer = setTimeout(function() {
					purgeAndHide();
				}, ESCAPE_HOLD_MS);
			}
		}
	});

	document.addEventListener('keyup', function(e) {
		if (e.key === 'Escape') {
			if (escapeHoldTimer) {
				clearTimeout(escapeHoldTimer);
				escapeHoldTimer = null;
				// Reset dot
				modeDot.style.transition = '';
				modeDot.style.background = '';
			}
		}
	});

	// ============================================================
    // DOUBLE-TAP ESCAPE — FAMILY HIDE / RESTORE
    // ============================================================
    let lastEscapeTime = 0;
    let familyHidden = false;
    const FAMILY_HIDE_IDS = ['ad-panel', 'ad-player', 'ani-panel', 'ad-status-line'];
    const familyHiddenState = {};
    // Transform-based panels stay at display:flex even when slid off-screen,
    // so we can't use computed display to detect their actual visibility.
    // Track their "open" state separately so restore can re-open them.
    let familyAniWasOpen      = false;
    let familyAdLoungeWasOpen = false;

    document.addEventListener('keydown', function(e) {
        if (e.key !== 'Escape') return;
        const now = Date.now();
        const timeSinceLast = now - lastEscapeTime;

        if (timeSinceLast < 400 && timeSinceLast > 0) {
            // Double-tap detected
            e.stopImmediatePropagation();
            e.preventDefault();
            lastEscapeTime = 0;

            if (!familyHidden) {
                // Hide NSFW panels — only those actually visible right now
                familyHidden = true;
                familyAniWasOpen      = (typeof aniIsOpen !== 'undefined' && aniIsOpen);
                familyAdLoungeWasOpen = !!adAniOpen;

                FAMILY_HIDE_IDS.forEach(function(id) {
                    const el = document.getElementById(id);
                    if (!el) return;
                    let wasVisible;
                    if (id === 'ani-panel')      wasVisible = familyAniWasOpen;
                    else if (id === 'ad-panel')  wasVisible = familyAdLoungeWasOpen;
                    else                         wasVisible = window.getComputedStyle(el).display !== 'none';
                    familyHiddenState[id] = wasVisible;
                    if (!wasVisible) return;
                    el.classList.add('ad-family-hidden');
                });

                // Close the ad lounge if it was slid open
                if (familyAdLoungeWasOpen) {
                    const adPanel = document.getElementById('ad-panel');
                    if (adPanel) adPanel.classList.remove('ad-panel-open');
                    adAniOpen = false;
                }
                // Close ani chat if it was open
                if (familyAniWasOpen && typeof aniToggle === 'function') aniToggle();
            } else {
                // Restore — only elements that were visible before the hide
                familyHidden = false;
                FAMILY_HIDE_IDS.forEach(function(id) {
                    const el = document.getElementById(id);
                    if (!el) return;
                    if (!familyHiddenState[id]) return;
                    el.classList.remove('ad-family-hidden');
                    if (id === 'ad-player') el.style.display = '';
                });
                // Re-slide the ad lounge back on if it was open
                if (familyAdLoungeWasOpen) {
                    const adPanel = document.getElementById('ad-panel');
                    if (adPanel) adPanel.classList.add('ad-panel-open');
                    adAniOpen = true;
                }
                // Re-open ani chat if it was open (aniToggle is a state flip)
                if (familyAniWasOpen && typeof aniToggle === 'function' && !aniIsOpen) {
                    aniToggle();
                }
            }
            return;
        }
        lastEscapeTime = now;
    }, true); // capture phase so it fires before other escape handlers

	function purgeAndHide() {
		escapeHoldTimer = null;
		fetch('/cockpit/mode/clear', { method: 'POST' })
			.then(() => window.location.reload())
			.catch(() => window.location.reload());
	}

	// On Work Mode load, default to DESK tab
    if (COCKPIT_MODE === 'work') {
        document.addEventListener('DOMContentLoaded', function() {
            scratchSwitchTab('desk');
        });
    }

	// ============================================================
	// FOCUS TIMER
	// ============================================================

	let focusRunning = false;
	let focusPhase = 'focus'; // 'focus' | 'break'
	let focusSecondsLeft = 25 * 60;
	let focusInterval = null;
	let focusEndTime = null; // wall-clock ms timestamp when current phase ends; null when paused

	function focusDurationMins()  { return parseInt(document.getElementById('focus-duration-input').value) || 25; }
	function breakDurationMins()  { return parseInt(document.getElementById('break-duration-input').value) || 5; }

	function focusFormatTime(secs) {
		const m = Math.floor(secs / 60);
		const s = secs % 60;
		return String(m).padStart(2, '0') + ':' + String(s).padStart(2, '0');
	}

	function focusUpdateDisplay() {
		document.getElementById('focus-timer-display').textContent = focusFormatTime(focusSecondsLeft);
		document.getElementById('focus-timer-phase').textContent = focusPhase === 'focus' ? 'FOCUS' : 'BREAK';
	}

	function focusComputeSecondsLeft() {
		if (!focusEndTime) return focusSecondsLeft;
		return Math.max(0, Math.ceil((focusEndTime - Date.now()) / 1000));
	}

	function focusToggle() {
		const btn = document.getElementById('focus-start-btn');
		if (focusRunning) {
			// Pause — freeze remaining seconds, clear end time
			clearInterval(focusInterval);
			focusSecondsLeft = focusComputeSecondsLeft();
			focusEndTime = null;
			focusRunning = false;
			btn.textContent = 'RESUME';
			btn.classList.remove('is-running');
			focusPersistState();
		} else {
			// Start / Resume — anchor an end timestamp
			if (focusSecondsLeft === focusDurationMins() * 60 && focusPhase === 'focus') {
				// Fresh start
				focusSecondsLeft = focusDurationMins() * 60;
			}
			focusRequestNotificationPermission();
			focusRunning = true;
			focusEndTime = Date.now() + focusSecondsLeft * 1000;
			btn.textContent = 'PAUSE';
			btn.classList.add('is-running');
			focusTick(); // immediate first tick
			focusInterval = setInterval(focusTick, 1000);
			focusPersistState();
		}
	}

	function focusTick() {
		if (!focusRunning) return;

		focusSecondsLeft = focusComputeSecondsLeft();

		// Phase ended → fire tone + webhook, swap to the next phase, then PAUSE.
		// Manual gating: user must press START to begin the next phase.
		if (focusSecondsLeft <= 0) {
			if (focusPhase === 'focus') {
				focusPlayTone('focus_end');
				focusNotifyBreakStart();
				focusDesktopNotify('focus_end');
				focusPhase = 'break';
				focusSecondsLeft = breakDurationMins() * 60;
			} else {
				focusPlayTone('break_end');
				focusNotifyBreakEnd();
				focusDesktopNotify('break_end');
				focusPhase = 'focus';
				focusSecondsLeft = focusDurationMins() * 60;
			}
			clearInterval(focusInterval);
			focusInterval = null;
			focusRunning = false;
			focusEndTime = null;
			const btn = document.getElementById('focus-start-btn');
			if (btn) {
				btn.textContent = 'START';
				btn.classList.remove('is-running');
			}
		}

		focusPersistState();
		focusUpdateDisplay();
	}

	function focusReset() {
		clearInterval(focusInterval);
		focusRunning = false;
		focusPhase = 'focus';
		focusSecondsLeft = focusDurationMins() * 60;
		focusEndTime = null;
		focusUpdateDisplay();
		const btn = document.getElementById('focus-start-btn');
		btn.textContent = 'START';
		btn.classList.remove('is-running');
		localStorage.removeItem('cockpit-focus-state');
	}

	function focusPersistState() {
		localStorage.setItem('cockpit-focus-state', JSON.stringify({
			phase: focusPhase,
			secondsLeft: focusSecondsLeft,
			running: focusRunning,
			endTime: focusEndTime,
			savedAt: Date.now()
		}));
	}

	function focusRestoreState() {
		try {
			const raw = localStorage.getItem('cockpit-focus-state');
			if (!raw) return;
			const state = JSON.parse(raw);
			focusPhase = state.phase;
			if (!state.running) {
				// Was paused — restore frozen seconds, no end time
				focusSecondsLeft = state.secondsLeft;
				focusEndTime = null;
				focusUpdateDisplay();
				const btn = document.getElementById('focus-start-btn');
				if (btn) {
					// Phase-boundary pause (manual gating) shows START;
					// mid-phase pause shows RESUME.
					const phaseFullDuration = focusPhase === 'focus'
						? focusDurationMins() * 60
						: breakDurationMins() * 60;
					btn.textContent = (focusSecondsLeft === phaseFullDuration) ? 'START' : 'RESUME';
					btn.classList.remove('is-running');
				}
				return;
			}
			// Was running — restore the end-time anchor (fall back to savedAt math for old state shapes)
			focusEndTime = state.endTime || (state.savedAt + state.secondsLeft * 1000);
			focusRunning = true;
			const btn = document.getElementById('focus-start-btn');
			if (btn) { btn.textContent = 'PAUSE'; btn.classList.add('is-running'); }
			focusTick(); // catches up any phase boundaries crossed while the page was closed
			focusInterval = setInterval(focusTick, 1000);
		} catch (e) { /* ignore */ }
	}

	// Re-tick the moment the tab becomes visible again — the running setInterval may have
	// been throttled or fully paused while backgrounded, so the displayed countdown
	// could be stale and unfired phase transitions need to fire.
	document.addEventListener('visibilitychange', function() {
		if (!document.hidden && focusRunning) focusTick();
	});

	function focusNotifyBreakStart() {
		fetch('/cockpit/focus/break', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ phase: 'break_start' })
		}).catch(() => {});
	}

	function focusNotifyBreakEnd() {
		fetch('/cockpit/focus/break', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ phase: 'break_end' })
		}).catch(() => {});
	}

	function focusRequestNotificationPermission() {
		if (!('Notification' in window)) return;
		if (Notification.permission === 'default') {
			Notification.requestPermission().catch(() => {});
		}
	}

	function focusDesktopNotify(type) {
		if (!('Notification' in window) || Notification.permission !== 'granted') return;
		try {
			if (type === 'focus_end') {
				new Notification('Focus session ended', {
					body: 'Step away. Break starts when you press START.',
					tag: 'cockpit-focus'
				});
			} else {
				new Notification('Break\'s up', {
					body: 'Back to it when you\'re ready.',
					tag: 'cockpit-focus'
				});
			}
		} catch (e) { /* ignore */ }
	}

	function focusPlayTone(type) {
		if (!cockpitAudioCtx) cockpitAudioCtx = new (window.AudioContext || window.webkitAudioContext)();
		if (cockpitAudioCtx.state === 'suspended') cockpitAudioCtx.resume();
		const ctx = cockpitAudioCtx;
		const now = ctx.currentTime;

		if (type === 'focus_end') {
			// Three descending tones — break time
			[660, 550, 440].forEach((freq, i) => {
				const o = ctx.createOscillator();
				const g = ctx.createGain();
				o.type = 'sine';
				o.frequency.value = freq;
				o.connect(g); g.connect(ctx.destination);
				const t = now + i * 0.22;
				g.gain.setValueAtTime(0.12, t);
				g.gain.exponentialRampToValueAtTime(0.0001, t + 0.3);
				o.start(t); o.stop(t + 0.35);
			});
		} else {
			// Two ascending tones — back to focus
			[440, 660].forEach((freq, i) => {
				const o = ctx.createOscillator();
				const g = ctx.createGain();
				o.type = 'square';
				o.frequency.value = freq;
				o.connect(g); g.connect(ctx.destination);
				const t = now + i * 0.18;
				g.gain.setValueAtTime(0.06, t);
				g.gain.exponentialRampToValueAtTime(0.0001, t + 0.25);
				o.start(t); o.stop(t + 0.28);
			});
		}
	}

	// Restore on load if in work mode
	if (COCKPIT_MODE === 'work') {
		document.addEventListener('DOMContentLoaded', function() {
			focusSecondsLeft = focusDurationMins() * 60;
			focusUpdateDisplay();
			focusRestoreState();
		});
	}

	// ============================================================
	// AFTER DARK — ANI LOUNGE
	// ============================================================

	let adAniLoops = [];
	let adAniIndex = 0;
	let adAniOpen = false;

	function adAniToggle() {
        // When Ani fullscreen is active, the LOOPS panel slide is driven by
        // body.ani-fs-loops-open, not ad-panel-open. Delegate so the panel's
        // own CLOSE button still works in that mode.
        if (document.body.classList.contains('ani-fullscreen') && typeof window.aniFsLoopsToggle === 'function') {
            window.aniFsLoopsToggle();
            return;
        }
        adAniOpen = !adAniOpen;
        const panel = document.getElementById('ad-panel');
        panel.classList.toggle('ad-panel-open', adAniOpen);
        if (adAniOpen && adAniLoops.length === 0) {
            adLoadAniLoops();
        }
    }

	function adLoadAniLoops() {
        fetch('/cockpit/after-dark/ani-loops')
            .then(r => r.json())
            .then(data => {
                adAniLoops = data.items || [];
                if (adAniLoops.length > 0) {
                    adAniIndex = -1;
                    const startIdx = Math.floor(Math.random() * adAniLoops.length);
                    adAniIndex = startIdx;
                    const loop = adAniLoops[startIdx];
                    const vid = document.getElementById('ad-ani-video');
                    vid.src = loop.url;
                    vid.load();
                    vid.play().catch(() => {});
                    document.getElementById('ad-loop-label').textContent =
                        loop.name.replace(/\.[^.]+$/, '').replace(/[-_]/g, ' ');
                }
            })
            .catch(() => {});
    }

	function adAniSetLoop() {
        if (adAniLoops.length === 0) return;
        let newIdx;
        if (adAniLoops.length === 1) {
            newIdx = 0;
        } else {
            do {
                newIdx = Math.floor(Math.random() * adAniLoops.length);
            } while (newIdx === adAniIndex);
        }
        adAniIndex = newIdx;
        const loop = adAniLoops[adAniIndex];
        const vid = document.getElementById('ad-ani-video');
        vid.src = loop.url;
        vid.load();
        vid.play().catch(() => {});
        document.getElementById('ad-loop-label').textContent =
            loop.name.replace(/\.[^.]+$/, '').replace(/[-_]/g, ' ');
    }

    // Auto-advance Ani loops on end (shuffle)
    document.addEventListener('DOMContentLoaded', function() {
        const aniVid = document.getElementById('ad-ani-video');
        if (!aniVid) return;
        aniVid.addEventListener('ended', function() {
            adAniSetLoop();
        });
    });

    function adAniPrev() { adAniSetLoop(adAniIndex); }
    function adAniNext() { adAniSetLoop(adAniIndex); }

	function adAniToggleMute() {
		const vid = document.getElementById('ad-ani-video');
		const btn = document.getElementById('ad-ani-mute-btn');
		vid.muted = !vid.muted;
		btn.textContent = vid.muted ? 'UNMUTE' : 'MUTE';
	}

	// Load loops on After Dark mode init
	if (COCKPIT_MODE === 'after-dark') {
        adLoadAniLoops();
    }

	// ============================================================
	// AFTER DARK — FLOATING VIDEO PLAYER
	// ============================================================

	let adLibraryItems = [];
	let adLibraryVisible = false;
	let adPlayerMinimized = false;
	let adCurrentIdx = -1;

	// Ad-hoc paste queue (ephemeral — not saved to the .txt library).
	let adQueue = [];          // [{url, label}]
	let adQueueIdx = -1;
	let adQueueActive = false;
	let adQueueVisible = false;
	let adAutoTimer = null;

	// ---- Drag ----
	(function initAdPlayerDrag() {
		const player = document.getElementById('ad-player');
		const handle = document.getElementById('ad-player-titlebar');
		if (!player || !handle) return;

		// Restore saved position
		try {
            const saved = JSON.parse(localStorage.getItem('ad-player-pos'));
            if (saved) {
                const clampedX = Math.min(saved.x, window.innerWidth - 340);
                const clampedY = Math.min(saved.y, window.innerHeight - 200);
                player.style.left = Math.max(0, clampedX) + 'px';
                player.style.top  = Math.max(0, clampedY) + 'px';
                player.style.right  = 'auto';
                player.style.bottom = 'auto';
            }
        } catch(e) {}

		let dragging = false, startX, startY, startL, startT;

		handle.addEventListener('mousedown', function(e) {
			if (e.target.tagName === 'BUTTON') return; // don't drag on button clicks
			dragging = true;
			const rect = player.getBoundingClientRect();
			startX = e.clientX;
			startY = e.clientY;
			startL = rect.left;
			startT = rect.top;
			player.style.left   = startL + 'px';
			player.style.top    = startT + 'px';
			player.style.right  = 'auto';
			player.style.bottom = 'auto';
			document.body.style.cursor = 'grabbing';
			e.preventDefault();
		});

		document.addEventListener('mousemove', function(e) {
			if (!dragging) return;
			const dx = e.clientX - startX;
			const dy = e.clientY - startY;
			let newL = startL + dx;
			let newT = startT + dy;
			// Keep within viewport
			newL = Math.max(0, Math.min(newL, window.innerWidth  - player.offsetWidth));
			newT = Math.max(0, Math.min(newT, window.innerHeight - player.offsetHeight));
			player.style.left = newL + 'px';
			player.style.top  = newT + 'px';
		});

		document.addEventListener('mouseup', function() {
			if (!dragging) return;
			dragging = false;
			document.body.style.cursor = '';
			// Save position
			localStorage.setItem('ad-player-pos', JSON.stringify({
				x: parseFloat(player.style.left),
				y: parseFloat(player.style.top)
			}));
		});
	})();

	// ---- AD Player resize-grip drag ----
	// Custom grip instead of relying on CSS `resize: both`, which is hard to
	// grab once the iframe overlays the corner. While the user drags, the
	// iframe gets `pointer-events: none` so the mouse can sweep across it
	// without the embed swallowing the events.
	(function initAdPlayerResize() {
		const player = document.getElementById('ad-player');
		const grip   = document.getElementById('ad-player-resize-grip');
		const frame  = document.getElementById('ad-viewer-iframe');
		if (!player || !grip || !frame) return;

		// The PH embed renders its content (title strip, video, controls)
		// at a fixed internal size and does NOT scale to fill the iframe —
		// growing the iframe just adds empty black space below. So we keep
		// the iframe at its native embed size (481×367 from PH's share
		// dialog) and visually scale it with CSS transform. Everything
		// inside the embed scales together; no letterboxing.
		const NATIVE_W = 481;
		const NATIVE_H = 367;
		const titlebarH = function () {
			const tb = document.getElementById('ad-player-titlebar');
			return tb ? tb.offsetHeight : 28;
		};

		function applySize(newW) {
			newW = Math.max(320, newW);
			const scale = newW / NATIVE_W;
			const videoH = Math.round(NATIVE_H * scale);
			player.style.width  = newW + 'px';
			player.style.height = (videoH + titlebarH()) + 'px';
			frame.style.transform = 'scale(' + scale + ')';
		}

		try {
			const saved = JSON.parse(localStorage.getItem('ad-player-size'));
			applySize(saved && saved.w ? saved.w : 481);
		} catch (e) {
			applySize(481);
		}

		let resizing = false, startX, startY, startW;

		grip.addEventListener('mousedown', function(e) {
			resizing = true;
			const rect = player.getBoundingClientRect();
			startX = e.clientX;
			startY = e.clientY;
			startW = rect.width;
			// Anchor top/left so the player grows toward the mouse rather
			// than away from it (default `bottom/right` anchor inverts).
			player.style.left   = rect.left + 'px';
			player.style.top    = rect.top + 'px';
			player.style.right  = 'auto';
			player.style.bottom = 'auto';
			frame.style.pointerEvents = 'none';
			document.body.style.cursor = 'nwse-resize';
			e.preventDefault();
		});

		document.addEventListener('mousemove', function(e) {
			if (!resizing) return;
			// Either axis drives — whichever moved more (signed) feeds
			// applySize. Drag down-right grows; up-left shrinks.
			const dx = e.clientX - startX;
			const dy = e.clientY - startY;
			const effectiveDelta = Math.abs(dx) > Math.abs(dy) ? dx : dy;
			applySize(startW + effectiveDelta);
		});

		document.addEventListener('mouseup', function() {
			if (!resizing) return;
			resizing = false;
			frame.style.pointerEvents = '';
			document.body.style.cursor = '';
			localStorage.setItem('ad-player-size', JSON.stringify({
				w: parseFloat(player.style.width),
			}));
		});
	})();

	// ============================================================
	// AFTER DARK — FLOATING YOUTUBE PLAYER
	// Mirror of the AD video player but YT embeds scale responsively, so
	// the iframe is plain 100%/100% with no transform: scale hack. Default
	// position is bottom-LEFT so it doesn't stack on top of the PH player.
	// ============================================================

	let ytLibraryItems = [];
	let ytLibraryVisible = false;
	let ytPlayerMinimized = false;
	let ytCurrentIdx = -1;
	// --- YouTube IFrame API player + queue state ---
	let ytPlayer = null;          // YT.Player instance (created lazily on first play)
	let ytPlayerReady = false;
	let ytApiLoading = false;
	let ytPendingCbs = [];        // run once the player is ready
	let ytSource = null;          // 'lib' | 'queue' — what's driving playback (for end-of-video advance)
	let ytQueue = [];             // [{type:'video'|'playlist', id, label}]
	let ytQueueIdx = -1;
	let ytQueueActive = false;
	let ytQueueVisible = false;
	let ytShuffle = false;
	let ytLoop = false;

	function ytPlayerMinimize() {
		ytPlayerMinimized = !ytPlayerMinimized;
		const p = document.getElementById('yt-player');
		p.classList.toggle('is-minimized', ytPlayerMinimized);
		document.getElementById('yt-minimize-btn').textContent = ytPlayerMinimized ? '□' : '—';
	}

	function ytPlayerClose() {
		try { if (ytPlayer && ytPlayer.stopVideo) ytPlayer.stopVideo(); } catch (e) {}
		ytSource = null;
		document.getElementById('yt-player').style.display = 'none';
	}

	// Show/hide the YouTube player without touching playback (unlike Close,
	// which clears the iframe src). Bound to Cmd/Ctrl+Shift+Y and the command
	// palette. Showing a previously-closed player just reveals the idle frame —
	// no autoplay surprise; LIB / NEXT launch a video.
	function ytPlayerToggle() {
		const p = document.getElementById('yt-player');
		if (!p) return;
		const hidden = getComputedStyle(p).display === 'none';
		p.style.display = hidden ? '' : 'none';
	}

	function ytLibraryToggle() {
		ytLibraryVisible = !ytLibraryVisible;
		const drawer = document.getElementById('yt-player-library');
		drawer.classList.toggle('is-open', ytLibraryVisible);
		document.getElementById('yt-library-toggle-btn').style.color =
			ytLibraryVisible ? '#8b1a1a' : '';
		if (ytLibraryVisible && ytLibraryItems.length === 0) ytLoadLibrary();
	}

	function ytLoadLibrary(cb) {
		fetch('/cockpit/after-dark/youtube')
			.then(r => {
				if (!r.ok) throw new Error('HTTP ' + r.status);
				return r.json();
			})
			.then(data => {
				console.log('[yt] library loaded:', (data.items || []).length, 'items');
				ytLibraryItems = data.items || [];
				ytRenderLibrary();
				if (cb) cb();
			})
			.catch(err => {
				console.error('[yt] library load failed:', err);
				ytLibraryItems = [];
				const grid = document.getElementById('yt-player-library-grid');
				if (grid) {
					grid.innerHTML =
						'<div style="color:#c04040;font-size:0.55rem;letter-spacing:0.12em;padding:12px;">' +
						'load failed: ' + (err && err.message ? err.message : 'unknown') + '<br>' +
						'check browser console + /cockpit/after-dark/youtube directly</div>';
				}
			});
	}

	function ytRenderLibrary() {
		const grid = document.getElementById('yt-player-library-grid');
		grid.innerHTML = '';
		if (ytLibraryItems.length === 0) {
			grid.innerHTML =
				'<div style="color:#2a0f0f;font-size:0.55rem;letter-spacing:0.12em;padding:12px;line-height:1.5;">' +
				'no valid items returned by /cockpit/after-dark/youtube.<br>' +
				'check static/after_dark_youtube.txt — one URL per line; supported formats:<br>' +
				'<code>youtu.be/&lt;id&gt;</code> · <code>youtube.com/watch?v=&lt;id&gt;</code> · <code>youtube.com/embed/&lt;id&gt;</code> · <code>youtube.com/shorts/&lt;id&gt;</code><br>' +
				'optional <code>|label</code> after URL · <code>#</code> for comments' +
				'</div>';
			return;
		}
		ytLibraryItems.forEach(function (item, idx) {
			const tile = document.createElement('div');
			tile.className = 'ad-library-tile';
			tile.textContent = item.name;
			tile.onclick = function () { ytPlayVideo(item, idx); };
			grid.appendChild(tile);
		});
	}

	function ytPlayVideo(item, idx) {
		ytCurrentIdx = idx;
		ytSource = 'lib';
		ytQueueActive = false;
		ytLibraryVisible = false;
		document.getElementById('yt-player-library').classList.remove('is-open');
		document.getElementById('yt-library-toggle-btn').style.color = '';

		const player = document.getElementById('yt-player');
		player.style.display = '';
		if (ytPlayerMinimized) ytPlayerMinimize();

		const vid = ytVideoId(item.url) || item.id;
		if (vid) ytEnsurePlayer(function () { ytPlayer.loadVideoById(vid); });

		document.querySelectorAll('#yt-player-library-grid .ad-library-tile')
			.forEach(function (t, i) { t.classList.toggle('is-playing', i === idx); });
		ytSetNowPlaying(item.name || '');
	}

	function ytPlayNext() {
		if (ytLibraryItems.length === 0) {
			ytLoadLibrary(function () { if (ytLibraryItems.length > 0) ytPlayNext(); });
			return;
		}
		if (ytLibraryItems.length === 1) { ytPlayVideo(ytLibraryItems[0], 0); return; }
		let nextIdx;
		do { nextIdx = Math.floor(Math.random() * ytLibraryItems.length); }
		while (nextIdx === ytCurrentIdx);
		ytPlayVideo(ytLibraryItems[nextIdx], nextIdx);
	}

	// ============================================================
	// YT — IFrame API player (real end-detection) + smart queue
	// ============================================================

	function ytVideoId(u) {
		if (!u) return null;
		var m = String(u).match(/(?:youtu\.be\/|youtube\.com\/(?:watch\?v=|embed\/|shorts\/|live\/|v\/))([A-Za-z0-9_-]{11})/);
		if (m) return m[1];
		if (/^[A-Za-z0-9_-]{11}$/.test(u)) return u;
		return null;
	}

	// Lazily create the YT.Player (loads the IFrame API script on first use). Runs cb once ready.
	function ytEnsurePlayer(cb) {
		if (ytPlayer && ytPlayerReady) { if (cb) cb(); return; }
		if (cb) ytPendingCbs.push(cb);
		if (ytPlayer) return;                        // being created — cbs fire on ready
		if (window.YT && window.YT.Player) { ytCreatePlayer(); return; }
		if (!ytApiLoading) {
			ytApiLoading = true;
			window.onYouTubeIframeAPIReady = ytCreatePlayer;
			var s = document.createElement('script');
			s.src = 'https://www.youtube.com/iframe_api';
			document.head.appendChild(s);
		}
	}

	function ytCreatePlayer() {
		if (ytPlayer) return;
		ytPlayer = new YT.Player('yt-viewer-iframe', {
			width: '100%', height: '100%',
			playerVars: { autoplay: 0, mute: 0, rel: 0, playsinline: 1, modestbranding: 1 },
			events: { onReady: ytOnReady, onStateChange: ytOnStateChange }
		});
	}

	function ytOnReady() {
		ytPlayerReady = true;
		var cbs = ytPendingCbs; ytPendingCbs = [];
		cbs.forEach(function (f) { try { f(); } catch (e) {} });
	}

	// Real auto-advance: when a video truly ENDS, move on. A loaded playlist advances itself
	// internally, so only step MY queue once its last item finishes.
	function ytOnStateChange(e) {
		if (!window.YT || e.data !== YT.PlayerState.ENDED) return;
		if (ytQueueActive && ytQueue[ytQueueIdx] && ytQueue[ytQueueIdx].type === 'playlist') {
			try {
				var pl = ytPlayer.getPlaylist() || [];
				if (pl.length && ytPlayer.getPlaylistIndex() < pl.length - 1) return;
			} catch (e2) {}
		}
		if (ytQueueActive) ytQueueAdvance();
		else if (ytSource === 'lib') ytPlayNext();   // endless LIB play, now that we can detect end
	}

	function ytQueueToggle() {
		ytQueueVisible = !ytQueueVisible;
		document.getElementById('yt-player-queue').classList.toggle('is-open', ytQueueVisible);
		document.getElementById('yt-queue-toggle-btn').style.color = ytQueueVisible ? '#8b1a1a' : '';
	}

	// Parse one pasted line into a queue entry (video or playlist), or null. Optional '|label' suffix.
	function ytParseEntry(line) {
		line = (line || '').trim();
		if (!line || line.charAt(0) === '#') return null;
		var label = '', bar = line.indexOf('|');
		if (bar >= 0) { label = line.slice(bar + 1).trim(); line = line.slice(0, bar).trim(); }
		var m = line.match(/[?&]list=([A-Za-z0-9_-]+)/);
		if (m) return { type: 'playlist', id: m[1], label: label || 'playlist' };
		var vid = ytVideoId(line);
		if (vid) return { type: 'video', id: vid, label: label || vid };
		return null;
	}

	function ytParseInput() {
		return document.getElementById('yt-queue-input').value.split('\n').map(ytParseEntry).filter(Boolean);
	}

	function ytQueueLoad() {
		var items = ytParseInput();
		if (items.length === 0) { ytSetQueueStatus('no valid YouTube URLs'); return; }
		ytQueue = items; ytQueueIdx = -1; ytQueueActive = true;
		ytSaveQueue(); ytRenderQueue(); ytQueuePlay(0);
	}

	function ytQueueAddFromInput() {
		var items = ytParseInput();
		if (items.length === 0) { ytSetQueueStatus('no valid YouTube URLs'); return; }
		var wasEmpty = ytQueue.length === 0;
		ytQueue = ytQueue.concat(items);
		document.getElementById('yt-queue-input').value = '';
		ytQueueActive = true; ytSaveQueue(); ytRenderQueue();
		if (wasEmpty) ytQueuePlay(0);
	}

	function ytQueuePlay(idx) {
		if (idx < 0 || idx >= ytQueue.length) return;
		ytQueueIdx = idx; ytQueueActive = true; ytSource = 'queue';
		var player = document.getElementById('yt-player');
		player.style.display = '';
		if (ytPlayerMinimized) ytPlayerMinimize();
		var entry = ytQueue[idx];
		ytEnsurePlayer(function () {
			if (entry.type === 'playlist') ytPlayer.loadPlaylist({ list: entry.id, listType: 'playlist', index: 0 });
			else ytPlayer.loadVideoById(entry.id);
		});
		ytSetNowPlaying(entry.label + (entry.type === 'playlist' ? '  (playlist)' : ''));
		ytSaveQueue(); ytRenderQueue();
	}

	function ytQueueAdvance() {
		if (ytQueue.length === 0) return;
		var next;
		if (ytShuffle) {
			if (ytQueue.length === 1) next = 0;
			else { do { next = Math.floor(Math.random() * ytQueue.length); } while (next === ytQueueIdx); }
		} else {
			next = ytQueueIdx + 1;
			if (next >= ytQueue.length) {
				if (!ytLoop) { ytSetNowPlaying('queue ended'); ytSetQueueStatus('done'); return; }
				next = 0;
			}
		}
		ytQueuePlay(next);
	}

	function ytQueueClear() {
		ytQueue = []; ytQueueIdx = -1; ytQueueActive = false;
		document.getElementById('yt-queue-input').value = '';
		ytSetNowPlaying(''); ytSaveQueue(); ytRenderQueue();
	}

	function ytQueueToggleShuffle() {
		ytShuffle = !ytShuffle;
		var b = document.getElementById('yt-queue-shuffle-btn');
		b.textContent = 'SHUFFLE ' + (ytShuffle ? '●' : '○'); b.style.color = ytShuffle ? '#e05050' : '';
		ytSaveQueue();
	}

	function ytQueueToggleLoop() {
		ytLoop = !ytLoop;
		var b = document.getElementById('yt-queue-loop-btn');
		b.textContent = 'LOOP ' + (ytLoop ? '●' : '○'); b.style.color = ytLoop ? '#e05050' : '';
		ytSaveQueue();
	}

	function ytSetQueueStatus(msg) { var el = document.getElementById('yt-queue-status'); if (el) el.textContent = msg || ''; }
	function ytSetNowPlaying(txt) { var el = document.getElementById('yt-now-playing'); if (el) el.textContent = txt ? ('now: ' + txt) : ''; }

	function ytRenderQueue() {
		var list = document.getElementById('yt-queue-list');
		if (!list) return;
		list.innerHTML = '';
		if (ytQueue.length === 0) { ytSetQueueStatus(''); return; }
		ytQueue.forEach(function (item, i) {
			var row = document.createElement('div');
			row.className = 'ad-queue-row' + (i === ytQueueIdx ? ' is-playing' : '');
			var label = document.createElement('span');
			label.className = 'ad-queue-label';
			label.textContent = (i + 1) + '. ' + item.label + (item.type === 'playlist' ? ' ⋯' : '');
			label.onclick = function () { ytQueuePlay(i); };
			var del = document.createElement('button');
			del.className = 'ad-queue-del'; del.textContent = '✕'; del.title = 'remove';
			del.onclick = function (e) { e.stopPropagation(); ytQueueRemove(i); };
			row.appendChild(label); row.appendChild(del); list.appendChild(row);
		});
		ytSetQueueStatus((ytQueueIdx + 1) + ' / ' + ytQueue.length);
	}

	function ytQueueRemove(i) {
		if (i < 0 || i >= ytQueue.length) return;
		ytQueue.splice(i, 1);
		if (ytQueue.length === 0) { ytQueueClear(); return; }
		if (i < ytQueueIdx) ytQueueIdx--;
		else if (i === ytQueueIdx) ytQueueIdx = Math.min(ytQueueIdx, ytQueue.length - 1);
		ytSaveQueue(); ytRenderQueue();
	}

	// ---- Persistence: the queue survives reloads (localStorage) ----
	function ytSaveQueue() {
		try {
			localStorage.setItem('cockpit-yt-queue', JSON.stringify({
				queue: ytQueue, idx: ytQueueIdx, shuffle: ytShuffle, loop: ytLoop
			}));
		} catch (e) {}
	}

	function ytLoadQueue() {
		try {
			var d = JSON.parse(localStorage.getItem('cockpit-yt-queue') || 'null');
			if (!d) return;
			if (Array.isArray(d.queue)) ytQueue = d.queue;
			if (typeof d.idx === 'number') ytQueueIdx = d.idx;
			ytShuffle = !!d.shuffle; ytLoop = !!d.loop;
			var sb = document.getElementById('yt-queue-shuffle-btn');
			if (sb) { sb.textContent = 'SHUFFLE ' + (ytShuffle ? '●' : '○'); sb.style.color = ytShuffle ? '#e05050' : ''; }
			var lb = document.getElementById('yt-queue-loop-btn');
			if (lb) { lb.textContent = 'LOOP ' + (ytLoop ? '●' : '○'); lb.style.color = ytLoop ? '#e05050' : ''; }
			ytRenderQueue();
			if (ytQueue.length) ytSetQueueStatus(ytQueue.length + ' saved — PLAY QUEUE to resume');
		} catch (e) {}
	}
	document.addEventListener('DOMContentLoaded', ytLoadQueue);

	// The YouTube player starts hidden on load (style="display:none" in the
	// template) and is summoned with Cmd/Ctrl+Shift+Y or the Ctrl+K palette —
	// no auto-open/auto-play in any mode. Once shown, LIB / NEXT load + play.

	// ---- YT Player drag (titlebar) ----
	(function initYtPlayerDrag() {
		const player = document.getElementById('yt-player');
		const handle = document.getElementById('yt-player-titlebar');
		if (!player || !handle) return;

		try {
			const saved = JSON.parse(localStorage.getItem('yt-player-pos'));
			if (saved) {
				const cx = Math.min(saved.x, window.innerWidth - 340);
				const cy = Math.min(saved.y, window.innerHeight - 200);
				player.style.left = Math.max(0, cx) + 'px';
				player.style.top  = Math.max(0, cy) + 'px';
				player.style.right = 'auto';
				player.style.bottom = 'auto';
			}
		} catch (e) {}

		let dragging = false, startX, startY, startL, startT;
		handle.addEventListener('mousedown', function (e) {
			if (e.target.tagName === 'BUTTON') return;
			dragging = true;
			const rect = player.getBoundingClientRect();
			startX = e.clientX; startY = e.clientY;
			startL = rect.left;  startT = rect.top;
			player.style.left = startL + 'px';
			player.style.top  = startT + 'px';
			player.style.right = 'auto';
			player.style.bottom = 'auto';
			document.body.style.cursor = 'grabbing';
			e.preventDefault();
		});
		document.addEventListener('mousemove', function (e) {
			if (!dragging) return;
			let nl = startL + (e.clientX - startX);
			let nt = startT + (e.clientY - startY);
			nl = Math.max(0, Math.min(nl, window.innerWidth  - player.offsetWidth));
			nt = Math.max(0, Math.min(nt, window.innerHeight - player.offsetHeight));
			player.style.left = nl + 'px';
			player.style.top  = nt + 'px';
		});
		document.addEventListener('mouseup', function () {
			if (!dragging) return;
			dragging = false;
			document.body.style.cursor = '';
			localStorage.setItem('yt-player-pos', JSON.stringify({
				x: parseFloat(player.style.left),
				y: parseFloat(player.style.top),
			}));
		});
	})();

	// ---- YT Player resize-grip ----
	// YT embeds are responsive — no native-size + transform-scale hack
	// needed. Lock to 16:9 video area + titlebar; either axis can drive.
	(function initYtPlayerResize() {
		const player = document.getElementById('yt-player');
		const grip   = document.getElementById('yt-player-resize-grip');
		const frame  = document.getElementById('yt-viewer-iframe');
		if (!player || !grip || !frame) return;

		const ASPECT = 16 / 9;
		const titlebarH = function () {
			const tb = document.getElementById('yt-player-titlebar');
			return tb ? tb.offsetHeight : 28;
		};

		function applySize(newW) {
			newW = Math.max(320, newW);
			const newH = Math.round(newW / ASPECT) + titlebarH();
			player.style.width  = newW + 'px';
			player.style.height = newH + 'px';
		}

		try {
			const saved = JSON.parse(localStorage.getItem('yt-player-size'));
			applySize(saved && saved.w ? saved.w : 480);
		} catch (e) { applySize(480); }

		let resizing = false, startX, startY, startW;
		grip.addEventListener('mousedown', function (e) {
			resizing = true;
			const rect = player.getBoundingClientRect();
			startX = e.clientX; startY = e.clientY;
			startW = rect.width;
			player.style.left = rect.left + 'px';
			player.style.top  = rect.top + 'px';
			player.style.right = 'auto';
			player.style.bottom = 'auto';
			frame.style.pointerEvents = 'none';
			document.body.style.cursor = 'nwse-resize';
			e.preventDefault();
		});
		document.addEventListener('mousemove', function (e) {
			if (!resizing) return;
			const dx = e.clientX - startX;
			const dy = e.clientY - startY;
			const d = Math.abs(dx) > Math.abs(dy) ? dx : dy;
			applySize(startW + d);
		});
		document.addEventListener('mouseup', function () {
			if (!resizing) return;
			resizing = false;
			frame.style.pointerEvents = '';
			document.body.style.cursor = '';
			localStorage.setItem('yt-player-size', JSON.stringify({
				w: parseFloat(player.style.width),
			}));
		});
	})();

	// ---- Focus Timer Drag ----
	(function initFocusTimerDrag() {
		const timer  = document.getElementById('focus-timer');
		const handle = document.getElementById('focus-timer-titlebar');
		if (!timer || !handle) return;

		try {
			const saved = JSON.parse(localStorage.getItem('focus-timer-pos'));
			if (saved) {
				timer.style.left   = saved.x + 'px';
				timer.style.top    = saved.y + 'px';
				timer.style.right  = 'auto';
				timer.style.bottom = 'auto';
			}
		} catch(e) {}

		let dragging = false, startX, startY, startL, startT;

		handle.addEventListener('mousedown', function(e) {
			dragging = true;
			const rect = timer.getBoundingClientRect();
			startX = e.clientX;
			startY = e.clientY;
			startL = rect.left;
			startT = rect.top;
			timer.style.left   = startL + 'px';
			timer.style.top    = startT + 'px';
			timer.style.right  = 'auto';
			timer.style.bottom = 'auto';
			document.body.style.cursor = 'grabbing';
			e.preventDefault();
		});

		document.addEventListener('mousemove', function(e) {
			if (!dragging) return;
			let newL = startL + (e.clientX - startX);
			let newT = startT + (e.clientY - startY);
			newL = Math.max(0, Math.min(newL, window.innerWidth  - timer.offsetWidth));
			newT = Math.max(0, Math.min(newT, window.innerHeight - timer.offsetHeight));
			timer.style.left = newL + 'px';
			timer.style.top  = newT + 'px';
		});

		document.addEventListener('mouseup', function() {
			if (!dragging) return;
			dragging = false;
			document.body.style.cursor = '';
			localStorage.setItem('focus-timer-pos', JSON.stringify({
				x: parseFloat(timer.style.left),
				y: parseFloat(timer.style.top)
			}));
		});
	})();

	(function initMusicPlayerDrag() {
        const player = document.getElementById('ad-music-player');
        const handle = document.getElementById('ad-music-titlebar');
        if (!player || !handle) return;
        let dragging = false, startX, startY, startL, startT;
        handle.addEventListener('mousedown', function(e) {
            dragging = true;
            const rect = player.getBoundingClientRect();
            startX = e.clientX; startY = e.clientY;
            startL = rect.left; startT = rect.top;
            player.style.left = startL + 'px';
            player.style.top = startT + 'px';
            player.style.transform = 'none';
            player.style.right = 'auto';
            player.style.bottom = 'auto';
            document.body.style.cursor = 'grabbing';
            e.preventDefault();
        });
        document.addEventListener('mousemove', function(e) {
            if (!dragging) return;
            let newL = startL + (e.clientX - startX);
            let newT = startT + (e.clientY - startY);
            newL = Math.max(0, Math.min(newL, window.innerWidth - player.offsetWidth));
            newT = Math.max(0, Math.min(newT, window.innerHeight - player.offsetHeight));
            player.style.left = newL + 'px';
            player.style.top = newT + 'px';
        });
        document.addEventListener('mouseup', function() {
            if (!dragging) return;
            dragging = false;
            document.body.style.cursor = '';
        });
    })();

	// ---- Controls ----
	function adPlayerMinimize() {
		adPlayerMinimized = !adPlayerMinimized;
		const player = document.getElementById('ad-player');
		player.classList.toggle('is-minimized', adPlayerMinimized);
		document.getElementById('ad-minimize-btn').textContent = adPlayerMinimized ? '□' : '—';
	}

	function adPlayerClose() {
		const frame = document.getElementById('ad-viewer-iframe');
		if (frame) frame.src = '';
		document.getElementById('ad-player').style.display = 'none';
	}

	function adLibraryToggle() {
		adLibraryVisible = !adLibraryVisible;
		const drawer = document.getElementById('ad-player-library');
		drawer.classList.toggle('is-open', adLibraryVisible);
		document.getElementById('ad-library-toggle-btn').style.color =
			adLibraryVisible ? '#8b1a1a' : '';
		if (adLibraryVisible && adLibraryItems.length === 0) {
			adLoadLibrary();
		}
	}

	function adLoadLibrary() {
		fetch('/cockpit/after-dark/library')
			.then(r => r.json())
			.then(data => {
				adLibraryItems = data.items || [];
				adRenderLibrary();
			})
			.catch(() => {});
	}

	function adRenderLibrary() {
		const grid = document.getElementById('ad-player-library-grid');
		grid.innerHTML = '';
		if (adLibraryItems.length === 0) {
			grid.innerHTML = '<div style="color:#2a0f0f;font-size:0.55rem;letter-spacing:0.12em;padding:12px;">no videos in library — add URLs to static/after_dark_videos.txt</div>';
			return;
		}
		adLibraryItems.forEach(function(item, idx) {
			const tile = document.createElement('div');
			tile.className = 'ad-library-tile';
			tile.textContent = item.name;
			tile.onclick = function() { adPlayVideo(item, idx); };
			grid.appendChild(tile);
		});
	}

	function adPlayVideo(item, idx) {
		adCurrentIdx = idx;
		adQueueActive = false;   // playing a library item exits queue mode

		// Close library drawer
		adLibraryVisible = false;
		document.getElementById('ad-player-library').classList.remove('is-open');
		document.getElementById('ad-library-toggle-btn').style.color = '';

		// Show player if it was closed — clear the inline 'none' so the
		// mode-after-dark CSS (display: flex column) can take over.
		const player = document.getElementById('ad-player');
		player.style.display = '';

		// If minimized, restore
		if (adPlayerMinimized) adPlayerMinimize();

		const frame = document.getElementById('ad-viewer-iframe');
		// autoplay=1 starts without a click; muted=1 is required for autoplay
		// to actually fire (browser policy) and matches the "calm by default"
		// preference — the embed has its own unmute control.
		const sep = item.url.indexOf('?') >= 0 ? '&' : '?';
		frame.src = item.url + sep + 'autoplay=1&muted=1';

		// Highlight active tile
		document.querySelectorAll('.ad-library-tile').forEach(function(t, i) {
			t.classList.toggle('is-playing', i === idx);
		});
	}

	function adPlayNext() {
		// If a paste-queue is active, NEXT steps through it in order.
		if (adQueueActive && adQueue.length > 0) { adQueueNext(); return; }
		// Lazy-load the library on first NEXT so the player can be opened
		// from outside the LIB drawer.
		if (adLibraryItems.length === 0) {
			fetch('/cockpit/after-dark/library')
				.then(r => r.json())
				.then(data => {
					adLibraryItems = data.items || [];
					adRenderLibrary();
					if (adLibraryItems.length > 0) adPlayNext();
				})
				.catch(() => {});
			return;
		}
		if (adLibraryItems.length === 1) {
			// Re-play the only item (re-set src to nudge the embed to restart).
			adPlayVideo(adLibraryItems[0], 0);
			return;
		}
		let nextIdx;
		do {
			nextIdx = Math.floor(Math.random() * adLibraryItems.length);
		} while (nextIdx === adCurrentIdx);
		adPlayVideo(adLibraryItems[nextIdx], nextIdx);
	}

	// ---- Ad-hoc paste queue ----------------------------------------
	// Paste URLs, play through them in order. NEXT steps the queue; an
	// optional AUTO timer advances hands-free (PH embeds are cross-origin,
	// so we can't detect the actual video-end — the timer is the workaround).

	function adQueueToggle() {
		adQueueVisible = !adQueueVisible;
		document.getElementById('ad-player-queue').classList.toggle('is-open', adQueueVisible);
		document.getElementById('ad-queue-toggle-btn').style.color = adQueueVisible ? '#8b1a1a' : '';
	}

	// Parse one pasted line into a Pornhub embed entry, or null. Accepts a
	// page/share URL (viewkey=…), an /embed/<key> URL, or a bare viewkey,
	// with an optional '|label' suffix. Mirrors the server's after_dark_library.
	function adParseEntry(line) {
		line = (line || '').trim();
		if (!line || line.charAt(0) === '#') return null;
		let label = '';
		const bar = line.indexOf('|');
		if (bar >= 0) { label = line.slice(bar + 1).trim(); line = line.slice(0, bar).trim(); }
		let vk = null, m;
		if ((m = line.match(/viewkey=([A-Za-z0-9]+)/))) vk = m[1];
		else if ((m = line.match(/\/embed\/([A-Za-z0-9]+)/))) vk = m[1];
		else if (/^[A-Za-z0-9]+$/.test(line)) vk = line;
		if (!vk) return null;
		return { url: 'https://www.pornhub.com/embed/' + vk, label: label || vk };
	}

	function adParseInput() {
		return document.getElementById('ad-queue-input').value
			.split('\n').map(adParseEntry).filter(Boolean);
	}

	function adQueueLoad() {
		const items = adParseInput();
		if (items.length === 0) { adSetQueueStatus('no valid URLs'); return; }
		adQueue = items;
		adQueueIdx = -1;
		adQueueActive = true;
		adRenderQueue();
		adQueuePlay(0);
	}

	// '+ ADD' appends pasted URLs to a running queue without restarting it.
	function adQueueAddFromInput() {
		const items = adParseInput();
		if (items.length === 0) { adSetQueueStatus('no valid URLs'); return; }
		const wasEmpty = adQueue.length === 0;
		adQueue = adQueue.concat(items);
		document.getElementById('ad-queue-input').value = '';
		adQueueActive = true;
		adRenderQueue();
		if (wasEmpty) adQueuePlay(0);
	}

	function adQueuePlay(idx) {
		if (idx < 0 || idx >= adQueue.length) return;
		adQueueIdx = idx;
		adQueueActive = true;

		const player = document.getElementById('ad-player');
		player.style.display = '';
		if (adPlayerMinimized) adPlayerMinimize();

		const frame = document.getElementById('ad-viewer-iframe');
		const url = adQueue[idx].url;
		const sep = url.indexOf('?') >= 0 ? '&' : '?';
		frame.src = url + sep + 'autoplay=1&muted=1';
		adRenderQueue();
	}

	function adQueueNext() {
		if (adQueue.length === 0) return;
		adQueuePlay((adQueueIdx + 1) % adQueue.length);   // loop at the end
	}

	function adQueuePrev() {
		if (adQueue.length === 0) return;
		adQueuePlay((adQueueIdx - 1 + adQueue.length) % adQueue.length);
	}

	function adQueueClear() {
		adQueue = [];
		adQueueIdx = -1;
		adQueueActive = false;
		adStopAuto();
		document.getElementById('ad-queue-input').value = '';
		adRenderQueue();
	}

	function adStopAuto() {
		if (adAutoTimer) { clearInterval(adAutoTimer); adAutoTimer = null; }
		const btn = document.getElementById('ad-queue-auto-btn');
		if (btn) { btn.textContent = 'AUTO ○'; btn.style.color = ''; }
	}

	function adQueueToggleAuto() {
		if (adAutoTimer) { adStopAuto(); adSetQueueStatus(''); return; }
		if (adQueue.length === 0) { adSetQueueStatus('load a queue first'); return; }
		let min = parseInt(document.getElementById('ad-queue-auto-min').value, 10);
		if (!(min >= 1)) min = 10;
		if (min > 180) min = 180;
		adAutoTimer = setInterval(adQueueNext, min * 60000);
		const btn = document.getElementById('ad-queue-auto-btn');
		btn.textContent = 'AUTO ●';
		btn.style.color = '#e05050';
		adSetQueueStatus('auto every ' + min + ' min');
	}

	function adSetQueueStatus(msg) {
		const el = document.getElementById('ad-queue-status');
		if (el) el.textContent = msg || '';
	}

	function adRenderQueue() {
		const list = document.getElementById('ad-queue-list');
		if (!list) return;
		list.innerHTML = '';
		if (adQueue.length === 0) { adSetQueueStatus(''); return; }
		adQueue.forEach(function(item, i) {
			const row = document.createElement('div');
			row.className = 'ad-queue-row' + (i === adQueueIdx ? ' is-playing' : '');
			const label = document.createElement('span');
			label.className = 'ad-queue-label';
			label.textContent = (i + 1) + '. ' + item.label;
			label.onclick = function() { adQueuePlay(i); };
			const del = document.createElement('button');
			del.className = 'ad-queue-del';
			del.textContent = '✕';
			del.title = 'remove';
			del.onclick = function(e) { e.stopPropagation(); adQueueRemove(i); };
			row.appendChild(label);
			row.appendChild(del);
			list.appendChild(row);
		});
		if (!adAutoTimer) adSetQueueStatus('▶ ' + (adQueueIdx + 1) + ' / ' + adQueue.length);
	}

	function adQueueRemove(i) {
		if (i < 0 || i >= adQueue.length) return;
		adQueue.splice(i, 1);
		if (adQueue.length === 0) { adQueueClear(); return; }
		if (i < adQueueIdx) adQueueIdx--;
		else if (i === adQueueIdx) adQueueIdx = Math.min(adQueueIdx, adQueue.length - 1);
		adRenderQueue();
	}

	// ============================================================
	// AFTER DARK — MUSIC PLAYER
	// ============================================================

	let adMusicItems = [];
	let adMusicIndex = 0;
	let adMusicPlaying = false;
	let adMusicShuffle_on = false;

	const adAudio = document.getElementById('ad-audio');

	function adLoadMusic() {
        fetch('/cockpit/after-dark/music')
            .then(r => r.json())
            .then(data => {
                adMusicItems = data.items || [];
                if (adMusicItems.length > 0) {
                    // Shuffle on by default in After Dark
                    adMusicShuffle_on = true;
                    document.getElementById('ad-shuffle-btn').style.color = '#c04040';
                    // Start on random track
                    const startIdx = Math.floor(Math.random() * adMusicItems.length);
                    adMusicIndex = startIdx;
                    adMusicSetTrack(startIdx, true);
                }
            })
            .catch(() => {});
    }

	function adMusicSetTrack(idx, autoplay) {
		if (adMusicItems.length === 0) return;
		adMusicIndex = ((idx % adMusicItems.length) + adMusicItems.length) % adMusicItems.length;
		const track = adMusicItems[adMusicIndex];
		adAudio.src = track.url;
		adAudio.load();
		document.getElementById('ad-track-name').textContent =
			track.name.replace(/\.[^.]+$/, '').replace(/[-_]/g, ' ');
		if (autoplay) {
			adAudio.play().then(() => {
				adMusicPlaying = true;
				document.getElementById('ad-play-btn').textContent = '❚❚ PAUSE';
				document.getElementById('ad-play-btn').classList.add('is-playing');
			}).catch(() => {});
		}
	}

	function adMusicToggle() {
		if (adMusicPlaying) {
			adAudio.pause();
			adMusicPlaying = false;
			document.getElementById('ad-play-btn').textContent = '▶ PLAY';
			document.getElementById('ad-play-btn').classList.remove('is-playing');
		} else {
			adAudio.play().then(() => {
				adMusicPlaying = true;
				document.getElementById('ad-play-btn').textContent = '❚❚ PAUSE';
				document.getElementById('ad-play-btn').classList.add('is-playing');
			}).catch(() => {});
		}
	}

	function adMusicPrev() {
		adMusicSetTrack(adMusicIndex - 1, adMusicPlaying);
	}

	function adMusicNext() {
        let nextIdx;
        if (adMusicShuffle_on && adMusicItems.length > 1) {
            do {
                nextIdx = Math.floor(Math.random() * adMusicItems.length);
            } while (nextIdx === adMusicIndex);
        } else {
            nextIdx = adMusicIndex + 1;
        }
        adMusicSetTrack(nextIdx, adMusicPlaying);
    }

	function adMusicShuffle() {
		adMusicShuffle_on = !adMusicShuffle_on;
		document.getElementById('ad-shuffle-btn').style.color = adMusicShuffle_on ? '#8b1a1a' : '';
	}

	function adMusicVolume(val) {
		adAudio.volume = parseFloat(val);
	}

	adAudio.addEventListener('ended', function() {
		adMusicNext();
	});

	// ============================================================
    // WAVEFORM VISUALIZER
    // ============================================================
    (function initWaveform() {
        const canvas = document.getElementById('ad-waveform-canvas');
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        let analyser = null;
        let animFrame = null;
        let source = null;

        // Color palette — crimson to amber to gold, cycling
        const COLORS = [
            '#8b1a1a', '#c04040', '#e05555',
            '#c05020', '#d4880a', '#f5b332',
            '#c04040', '#8b1a1a'
        ];

        function setupAnalyser() {
            if (analyser) return;
            if (!cockpitAudioCtx) {
                cockpitAudioCtx = new (window.AudioContext || window.webkitAudioContext)();
            }
            if (cockpitAudioCtx.state === 'suspended') cockpitAudioCtx.resume();

            analyser = cockpitAudioCtx.createAnalyser();
            analyser.fftSize = 128;
            analyser.smoothingTimeConstant = 0.75;

            try {
                source = cockpitAudioCtx.createMediaElementSource(adAudio);
                source.connect(analyser);
                analyser.connect(cockpitAudioCtx.destination);
            } catch(e) {
                // Already connected
            }
        }

        function drawWaveform() {
            animFrame = requestAnimationFrame(drawWaveform);

            const W = canvas.offsetWidth;
            const H = canvas.offsetHeight;
            if (canvas.width !== W) canvas.width = W;
            if (canvas.height !== H) canvas.height = H;

            ctx.clearRect(0, 0, W, H);

            if (!analyser) {
                // Draw flat idle bars
                drawIdleBars(W, H);
                return;
            }

            const bufferLen = analyser.frequencyBinCount;
            const dataArray = new Uint8Array(bufferLen);
            analyser.getByteFrequencyData(dataArray);

            const barCount = 48;
            const barW = (W / barCount) * 0.7;
            const gap = (W / barCount) * 0.3;

            for (let i = 0; i < barCount; i++) {
                const dataIdx = Math.floor((i / barCount) * bufferLen);
                const value = dataArray[dataIdx] / 255;
                const barH = Math.max(2, value * H);

                // Color cycles across bars + shifts over time
                const colorIdx = Math.floor((i / barCount) * COLORS.length);
                const nextColorIdx = (colorIdx + 1) % COLORS.length;
                const t = (Date.now() / 1000 + i * 0.1) % 1;

                // Interpolate between two palette colors
                const grad = ctx.createLinearGradient(0, H - barH, 0, H);
                grad.addColorStop(0, COLORS[nextColorIdx]);
                grad.addColorStop(1, COLORS[colorIdx]);

                ctx.fillStyle = grad;

                // Glow effect on tall bars
                if (value > 0.6) {
                    ctx.shadowBlur = 8 + value * 12;
                    ctx.shadowColor = COLORS[nextColorIdx];
                } else {
                    ctx.shadowBlur = 0;
                }

                const x = i * (barW + gap);
                // Mirror: draw bar from center both up and down
                const centerY = H / 2;
                const halfH = barH / 2;

                ctx.beginPath();
                ctx.roundRect(x, centerY - halfH, barW, barH, 1);
                ctx.fill();
            }
            ctx.shadowBlur = 0;
        }

        function drawIdleBars(W, H) {
            const barCount = 48;
            const barW = (W / barCount) * 0.7;
            const gap = (W / barCount) * 0.3;
            const centerY = H / 2;
            const t = Date.now() / 2000;

            for (let i = 0; i < barCount; i++) {
                const idleH = 2 + Math.sin(t * 2 + i * 0.3) * 1.5;
                const colorIdx = Math.floor((i / barCount) * COLORS.length);
                ctx.fillStyle = COLORS[colorIdx];
                ctx.globalAlpha = 0.3;
                ctx.beginPath();
                ctx.roundRect(i * (barW + gap), centerY - idleH / 2, barW, idleH, 1);
                ctx.fill();
            }
            ctx.globalAlpha = 1;
        }

        // Start animation loop
        drawWaveform();

        // Hook into audio play
        adAudio.addEventListener('play', function() {
            setupAnalyser();
        });

        adAudio.addEventListener('pause', function() {
            // Keep drawing — just shows decay
        });

        // Expose for external use
        window._adWaveformSetup = setupAnalyser;
    })();

	if (COCKPIT_MODE === 'after-dark') {
        adLoadMusic();
        // Autoplay unblock — start music on first interaction
        document.addEventListener('click', function startOnInteraction() {
            if (!adMusicPlaying && adMusicItems.length > 0) {
                adAudio.play().then(() => {
                    adMusicPlaying = true;
                    document.getElementById('ad-play-btn').textContent = '❚❚ PAUSE';
                    document.getElementById('ad-play-btn').classList.add('is-playing');
                }).catch(() => {});
            }
            document.removeEventListener('click', startOnInteraction);
        }, { once: true });
    }

	// ============================================================
	// AFTER DARK — STATUS LINE
	// ============================================================

	const adComms = window.COCKPIT_AD_COMMS || [];

	(function initAdStatusLine() {
		if (adComms.length === 0) return;
		const el = document.getElementById('ad-status-line');
		let idx = 0;

		function showNext() {
			el.style.opacity = '0';
			setTimeout(function() {
				el.textContent = adComms[idx % adComms.length];
				idx++;
				el.style.opacity = '1';
			}, 1200);
		}

		showNext();
		setInterval(showNext, 8000);
	})();

	// ============================================================
	// BRAIN DUMP — Ctrl+Space (anywhere)
	// ============================================================

	document.addEventListener('keydown', function(e) {
		if (e.ctrlKey && e.code === 'Space') {
			e.preventDefault();
			brainDumpOpen();
		}
	});

	function brainDumpOpen() {
		const overlay = document.getElementById('brain-dump-overlay');
		overlay.classList.add('is-open');
		setTimeout(function() {
			document.getElementById('brain-dump-textarea').focus();
		}, 50);
	}

	function brainDumpClose() {
		document.getElementById('brain-dump-overlay').classList.remove('is-open');
		document.getElementById('brain-dump-textarea').value = '';
		document.getElementById('brain-dump-tag').value = '';
	}

	document.getElementById('brain-dump-overlay').addEventListener('click', function(e) {
		if (e.target === this) brainDumpClose();
	});

	document.getElementById('brain-dump-textarea').addEventListener('keydown', function(e) {
		if (e.key === 'Enter' && !e.shiftKey) {
			e.preventDefault();
			brainDumpSave();
		}
	});

	function brainDumpSave() {
		const text = document.getElementById('brain-dump-textarea').value.trim();
		const tag  = document.getElementById('brain-dump-tag').value;
		if (!text) { brainDumpClose(); return; }

		const fd = new FormData();
		fd.append('title', text);
		if (tag) fd.append('tag', tag);

		fetch('/below-deck/add', { method: 'POST', body: fd })
			.then(r => r.json())
			.then(data => {
				if (data.success) {
					playChirp(880, 'sine');
					brainDumpClose();
				}
			})
			.catch(() => brainDumpClose());
	}

	// ============================================================
	// QUICK TRANSMISSION — Ctrl+Shift+U (work + after-dark only)
	// ============================================================

	document.addEventListener('keydown', function(e) {
		if (e.ctrlKey && e.shiftKey && (e.key === 'U' || e.key === 'u')) {
			if (COCKPIT_MODE !== 'work' && COCKPIT_MODE !== 'after-dark') return;
			e.preventDefault();
			quickTxOpen();
		}
	});

	function quickTxOpen() {
		const overlay = document.getElementById('quick-tx-overlay');
		overlay.classList.add('is-open');
		setTimeout(function() {
			document.getElementById('quick-tx-textarea').focus();
		}, 50);
	}

	function quickTxClose() {
		document.getElementById('quick-tx-overlay').classList.remove('is-open');
		document.getElementById('quick-tx-textarea').value = '';
	}

	document.getElementById('quick-tx-overlay').addEventListener('click', function(e) {
		if (e.target === this) quickTxClose();
	});

	document.getElementById('quick-tx-textarea').addEventListener('keydown', function(e) {
		if (e.key === 'Enter' && !e.shiftKey) {
			e.preventDefault();
			quickTxSend();
		}
	});

	function quickTxSend() {
		const text = document.getElementById('quick-tx-textarea').value.trim();
		if (!text) { quickTxClose(); return; }

		const fd = new FormData();
		fd.append('status', text);

		fetch('/publish', { method: 'POST', body: fd })
			.then(r => {
				if (r.ok) {
					playChirp(880, 'sine');
					quickTxClose();
				}
			})
			.catch(() => quickTxClose());
	}

	// ============================================================
	// COMMAND PALETTE — Ctrl+K
	// ============================================================

	const CMD_ITEMS = [
		{ icon: '⌘', label: 'Command Deck',   hint: '/command-deck/', action: () => window.location.href = '/command-deck/' },
		{ icon: '▼', label: 'Below Deck',     hint: '/below-deck',    action: () => window.location.href = '/below-deck' },
		{ icon: '⌇', label: 'Publish Status', hint: '/publish',       action: () => window.location.href = '/publish' },
		{ icon: '✦', label: 'Brain Dump',     hint: 'Ctrl+Space',     action: () => { cmdClose(); brainDumpOpen(); } },
		{ icon: '▶', label: 'Toggle YouTube Player', hint: 'Ctrl+Shift+Y', action: () => { cmdClose(); ytPlayerToggle(); } },
		{ icon: '⏎', label: 'Refresh',        hint: '',               action: () => window.location.reload() },
	];

	function getAllCmdItems() {
		const timerItems = (typeof window.getTimerCmdItems === 'function') ? window.getTimerCmdItems() : [];
		return CMD_ITEMS.concat(timerItems);
	}

	let cmdFiltered = [...CMD_ITEMS];
	let cmdSelected = 0;

	document.addEventListener('keydown', function(e) {
		if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
			e.preventDefault();
			cmdOpen();
		}
		// Cmd/Ctrl+Shift+Y — show/hide the floating YouTube player
		if ((e.ctrlKey || e.metaKey) && e.shiftKey && (e.key === 'y' || e.key === 'Y')) {
			e.preventDefault();
			ytPlayerToggle();
		}
	});

	function cmdOpen() {
		const overlay = document.getElementById('cmd-palette-overlay');
		overlay.classList.add('is-open');
		cmdFiltered = getAllCmdItems();
		cmdSelected = 0;
		cmdRender();
		setTimeout(function() {
			const inp = document.getElementById('cmd-palette-input');
			inp.value = '';
			inp.focus();
		}, 50);
	}

	function cmdClose() {
		document.getElementById('cmd-palette-overlay').classList.remove('is-open');
		document.getElementById('cmd-palette-input').value = '';
	}

	document.getElementById('cmd-palette-overlay').addEventListener('click', function(e) {
		if (e.target === this) cmdClose();
	});

	function cmdFilter() {
		const q = document.getElementById('cmd-palette-input').value.toLowerCase();
		cmdFiltered = getAllCmdItems().filter(item => item.label.toLowerCase().includes(q));
		cmdSelected = 0;
		cmdRender();
	}

	function cmdRender() {
		const list = document.getElementById('cmd-palette-list');
		list.innerHTML = '';
		cmdFiltered.forEach(function(item, idx) {
			const div = document.createElement('div');
			div.className = 'cmd-item' + (idx === cmdSelected ? ' is-selected' : '');
			div.innerHTML =
				'<span class="cmd-item-icon">' + item.icon + '</span>' +
				'<span class="cmd-item-label">' + item.label + '</span>' +
				'<span class="cmd-item-hint">' + item.hint + '</span>';
			div.onclick = function() { item.action(); cmdClose(); };
			list.appendChild(div);
		});
	}

	function cmdKeydown(e) {
		if (e.key === 'ArrowDown') {
			e.preventDefault();
			cmdSelected = Math.min(cmdSelected + 1, cmdFiltered.length - 1);
			cmdRender();
		} else if (e.key === 'ArrowUp') {
			e.preventDefault();
			cmdSelected = Math.max(cmdSelected - 1, 0);
			cmdRender();
		} else if (e.key === 'Enter') {
			e.preventDefault();
			if (cmdFiltered[cmdSelected]) {
				cmdFiltered[cmdSelected].action();
				cmdClose();
			}
		} else if (e.key === 'Escape') {
			cmdClose();
		}
	}


