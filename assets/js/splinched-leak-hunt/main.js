// Splinched · Leak Hunt — UI orchestration.
//
// Glues file drop → parse → categorize → results → review loop. All math
// runs in this tab; no network calls after page load (CSP enforces that).
// The only fetch is the bundled example CSV, served same-origin.

import {
  parseCsv, categorizeAll, computeStats, cleanMerchantName,
  DEFAULT_CATEGORIES, DEFAULT_RULES, EXCLUDED_FROM_LEAK,
} from './leak_hunt.js';

const RULES_KEY    = 'splinched-leak-rules-v1';
const BASELINE_KEY = 'splinched-leak-baseline-v1';
const EXAMPLE_URL  = '/assets/splinched/leak-hunt-example.csv';
const CADENCE_MIN_DAYS = 75;

// ---- state ----
const app = {
  records: [],       // parsed + categorized transactions
  rules: cloneRules(DEFAULT_RULES),
  result: null,      // computeStats() output
  format: '',
  rawHeader: [],     // header row (for the column mapper)
  rawContent: '',    // raw CSV text (re-parse with a column map)
  cancelled: new Set(), // cleaned_name of charges flagged to cancel (this session)
};

function cloneRules(rules) {
  return rules.map(r => ({ ...r }));
}

// ---- DOM helpers ----
const $  = (sel) => document.querySelector(sel);
const $$ = (sel) => Array.from(document.querySelectorAll(sel));
function showState(name) {
  $$('[data-state]').forEach(el => el.classList.toggle('is-active', el.dataset.state === name));
}
function escapeHtml(s) {
  return String(s == null ? '' : s).replace(/[&<>"']/g, c =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}
const fmtMoney = (n) => '$' + (n || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const fmtMoney0 = (n) => '$' + Math.round(n || 0).toLocaleString('en-US');

// ---- file load ----
async function loadFile(file) {
  try {
    const text = await file.text();
    ingest(text);
  } catch (err) {
    showFatal(err);
  }
}

function ingest(text) {
  app.rawContent = text;
  const { records, format, header } = parseCsv(text);
  app.format = format;
  app.rawHeader = header;
  if (format === 'unknown' || !records.length) {
    showColumnMapper(header, records.length);
    return;
  }
  setRecords(records);
}

function setRecords(records) {
  app.records = records;
  app.cancelled = new Set();
  categorizeAll(app.records, app.rules);
  recompute();
  renderAll();
  showState('results');
  window.scrollTo({ top: 0, behavior: 'auto' });
}

function recompute() {
  app.result = computeStats(app.records);
}

function showFatal(err) {
  $('#lh-map-body').innerHTML =
    `<div class="sp-issue"><p class="sp-issue-msg">Couldn't read the file: ${escapeHtml(String(err && err.message || err))}</p>
     <p class="sp-issue-hint">Make sure it's a plain CSV export (not a PDF or .xlsx). In your bank, look for "Export" or "Download" → CSV.</p></div>`;
  $('#lh-map-go').style.display = 'none';
  $('#lh-map-flip').closest('label').style.display = 'none';
  showState('map');
}

// ---- column mapper (unknown format) ----
function showColumnMapper(header, recordCount) {
  $('#lh-map-go').style.display = '';
  $('#lh-map-flip').closest('label').style.display = '';
  const cols = (header || []).map((h, i) => ({ i, name: (h || '').trim() || `Column ${i + 1}` }));
  const opts = (selIdx) => cols.map(c =>
    `<option value="${c.i}"${c.i === selIdx ? ' selected' : ''}>${escapeHtml(c.name)}</option>`).join('');
  // Best-guess defaults from header names.
  const guess = (...needles) => {
    const idx = cols.findIndex(c => needles.some(n => c.name.toLowerCase().includes(n)));
    return idx === -1 ? 0 : idx;
  };
  const gDate = guess('date', 'posted');
  const gDesc = guess('desc', 'memo', 'name', 'payee', 'merchant');
  const gAmt  = guess('amount', 'debit', 'value');
  $('#lh-map-body').innerHTML = `
    ${recordCount === 0 ? '<p class="sp-issue-hint" style="margin-bottom:14px;">No data rows were detected with the default columns — pick them manually below.</p>' : ''}
    <div class="lh-map-row"><label>Date column</label><select class="sp-select" id="lh-map-date">${opts(gDate)}</select></div>
    <div class="lh-map-row"><label>Description</label><select class="sp-select" id="lh-map-desc">${opts(gDesc)}</select></div>
    <div class="lh-map-row"><label>Amount</label><select class="sp-select" id="lh-map-amt">${opts(gAmt)}</select></div>
  `;
  showState('map');
}

function applyColumnMap() {
  const dateCol = app.rawHeader[+$('#lh-map-date').value] || '';
  const descCol = app.rawHeader[+$('#lh-map-desc').value] || '';
  const amtCol  = app.rawHeader[+$('#lh-map-amt').value]  || '';
  const flip = $('#lh-map-flip').checked;
  const { records } = parseCsv(app.rawContent, 'generic_v1', {
    date: dateCol, description: descCol, amount: amtCol,
  });
  if (flip) for (const r of records) r.amount = -r.amount;
  if (!records.length) {
    $('#lh-map-body').insertAdjacentHTML('beforeend',
      `<div class="sp-issue" style="margin-top:12px;"><p class="sp-issue-msg">Still no rows parsed.</p>
       <p class="sp-issue-hint">Double-check the Amount column — it should hold dollar figures.</p></div>`);
    return;
  }
  app.format = 'generic_v1';
  setRecords(records);
}

// ---- results: render everything ----
function renderAll() {
  renderTotals();
  renderCadence();
  renderComparison();
  renderBreakdown();
  renderRecurring();
  renderBiggest();
  renderReview();
}

function renderTotals() {
  const r = app.result;
  $('#lh-totals').innerHTML = `
    <div class="sp-totals">
      <div><span class="sp-mid-label">Total outflow</span>
        <div class="sp-tot-val">${fmtMoney(r.totalOutflow)}</div>
        <div class="sp-tot-sub">leaks only · transfers &amp; income excluded</div></div>
      <div><span class="sp-mid-label">Inflow</span>
        <div class="sp-tot-val">${fmtMoney(r.totalInflow)}</div>
        <div class="sp-tot-sub">deposits / refunds</div></div>
      <div><span class="sp-mid-label">Net</span>
        <div class="sp-tot-val ${r.net > 0 ? 'sp-neg' : 'sp-pos'}">${r.net < 0 ? '+' : '−'}${fmtMoney(Math.abs(r.net))}</div>
        <div class="sp-tot-sub">${r.net > 0 ? 'spent more than came in' : 'came out ahead'}</div></div>
      <div><span class="sp-mid-label">Period</span>
        <div class="sp-tot-val" style="font-size:1.05rem;font-family:var(--sp-mono);">${r.periodStart || '—'}<br>→ ${r.periodEnd || '—'}</div>
        <div class="sp-tot-sub">${r.spanDays} days</div></div>
      <div><span class="sp-mid-label">Transactions</span>
        <div class="sp-tot-val">${r.transactionCount}</div>
        <div class="sp-tot-sub">${r.recurringCount} look recurring</div></div>
    </div>`;
}

function renderCadence() {
  const r = app.result;
  if (r.spanDays && r.spanDays < CADENCE_MIN_DAYS) {
    $('#lh-cadence').innerHTML = `
      <div class="sp-cadence-inline">
        This file spans only <strong>${r.spanDays} days</strong>. The recurring detector needs to see a
        charge at least twice, so a short window misses most subscriptions. For a real first hunt,
        export <strong>≥ 90 days</strong> and re-run.
      </div>`;
  } else {
    $('#lh-cadence').innerHTML = '';
  }
}

// brass tints by rank for the stacked bar / legend
const TINTS = [0.95, 0.78, 0.62, 0.50, 0.40, 0.32, 0.26, 0.22, 0.18, 0.15];
const tintAt = (i) => i < TINTS.length ? TINTS[i] : 0.12;
const swatch = (i) => `rgba(var(--sp-bar-rgb), ${tintAt(i)})`;

function renderBreakdown() {
  const r = app.result;
  const spend = r.breakdown.filter(b => !b.is_excluded && b.total > 0);
  let bar = '', legend = '';
  if (r.totalOutflow > 0 && spend.length) {
    bar = `<div class="lh-stacked-bar" title="Where the money went">` + spend.map((b, i) => {
      const pct = b.total / r.totalOutflow * 100;
      return `<div class="lh-bar-segment" style="width:${pct}%;background-color:${swatch(i)};"
        title="${escapeHtml(b.category)}: ${fmtMoney(b.total)} (${pct.toFixed(1)}%)">
        ${pct > 8 ? `<span class="lh-bar-label">${escapeHtml(b.category)}</span>` : ''}</div>`;
    }).join('') + `</div>`;
    legend = `<div class="lh-bar-legend">` + spend.map((b, i) =>
      `<span class="lh-legend-item"><span class="lh-legend-swatch" style="background-color:${swatch(i)};"></span>
       ${escapeHtml(b.category)} <span class="sp-mono sp-dim">${fmtMoney0(b.total)}</span></span>`).join('') + `</div>`;
  }
  const rows = r.breakdown.map(b => `
    <tr class="${b.is_excluded ? 'is-excluded' : ''}">
      <td class="l">${escapeHtml(b.category)}${b.is_excluded ? ' <span class="sp-dim" style="font-size:0.72rem;">(not a leak)</span>' : ''}</td>
      <td>${fmtMoney(b.total)}</td>
      <td class="sp-dim">${b.is_excluded ? '—' : b.percent_of_outflow.toFixed(1) + '%'}</td>
      <td>${b.count}</td>
      <td>${fmtMoney(b.avg)}</td>
    </tr>`).join('');
  $('#lh-breakdown').innerHTML = `
    <div class="sp-section-label">Category breakdown</div>
    <div class="sp-card">
      ${bar}${legend}
      <div class="sp-table-wrap" style="margin-top:${bar ? '18px' : '0'};">
        <table class="sp-table">
          <thead><tr><th class="l">Category</th><th>Total</th><th>% outflow</th><th>#</th><th>Avg</th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
      <p class="sp-ctl-hint">Wrong bucket? Open <strong>Review &amp; recategorize</strong> below to fix any transaction or tune the rules.</p>
    </div>`;
}

function renderRecurring() {
  const rec = app.result.recurring;
  if (!rec.length) {
    $('#lh-recurring').innerHTML = `
      <div class="sp-section-label">Recurring charges detected</div>
      <div class="sp-card lh-recurring-card">
        <p class="sp-dim" style="font-style:italic;margin:0;">Nothing flagged as recurring. That usually means a short window — the detector needs to see the same charge ≥ 2 times. Try a 90-day export.</p>
      </div>`;
    return;
  }
  const monthlyTotal = rec.reduce((a, g) => a + g.avg_amount, 0);
  const rows = rec.map(g => {
    const on = app.cancelled.has(g.cleaned_name);
    return `
      <tr class="${on ? 'is-cancel' : ''}">
        <td class="l">${escapeHtml(g.description)}
          <div class="lh-cleaned">→ ${escapeHtml(g.cleaned_name)}${g.suggested_category ? ' · ' + escapeHtml(g.suggested_category) : ''}</div></td>
        <td><span class="sp-pos">${fmtMoney(g.avg_amount)}</span></td>
        <td>${fmtMoney(g.total)}</td>
        <td class="sp-dim">${g.count}</td>
        <td class="l"><button class="lh-chip ${on ? 'is-on' : ''}" data-cancel-toggle="${escapeHtml(g.cleaned_name)}" data-amt="${g.avg_amount}">${on ? '✓ canceling' : '× cancel'}</button></td>
      </tr>`;
  }).join('');
  $('#lh-recurring').innerHTML = `
    <div class="sp-section-label">Recurring charges detected</div>
    <div class="sp-card lh-recurring-card">
      <p class="sp-dim" style="font-style:italic;margin-top:0;">
        The highest-leverage list here. Each one you cancel is money freed <em>every month</em>, forever.
        Flag the ones you don't actually use — the tally updates as you go.
      </p>
      <div class="lh-cancel-tally" id="lh-cancel-tally" style="${app.cancelled.size ? '' : 'display:none;'}"></div>
      <div class="sp-table-wrap">
        <table class="sp-table">
          <thead><tr><th class="l">Merchant</th><th>Avg / charge</th><th>Total</th><th>#</th><th class="l">Flag</th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
      <p class="sp-ctl-hint" style="margin-top:14px;">
        Detected recurring spend totals ~<strong>${fmtMoney0(monthlyTotal)}/mo</strong> (avg per charge).
        Redirect anything you cancel straight at your debt.
      </p>
    </div>`;
  renderCancelTally();
  $$('#lh-recurring [data-cancel-toggle]').forEach(btn => {
    btn.addEventListener('click', () => {
      const name = btn.getAttribute('data-cancel-toggle');
      if (app.cancelled.has(name)) app.cancelled.delete(name); else app.cancelled.add(name);
      renderRecurring();
    });
  });
}

function renderCancelTally() {
  const el = $('#lh-cancel-tally');
  if (!el) return;
  if (!app.cancelled.size) { el.style.display = 'none'; return; }
  const rec = app.result.recurring;
  let monthly = 0;
  for (const g of rec) if (app.cancelled.has(g.cleaned_name)) monthly += g.avg_amount;
  el.style.display = '';
  el.innerHTML = `
    <div><span class="sp-mid-label">Flagged to cancel</span>
      <div><span class="big sp-pos">${fmtMoney(monthly)}</span><span class="sp-dim">/mo</span>
        · <span class="sp-pos">${fmtMoney0(monthly * 12)}</span>/yr freed
        · ${app.cancelled.size} item(s)</div></div>
    <div class="sp-dim" style="max-width:320px;text-align:right;font-size:0.85rem;">
      Apply it by bumping your debt attack by ${fmtMoney0(monthly)}/mo.</div>`;
}

function renderBiggest() {
  const big = app.result.biggest;
  if (!big.length) { $('#lh-biggest').innerHTML = ''; return; }
  const rows = big.map(t => `
    <tr>
      <td class="l sp-mono" style="font-size:0.8rem;">${escapeHtml(t.tx_date)}</td>
      <td class="l">${escapeHtml(t.description)}</td>
      <td class="l sp-dim">${escapeHtml(t.category)}</td>
      <td>${fmtMoney(t.amount)}</td>
    </tr>`).join('');
  $('#lh-biggest').innerHTML = `
    <div class="sp-section-label">Biggest individual transactions</div>
    <div class="sp-card" style="padding:0;">
      <div class="sp-table-wrap">
        <table class="sp-table">
          <thead><tr><th class="l">Date</th><th class="l">Description</th><th class="l">Category</th><th>Amount</th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
    </div>`;
}

// ---- comparison vs last saved hunt ----
function renderComparison() {
  const base = loadBaseline();
  if (!base) { $('#lh-comparison').innerHTML = ''; return; }
  const r = app.result;
  const deltaTotal = r.totalOutflow - (base.totalOutflow || 0);
  const thisMap = {};
  for (const b of r.breakdown) if (!b.is_excluded) thisMap[b.category] = b.total;
  const priorMap = base.breakdown || {};
  const cats = Array.from(new Set([...Object.keys(thisMap), ...Object.keys(priorMap)]));
  const deltas = cats.map(c => ({ category: c, now: thisMap[c] || 0, prior: priorMap[c] || 0, delta: (thisMap[c] || 0) - (priorMap[c] || 0) }))
    .sort((a, b) => Math.abs(b.delta) - Math.abs(a.delta)).slice(0, 10);
  const deltaCell = (d) => d < -0.005 ? `<span class="sp-pos">−${fmtMoney(-d)}</span>`
    : d > 0.005 ? `<span class="sp-neg">+${fmtMoney(d)}</span>` : '—';
  $('#lh-comparison').innerHTML = `
    <div class="sp-section-label">vs. your saved baseline (${escapeHtml(base.periodStart || '?')} → ${escapeHtml(base.periodEnd || '?')})</div>
    <div class="sp-card">
      <p class="sp-delta-headline ${deltaTotal > 0 ? 'sp-neg' : 'sp-pos'}">
        Δ ${deltaCell(deltaTotal)} <span class="sp-dim" style="font-size:0.85rem;">in total leak spend</span></p>
      <div class="sp-table-wrap" style="margin-top:12px;">
        <table class="sp-table">
          <thead><tr><th class="l">Category</th><th>This hunt</th><th>Baseline</th><th>Δ</th></tr></thead>
          <tbody>${deltas.map(d => `<tr><td class="l">${escapeHtml(d.category)}</td>
            <td>${fmtMoney(d.now)}</td><td class="sp-dim">${fmtMoney(d.prior)}</td><td>${deltaCell(d.delta)}</td></tr>`).join('')}</tbody>
        </table>
      </div>
    </div>`;
}

function saveBaseline() {
  const r = app.result;
  const breakdown = {};
  for (const b of r.breakdown) if (!b.is_excluded) breakdown[b.category] = b.total;
  const payload = {
    periodStart: r.periodStart, periodEnd: r.periodEnd,
    totalOutflow: r.totalOutflow, breakdown,
  };
  try {
    localStorage.setItem(BASELINE_KEY, JSON.stringify(payload));
    const btn = $('#lh-save-compare');
    if (btn) { const o = btn.textContent; btn.textContent = 'Saved ✓'; setTimeout(() => btn.textContent = o, 1800); }
    renderComparison();
  } catch (_) { /* private mode / quota */ }
}

function loadBaseline() {
  try {
    const raw = localStorage.getItem(BASELINE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch (_) { return null; }
}

// ---- review & recategorize panel ----
function availableCategories() {
  const set = new Set(DEFAULT_CATEGORIES);
  for (const r of app.records) if (r.category) set.add(r.category);
  return Array.from(set);
}

function renderReview() {
  const cats = availableCategories();
  const catOpts = (sel) => cats.map(c => `<option value="${escapeHtml(c)}"${c === sel ? ' selected' : ''}>${escapeHtml(c)}</option>`).join('');

  // Rules editor
  const ruleRows = app.rules.map((rule, i) => `
    <div class="lh-rule-row" data-rule-idx="${i}">
      <select class="sp-select" data-rf="match_type">
        ${['contains', 'starts_with', 'equals', 'regex'].map(t => `<option value="${t}"${rule.match_type === t ? ' selected' : ''}>${t}</option>`).join('')}
      </select>
      <input class="sp-input" data-rf="match_value" value="${escapeHtml(rule.match_value)}" placeholder="text to match">
      <select class="sp-select" data-rf="category">${catOpts(rule.category)}</select>
      <button data-rule-remove title="Delete rule">×</button>
    </div>`).join('');

  // Transaction table (sorted by date desc for review)
  const txSorted = app.records.map((r, i) => ({ r, i }))
    .sort((a, b) => (b.r.date || '').localeCompare(a.r.date || '') || b.i - a.i);
  const txRows = txSorted.map(({ r, i }) => `
    <tr>
      <td class="l sp-mono" style="font-size:0.78rem;">${escapeHtml(r.date)}${r.pending ? ' <span class="sp-dim">(pending)</span>' : ''}</td>
      <td class="l">${escapeHtml(r.description)}</td>
      <td>${r.amount >= 0 ? fmtMoney(r.amount) : `<span class="sp-pos">−${fmtMoney(-r.amount)}</span>`}</td>
      <td class="l"><select class="sp-select" data-tx-cat="${i}">${catOpts(r.category)}</select></td>
    </tr>`).join('');

  $('#lh-review-body').innerHTML = `
    <div class="lh-review-block">
      <p class="sp-ctl-label">Auto-categorize rules</p>
      <p class="sp-ctl-hint" style="margin-top:0;margin-bottom:10px;">First match wins, top to bottom. Edit, add, or remove — then <strong>Re-apply</strong> to recategorize every transaction (this overwrites manual fixes below). Rules are saved in your browser.</p>
      <div id="lh-rules">${ruleRows}</div>
      <div style="margin-top:10px;display:flex;gap:8px;flex-wrap:wrap;">
        <button class="sp-btn-secondary" id="lh-add-rule">+ Add rule</button>
        <button class="sp-btn-secondary" id="lh-apply-rules">↻ Re-apply rules</button>
        <button class="sp-btn-secondary" id="lh-reset-rules">Reset to defaults</button>
      </div>
    </div>
    <div class="lh-review-block">
      <p class="sp-ctl-label">Transactions (${app.records.length}) — fix any bucket directly</p>
      <div class="sp-table-wrap" style="max-height:460px;overflow-y:auto;">
        <table class="sp-table">
          <thead><tr><th class="l">Date</th><th class="l">Description</th><th>Amount</th><th class="l">Category</th></tr></thead>
          <tbody>${txRows}</tbody>
        </table>
      </div>
    </div>`;
  wireReview();
}

function wireReview() {
  // Per-transaction category edit → recompute stats (preserve other edits)
  $$('#lh-review-body [data-tx-cat]').forEach(sel => {
    sel.addEventListener('change', e => {
      const idx = +e.target.getAttribute('data-tx-cat');
      app.records[idx].category = e.target.value;
      recompute();
      // Re-render results sections but keep the review panel scroll/state.
      renderTotals(); renderCadence(); renderComparison();
      renderBreakdown(); renderRecurring(); renderBiggest();
    });
  });

  // Rule field edits
  $$('#lh-review-body .lh-rule-row').forEach(row => {
    const idx = +row.getAttribute('data-rule-idx');
    row.querySelectorAll('[data-rf]').forEach(inp => {
      inp.addEventListener('change', e => {
        app.rules[idx][e.target.getAttribute('data-rf')] = e.target.value;
        persistRules();
      });
    });
    row.querySelector('[data-rule-remove]').addEventListener('click', () => {
      app.rules.splice(idx, 1);
      persistRules();
      renderReview();
    });
  });

  $('#lh-add-rule').addEventListener('click', () => {
    app.rules.push({ id: Date.now(), match_type: 'contains', match_value: '', category: 'Uncategorized', subcategory: null, priority: app.rules.length });
    persistRules();
    renderReview();
  });
  $('#lh-apply-rules').addEventListener('click', () => {
    categorizeAll(app.records, app.rules);
    recompute();
    renderAll();
    keepReviewOpen();
  });
  $('#lh-reset-rules').addEventListener('click', () => {
    if (!confirm('Reset categorization rules to the defaults? Your custom rules will be lost.')) return;
    app.rules = cloneRules(DEFAULT_RULES);
    try { localStorage.removeItem(RULES_KEY); } catch (_) {}
    categorizeAll(app.records, app.rules);
    recompute();
    renderAll();
    keepReviewOpen();
  });
}

function keepReviewOpen() {
  $('#lh-review').classList.add('is-open');
}

function persistRules() {
  try { localStorage.setItem(RULES_KEY, JSON.stringify(app.rules)); } catch (_) {}
}
function restoreRules() {
  try {
    const raw = localStorage.getItem(RULES_KEY);
    if (raw) {
      const arr = JSON.parse(raw);
      if (Array.isArray(arr) && arr.length) app.rules = arr.map(r => ({ ...r }));
    }
  } catch (_) {}
}

// ---- example ----
async function loadExample() {
  try {
    const res = await fetch(EXAMPLE_URL);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    ingest(await res.text());
  } catch (err) {
    showFatal(new Error('Could not load the example file: ' + err.message));
  }
}

// ---- init ----
function init() {
  restoreRules();

  const drop = $('#lh-drop');
  const fileIn = $('#lh-file');
  drop.addEventListener('click', () => fileIn.click());
  fileIn.addEventListener('change', e => { if (e.target.files[0]) loadFile(e.target.files[0]); });
  drop.addEventListener('dragover', e => { e.preventDefault(); drop.classList.add('is-dragover'); });
  drop.addEventListener('dragleave', () => drop.classList.remove('is-dragover'));
  drop.addEventListener('drop', e => {
    e.preventDefault(); drop.classList.remove('is-dragover');
    if (e.dataTransfer.files[0]) loadFile(e.dataTransfer.files[0]);
  });
  $('#lh-try-example').addEventListener('click', e => { e.stopPropagation(); loadExample(); });

  $('#lh-map-go').addEventListener('click', applyColumnMap);
  $('#lh-map-back').addEventListener('click', () => showState('upload'));

  $('#lh-review-head').addEventListener('click', () => $('#lh-review').classList.toggle('is-open'));
  $('#lh-save-compare').addEventListener('click', saveBaseline);
  $('#lh-print').addEventListener('click', () => window.print());
  $('#lh-restart').addEventListener('click', () => { showState('upload'); window.scrollTo({ top: 0 }); });

  showState('upload');
}

document.addEventListener('DOMContentLoaded', init);
