/*
 * Leak Hunt review interactions:
 *   - inline category change → POST tx_update, offers "make rule"
 *   - recurring star toggle
 *   - bulk select + bulk apply category / recurring
 *   - filter pills (uncategorized / recurring / all)
 *   - keyboard mode: 1-9 keys assign top categories, arrows navigate
 */
(function () {
  const $ = (sel, root) => (root || document).querySelector(sel);
  const $$ = (sel, root) => Array.from((root || document).querySelectorAll(sel));

  const LEAK_ID = window.LH_LEAK_ID;
  const CATEGORIES = window.LH_CATEGORIES || [];
  if (!LEAK_ID) return;

  // Quick-key category map for keyboard mode (1-9). Pick from the
  // available categories — fall back to defaults if not present.
  const QUICK_KEYS = [
    'Groceries', 'Dining out', 'Coffee', 'Streaming & subscriptions',
    'Transportation', 'Shopping', 'Bills', 'Health', 'Other',
  ];

  const tbody = $('#lh-tbody');
  if (!tbody) return;

  // ---- Mark uncategorized rows so the style highlights them.
  refreshRowFlags();

  function refreshRowFlags() {
    $$('.lh-row').forEach(row => {
      const cat = row.dataset.category;
      row.classList.toggle('lh-uncategorized', cat === 'Uncategorized');
    });
  }

  // ---- inline category change ----
  tbody.addEventListener('change', async (e) => {
    // (a) "rule?" checkbox toggled — create a rule for this row's
    // current description + current category. Checking after the fact
    // works exactly like checking it before the category change.
    if (e.target.classList && e.target.classList.contains('lh-make-rule')) {
      if (!e.target.checked) return;  // unchecking doesn't delete the rule
      const tr = e.target.closest('tr');
      const sel = tr.querySelector('.lh-cat-select');
      const id  = e.target.dataset.id;
      if (!sel || sel.value === 'Uncategorized') {
        flash('Pick a real category first — rule needs something to assign.');
        e.target.checked = false;
        return;
      }
      const fd = new FormData();
      fd.set('category', sel.value);
      fd.set('make_rule', '1');
      try {
        const res = await fetch(`/ledger/leak-hunt/${LEAK_ID}/transactions/${id}/update`, {
          method: 'POST',
          body: fd,
          headers: {'X-Requested-With': 'fetch'},
        });
        const data = await res.json();
        applyRetroUpdates(data.retro_updates || []);
        const n = (data.retro_updates || []).length;
        if (data.rule_created) {
          flash(n > 0
            ? `Rule created. Auto-applied to ${n} matching row${n>1?'s':''} in this hunt.`
            : `Rule created: future "${data.rule_created}" → ${sel.value}`);
        } else {
          flash(n > 0
            ? `Rule already existed — applied to ${n} matching row${n>1?'s':''} here.`
            : `Rule already exists for that description.`);
        }
      } catch (err) {
        console.error(err);
      }
      return;
    }

    // (b) category dropdown changed — update the transaction, show the
    // "rule?" affordance, and (if the user pre-checked it) create the rule.
    const sel = e.target.closest('.lh-cat-select');
    if (!sel) return;
    const id = sel.dataset.id;
    const newCat = sel.value;

    const ruleLabel = sel.closest('tr').querySelector('.lh-rule-label');
    if (ruleLabel) ruleLabel.style.display = 'inline-flex';

    const fd = new FormData();
    fd.set('category', newCat);
    const makeRule = sel.closest('tr').querySelector('.lh-make-rule');
    if (makeRule && makeRule.checked) fd.set('make_rule', '1');

    try {
      const res = await fetch(`/ledger/leak-hunt/${LEAK_ID}/transactions/${id}/update`, {
        method: 'POST',
        body: fd,
        headers: {'X-Requested-With': 'fetch'},
      });
      const data = await res.json();
      sel.closest('tr').dataset.category = newCat;
      sel.dataset.original = newCat;
      refreshRowFlags();
      applyRetroUpdates(data.retro_updates || []);
      const n = (data.retro_updates || []).length;
      if (data.rule_created) {
        flash(n > 0
          ? `Rule created — also applied to ${n} matching row${n>1?'s':''} in this hunt.`
          : `Rule created: "${data.rule_created}" → ${newCat}`);
      }
    } catch (err) {
      console.error(err);
    }
  });

  function applyRetroUpdates(updates) {
    updates.forEach(u => {
      const tr = $$('.lh-row').find(r => parseInt(r.dataset.id, 10) === u.id);
      if (!tr) return;
      const s = tr.querySelector('.lh-cat-select');
      if (s) {
        s.value = u.category;
        s.dataset.original = u.category;
        // Brief brass flash so the user sees what just changed
        tr.style.transition = 'background-color 0.6s';
        tr.style.backgroundColor = 'rgba(176,141,87,0.18)';
        setTimeout(() => { tr.style.backgroundColor = ''; }, 900);
      }
      tr.dataset.category = u.category;
    });
    refreshRowFlags();
  }

  // ---- recurring star toggle ----
  tbody.addEventListener('click', async (e) => {
    const btn = e.target.closest('.lh-recurring-toggle');
    if (!btn) return;
    const tr = btn.closest('tr');
    const current = tr.dataset.recurring === '1';
    const next = !current;
    const fd = new FormData();
    fd.set('is_recurring', next ? '1' : '0');
    const id = btn.dataset.id;
    try {
      await fetch(`/ledger/leak-hunt/${LEAK_ID}/transactions/${id}/update`, {
        method: 'POST',
        body: fd,
        headers: {'X-Requested-With': 'fetch'},
      });
      tr.dataset.recurring = next ? '1' : '0';
      btn.textContent = next ? '★' : '☆';
      btn.style.color = next ? 'var(--lg-brass)' : 'var(--lg-text-dim)';
    } catch (err) {
      console.error(err);
    }
  });

  // ---- bulk select ----
  const selectAll = $('#lh-select-all');
  const bulkStrip = $('#lh-bulk-strip');
  const bulkCount = $('#lh-bulk-count');

  function visibleRows() {
    return $$('.lh-row').filter(r => !r.classList.contains('lh-hidden'));
  }
  function selectedIds() {
    return $$('.lh-row-check:checked').map(cb => parseInt(cb.dataset.id, 10));
  }
  function refreshBulkStrip() {
    const n = selectedIds().length;
    if (n > 0) {
      bulkStrip.style.display = 'flex';
      bulkCount.textContent = `${n} selected`;
    } else {
      bulkStrip.style.display = 'none';
    }
  }

  selectAll.addEventListener('change', () => {
    visibleRows().forEach(r => {
      const cb = r.querySelector('.lh-row-check');
      if (cb) cb.checked = selectAll.checked;
    });
    refreshBulkStrip();
  });
  tbody.addEventListener('change', (e) => {
    if (e.target.classList && e.target.classList.contains('lh-row-check')) {
      refreshBulkStrip();
    }
  });

  $('#lh-bulk-apply').addEventListener('click', async () => {
    const ids = selectedIds();
    const cat = $('#lh-bulk-category').value;
    if (!ids.length || !cat) return;
    const res = await fetch(`/ledger/leak-hunt/${LEAK_ID}/transactions/bulk`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ ids, category: cat }),
    });
    if (res.ok) {
      ids.forEach(id => {
        const tr = $$('.lh-row').find(r => parseInt(r.dataset.id, 10) === id);
        if (!tr) return;
        const sel = tr.querySelector('.lh-cat-select');
        if (sel) {
          sel.value = cat;
          sel.dataset.original = cat;
        }
        tr.dataset.category = cat;
      });
      refreshRowFlags();
      flash(`Updated ${ids.length} transactions → ${cat}`);
    }
  });

  $('#lh-bulk-recurring').addEventListener('click', async () => {
    const ids = selectedIds();
    if (!ids.length) return;
    // Toggle based on majority current state (if most are recurring, unset; else set).
    const rows = ids.map(id => $$('.lh-row').find(r => parseInt(r.dataset.id, 10) === id)).filter(Boolean);
    const recCount = rows.filter(r => r.dataset.recurring === '1').length;
    const next = recCount < rows.length / 2 ? 1 : 0;
    const res = await fetch(`/ledger/leak-hunt/${LEAK_ID}/transactions/bulk`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ ids, is_recurring: next }),
    });
    if (res.ok) {
      rows.forEach(r => {
        r.dataset.recurring = String(next);
        const btn = r.querySelector('.lh-recurring-toggle');
        if (btn) {
          btn.textContent = next ? '★' : '☆';
          btn.style.color = next ? 'var(--lg-brass)' : 'var(--lg-text-dim)';
        }
      });
      flash(`${ids.length} transactions ${next ? 'marked' : 'cleared'} as recurring`);
    }
  });

  $('#lh-bulk-clear').addEventListener('click', () => {
    $$('.lh-row-check').forEach(cb => { cb.checked = false; });
    selectAll.checked = false;
    refreshBulkStrip();
  });

  // ---- filter pills ----
  function applyFilter(predicate) {
    $$('.lh-row').forEach(r => {
      r.classList.toggle('lh-hidden', !predicate(r));
    });
  }
  $('#lh-filter-uncategorized').addEventListener('click', () =>
    applyFilter(r => r.dataset.category === 'Uncategorized')
  );
  $('#lh-filter-recurring').addEventListener('click', () =>
    applyFilter(r => r.dataset.recurring === '1')
  );
  $('#lh-filter-all').addEventListener('click', () =>
    applyFilter(() => true)
  );

  // ---- keyboard mode ----
  const kbBtn = $('#lh-keyboard-mode');
  let kbActive = false;
  let kbIndex = 0;

  function enterKbMode() {
    // Filter to uncategorized, sort by amount desc by reordering DOM.
    applyFilter(r => r.dataset.category === 'Uncategorized');
    const rows = visibleRows().sort((a, b) => {
      const aAmt = parseFloat(a.children[3].textContent.replace(/[^\d.-]/g, '')) || 0;
      const bAmt = parseFloat(b.children[3].textContent.replace(/[^\d.-]/g, '')) || 0;
      return bAmt - aAmt;
    });
    rows.forEach(r => tbody.appendChild(r));
    kbActive = true;
    kbIndex = 0;
    kbBtn.textContent = 'Exit keyboard mode';
    focusRow();
    flash('Keyboard mode: 1-9 to categorize, ↑/↓ to navigate, Esc to exit');
  }
  function exitKbMode() {
    kbActive = false;
    $$('.lh-row').forEach(r => r.classList.remove('lh-keyboard-focus'));
    applyFilter(() => true);
    kbBtn.textContent = 'Keyboard mode →';
  }
  function focusRow() {
    $$('.lh-row').forEach(r => r.classList.remove('lh-keyboard-focus'));
    const visible = visibleRows();
    if (!visible.length) {
      flash('Nothing left to categorize. Great work.');
      exitKbMode();
      return;
    }
    if (kbIndex >= visible.length) kbIndex = visible.length - 1;
    if (kbIndex < 0) kbIndex = 0;
    visible[kbIndex].classList.add('lh-keyboard-focus');
    visible[kbIndex].scrollIntoView({block: 'center', behavior: 'smooth'});
  }

  kbBtn.addEventListener('click', () => {
    if (kbActive) exitKbMode(); else enterKbMode();
  });

  document.addEventListener('keydown', async (e) => {
    if (!kbActive) return;
    // Ignore when typing in an input
    if (e.target.matches('input, select, textarea')) return;
    if (e.key === 'Escape') {
      exitKbMode();
      return;
    }
    if (e.key === 'ArrowDown' || e.key === 'j') {
      e.preventDefault();
      kbIndex += 1;
      focusRow();
      return;
    }
    if (e.key === 'ArrowUp' || e.key === 'k') {
      e.preventDefault();
      kbIndex -= 1;
      focusRow();
      return;
    }
    const n = parseInt(e.key, 10);
    if (n >= 1 && n <= 9) {
      const cat = QUICK_KEYS[n - 1];
      if (!cat) return;
      const visible = visibleRows();
      const row = visible[kbIndex];
      if (!row) return;
      const sel = row.querySelector('.lh-cat-select');
      if (!sel) return;
      sel.value = cat;
      sel.dispatchEvent(new Event('change', { bubbles: true }));
      // Advance to next row.
      kbIndex += 1;
      // Brief delay then re-filter to drop the just-categorized row
      setTimeout(() => {
        applyFilter(r => r.dataset.category === 'Uncategorized');
        focusRow();
      }, 80);
    }
  });

  // ---- flash helper ----
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
