
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

    // Video player events — all modes
    document.addEventListener('DOMContentLoaded', function() {
        const vid = document.getElementById('ad-viewer-video');
        if (!vid) return;
        vid.addEventListener('ended', function() {
            if (adLibraryItems.length > 1) {
                let currentIdx = adLibraryItems.findIndex(i => i.url === vid.src);
                let nextIdx;
                do {
                    nextIdx = Math.floor(Math.random() * adLibraryItems.length);
                } while (nextIdx === currentIdx);
                adPlayVideo(adLibraryItems[nextIdx], nextIdx);
            }
        });
        vid.addEventListener('pause', function() {
            document.getElementById('ad-playpause-btn').textContent = '▶';
        });
        vid.addEventListener('play', function() {
            document.getElementById('ad-playpause-btn').textContent = '❚❚';
        });
    });

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
		const vid = document.getElementById('ad-viewer-video');
		vid.pause();
		vid.src = '';
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
			grid.innerHTML = '<div style="color:#2a0f0f;font-size:0.55rem;letter-spacing:0.12em;padding:12px;">no videos in library</div>';
			return;
		}
		adLibraryItems.forEach(function(item, idx) {
			const tile = document.createElement('div');
			tile.className = 'ad-library-tile';
			tile.textContent = item.name.replace(/\.[^.]+$/, '').replace(/[-_]/g, ' ');
			tile.onclick = function() { adPlayVideo(item, idx); };
			grid.appendChild(tile);
		});
	}

	function adPlayVideo(item, idx) {
		// Close library drawer
		adLibraryVisible = false;
		document.getElementById('ad-player-library').classList.remove('is-open');
		document.getElementById('ad-library-toggle-btn').style.color = '';

		// Show player if it was closed
		const player = document.getElementById('ad-player');
		player.style.display = 'block';

		// If minimized, restore
		if (adPlayerMinimized) adPlayerMinimize();

		const vid = document.getElementById('ad-viewer-video');
		vid.src = item.url;
		vid.volume = parseFloat(document.getElementById('ad-player-volume').value);
		vid.load();
		vid.play().catch(() => {});

		document.getElementById('ad-now-playing').textContent =
			item.name.replace(/\.[^.]+$/, '').replace(/[-_]/g, ' ');
		document.getElementById('ad-playpause-btn').textContent = '❚❚';

		// Highlight active tile
		document.querySelectorAll('.ad-library-tile').forEach(function(t, i) {
			t.classList.toggle('is-playing', i === idx);
		});
	}

	function adViewerPlayPause() {
		const vid = document.getElementById('ad-viewer-video');
		const btn = document.getElementById('ad-playpause-btn');
		if (vid.paused) {
			vid.play().catch(() => {});
			btn.textContent = '❚❚';
		} else {
			vid.pause();
			btn.textContent = '▶';
		}
	}

	function adViewerToggleMute() {
		const vid = document.getElementById('ad-viewer-video');
		const btn = document.getElementById('ad-viewer-mute-btn');
		vid.muted = !vid.muted;
		btn.textContent = vid.muted ? 'UNMUTE' : 'MUTE';
	}

	function adViewerVolume(val) {
		document.getElementById('ad-viewer-video').volume = parseFloat(val);
	}

	// Update play/pause button when video ends or pauses externally
	document.addEventListener('DOMContentLoaded', function() {
		const vid = document.getElementById('ad-viewer-video');
		if (!vid) return;
		vid.addEventListener('ended', function() {
			document.getElementById('ad-playpause-btn').textContent = '▶';
		});
		vid.addEventListener('pause', function() {
			document.getElementById('ad-playpause-btn').textContent = '▶';
		});
		vid.addEventListener('play', function() {
			document.getElementById('ad-playpause-btn').textContent = '❚❚';
		});
	});

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
		{ icon: '⏎', label: 'Refresh',        hint: '',               action: () => window.location.reload() },
	];

	let cmdFiltered = [...CMD_ITEMS];
	let cmdSelected = 0;

	document.addEventListener('keydown', function(e) {
		if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
			e.preventDefault();
			cmdOpen();
		}
	});

	function cmdOpen() {
		const overlay = document.getElementById('cmd-palette-overlay');
		overlay.classList.add('is-open');
		cmdFiltered = [...CMD_ITEMS];
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
		cmdFiltered = CMD_ITEMS.filter(item => item.label.toLowerCase().includes(q));
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


