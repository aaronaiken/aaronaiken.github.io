
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
			cockpitDetachDock(player);                 // pop out of the dock into a floating window
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

	// ---- keep dragged floating panels on-screen when the viewport shrinks ----
	// (e.g. unplugging an external display) — otherwise a panel saved at external-monitor
	// coordinates is stranded off the smaller laptop screen with its resize grip unreachable.
	(function keepFloatersOnScreen() {
		function clampOne(id) {
			const elp = document.getElementById(id);
			if (!elp || getComputedStyle(elp).display === 'none') return;
			const left = parseFloat(elp.style.left), top = parseFloat(elp.style.top);
			if (isNaN(left) && isNaN(top)) return;   // still on its default corner anchor — always on-screen
			const maxL = Math.max(0, window.innerWidth  - elp.offsetWidth);
			const maxT = Math.max(0, window.innerHeight - elp.offsetHeight);
			if (!isNaN(left)) { elp.style.left = Math.min(Math.max(0, left), maxL) + 'px'; elp.style.right = 'auto'; }
			if (!isNaN(top))  { elp.style.top  = Math.min(Math.max(0, top),  maxT) + 'px'; elp.style.bottom = 'auto'; }
		}
		function clampAll() { ['ad-player', 'yt-player', 'focus-timer', 'ad-music-player'].forEach(clampOne); }
		let t;
		window.addEventListener('resize', function () { clearTimeout(t); t = setTimeout(clampAll, 120); });
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
			// keep the WHOLE player within the viewport (both dimensions) so the bottom-right resize
			// grip is always reachable — width-only wasn't enough: the huge video made it taller than
			// the screen, stranding the grip below the bottom edge
			const maxByH = (window.innerHeight - titlebarH() - 40) * NATIVE_W / NATIVE_H;
			newW = Math.max(320, Math.min(newW, window.innerWidth - 24, maxByH));
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

		// re-fit to the viewport when it shrinks (unplug external display) — keeps the grip reachable
		let fitT;
		window.addEventListener('resize', function () {
			clearTimeout(fitT);
			fitT = setTimeout(function () { applySize(parseFloat(player.style.width) || 481); }, 120);
		});

		// escape hatch: double-click the titlebar to snap back to default size + corner
		const tbar = document.getElementById('ad-player-titlebar');
		if (tbar) tbar.addEventListener('dblclick', function () {
			player.style.left = ''; player.style.top = ''; player.style.right = ''; player.style.bottom = '';
			localStorage.removeItem('ad-player-pos');
			applySize(481);
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
	// ---- DOCK ⇄ FLOAT for rail players (YT / Music) ----
	// A rail summons its player DOCKED inline right below the rail (slides open).
	// Dragging the player's titlebar pops it out into a free-floating window.
	function cockpitDockToggle(playerId, railId) {
		var p = document.getElementById(playerId);
		if (!p) return;
		var shown = getComputedStyle(p).display !== 'none';
		if (shown) { p.style.display = 'none'; p.classList.remove('is-docked'); return; }
		var rail = document.getElementById(railId);
		if (rail && rail.offsetParent !== null) {
			rail.insertAdjacentElement('afterend', p);
			p.classList.add('is-docked');
			p.style.position = ''; p.style.left = ''; p.style.top = ''; p.style.right = ''; p.style.bottom = ''; p.style.width = '';
		} else {
			p.classList.remove('is-docked');   // no visible rail → float it
		}
		p.style.display = 'flex';
	}
	function cockpitDetachDock(player) {
		if (!player || !player.classList.contains('is-docked')) return;
		var r = player.getBoundingClientRect();
		document.body.appendChild(player);
		player.classList.remove('is-docked');
		player.style.position = 'fixed';
		player.style.left = r.left + 'px';
		player.style.top = r.top + 'px';
		player.style.width = r.width + 'px';
		player.style.right = 'auto';
		player.style.bottom = 'auto';
	}
	window.cockpitDetachDock = cockpitDetachDock;

	function ytPlayerToggle() { cockpitDockToggle('yt-player', 'rail-yt'); }

	function ytLibraryToggle() {
		ytLibraryVisible = !ytLibraryVisible;
		const drawer = document.getElementById('yt-player-library');
		drawer.classList.toggle('is-open', ytLibraryVisible);
		document.getElementById('yt-library-toggle-btn').style.color =
			ytLibraryVisible ? '#b45309' : '';
		if (ytLibraryVisible && ytLibraryItems.length === 0) ytLoadLibrary();
		// Drawers overlay the video — only one open at a time.
		if (ytLibraryVisible && ytQueueVisible) {
			ytQueueVisible = false;
			document.getElementById('yt-player-queue').classList.remove('is-open');
			document.getElementById('yt-queue-toggle-btn').style.color = '';
		}
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
			const label = document.createElement('span');
			label.className = 'lib-tile-label';
			label.textContent = item.name;
			label.onclick = function () { ytPlayVideo(item, idx); };
			const del = document.createElement('button');
			del.className = 'lib-tile-del';
			del.textContent = '✕';
			del.title = 'remove from library';
			del.onclick = function (e) { e.stopPropagation(); ytLibDelete(item, del); };
			tile.appendChild(label);
			tile.appendChild(del);
			grid.appendChild(tile);
		});
	}

	// Save the CURRENT video to the persistent library (works from queue or a playlist —
	// uses what's actually playing). Feedback flashes on the +LIB button.
	function ytAddCurrentToLib(btn) {
		var id = null, label = '';
		try {
			if (ytPlayer && ytPlayer.getVideoData) {
				var d = ytPlayer.getVideoData() || {};
				id = d.video_id || null; label = d.title || '';
			}
		} catch (e) {}
		if (!id) {
			var cur = ytQueueActive ? ytQueue[ytQueueIdx] : ytLibraryItems[ytCurrentIdx];
			if (cur) { id = cur.id || ytVideoId(cur.url); label = cur.label || cur.name || ''; }
		}
		if (!id) { ytFlashBtn(btn, 'NOTHING'); return; }
		fetch('/cockpit/after-dark/youtube/add', {
			method: 'POST', headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ id: id, label: label })
		}).then(function (r) { return r.json(); }).then(function (res) {
			ytFlashBtn(btn, res.ok ? 'SAVED ✓' : 'ERR');
			if (ytLibraryVisible) ytLoadLibrary();
		}).catch(function () { ytFlashBtn(btn, 'ERR'); });
	}

	// Backfill real titles for already-saved YouTube items that only show an id.
	// Bounded server-side; re-run automatically while there's more to fill.
	function ytRefreshTitles(btn) {
		var status = document.getElementById('yt-library-refresh-status');
		if (btn) btn.disabled = true;
		if (status) status.textContent = 'fetching…';
		fetch('/cockpit/after-dark/youtube/refresh-titles', { method: 'POST' })
			.then(function (r) { return r.json(); }).then(function (res) {
				if (ytLibraryVisible) ytLoadLibrary();
				// Only auto-continue when we hit the per-call cap (more to fill).
				// A leftover 'remaining' otherwise means unresolvable (private /
				// deleted) — don't loop on those.
				if (res.updated >= 40 && res.remaining > 0) {
					if (status) status.textContent = 'updated ' + res.updated + ' — continuing…';
					setTimeout(function () { ytRefreshTitles(btn); }, 400);
					return;
				}
				if (btn) btn.disabled = false;
				if (status) {
					var msg = res.updated > 0 ? 'done — updated ' + res.updated : 'nothing to update';
					if (res.remaining > 0) msg += ' — ' + res.remaining + ' couldn’t resolve';
					status.textContent = msg;
				}
				setTimeout(function () { if (status) status.textContent = ''; }, 4000);
			}).catch(function () {
				if (btn) btn.disabled = false;
				if (status) status.textContent = 'error';
			});
	}

	function ytLibDelete(item, btn) {
		if (!item || !item.id) return;
		if (!confirm('remove "' + (item.name || item.id) + '" from the library?')) return;
		if (btn) btn.disabled = true;
		fetch('/cockpit/after-dark/youtube/delete', {
			method: 'POST', headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ id: item.id })
		}).then(function (r) { return r.json(); }).then(function () { ytLoadLibrary(); })
			.catch(function () { if (btn) btn.disabled = false; });
	}

	function ytFlashBtn(btn, txt) {
		if (!btn) return;
		btn.textContent = txt;
		setTimeout(function () { btn.textContent = '+LIB'; }, 1400);
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
		if (!window.YT) return;
		if (e.data === YT.PlayerState.PLAYING) cockpitUpdateChipIcon(true);
		else if (e.data === YT.PlayerState.PAUSED) cockpitUpdateChipIcon(false);
		// Fill the chip with the real title once the (possibly resumed) video loads.
		if ((e.data === YT.PlayerState.PLAYING || e.data === YT.PlayerState.CUED) && activeMediaPlayer === 'yt') {
			try {
				var _title = (ytPlayer.getVideoData() || {}).title;
				var _lab = document.getElementById('np-label');
				if (_title && _lab) _lab.textContent = _title;
			} catch (e2) {}
		}
		if (e.data !== YT.PlayerState.ENDED) return;
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
		document.getElementById('yt-queue-toggle-btn').style.color = ytQueueVisible ? '#b45309' : '';
		// Drawers overlay the video — only one open at a time.
		if (ytQueueVisible && ytLibraryVisible) {
			ytLibraryVisible = false;
			document.getElementById('yt-player-library').classList.remove('is-open');
			document.getElementById('yt-library-toggle-btn').style.color = '';
		}
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
		b.textContent = 'SHUFFLE ' + (ytShuffle ? '●' : '○'); b.style.color = ytShuffle ? '#b45309' : '';
		ytSaveQueue();
	}

	function ytQueueToggleLoop() {
		ytLoop = !ytLoop;
		var b = document.getElementById('yt-queue-loop-btn');
		b.textContent = 'LOOP ' + (ytLoop ? '●' : '○'); b.style.color = ytLoop ? '#b45309' : '';
		ytSaveQueue();
	}

	function ytSetQueueStatus(msg) { var el = document.getElementById('yt-queue-status'); if (el) el.textContent = msg || ''; }
	function ytSetNowPlaying(txt) {
		var el = document.getElementById('yt-now-playing');
		if (el) el.textContent = txt ? ('now: ' + txt) : '';
		cockpitSetNowPlaying('yt', txt);
	}

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
			if (sb) { sb.textContent = 'SHUFFLE ' + (ytShuffle ? '●' : '○'); sb.style.color = ytShuffle ? '#b45309' : ''; }
			var lb = document.getElementById('yt-queue-loop-btn');
			if (lb) { lb.textContent = 'LOOP ' + (ytLoop ? '●' : '○'); lb.style.color = ytLoop ? '#b45309' : ''; }
			ytRenderQueue();
			if (ytQueue.length) ytSetQueueStatus(ytQueue.length + ' saved — PLAY QUEUE to resume');
		} catch (e) {}
	}
	document.addEventListener('DOMContentLoaded', function () {
		ytLoadQueue();
		adLoadQueue();         // restore the PH queue saved from a previous session
		ytRestoreProgress();   // resume YT at the saved position (cued; a tap plays)
		adRestoreLast();       // restore the PH chip to the last item
		setInterval(ytSaveProgress, 5000);
		window.addEventListener('pagehide', ytSaveProgress);
	});

	// ============================================================
	// Shared NOW-PLAYING chip — surfaces the active media player in
	// the status bar with mini controls. Both players feed it.
	// ============================================================
	let activeMediaPlayer = null;   // 'yt' | 'ad'

	function cockpitSetNowPlaying(source, label) {
		activeMediaPlayer = source;
		var chip = document.getElementById('now-playing-chip');
		if (!chip) return;
		var txt = (label || '').trim();
		if (!txt || txt === 'queue ended') { chip.style.display = 'none'; return; }
		var lab = document.getElementById('np-label');
		var icon = document.getElementById('np-icon');
		var pp = document.getElementById('np-playpause');
		if (lab) lab.textContent = txt;
		if (icon) icon.textContent = (source === 'ad') ? '▤' : '♪';
		// play/pause only works for YouTube (its API); the PH embed owns its own playback.
		if (pp) pp.style.display = (source === 'yt') ? '' : 'none';
		chip.style.display = '';
	}

	function cockpitMediaNext() {
		if (activeMediaPlayer === 'ad') { (adQueueActive ? adQueueNext : adPlayNext)(); }
		else if (activeMediaPlayer === 'yt') { if (ytQueueActive) ytQueueAdvance(); else ytPlayNext(); }
	}

	function cockpitMediaPlayPause() {
		if (activeMediaPlayer !== 'yt' || !ytPlayer) return;
		try {
			if (ytPlayer.getPlayerState() === 1) ytPlayer.pauseVideo();
			else ytPlayer.playVideo();
		} catch (e) {}
	}

	function cockpitMediaShow() {
		if (activeMediaPlayer === 'ad') {
			var p = document.getElementById('ad-player'); if (p) p.style.display = 'flex';  // flex column (see adPlayVideo)
			// after a refresh the iframe is empty — reload the last item (PH can't resume position)
			var f = document.getElementById('ad-viewer-iframe');
			if (f && !f.getAttribute('src') && adResumeUrl) {
				var sep = adResumeUrl.indexOf('?') >= 0 ? '&' : '?';
				f.src = adResumeUrl + sep + 'autoplay=1&muted=1';
			}
		} else {
			var y = document.getElementById('yt-player'); if (y) y.style.display = '';
			if (ytPlayer && ytPlayer.playVideo) { try { ytPlayer.playVideo(); } catch (e) {} }
		}
	}

	function cockpitUpdateChipIcon(playing) {
		var pp = document.getElementById('np-playpause');
		if (pp && activeMediaPlayer === 'yt') pp.textContent = playing ? '❚❚' : '▶';
	}

	// ---- Resume-across-refresh ----
	// YT: the IFrame API gives us the video id + exact position, so we save both periodically and on
	// unload, then CUE the video at that spot on load (a tap resumes — autoplay-on-load is browser-blocked).
	let adResumeUrl = null;   // PH: last-played embed url (no API → position can't be recovered)

	function ytSaveProgress() {
		try {
			if (!ytPlayer || !ytPlayer.getCurrentTime) return;
			var vid = (ytPlayer.getVideoData() || {}).video_id;
			if (!vid) return;
			localStorage.setItem('cockpit-yt-progress', JSON.stringify({
				videoId: vid, time: Math.floor(ytPlayer.getCurrentTime() || 0),
				queueActive: ytQueueActive, queueIdx: ytQueueIdx
			}));
		} catch (e) {}
	}

	function ytRestoreProgress() {
		try {
			var d = JSON.parse(localStorage.getItem('cockpit-yt-progress') || 'null');
			if (!d || !d.videoId) return;
			if (d.queueActive && ytQueue.length && typeof d.queueIdx === 'number'
			    && d.queueIdx >= 0 && d.queueIdx < ytQueue.length) {
				ytQueueIdx = d.queueIdx; ytQueueActive = true; ytSource = 'queue';
			} else {
				ytSource = 'lib';
			}
			ytEnsurePlayer(function () {
				try { ytPlayer.cueVideoById({ videoId: d.videoId, startSeconds: d.time || 0 }); } catch (e) {}
			});
			var lbl = (ytQueueActive && ytQueue[ytQueueIdx]) ? ytQueue[ytQueueIdx].label : 'your last video';
			cockpitSetNowPlaying('yt', lbl);
			cockpitUpdateChipIcon(false);   // cued/paused — tap to resume
			ytRenderQueue();
		} catch (e) {}
	}

	function adRestoreLast() {
		try {
			var d = JSON.parse(localStorage.getItem('cockpit-ad-lastplayed') || 'null');
			if (!d || !d.url) return;
			adResumeUrl = d.url;
			cockpitSetNowPlaying('ad', d.label || 'video');
		} catch (e) {}
	}

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
			cockpitDetachDock(player);                 // pop out of the dock into a floating window
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
			// keep the whole player within the viewport (both dimensions) so the resize grip stays reachable
			const maxByH = (window.innerHeight - titlebarH() - 40) * ASPECT;
			newW = Math.max(320, Math.min(newW, window.innerWidth - 24, maxByH));
			const newH = Math.round(newW / ASPECT) + titlebarH();
			player.style.width  = newW + 'px';
			player.style.height = newH + 'px';
		}

		try {
			const saved = JSON.parse(localStorage.getItem('yt-player-size'));
			applySize(saved && saved.w ? saved.w : 480);
		} catch (e) { applySize(480); }

		// re-fit to the viewport when it shrinks (unplug external display) — keeps the grip reachable
		let ytFitT;
		window.addEventListener('resize', function () {
			clearTimeout(ytFitT);
			ytFitT = setTimeout(function () { applySize(parseFloat(player.style.width) || 480); }, 120);
		});

		// escape hatch: double-click the titlebar to snap back to default size + corner
		const ytTbar = document.getElementById('yt-player-titlebar');
		if (ytTbar) ytTbar.addEventListener('dblclick', function () {
			player.style.left = ''; player.style.top = ''; player.style.right = ''; player.style.bottom = '';
			localStorage.removeItem('yt-player-pos');
			applySize(480);
		});

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
            cockpitDetachDock(player);                 // pop out of the dock into a floating window
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

	// Show/hide the After Dark video player without touching playback (unlike Close,
	// which clears the iframe). Bound to Cmd/Ctrl+Shift+V + the command palette, so it
	// can be summoned from any mode — not just after-dark.
	function adPlayerToggle() {
		const p = document.getElementById('ad-player');
		if (!p) return;
		// Base CSS hides #ad-player (shown only in after-dark), so an explicit 'flex' is needed to
		// reveal it in normal/work modes — the shown layout is a flex column ('block'/'' break the video).
		const shown = getComputedStyle(p).display !== 'none';
		p.style.display = shown ? 'none' : 'flex';
	}

	// PIN-gate OPENING the ▷ VIDEO player (After Dark PIN, verified server-side).
	// Hiding needs no PIN; the unlock persists for the browser session. Bound to
	// the Ctrl+K palette + Ctrl+Shift+V so the player can't be summoned without it.
	function adPlayerToggleGated() {
		const p = document.getElementById('ad-player');
		if (!p) return;
		const shown = getComputedStyle(p).display !== 'none';
		if (shown || sessionStorage.getItem('videoUnlocked') === '1') { adPlayerToggle(); return; }
		videoPinOpen();
	}

	// Styled inline PIN gate for the ▷ VIDEO player (replaces the raw prompt()).
	// Server-verified; 3 wrong tries in a row cool down for 30s. Unlock is per-session.
	let _videoPinStrikes = 0, _videoPinLockUntil = 0;
	function videoPinOpen() {
		const ov = document.getElementById('video-pin-overlay');
		if (!ov) { adPlayerToggle(); return; }   // graceful fallback if markup absent
		const inp = document.getElementById('video-pin-input');
		const msg = document.getElementById('video-pin-msg');
		if (msg) msg.textContent = '';
		if (inp) { inp.value = ''; inp.disabled = Date.now() < _videoPinLockUntil; }
		ov.classList.add('is-open');
		if (inp && !inp.disabled) setTimeout(function () { inp.focus(); }, 60);
		_videoPinCoolTick();
	}
	function videoPinClose() {
		const ov = document.getElementById('video-pin-overlay');
		if (ov) ov.classList.remove('is-open');
	}
	function _videoPinCoolTick() {
		const msg = document.getElementById('video-pin-msg');
		const inp = document.getElementById('video-pin-input');
		const left = Math.ceil((_videoPinLockUntil - Date.now()) / 1000);
		if (left > 0) {
			if (msg) msg.textContent = 'LOCKED · ' + left + 's';
			if (inp) inp.disabled = true;
			setTimeout(_videoPinCoolTick, 500);
		} else if (inp && inp.disabled) {
			inp.disabled = false; if (msg) msg.textContent = '';
			const ov = document.getElementById('video-pin-overlay');
			if (ov && ov.classList.contains('is-open')) inp.focus();
		}
	}
	function videoPinSubmit() {
		if (Date.now() < _videoPinLockUntil) return;
		const inp = document.getElementById('video-pin-input');
		const box = document.getElementById('video-pin-box');
		const msg = document.getElementById('video-pin-msg');
		const pin = inp ? inp.value.trim() : '';
		if (!pin) return;
		fetch('/cockpit/video-unlock', {
			method: 'POST', headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ pin: pin })
		}).then(function (r) { return r.json(); }).then(function (d) {
			if (d && d.ok) {
				_videoPinStrikes = 0;
				sessionStorage.setItem('videoUnlocked', '1');
				videoPinClose();
				adPlayerToggle();
			} else {
				_videoPinStrikes++;
				if (box) { box.classList.remove('shake'); void box.offsetWidth; box.classList.add('shake'); }
				if (inp) { inp.value = ''; inp.focus(); }
				if (_videoPinStrikes >= 3) {
					_videoPinStrikes = 0;
					_videoPinLockUntil = Date.now() + 30000;
					_videoPinCoolTick();
				} else if (msg) {
					msg.textContent = 'WRONG PIN';
				}
			}
		}).catch(function () { if (msg) msg.textContent = 'ERROR'; });
	}

	function adLibraryToggle() {
		adLibraryVisible = !adLibraryVisible;
		const drawer = document.getElementById('ad-player-library');
		drawer.classList.toggle('is-open', adLibraryVisible);
		document.getElementById('ad-library-toggle-btn').style.color =
			adLibraryVisible ? '#b45309' : '';
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
			const label = document.createElement('span');
			label.className = 'lib-tile-label';
			label.textContent = item.name;
			label.onclick = function() { adPlayVideo(item, idx); };
			const del = document.createElement('button');
			del.className = 'lib-tile-del';
			del.textContent = '✕';
			del.title = 'remove from library';
			del.onclick = function(e) { e.stopPropagation(); adLibDelete(item, del); };
			tile.appendChild(label);
			tile.appendChild(del);
			grid.appendChild(tile);
		});
	}

	// Save the current video (queue or library) to the persistent library.
	function adAddCurrentToLib(btn) {
		var cur = adQueueActive ? adQueue[adQueueIdx] : adLibraryItems[adCurrentIdx];
		if (!cur || !cur.url) { adFlashBtn(btn, 'NOTHING'); return; }
		var m = cur.url.match(/(?:viewkey=|\/embed\/)([A-Za-z0-9]+)/);
		var vk = m ? m[1] : null;
		if (!vk) { adFlashBtn(btn, 'NOTHING'); return; }
		fetch('/cockpit/after-dark/library/add', {
			method: 'POST', headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ id: vk, label: cur.label || cur.name || '' })
		}).then(function(r) { return r.json(); }).then(function(res) {
			adFlashBtn(btn, res.ok ? 'SAVED ✓' : 'ERR');
			if (adLibraryVisible) adLoadLibrary();
		}).catch(function() { adFlashBtn(btn, 'ERR'); });
	}

	// Backfill real titles for already-saved PH items showing only a viewkey.
	// PH is best-effort server-side; some may stay unresolved.
	function adRefreshTitles(btn) {
		var status = document.getElementById('ad-library-refresh-status');
		if (btn) btn.disabled = true;
		if (status) status.textContent = 'fetching…';
		fetch('/cockpit/after-dark/library/refresh-titles', { method: 'POST' })
			.then(function (r) { return r.json(); }).then(function (res) {
				if (adLibraryVisible) adLoadLibrary();
				if (res.updated > 0 && res.remaining > 0 && res.updated >= 40) {
					// Only auto-continue when we hit the per-call cap (there's
					// definitely more we could fill). Otherwise remaining ones
					// are just unresolvable — don't hammer.
					if (status) status.textContent = 'updated ' + res.updated + ' — continuing…';
					setTimeout(function () { adRefreshTitles(btn); }, 400);
					return;
				}
				if (btn) btn.disabled = false;
				if (status) {
					var msg = res.updated > 0 ? 'updated ' + res.updated : 'nothing updated';
					if (res.remaining > 0) msg += ' — ' + res.remaining + ' couldn’t resolve';
					status.textContent = msg;
				}
				setTimeout(function () { if (status) status.textContent = ''; }, 4000);
			}).catch(function () {
				if (btn) btn.disabled = false;
				if (status) status.textContent = 'error';
			});
	}

	function adLibDelete(item, btn) {
		if (!item || !item.id) return;
		if (!confirm('remove "' + (item.name || item.id) + '" from the library?')) return;
		if (btn) btn.disabled = true;
		fetch('/cockpit/after-dark/library/delete', {
			method: 'POST', headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ id: item.id })
		}).then(function(r) { return r.json(); }).then(function() { adLoadLibrary(); })
			.catch(function() { if (btn) btn.disabled = false; });
	}

	function adFlashBtn(btn, txt) {
		if (!btn) return;
		btn.textContent = txt;
		setTimeout(function() { btn.textContent = '+LIB'; }, 1400);
	}

	function adPlayVideo(item, idx) {
		adCurrentIdx = idx;
		adQueueActive = false;   // playing a library item exits queue mode

		// Close library drawer
		adLibraryVisible = false;
		document.getElementById('ad-player-library').classList.remove('is-open');
		document.getElementById('ad-library-toggle-btn').style.color = '';

		// Show the player. Must be an explicit 'flex' (not '' or 'block') — base CSS is
		// #ad-player{display:none}, only .mode-after-dark reveals it, and the shown layout is a
		// flex COLUMN (video-wrap uses flex:1 for its height). 'block' collapses the video to 0px.
		const player = document.getElementById('ad-player');
		player.style.display = 'flex';

		// If minimized, restore
		if (adPlayerMinimized) adPlayerMinimize();

		const frame = document.getElementById('ad-viewer-iframe');
		// autoplay=1 starts without a click; muted=1 is required for autoplay
		// to actually fire (browser policy) and matches the "calm by default"
		// preference — the embed has its own unmute control.
		const sep = item.url.indexOf('?') >= 0 ? '&' : '?';
		frame.src = item.url + sep + 'autoplay=1&muted=1';
		cockpitSetNowPlaying('ad', item.name);
		try { localStorage.setItem('cockpit-ad-lastplayed', JSON.stringify({ url: item.url, label: item.name })); adResumeUrl = item.url; } catch (e) {}

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
		document.getElementById('ad-queue-toggle-btn').style.color = adQueueVisible ? '#b45309' : '';
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
		return { url: 'https://www.pornhub.com/embed/' + vk, label: label || vk, id: vk };
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
		adSaveQueue();
		adResolveQueueTitles();
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
		adSaveQueue();
		adResolveQueueTitles();
		if (wasEmpty) adQueuePlay(0);
	}

	function adQueuePlay(idx) {
		if (idx < 0 || idx >= adQueue.length) return;
		adQueueIdx = idx;
		adQueueActive = true;

		const player = document.getElementById('ad-player');
		player.style.display = 'flex';  // flex column — 'block'/'' break the video-wrap height (see adPlayVideo)
		if (adPlayerMinimized) adPlayerMinimize();

		const frame = document.getElementById('ad-viewer-iframe');
		const url = adQueue[idx].url;
		const sep = url.indexOf('?') >= 0 ? '&' : '?';
		frame.src = url + sep + 'autoplay=1&muted=1';
		cockpitSetNowPlaying('ad', (adQueue[idx] || {}).label);
		try { localStorage.setItem('cockpit-ad-lastplayed', JSON.stringify({ url: url, label: (adQueue[idx] || {}).label })); adResumeUrl = url; } catch (e) {}
		adRenderQueue();
		adSaveQueue();   // persist the moved playhead so a reload resumes at the right item
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
		adSaveQueue();   // clears the persisted queue too
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
		btn.style.color = '#b45309';
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
		adSaveQueue();
	}

	// ---- Persistence: the PH queue survives reloads (localStorage), mirroring the YT player. ----
	// Playback isn't auto-resumed — the saved queue is re-rendered and a click / NEXT picks it back up.
	function adSaveQueue() {
		try {
			localStorage.setItem('cockpit-ad-queue', JSON.stringify({
				queue: adQueue, idx: adQueueIdx
			}));
		} catch (e) {}
	}

	function adLoadQueue() {
		try {
			var d = JSON.parse(localStorage.getItem('cockpit-ad-queue') || 'null');
			if (!d || !Array.isArray(d.queue) || d.queue.length === 0) return;
			adQueue = d.queue;
			if (typeof d.idx === 'number') adQueueIdx = d.idx;
			adRenderQueue();
			adSetQueueStatus(adQueue.length + ' saved — click one to resume');
			adResolveQueueTitles();   // fill real titles for any restored items still on a bare viewkey
		} catch (e) {}
	}

	// The viewkey for a queue item — from its stored id, or recovered from the /embed/<key> URL
	// for older saved items that predate the id field.
	function adItemViewkey(item) {
		if (item && item.id) return item.id;
		var m = ((item && item.url) || '').match(/\/embed\/([A-Za-z0-9]+)/);
		return m ? m[1] : null;
	}

	// Resolve real video titles (server-side oEmbed, same source as the library) for any queue items
	// still labeled with a bare viewkey. Best-effort + non-blocking — playback never waits on it;
	// it patches labels in place, then re-renders + re-saves so the names persist.
	function adResolveQueueTitles() {
		var need = [];
		adQueue.forEach(function (item) {
			var vk = adItemViewkey(item);
			if (vk && (!item.label || item.label === vk)) need.push(vk);
		});
		if (need.length === 0) return;
		fetch('/cockpit/after-dark/resolve-titles', {
			method: 'POST', headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ items: need.map(function (id) { return { id: id, kind: 'ph' }; }) })
		}).then(function (r) { return r.json(); }).then(function (res) {
			var titles = (res && res.titles) || {};
			var changed = false;
			adQueue.forEach(function (item) {
				var vk = adItemViewkey(item);
				if (vk && titles[vk] && (!item.label || item.label === vk)) { item.label = titles[vk]; changed = true; }
			});
			if (changed) { adRenderQueue(); adSaveQueue(); }
		}).catch(function () {});
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

	// Show/hide the floating Music player (base CSS hides it — it used to be revealed only
	// by the removed After Dark mode). Lazy-loads the library on first reveal. Bound to the
	// home MUSIC rail + the command palette so music is reachable in normal mode.
	let adMusicLoaded = false;
	function adMusicPlayerToggle() {
		const p = document.getElementById('ad-music-player');
		if (!p) return false;
		const shown = getComputedStyle(p).display !== 'none';
		cockpitDockToggle('ad-music-player', 'rail-music');
		if (!shown && !adMusicLoaded) { adMusicLoaded = true; adLoadMusic(); }
		return !shown;
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
	// COMMAND PALETTE — Ctrl+K
	// ============================================================

	// Open an external app respecting the "open nav in new tabs" setting (default ON) — keeps THIS tab
	// (and whatever's playing in the Cockpit) alive.
	function cmdGo(url) {
		if (localStorage.getItem('cockpit-nav-newtab') !== '0') window.open(url, '_blank');
		else window.location.href = url;
	}

	const CMD_ITEMS = [
		{ icon: '⌘', label: 'Command Deck',   hint: '/command-deck/', action: () => cmdGo('/command-deck/') },
		{ icon: '▼', label: 'Below Deck',     hint: '/below-deck',    action: () => cmdGo('/below-deck') },
		{ icon: '⌇', label: 'Publish Status', hint: '/publish',       action: () => window.location.href = '/publish' },
		{ icon: '▶', label: 'Toggle YouTube Player', hint: 'Ctrl+Shift+Y', action: () => { cmdClose(); ytPlayerToggle(); } },
		{ icon: '▹', label: 'Toggle Video Player', hint: 'Ctrl+Shift+V', action: () => { cmdClose(); adPlayerToggleGated(); } },
		{ icon: '♪', label: 'Toggle Music Player', hint: '', action: () => { cmdClose(); adMusicPlayerToggle(); } },
		{ icon: '◧', label: 'Mode: Write', hint: 'Ctrl+1', action: () => { cmdClose(); if (window.cockpitSetMode) cockpitSetMode('write'); } },
		{ icon: '◧', label: 'Mode: Desk', hint: 'Ctrl+2', action: () => { cmdClose(); if (window.cockpitSetMode) cockpitSetMode('desk'); } },
		{ icon: '◧', label: 'Mode: Watch', hint: 'Ctrl+3', action: () => { cmdClose(); if (window.cockpitSetMode) cockpitSetMode('watch'); } },
		{ icon: '◧', label: 'Mode: Theater', hint: 'Ctrl+4', action: () => { cmdClose(); if (window.cockpitSetMode) cockpitSetMode('theater'); } },
		{ icon: '◧', label: 'Mode: Minimal', hint: 'Ctrl+5', action: () => { cmdClose(); if (window.cockpitSetMode) cockpitSetMode('minimal'); } },
		{ icon: '◱', label: 'Toggle Focus Mode', hint: 'Ctrl+Shift+F', action: () => { cmdClose(); if (typeof toggleFocus === 'function') toggleFocus(); } },
		{ icon: '🦇', label: 'Toggle Ani',    hint: 'Ctrl+Shift+A',   action: () => { cmdClose(); if (typeof aniToggle === 'function') aniToggle(); } },
		{ icon: '$', label: 'The Ledger',     hint: '/ledger/',       action: () => cmdGo('/ledger/') },
		{ icon: '⚙', label: 'Settings',       hint: 'Ctrl+,',         action: () => { cmdClose(); if (typeof settingsOpen === 'function') settingsOpen(); } },
		{ icon: '🙏', label: 'Insert Grateful Log', hint: '',         action: () => { cmdClose(); if (typeof insertGratefulLog === 'function') insertGratefulLog(); } },
		{ icon: '▦', label: 'Toggle Mission Log', hint: '',           action: () => { cmdClose(); if (typeof toggleTasks === 'function') toggleTasks(); } },
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
		// Cmd/Ctrl+Shift+V — show/hide the After Dark video player (any mode). Skipped
		// while typing in a field so it doesn't hijack paste-as-plain-text.
		if ((e.ctrlKey || e.metaKey) && e.shiftKey && (e.key === 'v' || e.key === 'V')) {
			const t = e.target;
			const editable = t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.isContentEditable);
			if (!editable) { e.preventDefault(); adPlayerToggleGated(); }
		}
		// Cmd/Ctrl+Shift+F — focus mode (collapse everything but the transmission box)
		if ((e.ctrlKey || e.metaKey) && e.shiftKey && (e.key === 'f' || e.key === 'F')) {
			e.preventDefault();
			if (typeof toggleFocus === 'function') toggleFocus();
		}
		// Cmd/Ctrl+, — settings
		if ((e.ctrlKey || e.metaKey) && e.key === ',') {
			e.preventDefault();
			if (typeof settingsOpen === 'function') settingsOpen();
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

	var cmdSearchTimer = null, cmdSearchToken = 0;
	var CMD_TYPE_ICON = { task: '✓', ticket: '▤', project: '⌘', meeting: '▦', post: '⌇', status: '›' };

	function cmdActionMatches(q) {
		return getAllCmdItems().filter(function (item) { return item.label.toLowerCase().includes(q); });
	}

	function cmdFilter() {
		var raw = document.getElementById('cmd-palette-input').value;
		var q = raw.toLowerCase();
		cmdFiltered = cmdActionMatches(q);
		cmdSelected = 0;
		cmdRender();
		// Universal search (debounced) — merge content results (tasks, tickets, projects, posts,
		// status updates…) below the action matches. Results open in a NEW TAB (keeps this tab + player alive).
		if (cmdSearchTimer) clearTimeout(cmdSearchTimer);
		if (raw.trim().length < 2) return;
		var myToken = ++cmdSearchToken;
		cmdSearchTimer = setTimeout(function () {
			fetch('/cockpit/search?q=' + encodeURIComponent(raw.trim()))
				.then(function (r) { return r.json(); })
				.then(function (data) {
					if (myToken !== cmdSearchToken) return;                                   // stale response
					if (document.getElementById('cmd-palette-input').value !== raw) return;   // query moved on
					var items = (data.results || []).map(function (res) {
						return {
							icon: CMD_TYPE_ICON[res.type] || '›',
							label: res.title,
							hint: res.sub || res.type,
							action: function () { cmdClose(); window.open(res.url, '_blank'); }
						};
					});
					if (items.length) { cmdFiltered = cmdActionMatches(q).concat(items); cmdRender(); }
				})
				.catch(function () {});
		}, 220);
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

	// ============================================================
	// FOCUS-MODE DIAL + SPATIAL LAYOUT ENGINE (1g)
	// Named modes place each panel into a layout zone (full / left / right / off).
	// Long-press a mode to edit it; "+ NEW" creates custom modes. Reparents the
	// panels into #nb-zone-*. Persists to /cockpit/layout (localStorage fallback).
	// ============================================================
	(function () {
		var PANELS = [
			{ key: 'tx',     label: ') TX',           sel: '#tx-panel' },
			{ key: 'slip',   label: '\u{1F4D3} NOTEBOOK',   sel: '#nb-slip' },
			{ key: 'yt',     label: '▶ YT',           sel: '#rail-yt' },
			{ key: 'music',  label: '♪ MUSIC',        sel: '#rail-music' },
			{ key: 'mlog',   label: '// MISSION LOG', sel: '#mission-log-panel' },
			{ key: 'ledger', label: '$ LEDGER',       sel: '#ledger-pill-row' }
		];
		var COLS = ['off', 'full', 'left', 'right'];
		var WIDTHS = ['narrow', 'normal', 'wide', 'full'];
		var WIDTH_PX = { narrow: '560px', normal: '820px', wide: '1100px', full: '96vw' };
		var BUILTIN = {
			write:   { label: 'WRITE',   width: 'narrow', panels: { tx: 'full', slip: 'full',  yt: 'off',   music: 'off',   mlog: 'off',  ledger: 'off' } },
			desk:    { label: 'DESK',    width: 'normal', panels: { tx: 'full', slip: 'left',  yt: 'right', music: 'right', mlog: 'left', ledger: 'right' } },
			watch:   { label: 'WATCH',   width: 'normal', panels: { tx: 'off',  slip: 'right', yt: 'left',  music: 'off',   mlog: 'off',  ledger: 'off' } },
			theater: { label: 'THEATER', width: 'wide',   panels: { tx: 'off',  slip: 'off',   yt: 'left',  music: 'right', mlog: 'off',  ledger: 'off' } },
			minimal: { label: 'MINIMAL', width: 'narrow', panels: { tx: 'full', slip: 'off',   yt: 'off',   music: 'off',   mlog: 'off',  ledger: 'off' } }
		};
		var BUILTIN_ORDER = ['write', 'desk', 'watch', 'theater', 'minimal'];
		var LS_KEY = 'cockpit-modes-v2';
		var state = { active: 'desk', order: BUILTIN_ORDER.slice(), modes: {} };
		var sbFor = null, zones = {};

		function esc(s) { var d = document.createElement('div'); d.textContent = s == null ? '' : s; return d.innerHTML; }

		function ensureZones() {
			zones.full = document.getElementById('nb-zone-full');
			zones.left = document.getElementById('nb-zone-left');
			zones.right = document.getElementById('nb-zone-right');
			var h = document.getElementById('nb-zone-hidden');
			if (!h) { h = document.createElement('div'); h.id = 'nb-zone-hidden'; h.style.display = 'none'; document.body.appendChild(h); }
			zones.hidden = h;
		}

		function normalize() {
			if (!state.modes) state.modes = {};
			BUILTIN_ORDER.forEach(function (m) {
				if (!state.modes[m]) state.modes[m] = { label: BUILTIN[m].label, builtin: true, panels: {} };
				state.modes[m].builtin = true;
				if (!state.modes[m].label) state.modes[m].label = BUILTIN[m].label;
				if (!state.modes[m].panels) state.modes[m].panels = {};
				if (WIDTHS.indexOf(state.modes[m].width) < 0) state.modes[m].width = BUILTIN[m].width;
				PANELS.forEach(function (p) { if (COLS.indexOf(state.modes[m].panels[p.key]) < 0) state.modes[m].panels[p.key] = BUILTIN[m].panels[p.key]; });
			});
			Object.keys(state.modes).forEach(function (m) {
				var md = state.modes[m]; if (!md.panels) md.panels = {};
				if (WIDTHS.indexOf(md.width) < 0) md.width = 'normal';
				PANELS.forEach(function (p) { if (COLS.indexOf(md.panels[p.key]) < 0) md.panels[p.key] = 'off'; });
			});
			if (!state.order || !state.order.length) state.order = BUILTIN_ORDER.slice();
			Object.keys(state.modes).forEach(function (m) { if (state.order.indexOf(m) < 0) state.order.push(m); });
			state.order = state.order.filter(function (m) { return state.modes[m]; });
			if (state.order.indexOf(state.active) < 0) state.active = state.order[0] || 'desk';
		}

		function loadState() {
			try { var s = JSON.parse(localStorage.getItem(LS_KEY)); if (s && s.modes) state = s; } catch (e) {}
			normalize();
			fetch('/cockpit/layout').then(function (r) { return r.json(); }).then(function (d) {
				if (d && d.modes) { state = d; normalize(); applyMode(state.active); renderDial(); }
			}).catch(function () {});
		}
		function saveState() {
			try { localStorage.setItem(LS_KEY, JSON.stringify(state)); } catch (e) {}
			fetch('/cockpit/layout', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(state) }).catch(function () {});
		}

		function applyMode(mode) {
			var md = state.modes[mode]; if (!md) return;
			ensureZones();
			// a layout change closes any docked player (it re-docks from its new rail on click)
			['yt-player', 'ad-music-player'].forEach(function (id) {
				var pl = document.getElementById(id);
				if (pl && pl.classList.contains('is-docked')) { pl.classList.remove('is-docked'); pl.style.display = 'none'; }
			});
			PANELS.forEach(function (p) {
				var el = document.querySelector(p.sel); if (!el) return;
				var col = md.panels[p.key] || 'off';
				el.classList.remove('mode-off');
				if (col === 'full') zones.full.appendChild(el);
				else if (col === 'left') zones.left.appendChild(el);
				else if (col === 'right') zones.right.appendChild(el);
				else { zones.hidden.appendChild(el); el.classList.add('mode-off'); }
			});
			state.active = mode;
			document.body.setAttribute('data-mode', mode);
			var cols = document.getElementById('stack-cols');
			if (cols) cols.classList.toggle('one-col', !(zones.left.children.length && zones.right.children.length));
			var cont = document.querySelector('.container');
			if (cont) cont.style.maxWidth = WIDTH_PX[md.width] || WIDTH_PX.normal;
		}

		function thumbHTML(md) {
			var full = [], left = [], right = [];
			PANELS.forEach(function (p) {
				var c = md.panels[p.key];
				if (c === 'full') full.push(p); else if (c === 'left') left.push(p); else if (c === 'right') right.push(p);
			});
			function blk(p) { return '<span class="mt-blk t-' + p.key + '"></span>'; }
			var h = '<span class="mode-thumb">';
			full.forEach(function (p) { h += '<span class="mt-row mt-full">' + blk(p) + '</span>'; });
			if (left.length || right.length) {
				h += '<span class="mt-cols"><span class="mt-col">' + left.map(blk).join('') + '</span><span class="mt-col">' + right.map(blk).join('') + '</span></span>';
			}
			if (!full.length && !left.length && !right.length) h += '<span class="mt-empty"></span>';
			return h + '</span>';
		}

		function renderDial() {
			var wrap = document.getElementById('mode-dial-btns'); if (!wrap) return;
			var html = state.order.map(function (m) {
				var md = state.modes[m];
				return '<button class="mode-btn' + (m === state.active ? ' is-active' : '') + (sbFor === m ? ' is-held' : '') + '" data-mode="' + m + '">'
					+ esc(md.label) + (m === state.active ? ' ●' : '') + '</button>';
			}).join('');
			html += '<button class="mode-btn mode-new" id="mode-new-btn" title="Create a new mode">+ NEW</button>';
			wrap.innerHTML = html;
			Array.prototype.forEach.call(wrap.querySelectorAll('.mode-btn[data-mode]'), function (btn) {
				var m = btn.getAttribute('data-mode'), lp = null, longFired = false;
				btn.addEventListener('click', function () { if (longFired) { longFired = false; return; } setActive(m); });
				btn.addEventListener('contextmenu', function (e) { e.preventDefault(); openSwitchboard(m); });
				btn.addEventListener('mousedown', function () { longFired = false; lp = setTimeout(function () { longFired = true; openSwitchboard(m); }, 550); });
				btn.addEventListener('mouseup', function () { clearTimeout(lp); });
				btn.addEventListener('mouseleave', function () { clearTimeout(lp); });
				btn.addEventListener('touchstart', function () { longFired = false; lp = setTimeout(function () { longFired = true; openSwitchboard(m); }, 550); }, { passive: true });
				btn.addEventListener('touchend', function () { clearTimeout(lp); });
			});
			var nb = document.getElementById('mode-new-btn');
			if (nb) nb.addEventListener('click', newMode);
		}

		function setActive(mode) { applyMode(mode); saveState(); closeSwitchboard(); renderDial(); }

		function openSwitchboard(mode) {
			sbFor = mode;
			var sb = document.getElementById('mode-switchboard'), grid = document.getElementById('mode-sb-grid'),
				title = document.getElementById('mode-sb-title'), nameIn = document.getElementById('mode-sb-name'),
				foot = document.getElementById('mode-sb-foot');
			if (!sb || !grid) return;
			var md = state.modes[mode];
			if (title) title.textContent = '// ' + md.label + ' — SWITCHBOARD';
			if (nameIn) {
				nameIn.style.display = '';
				nameIn.value = md.label;
				nameIn.disabled = !!md.builtin;
				nameIn.oninput = function () { md.label = nameIn.value.toUpperCase().slice(0, 14); if (title) title.textContent = '// ' + md.label + ' — SWITCHBOARD'; renderDial(); saveState(); };
			}
			var thumbBlock = '<div class="mode-sb-thumb" id="mode-sb-thumb">' + thumbHTML(md) + '</div>';
			var widthRow = '<div class="mode-sw-row"><span class="mode-sw-label">↔ WIDTH</span><span class="mode-segs">'
				+ WIDTHS.map(function (w) { return '<button class="mode-seg mode-wseg' + (md.width === w ? ' is-on' : '') + '" data-width="' + w + '">' + w.toUpperCase() + '</button>'; }).join('')
				+ '</span></div>';
			var panelRows = PANELS.map(function (p) {
				var cur = md.panels[p.key] || 'off';
				var segs = COLS.map(function (c) { return '<button class="mode-seg' + (cur === c ? ' is-on' : '') + '" data-panel="' + p.key + '" data-col="' + c + '">' + c.toUpperCase() + '</button>'; }).join('');
				return '<div class="mode-sw-row"><span class="mode-sw-label">' + p.label + '</span><span class="mode-segs">' + segs + '</span></div>';
			}).join('');
			grid.innerHTML = thumbBlock + widthRow + panelRows;
			function refreshThumb() { var t = document.getElementById('mode-sb-thumb'); if (t) t.innerHTML = thumbHTML(md); }
			Array.prototype.forEach.call(grid.querySelectorAll('.mode-seg[data-panel]'), function (seg) {
				seg.addEventListener('click', function () {
					var k = seg.getAttribute('data-panel'), c = seg.getAttribute('data-col');
					md.panels[k] = c;
					Array.prototype.forEach.call(grid.querySelectorAll('.mode-seg[data-panel="' + k + '"]'), function (s) { s.classList.toggle('is-on', s.getAttribute('data-col') === c); });
					refreshThumb();
					if (mode === state.active) applyMode(state.active);
					renderDial(); saveState();
				});
			});
			Array.prototype.forEach.call(grid.querySelectorAll('.mode-wseg'), function (seg) {
				seg.addEventListener('click', function () {
					md.width = seg.getAttribute('data-width');
					Array.prototype.forEach.call(grid.querySelectorAll('.mode-wseg'), function (s) { s.classList.toggle('is-on', s === seg); });
					if (mode === state.active) applyMode(state.active);
					saveState();
				});
			});
			if (foot) {
				foot.innerHTML = md.builtin ? '<span class="mode-sb-note">built-in mode</span>' : '<button class="mode-del-btn" id="mode-del-btn">DELETE MODE</button>';
				var del = document.getElementById('mode-del-btn');
				if (del) del.addEventListener('click', function () { deleteMode(mode); });
			}
			renderDial();
			sb.classList.add('is-open');
		}
		function closeSwitchboard() { var sb = document.getElementById('mode-switchboard'); if (sb) sb.classList.remove('is-open'); if (sbFor) { sbFor = null; renderDial(); } }

		function newMode() {
			var name = prompt('Name this mode');
			if (!name) return;
			name = name.trim(); if (!name) return;
			var base = name.toLowerCase().replace(/[^a-z0-9]+/g, '').slice(0, 8) || 'mode';
			var id = 'c_' + base, n = 1;
			while (state.modes[id]) { id = 'c_' + base + (++n); }
			var src = state.modes[state.active] ? state.modes[state.active].panels : BUILTIN.desk.panels;
			state.modes[id] = { label: name.toUpperCase().slice(0, 14), builtin: false, panels: Object.assign({}, src) };
			state.order.push(id);
			saveState(); renderDial(); openSwitchboard(id);
		}
		function deleteMode(mode) {
			var md = state.modes[mode]; if (!md || md.builtin) return;
			if (!confirm('Delete the "' + md.label + '" mode?')) return;
			delete state.modes[mode];
			state.order = state.order.filter(function (m) { return m !== mode; });
			if (state.active === mode) state.active = state.order[0] || 'desk';
			closeSwitchboard(); applyMode(state.active); saveState(); renderDial();
		}

		window.cockpitSetMode = setActive;
		window.cockpitOpenSwitchboard = openSwitchboard;
		window.cockpitNewMode = newMode;

		document.addEventListener('keydown', function (e) {
			if ((e.ctrlKey || e.metaKey) && !e.shiftKey && !e.altKey && e.key >= '1' && e.key <= '9' && document.getElementById('mode-dial')) {
				var idx = parseInt(e.key, 10) - 1;
				if (state.order[idx]) { e.preventDefault(); setActive(state.order[idx]); }
			}
			if (e.key === 'Escape') { var sb = document.getElementById('mode-switchboard'); if (sb && sb.classList.contains('is-open')) closeSwitchboard(); }
		});
		document.addEventListener('click', function (e) {
			var sb = document.getElementById('mode-switchboard');
			if (sb && sb.classList.contains('is-open') && !sb.contains(e.target) && !(e.target.closest && e.target.closest('.mode-btn'))) closeSwitchboard();
		});
		document.addEventListener('DOMContentLoaded', function () {
			if (!document.getElementById('mode-dial')) return;
			loadState(); applyMode(state.active); renderDial();
		});
	})();
