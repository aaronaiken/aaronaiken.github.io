// Status page + homepage status card — click/tap an image to view it full size.
//
// Images render capped inline; screenshots in particular need the full
// resolution to be legible. Delegated on document so items appended later
// by status-load-more.js work without re-binding. Click anywhere or Esc
// closes it.

(function () {
  var SELECTOR = '.older-status-item .content img, .latest-content .content img, .home-page__status-body img';
  var IMAGE_HREF = /\.(jpe?g|png|gif|webp)(\?.*)?$/i;

  var overlay = document.createElement('div');
  overlay.className = 'st-lightbox';
  overlay.setAttribute('role', 'dialog');
  overlay.setAttribute('aria-modal', 'true');
  overlay.setAttribute('aria-label', 'Full-size image');
  overlay.hidden = true;

  var full = document.createElement('img');
  full.className = 'st-lightbox-img';
  overlay.appendChild(full);

  var close = document.createElement('button');
  close.type = 'button';
  close.className = 'st-lightbox-close';
  close.setAttribute('aria-label', 'Close');
  close.textContent = '✕';
  overlay.appendChild(close);

  document.body.appendChild(overlay);

  var lastFocus = null;

  // Posts from the cockpit link the inline copy to a full-size one:
  // [![alt](display.jpg)](display-full.jpg). Older posts are a bare image.
  function fullSrc(img) {
    var a = img.closest('a');
    if (a && IMAGE_HREF.test(a.getAttribute('href') || '')) return a.href;
    return img.currentSrc || img.src;
  }

  function zoomable(img) {
    var a = img.closest('a');
    return !a || IMAGE_HREF.test(a.getAttribute('href') || '');
  }

  function open(img) {
    lastFocus = img.closest('a') || img;
    full.src = fullSrc(img);
    full.alt = img.alt || '';
    overlay.hidden = false;
    document.documentElement.classList.add('st-lightbox-open');
    close.focus();
  }

  function shut() {
    overlay.hidden = true;
    full.removeAttribute('src');
    document.documentElement.classList.remove('st-lightbox-open');
    if (lastFocus) lastFocus.focus();
  }

  function isTarget(el) {
    return el && el.tagName === 'IMG' && el.matches(SELECTOR);
  }

  document.addEventListener('click', function (e) {
    if (!overlay.hidden) return;
    var img = e.target;
    if (!isTarget(img)) return;
    // An image linked somewhere other than an image keeps its link behavior.
    if (!zoomable(img)) return;
    e.preventDefault();
    open(img);
  });

  // Keyboard access: make inline images focusable + Enter/Space opens.
  function prime(root) {
    var imgs = (root || document).querySelectorAll(SELECTOR);
    for (var i = 0; i < imgs.length; i++) {
      // Linked images are already focusable via their <a>.
      if (!zoomable(imgs[i])) continue;
      imgs[i].classList.add('st-zoomable');
      if (!imgs[i].closest('a') && !imgs[i].hasAttribute('tabindex')) {
        imgs[i].setAttribute('tabindex', '0');
      }
    }
  }
  prime();
  var list = document.getElementById('olderUpdatesList');
  if (list && window.MutationObserver) {
    new MutationObserver(function () { prime(list); })
      .observe(list, { childList: true });
  }

  document.addEventListener('keydown', function (e) {
    if (!overlay.hidden && e.key === 'Escape') { shut(); return; }
    if (overlay.hidden && (e.key === 'Enter' || e.key === ' ') && isTarget(document.activeElement)) {
      e.preventDefault();
      open(document.activeElement);
    }
  });

  overlay.addEventListener('click', shut);
})();
