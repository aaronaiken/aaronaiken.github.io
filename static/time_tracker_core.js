/* time_tracker_core.js
 *
 * Shared poller + cache + action helpers for time tracking.
 * Used by:
 *   - templates/includes/active_timer_strip.html  (Today, Below Deck, Command Deck pages)
 *   - templates/includes/time_tracker_panel.html  (Cockpit floating panel) — coming in commit 6
 *
 * One source of truth for /time/active to avoid double-polling. Subscribers
 * register a callback that fires on every poll AND every 1-second tick (so
 * elapsed counters can be re-rendered locally between polls without hitting
 * the server).
 *
 * Saved-state guard (lessons-learned pattern from scratch pad / video player):
 *   - `loaded` flag prevents notify() before initial fetch resolves
 *   - Network failures don't blow away cached state
 */
(function (window) {
  'use strict';

  if (window.TimeTrackerCore) return; // idempotent on multi-include

  var POLL_INTERVAL_MS = 30000;
  var TICK_INTERVAL_MS = 1000;

  var subscribers = [];
  var current = [];
  var loaded = false;
  var pollTimer = null;
  var tickTimer = null;
  var inFlight = null;

  // Phase 2 §3.4 — today total. Subscribers are notified on every
  // poll AND every tick with the live current value (server-fetched
  // stopped_today_seconds + locally-computed elapsed of currently-
  // running entries). This way the cockpit panel titlebar ticks up
  // every second without polling /time/today/total at 1Hz.
  var todaySubscribers = [];
  var todayStoppedSeconds = 0;     // server-cached, refreshed on poll
  var todayDate = null;
  var todayLoaded = false;
  var todayInFlight = null;

  function notify() {
    subscribers.forEach(function (cb) {
      try { cb(current); } catch (e) { console.error('TimeTrackerCore subscriber error:', e); }
    });
  }

  function fetchActive() {
    if (inFlight) return inFlight;
    inFlight = fetch('/time/active', { credentials: 'same-origin' })
      .then(function (r) { return r.ok ? r.json() : { active: [] }; })
      .then(function (data) {
        current = (data && data.active) || [];
        loaded = true;
        notify();
      })
      .catch(function () {
        // network blip — keep last known state, don't blow it away
      })
      .then(function () { inFlight = null; });
    return inFlight;
  }

  function tick() {
    // Re-emit so subscribers can recompute elapsed locally
    if (loaded) notify();
    if (todayLoaded) notifyToday();
  }

  function fetchTodayTotal() {
    if (todayInFlight) return todayInFlight;
    todayInFlight = fetch('/time/today/total', { credentials: 'same-origin' })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (data) {
        if (!data) return;
        // ET day rolled over since last fetch — reset cached stopped total
        if (todayDate && data.today_date !== todayDate) {
          todayStoppedSeconds = 0;
        }
        todayStoppedSeconds = Math.max(0, data.stopped_today_seconds | 0);
        todayDate = data.today_date;
        todayLoaded = true;
        notifyToday();
      })
      .catch(function () { /* network blip */ })
      .then(function () { todayInFlight = null; });
    return todayInFlight;
  }

  function liveTodayTotal() {
    // stopped (server) + elapsed-so-far for any active timer started today
    if (!todayLoaded) return 0;
    var totalRunning = 0;
    if (todayDate) {
      current.forEach(function (e) {
        if (!e || !e.started_at) return;
        // Approximate ET-day membership by comparing the started_at's
        // local-date to todayDate. Aaron's local TZ matches ET; this is
        // close enough for the panel display.
        var startedLocal = new Date(e.started_at);
        var iso = startedLocal.getFullYear() + '-' +
          pad(startedLocal.getMonth() + 1) + '-' +
          pad(startedLocal.getDate());
        if (iso === todayDate) {
          totalRunning += elapsedSeconds(e);
        }
      });
    }
    return todayStoppedSeconds + totalRunning;
  }

  function notifyToday() {
    var total = liveTodayTotal();
    todaySubscribers.forEach(function (cb) {
      try { cb(total, todayDate); }
      catch (e) { console.error('TimeTrackerCore today subscriber error:', e); }
    });
  }

  function subscribeToday(cb) {
    todaySubscribers.push(cb);
    if (todayLoaded) {
      try { cb(liveTodayTotal(), todayDate); } catch (e) { console.error(e); }
    }
    fetchTodayTotal();
    ensureRunning();
    return function unsubscribe() {
      todaySubscribers = todaySubscribers.filter(function (s) { return s !== cb; });
    };
  }

  function ensureRunning() {
    if (!pollTimer) pollTimer = setInterval(function () {
      fetchActive();
      if (todaySubscribers.length) fetchTodayTotal();
    }, POLL_INTERVAL_MS);
    if (!tickTimer) tickTimer = setInterval(tick, TICK_INTERVAL_MS);
  }

  function subscribe(cb) {
    subscribers.push(cb);
    if (loaded) {
      try { cb(current); } catch (e) { console.error(e); }
    }
    fetchActive();
    ensureRunning();
    return function unsubscribe() {
      subscribers = subscribers.filter(function (s) { return s !== cb; });
    };
  }

  function refresh() { return fetchActive(); }

  function elapsedSeconds(entry) {
    if (!entry || !entry.started_at) return 0;
    var t = new Date(entry.started_at).getTime();
    if (isNaN(t)) return 0;
    return Math.max(0, Math.floor((Date.now() - t) / 1000));
  }

  function pad(n) { return n < 10 ? '0' + n : '' + n; }

  function formatElapsed(secs) {
    if (!secs || secs < 0) secs = 0;
    var h = Math.floor(secs / 3600);
    var m = Math.floor((secs % 3600) / 60);
    var s = secs % 60;
    if (h > 0) return h + ':' + pad(m) + ':' + pad(s);
    return m + ':' + pad(s);
  }

  function postJson(url, body) {
    return fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
      body: JSON.stringify(body || {}),
    }).then(function (r) {
      return r.json().then(function (data) {
        return { ok: r.ok, status: r.status, data: data };
      });
    });
  }

  function postEmpty(url) {
    return fetch(url, { method: 'POST', credentials: 'same-origin' })
      .then(function (r) {
        return r.json().then(function (data) {
          return { ok: r.ok, status: r.status, data: data };
        });
      });
  }

  function startTimer(projectId, description) {
    return postJson('/time/start', { project_id: projectId, description: description || '' })
      .then(function (result) { if (result.ok) { refresh(); fetchTodayTotal(); } return result; });
  }

  function stopTimer(entryId) {
    return postEmpty('/time/' + entryId + '/stop')
      .then(function (result) { if (result.ok) { refresh(); fetchTodayTotal(); } return result; });
  }

  function stopAllTimers() {
    var ids = current.map(function (e) { return e.id; });
    return Promise.all(ids.map(function (id) {
      return postEmpty('/time/' + id + '/stop').catch(function () { /* swallow */ });
    })).then(function () { refresh(); fetchTodayTotal(); });
  }

  function deleteTimer(entryId) {
    return postEmpty('/time/' + entryId + '/delete')
      .then(function (result) { if (result.ok) { refresh(); fetchTodayTotal(); } return result; });
  }

  function updateTimer(entryId, fields) {
    return postJson('/time/' + entryId + '/update', fields || {})
      .then(function (result) { if (result.ok) { refresh(); fetchTodayTotal(); } return result; });
  }

  window.TimeTrackerCore = {
    subscribe: subscribe,
    subscribeToday: subscribeToday,
    refresh: refresh,
    refreshToday: fetchTodayTotal,
    elapsedSeconds: elapsedSeconds,
    formatElapsed: formatElapsed,
    startTimer: startTimer,
    stopTimer: stopTimer,
    stopAllTimers: stopAllTimers,
    deleteTimer: deleteTimer,
    updateTimer: updateTimer,
    isLoaded: function () { return loaded; },
    current: function () { return current.slice(); },
    todayTotalSeconds: liveTodayTotal,
  };
})(window);
