/*
 * Leak-hunt results-page interactions:
 *   - AJAX "+ Add to bills" with instant button swap to "✓ In Bills"
 *   - "× Cancel" toggle per recurring row with a running monthly/yearly
 *     freed-money tally, persisted to localStorage per hunt id
 */
(function () {
  const HUNT_ID = window.LH_HUNT_ID;
  if (!HUNT_ID) return;

  const STORAGE_KEY = `lh-cancel-flags-${HUNT_ID}`;

  // ---- "+ Add to bills" AJAX ----
  document.querySelectorAll('.lh-add-bill-form').forEach(form => {
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const btn = form.querySelector('button');
      const wrap = form.parentElement;
      const originalText = btn.textContent;
      btn.disabled = true;
      btn.textContent = 'Adding…';

      const fd = new FormData(form);
      try {
        const res = await fetch(form.action, {
          method: 'POST',
          body: fd,
          headers: {'X-Requested-With': 'fetch'},
        });
        const data = await res.json();
        if (data.ok) {
          // Swap to "✓ In Bills" pill
          wrap.innerHTML = '<span class="lg-btn sm" style="border:1px solid var(--lg-teal); color:var(--lg-teal); cursor:default; padding:6px 12px;">✓ In Bills</span>';
          flash(data.message || 'Added.');
        } else {
          btn.disabled = false;
          btn.textContent = originalText;
          flash(data.message || 'Could not add.');
        }
      } catch (err) {
        btn.disabled = false;
        btn.textContent = originalText;
        flash('Error: ' + err);
      }
    });
  });

  // ---- "× Cancel" toggle + tally ----
  const tally       = document.getElementById('lh-cancel-tally');
  const tallyMo     = document.getElementById('lh-cancel-monthly');
  const tallyYr     = document.getElementById('lh-cancel-yearly');
  const tallyCount  = document.getElementById('lh-cancel-count');

  function loadFlagged() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return new Set();
      return new Set(JSON.parse(raw));
    } catch (e) { return new Set(); }
  }
  function saveFlagged(set) {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(Array.from(set))); }
    catch (e) { /* ignore */ }
  }

  const flagged = loadFlagged();

  function refreshTally() {
    let monthly = 0;
    let count = 0;
    document.querySelectorAll('[data-recurring-row]').forEach(row => {
      const merchant = row.dataset.merchant;
      const m = parseFloat(row.dataset.monthly) || 0;
      const btn = row.querySelector('.lh-cancel-toggle');
      if (flagged.has(merchant)) {
        monthly += m;
        count += 1;
        if (btn) {
          btn.textContent = '✓ Will cancel';
          btn.style.color = 'var(--lg-teal)';
          btn.style.borderColor = 'var(--lg-teal)';
          btn.classList.remove('ghost');
          btn.classList.add('outline');
          row.style.background = 'rgba(108,157,157,0.06)';
        }
      } else {
        if (btn) {
          btn.textContent = '× Cancel';
          btn.style.color = 'var(--lg-text-muted)';
          btn.style.borderColor = '';
          btn.classList.add('ghost');
          btn.classList.remove('outline');
          row.style.background = '';
        }
      }
    });
    if (count > 0) {
      tally.style.display = 'block';
      tallyMo.textContent    = '$' + fmt(monthly);
      tallyYr.textContent    = '$' + fmt(monthly * 12);
      tallyCount.textContent = count;
    } else {
      tally.style.display = 'none';
    }
  }

  document.querySelectorAll('.lh-cancel-toggle').forEach(btn => {
    btn.addEventListener('click', () => {
      const merchant = btn.dataset.merchant;
      if (flagged.has(merchant)) {
        flagged.delete(merchant);
      } else {
        flagged.add(merchant);
      }
      saveFlagged(flagged);
      refreshTally();
    });
  });

  refreshTally();

  // ---- helpers ----
  function fmt(n) {
    return Number(n).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2});
  }
  let flashEl = null;
  function flash(msg) {
    if (!flashEl) {
      flashEl = document.createElement('div');
      flashEl.style.cssText = `
        position: fixed; bottom: 24px; left: 50%; transform: translateX(-50%);
        background: var(--lg-bg-elev); border: 1px solid var(--lg-brass-dim);
        color: var(--lg-text); padding: 10px 18px; border-radius: 999px;
        font-size: 0.88rem; z-index: 9999; box-shadow: var(--lg-shadow-lg);
        opacity: 0; transition: opacity 0.2s;
      `;
      document.body.appendChild(flashEl);
    }
    flashEl.textContent = msg;
    flashEl.style.opacity = '1';
    clearTimeout(flashEl._timer);
    flashEl._timer = setTimeout(() => { flashEl.style.opacity = '0'; }, 2400);
  }
})();
