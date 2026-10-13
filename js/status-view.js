// Status pages — '07 / TERMINAL view toggle.
//
// Loaded synchronously at the top of <body> so the saved mode is applied
// before first paint (no flash of the '07 view for terminal readers). The
// button is wired once the DOM is ready. Colors live in status.css
// (.st-toggle-opt--active per mode), not here.

(function () {
  var STORAGE_KEY = 'status-view-mode';
  var body = document.body;

  function setMode(mode, save) {
    var terminal = mode === 'terminal';
    body.classList.toggle('st-terminal', terminal);
    var tw = document.getElementById('st-opt-twitter');
    var te = document.getElementById('st-opt-terminal');
    if (tw) tw.classList.toggle('st-toggle-opt--active', !terminal);
    if (te) te.classList.toggle('st-toggle-opt--active', terminal);
    if (save) {
      try { localStorage.setItem(STORAGE_KEY, mode); } catch (e) {}
    }
  }

  var saved = null;
  try { saved = localStorage.getItem(STORAGE_KEY); } catch (e) {}
  if (!saved) {
    var dark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    saved = dark ? 'terminal' : 'twitter';
  }
  setMode(saved, false);

  document.addEventListener('DOMContentLoaded', function () {
    setMode(body.classList.contains('st-terminal') ? 'terminal' : 'twitter', false);
    var btn = document.getElementById('st-toggle');
    if (!btn) return;
    btn.addEventListener('click', function () {
      setMode(body.classList.contains('st-terminal') ? 'twitter' : 'terminal', true);
    });
  });
})();
