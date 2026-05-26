/*
 * Projection Sandbox — live what-if exploration.
 * Companion to ledger_projection.html and POST /ledger/projection/sandbox.
 */
(function () {
  const $ = (id) => document.getElementById(id);

  const STATE_KEY = 'ledger-sandbox-state';
  const DEBOUNCE_MS = 220;

  const els = {
    redirect:        $('lg-sb-redirect-bonuses'),
    extra:           $('lg-sb-extra-attack'),
    sidePreset:      $('lg-sb-side-preset'),
    sideStart:       $('lg-sb-side-start'),
    customRow:       $('lg-sb-custom-row'),
    customAmount:    $('lg-sb-side-custom-amount'),
    customRamp:      $('lg-sb-side-custom-ramp'),
    windfallList:    $('lg-sb-windfalls'),
    addWindfall:     $('lg-sb-add-windfall'),
    fedloanMin:      $('lg-sb-fedloan-min'),
    fedloanStart:    $('lg-sb-fedloan-start'),
    applyBtn:        $('lg-sb-apply'),
    resetBtn:        $('lg-sb-reset'),
    panel:           $('lg-sandbox-panel'),
    bonusImpact:     $('lg-sb-bonus-impact'),
    extraImpact:     $('lg-sb-extra-impact'),
    compareStrip:    $('lg-compare-strip'),
    stripBaseline:   $('lg-strip-baseline-date'),
    stripBaselineInt:$('lg-strip-baseline-interest'),
    stripSandbox:    $('lg-strip-sandbox-date'),
    stripSandboxInt: $('lg-strip-sandbox-interest'),
    stripMonths:     $('lg-strip-months-delta'),
    stripInterest:   $('lg-strip-interest-delta'),
    tablesWrap:      $('lg-tables-wrap'),
    baselineLabel:   $('lg-baseline-label'),
    sandboxCol:      $('lg-sandbox-table-col'),
    sandboxTbody:    $('lg-sandbox-tbody'),
    modal:           $('lg-apply-modal'),
    modalChanges:    $('lg-modal-changes'),
    modalConfirm:    $('lg-modal-confirm'),
  };

  if (!els.panel) return;  // not on the projection page

  // ---- read/write sandbox state ----
  function readState() {
    const windfalls = [];
    els.windfallList.querySelectorAll('.lg-windfall-row').forEach(row => {
      const mi = parseInt(row.querySelector('[data-w-month]').value, 10);
      const amt = parseFloat(row.querySelector('[data-w-amount]').value);
      const desc = row.querySelector('[data-w-desc]').value || '';
      if (!isNaN(mi) && !isNaN(amt) && amt > 0) {
        windfalls.push({ month_idx: mi, amount: amt, description: desc });
      }
    });
    return {
      redirect_bonuses: !!(els.redirect && els.redirect.checked && !els.redirect.disabled),
      extra_monthly_attack: parseFloat(els.extra.value) || 0,
      side_income: {
        preset: els.sidePreset.value,
        start_month_idx: parseInt(els.sideStart.value, 10) || 0,
        custom_amount: parseFloat(els.customAmount.value) || 0,
        custom_ramp: parseFloat(els.customRamp.value) || 0,
      },
      windfalls,
      fedloan_override: {
        amount: els.fedloanMin.value === '' ? null : (parseFloat(els.fedloanMin.value) || 0),
        starts_month_idx: parseInt(els.fedloanStart.value, 10) || 0,
      },
    };
  }

  function isDefaults(state) {
    if (state.redirect_bonuses) return false;
    if (state.extra_monthly_attack > 0) return false;
    if (state.side_income.preset !== 'none') return false;
    if (state.windfalls.length > 0) return false;
    if (state.fedloan_override.amount !== null && state.fedloan_override.amount !== '') return false;
    return true;
  }

  function persist(state) {
    try {
      if (isDefaults(state)) {
        localStorage.removeItem(STATE_KEY);
      } else {
        localStorage.setItem(STATE_KEY, JSON.stringify(state));
      }
    } catch (e) { /* localStorage unavailable — fine */ }
  }

  function loadPersisted() {
    try {
      const raw = localStorage.getItem(STATE_KEY);
      if (!raw) return null;
      return JSON.parse(raw);
    } catch (e) { return null; }
  }

  function applyStateToInputs(state) {
    if (!state) return;
    if (els.redirect && !els.redirect.disabled) els.redirect.checked = !!state.redirect_bonuses;
    els.extra.value = state.extra_monthly_attack || 0;
    if (state.side_income) {
      els.sidePreset.value = state.side_income.preset || 'none';
      els.sideStart.value = state.side_income.start_month_idx ?? 3;
      els.customAmount.value = state.side_income.custom_amount || 0;
      els.customRamp.value = state.side_income.custom_ramp || 0;
    }
    els.windfallList.innerHTML = '';
    (state.windfalls || []).forEach(w => addWindfallRow(w));
    if (state.fedloan_override) {
      els.fedloanMin.value = state.fedloan_override.amount == null ? '' : state.fedloan_override.amount;
      els.fedloanStart.value = state.fedloan_override.starts_month_idx || 0;
    }
    toggleCustomRow();
  }

  // ---- windfall rows ----
  function addWindfallRow(initial) {
    initial = initial || {};
    const row = document.createElement('div');
    row.className = 'lg-windfall-row';
    row.innerHTML = `
      <span style="display:inline-flex; align-items:baseline; gap:6px;">
        <span class="lg-note">month</span>
        <input type="number" data-w-month value="${initial.month_idx ?? 6}" min="0" max="120"
               class="lg-input lg-num" style="width:70px;">
      </span>
      <span style="display:inline-flex; align-items:baseline; gap:6px;">
        <div class="lg-currency-wrap" style="width:120px;">
          <input type="number" data-w-amount value="${initial.amount ?? 0}" step="50" min="0"
                 class="lg-input lg-num lg-currency">
        </div>
      </span>
      <input type="text" data-w-desc value="${(initial.description || '').replace(/"/g,'&quot;')}"
             class="lg-input" style="flex:1; min-width:140px;" placeholder="Description (optional)">
      <button type="button" class="lg-btn danger sm" data-w-remove>×</button>
    `;
    els.windfallList.appendChild(row);
    row.querySelector('[data-w-remove]').addEventListener('click', () => {
      row.remove();
      schedule();
    });
    row.querySelectorAll('input').forEach(i => i.addEventListener('input', schedule));
  }

  // ---- preset / custom row visibility ----
  function toggleCustomRow() {
    els.customRow.style.display = (els.sidePreset.value === 'custom') ? 'block' : 'none';
  }

  // ---- live update flow ----
  let pendingTimer = null;
  let lastDelta = { months: null, interest_saved: 0 };
  let lastBaselineDate = window.LG_BASELINE.debt_free_date;

  function schedule() {
    const state = readState();
    persist(state);

    if (isDefaults(state)) {
      hideSandbox();
      els.applyBtn.disabled = true;
      return;
    }

    if (pendingTimer) clearTimeout(pendingTimer);
    pendingTimer = setTimeout(() => runSandbox(state), DEBOUNCE_MS);
  }

  function hideSandbox() {
    els.compareStrip.style.display = 'none';
    els.sandboxCol.style.display = 'none';
    els.baselineLabel.style.display = 'none';
    els.tablesWrap.classList.remove('has-sandbox');
    if (els.bonusImpact) els.bonusImpact.textContent = 'toggle on to see the impact.';
    if (els.extraImpact) els.extraImpact.textContent = '';
  }

  async function runSandbox(state) {
    try {
      const res = await fetch('/ledger/projection/sandbox', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(state),
      });
      const data = await res.json();
      renderSandbox(data);
      enableApply(state);
    } catch (e) {
      console.error('sandbox fetch failed', e);
    }
  }

  function renderSandbox(data) {
    const { baseline, sandbox, delta } = data;
    els.compareStrip.style.display = 'block';
    els.baselineLabel.style.display = 'block';
    els.sandboxCol.style.display = 'block';
    els.tablesWrap.classList.add('has-sandbox');

    els.stripBaseline.textContent = baseline.debt_free_date || '—';
    els.stripBaselineInt.textContent = '$' + fmt(baseline.total_interest_paid);
    els.stripSandbox.textContent = sandbox.debt_free_date || '—';
    els.stripSandboxInt.textContent = '$' + fmt(sandbox.total_interest_paid);

    let monthsLabel = '—';
    if (delta.months != null) {
      const m = delta.months;
      if (m < 0) {
        monthsLabel = `${m} months`;
        els.stripMonths.className = 'lg-num lg-pos';
      } else if (m > 0) {
        monthsLabel = `+${m} months`;
        els.stripMonths.className = 'lg-num lg-neg';
      } else {
        monthsLabel = '0 months';
        els.stripMonths.className = 'lg-num lg-dim';
      }
    }
    els.stripMonths.textContent = 'Δ ' + monthsLabel;

    const saved = delta.interest_saved || 0;
    if (saved > 0) {
      els.stripInterest.textContent = '$' + fmt(saved);
      els.stripInterest.className = 'lg-num lg-pos';
    } else if (saved < 0) {
      els.stripInterest.textContent = '−$' + fmt(-saved);
      els.stripInterest.className = 'lg-num lg-neg';
    } else {
      els.stripInterest.textContent = '$0';
      els.stripInterest.className = 'lg-num lg-dim';
    }

    // Render sandbox table
    els.sandboxTbody.innerHTML = sandbox.monthly_rows.map(r => {
      const extraTotal = (r.bonus_applied + r.extra_applied + r.side_income_applied + r.windfall_applied);
      return `
        <tr class="${r.kill_account_name ? 'target-row' : ''}${r.sandbox_touched ? ' sandbox-row' : ''}">
          <td class="lg-mono" style="font-size:0.85rem;">${esc(r.month)}</td>
          <td class="num">$${fmtInt(r.starting_total)}</td>
          <td class="num col-hide-sm">$${fmtInt(r.minimums_applied)}</td>
          <td class="num col-hide-sm">$${fmtInt(r.attack_applied)}</td>
          <td class="num col-hide-sm">${extraTotal > 0 ? '<span class="lg-pos">+$'+fmtInt(extraTotal)+'</span>' : '—'}</td>
          <td class="num col-hide-sm lg-neg">$${fmtInt(r.interest_accrued)}</td>
          <td class="num">$${fmtInt(r.ending_total)}</td>
          <td>${r.kill_account_name ? '<strong class="lg-pos">'+esc(r.kill_account_name)+' ✓</strong>' : ''}</td>
        </tr>
      `;
    }).join('');

    // Inline impact hints
    if (els.extraImpact && readState().extra_monthly_attack > 0) {
      const m = delta.months;
      const dollars = '$' + fmt(Math.max(0, delta.interest_saved));
      els.extraImpact.textContent = (m != null && m < 0)
        ? `Cuts ${Math.abs(m)} months and saves ~${dollars} in interest.`
        : `Saves ~${dollars} in interest.`;
    } else if (els.extraImpact) {
      els.extraImpact.textContent = '';
    }
    if (els.bonusImpact && els.redirect && els.redirect.checked) {
      const m = delta.months;
      els.bonusImpact.textContent = (m != null && m < 0)
        ? `Redirecting them cuts ~${Math.abs(m)} months off your timeline.`
        : 'No measurable timeline change.';
    }
  }

  function enableApply(state) {
    // Enabled if any *applicable* setting is set:
    //   extra_monthly_attack > 0, OR windfalls non-empty, OR fedloan override is set.
    // Bonus redirect + side income ramp are projection-only and don't enable apply.
    const applicable =
      (state.extra_monthly_attack > 0) ||
      (state.windfalls.length > 0) ||
      (state.fedloan_override && state.fedloan_override.amount !== null && state.fedloan_override.amount !== '');
    els.applyBtn.disabled = !applicable;
  }

  // ---- apply modal ----
  function openApplyModal() {
    const state = readState();
    els.modalChanges.innerHTML = '';
    const items = [];

    if (state.extra_monthly_attack > 0) {
      const t = window.LG_CURRENT_TARGET;
      if (t) {
        items.push(`
          <div class="lg-modal-change">
            <span class="kind">Allocation bump</span>
            <strong>${esc(t.name)}</strong>: attack_allocation $${fmt(t.alloc)} → $${fmt(t.alloc + state.extra_monthly_attack)}
          </div>
        `);
      }
    }
    state.windfalls.forEach(w => {
      items.push(`
        <div class="lg-modal-change">
          <span class="kind">New one-time event (planned)</span>
          ${esc(w.description || 'Sandbox windfall')} — $${fmt(w.amount)} in ${monthLabel(w.month_idx)}
        </div>
      `);
    });
    if (state.fedloan_override.amount !== null && state.fedloan_override.amount !== '') {
      items.push(`
        <div class="lg-modal-change">
          <span class="kind">FedLoan minimum</span>
          minimum_payment $${fmt(window.LG_CURRENT_FEDLOAN_MIN)} → $${fmt(state.fedloan_override.amount)}
          ${state.fedloan_override.starts_month_idx > 0 ? '(effective in '+state.fedloan_override.starts_month_idx+' months)' : '(effective immediately)'}
        </div>
      `);
    }

    if (items.length === 0) {
      els.modalChanges.innerHTML = '<div class="lg-modal-empty">No applicable changes. Bonus redirect and side-income ramp are projection-only.</div>';
      els.modalConfirm.disabled = true;
    } else {
      els.modalChanges.innerHTML = items.join('') + `
        <p class="lg-note" style="margin-top:14px;">Bonus redirect and side-income ramp are projection-only assumptions and can't be applied directly.</p>
      `;
      els.modalConfirm.disabled = false;
    }
    els.modal.style.display = 'flex';
  }

  window.lgCloseApplyModal = function () { els.modal.style.display = 'none'; };

  async function confirmApply() {
    const state = readState();
    const payload = {
      apply_extra_attack: state.extra_monthly_attack || 0,
      apply_windfalls:    state.windfalls,
      apply_fedloan_min:  (state.fedloan_override.amount === null || state.fedloan_override.amount === '') ? null : state.fedloan_override.amount,
    };
    els.modalConfirm.disabled = true;
    els.modalConfirm.textContent = 'Applying…';
    try {
      const res = await fetch('/ledger/projection/sandbox/apply', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (data.ok) {
        try { localStorage.removeItem(STATE_KEY); } catch (e) {}
        window.location.reload();
      } else {
        els.modalConfirm.disabled = false;
        els.modalConfirm.textContent = 'Apply changes';
        alert('Apply failed: ' + (data.error || 'unknown'));
      }
    } catch (e) {
      els.modalConfirm.disabled = false;
      els.modalConfirm.textContent = 'Apply changes';
      alert('Apply error: ' + e);
    }
  }

  function resetSandbox() {
    if (els.redirect && !els.redirect.disabled) els.redirect.checked = false;
    els.extra.value = 0;
    els.sidePreset.value = 'none';
    els.sideStart.value = 3;
    els.customAmount.value = 0;
    els.customRamp.value = 0;
    els.windfallList.innerHTML = '';
    els.fedloanMin.value = '';
    els.fedloanStart.value = 0;
    toggleCustomRow();
    hideSandbox();
    try { localStorage.removeItem(STATE_KEY); } catch (e) {}
    els.applyBtn.disabled = true;
  }

  // ---- helpers ----
  function fmt(n) {
    return Number(n).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2});
  }
  function fmtInt(n) {
    return Number(n).toLocaleString('en-US', {maximumFractionDigits: 0});
  }
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":"&#039;"}[c]));
  }
  function monthLabel(idx) {
    const d = new Date();
    d.setDate(1);
    d.setMonth(d.getMonth() + idx);
    return d.toLocaleString('en-US', {month: 'short', year: 'numeric'});
  }

  // ---- wire it up ----
  [els.redirect, els.extra, els.sidePreset, els.sideStart, els.customAmount,
   els.customRamp, els.fedloanMin, els.fedloanStart].forEach(el => {
    if (el) el.addEventListener('input', schedule);
    if (el) el.addEventListener('change', schedule);
  });
  els.sidePreset.addEventListener('change', toggleCustomRow);
  els.addWindfall.addEventListener('click', () => { addWindfallRow(); schedule(); });
  els.applyBtn.addEventListener('click', openApplyModal);
  els.resetBtn.addEventListener('click', resetSandbox);
  els.modalConfirm.addEventListener('click', confirmApply);

  // Restore persisted state on load, open panel if non-default.
  const persisted = loadPersisted();
  if (persisted) {
    applyStateToInputs(persisted);
    if (!isDefaults(persisted)) {
      els.panel.setAttribute('open', 'open');
      schedule();
    }
  }
})();
