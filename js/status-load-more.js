// Status page — explicit "Load older updates" handler.
//
// First click: fetch /status.json once, cache the array.
// Each click: slice the next BATCH_SIZE items past what's already rendered
// and append them to .older-updates-list using the same DOM shape Liquid
// produced for the initial 30. When the cache is exhausted, hide the button.
//
// Why explicit rather than auto-fetch-on-scroll: matches Aaron's UX default
// of preferring deliberate, confirmed flows over silent zero-click behavior.

(function () {
  var BATCH_SIZE = 30;

  var container = document.getElementById('loadMoreContainer');
  if (!container) return; // page has 30 or fewer total — nothing to load

  var btn = document.getElementById('loadMoreBtn');
  var statusText = document.getElementById('loadMoreStatus');
  var shownCountEl = document.getElementById('loadMoreShown');
  var list = document.getElementById('olderUpdatesList');
  if (!btn || !list) return;

  var total = parseInt(container.getAttribute('data-total'), 10) || 0;
  var loaded = parseInt(container.getAttribute('data-loaded'), 10) || 0;
  var cache = null; // populated on first fetch

  function renderItem(item) {
    var li = document.createElement('li');
    li.className = 'older-status-item';

    // Terminal-only prefix
    var prefix = document.createElement('span');
    prefix.className = 'st-terminal-only st-line-prefix';
    prefix.textContent = '›';
    li.appendChild(prefix);

    // Body: markdown content, then a meta line (timestamp · source) —
    // same shape as the Liquid-rendered items. A <div> wrapper, not <p>:
    // content_html contains block elements (<p>, <ol>, <img>).
    var body = document.createElement('div');
    body.className = 'st-item-body';

    var content = document.createElement('div');
    content.className = 'content';
    content.innerHTML = item.content_html || '';
    body.appendChild(content);

    var meta = document.createElement('p');
    meta.className = 'st-item-meta';
    var ts = document.createElement('a');
    ts.href = item.url;
    ts.target = '_blank';
    ts.className = 'timestamp-link';
    ts.textContent = item.date_display || '';
    meta.appendChild(ts);
    if (item.source) {
      var src = document.createElement('span');
      src.className = 'source';
      src.textContent = 'via ' + item.source;
      meta.appendChild(document.createTextNode(' '));
      meta.appendChild(src);
    }
    body.appendChild(meta);
    li.appendChild(body);

    return li;
  }

  function appendBatch() {
    if (!cache) return; // shouldn't happen — guarded in the click handler
    var end = Math.min(loaded + BATCH_SIZE, cache.length);
    for (var i = loaded; i < end; i++) {
      list.appendChild(renderItem(cache[i]));
    }
    loaded = end;
    if (shownCountEl) shownCountEl.textContent = loaded;

    if (loaded >= cache.length) {
      // Nothing left — collapse the control
      btn.style.display = 'none';
      if (statusText) statusText.textContent = 'All ' + total + ' updates shown.';
    }
  }

  function setLoading(isLoading) {
    btn.disabled = !!isLoading;
    var label = btn.querySelector('.st-load-more-label');
    if (label) label.textContent = isLoading ? 'Loading…' : 'Load older updates';
  }

  btn.addEventListener('click', function () {
    if (cache) { appendBatch(); return; }
    setLoading(true);
    fetch('/status.json', { credentials: 'same-origin' })
      .then(function (r) {
        if (!r.ok) throw new Error('fetch failed: ' + r.status);
        return r.json();
      })
      .then(function (data) {
        cache = (data && data.items) || [];
        // The JSON includes the absolute-newest item (index 0), which is in
        // the .latest-update-container at top of the page — so the first 31
        // items (0..30) are already in the DOM. Start appending from index 31.
        // If the server-rendered count somehow differs, trust `loaded` from
        // the container's data attribute as the source of truth.
        appendBatch();
      })
      .catch(function (err) {
        console.error('status load-more fetch error', err);
        if (statusText) statusText.textContent = 'Could not load older updates.';
      })
      .finally(function () { setLoading(false); });
  });
})();
