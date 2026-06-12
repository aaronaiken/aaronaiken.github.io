// Splinched · Projection & Sandbox — UI orchestration.
//
// Glues together file drop → parse → render → sandbox loop. All math
// runs in this tab; no network calls after page load (CSP enforces that).

import { parseLedger, buildSupportDiagnostic, SUPPORTED_FORMAT_VERSION } from './parser.js';
import { projectPayoff, totalDebt, monthlyInterestBurn } from './projection.js';

const SANDBOX_KEY = 'splinched-sandbox-v1';

// ---- state ----
const app = {
  data:      null,   // parsed ledger data (from parseLedger.data)
  workbook:  null,   // SheetJS workbook (kept for diagnostic copy)
  baseline:  null,   // baseline projection result
  sandboxResult: null,
  sandbox: defaultSandboxState(),
};

function defaultSandboxState() {
  return {
    extraMonthlyAttack: 0,
    bonuses: [],                   // [{monthIdx, amount}] — manual bonus entries
    redirectBonuses: true,         // bonuses always redirect when listed
    sideIncomeRamp: 'none',        // 'none' | 'slow' | 'realistic' | 'custom'
    sideIncomeStartMonthIdx: 3,
    sideIncomeFlatAmount: 0,       // for 'custom'
    windfalls: [],                 // [{monthIdx, amount, note}]
  };
}

const RAMP_SLOW       = [0, 50, 100, 200, 350, 500, 650, 800, 950, 1100, 1250, 1500];
const RAMP_REALISTIC  = [0, 100, 250, 500, 800, 1200, 1600, 2000];

// ---- DOM refs ----
const $  = (sel) => document.querySelector(sel);
const $$ = (sel) => Array.from(document.querySelectorAll(sel));

function showState(name) {
  $$('[data-state]').forEach(el => el.classList.toggle('is-active', el.dataset.state === name));
}

// ---- format helpers ----
const fmtMoney = (n) => '$' + (n || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const fmtMoneyTerse = (n) => '$' + Math.round(n || 0).toLocaleString('en-US');

function monthIdxToYM(idx) {
  const d = new Date();
  const out = new Date(d.getFullYear(), d.getMonth() + idx, 1);
  return `${out.getFullYear()}-${String(out.getMonth() + 1).padStart(2, '0')}`;
}

function ymToMonthIdx(ym) {
  if (!/^\d{4}-\d{2}$/.test(ym)) return null;
  const [y, m] = ym.split('-').map(Number);
  const now = new Date();
  return (y - now.getFullYear()) * 12 + (m - 1 - now.getMonth());
}

function deltaMonths(baselineDate, sandboxDate) {
  if (!baselineDate || !sandboxDate) return null;
  const [by, bm] = baselineDate.split('-').map(Number);
  const [sy, sm] = sandboxDate.split('-').map(Number);
  return (sy - by) * 12 + (sm - bm);
}

// ---- file load ----

async function loadFile(file) {
  try {
    const buf = await file.arrayBuffer();
    if (!window.XLSX) throw new Error('SheetJS failed to load.');
    const wb = window.XLSX.read(buf, { type: 'array', cellDates: true });
    handleParsed(wb);
  } catch (err) {
    showFatal(err);
  }
}

function handleParsed(wb) {
  app.workbook = wb;
  const parsed = parseLedger(wb);
  if (parsed.ok) {
    app.data = parsed.data;
    showConfirm();
  } else {
    showIssues(parsed);
  }
}

function showFatal(err) {
  app.data = null;
  $('#sp-issues-list').innerHTML =
    `<div class="sp-issue"><p class="sp-issue-msg">Couldn't read the file: ${escapeHtml(String(err && err.message || err))}</p><p class="sp-issue-hint">Make sure the file is a valid .xlsx exported from Excel or Google Sheets (File → Download → Microsoft Excel).</p></div>`;
  $('#sp-issues-version').style.display = 'none';
  showState('issues');
}

function showIssues(parseResult) {
  app.data = null;
  const issues = parseResult.issues || [];
  const versionMismatch = issues.find(i => i.severity === 'version-mismatch');
  $('#sp-issues-version').style.display = versionMismatch ? 'block' : 'none';
  if (versionMismatch) {
    $('#sp-issues-version-msg').textContent =
      `Your spreadsheet is format version ${parseResult.formatVersion || '(unknown)'}, but this tool expects version ${SUPPORTED_FORMAT_VERSION}.`;
  }
  $('#sp-issues-list').innerHTML = issues.map(i => `
    <div class="sp-issue${i.severity === 'warning' ? ' is-warning' : ''}${i.severity === 'version-mismatch' ? ' is-version' : ''}">
      <div class="sp-issue-where">${escapeHtml(i.tab)}!${escapeHtml(i.cell)}</div>
      <p class="sp-issue-msg">${escapeHtml(i.message)}</p>
      ${i.suggestion ? `<p class="sp-issue-hint">${escapeHtml(i.suggestion)}</p>` : ''}
    </div>
  `).join('');
  showState('issues');
}

// ---- confirm view ----

function showConfirm() {
  const d = app.data;
  const ageDays = d.latestSnapshotDate
    ? Math.floor((Date.now() - new Date(d.latestSnapshotDate).getTime()) / 86400000)
    : null;
  const ageNote = ageDays === null ? '' :
    ageDays <= 7  ? `<span class="sp-mono sp-dim">(${ageDays} day${ageDays === 1 ? '' : 's'} ago — fresh)</span>` :
    ageDays <= 30 ? `<span class="sp-mono sp-dim">(${ageDays} days ago)</span>` :
    `<span class="sp-mono" style="color:var(--sp-brick)">(${ageDays} days ago — projection may lag reality)</span>`;
  $('#sp-confirm').innerHTML = `
    <h2 class="sp-card-title">What we found</h2>
    <div class="sp-grid-3">
      <div>
        <div class="sp-mid-label">Total owed</div>
        <div class="sp-mid-number">${fmtMoney(totalDebt(d.debts))}</div>
      </div>
      <div>
        <div class="sp-mid-label">Monthly interest burn</div>
        <div class="sp-mid-number">${fmtMoney(monthlyInterestBurn(d.debts))}</div>
      </div>
      <div>
        <div class="sp-mid-label">Default monthly attack</div>
        <div class="sp-mid-number">${fmtMoney(d.defaultAttack)}</div>
      </div>
    </div>
    <div style="margin-top:18px;color:var(--sp-text-body);">
      Parsed <strong>${d.accounts.length} accounts</strong>
      (<strong>${d.debts.length} active debts</strong>),
      <strong>${d.snapshots.length} snapshots</strong>.
      Latest snapshot: <strong>${d.latestSnapshotDate || '—'}</strong> ${ageNote}
    </div>
    ${d.warnings.length ? `<div class="sp-issues" style="margin-top:18px;">${d.warnings.map(w => `
      <div class="sp-issue is-warning">
        <div class="sp-issue-where">${escapeHtml(w.tab)}!${escapeHtml(w.cell)}</div>
        <p class="sp-issue-msg">${escapeHtml(w.message)}</p>
        ${w.suggestion ? `<p class="sp-issue-hint">${escapeHtml(w.suggestion)}</p>` : ''}
      </div>`).join('')}</div>` : ''}
    <details style="margin-top:18px;">
      <summary class="sp-mono" style="font-size:0.78rem;letter-spacing:0.14em;color:var(--sp-brass);cursor:pointer;">Show all accounts ▾</summary>
      <div style="margin-top:14px;">
        ${d.accounts.map(a => `
          <div class="sp-account-row">
            <div><strong>${escapeHtml(a.name)}</strong> <span class="sp-acc-meta">· ${escapeHtml(a.type)} · ${escapeHtml(a.status)}</span></div>
            <div class="sp-acc-meta">APR ${(a.apr || 0).toFixed(2)}%</div>
            <div class="sp-acc-amt">${fmtMoney(a.currentBalance || 0)}</div>
          </div>`).join('')}
      </div>
    </details>
  `;
  showState('confirm');
}

// ---- projection view ----

function runProjection() {
  if (!app.data) return;
  const startToday = startOfMonthFromLatestSnapshot();
  app.baseline = projectPayoff({
    debts: app.data.debts,
    defaultAttack: app.data.defaultAttack,
    today: startToday,
  });
  app.sandboxResult = projectPayoff({
    debts: app.data.debts,
    defaultAttack: app.data.defaultAttack,
    today: startToday,
  }, buildOverrides());
  renderProjection();
}

function startOfMonthFromLatestSnapshot() {
  // Project starts from the user's "now" — but if the latest snapshot is
  // newer than today (e.g. they snapshotted ahead), use that as today.
  // Otherwise use today's local date.
  const now = new Date();
  if (!app.data.latestSnapshotDate) return now;
  const snap = new Date(app.data.latestSnapshotDate + 'T00:00:00');
  return snap > now ? snap : now;
}

function buildOverrides() {
  const s = app.sandbox;
  const overrides = {};
  if (s.extraMonthlyAttack > 0) overrides.extraMonthlyAttack = s.extraMonthlyAttack;

  if (s.redirectBonuses && s.bonuses.length) {
    overrides.redirectBonuses = true;
    overrides.bonusByMonth = {};
    for (const b of s.bonuses) {
      const mi  = Number(b.monthIdx);
      const amt = Number(b.amount || 0);
      if (Number.isFinite(mi) && amt > 0) {
        overrides.bonusByMonth[mi] = (overrides.bonusByMonth[mi] || 0) + amt;
      }
    }
  }

  if (s.sideIncomeRamp && s.sideIncomeRamp !== 'none') {
    overrides.sideIncomeByMonth = buildSideIncomeMap(s);
  }

  if (s.windfalls.length) {
    overrides.windfalls = s.windfalls
      .map(w => ({ monthIdx: Number(w.monthIdx), amount: Number(w.amount || 0) }))
      .filter(w => Number.isFinite(w.monthIdx) && w.amount > 0);
  }

  return overrides;
}

function buildSideIncomeMap(s) {
  const start = Number(s.sideIncomeStartMonthIdx) || 0;
  const map = {};
  if (s.sideIncomeRamp === 'slow') {
    for (let i = 0; i < 240; i++) {
      const v = i < RAMP_SLOW.length ? RAMP_SLOW[i] : RAMP_SLOW[RAMP_SLOW.length - 1];
      if (v > 0) map[start + i] = v;
    }
  } else if (s.sideIncomeRamp === 'realistic') {
    for (let i = 0; i < 240; i++) {
      const v = i < RAMP_REALISTIC.length ? RAMP_REALISTIC[i] : RAMP_REALISTIC[RAMP_REALISTIC.length - 1];
      if (v > 0) map[start + i] = v;
    }
  } else if (s.sideIncomeRamp === 'custom') {
    const flat = Number(s.sideIncomeFlatAmount) || 0;
    if (flat > 0) for (let i = 0; i < 240; i++) map[start + i] = flat;
  }
  return map;
}

function isSandboxActive() {
  const s = app.sandbox;
  return (s.extraMonthlyAttack || 0) > 0
      || (s.bonuses && s.bonuses.some(b => Number(b.amount) > 0))
      || (s.windfalls && s.windfalls.some(w => Number(w.amount) > 0))
      || (s.sideIncomeRamp && s.sideIncomeRamp !== 'none');
}

function renderProjection() {
  const baseDate    = app.baseline.debtFreeDate;
  const baseInt     = app.baseline.totalInterestPaid;

  if (!isSandboxActive()) {
    // Lead with the honest baseline. No comparison until the user starts
    // playing with what-ifs in the sandbox panel below.
    $('#sp-projection').innerHTML = `
      <div class="sp-delta-strip">
        <div>
          <span class="sp-mid-label">Projected debt-free</span>
          <div class="sp-mid-number">${baseDate || '—'}</div>
          <div class="sp-delta-detail">total interest paid ${fmtMoney(baseInt)} · ${app.baseline.monthlyRows.length} months</div>
        </div>
      </div>
      ${renderTableCard('Projection', app.baseline)}
    `;
    showState('projection');
    return;
  }

  const sandboxDate = app.sandboxResult.debtFreeDate;
  const sandInt     = app.sandboxResult.totalInterestPaid;
  const dMonths     = deltaMonths(baseDate, sandboxDate);
  const dInt        = sandInt - baseInt;
  const dMonthsLabel = dMonths === null ? '—' : (dMonths === 0 ? '0' : (dMonths < 0 ? `${dMonths}` : `+${dMonths}`));
  const dIntLabel    = dInt === 0 ? '$0' : (dInt < 0 ? `−${fmtMoneyTerse(Math.abs(dInt))}` : `+${fmtMoneyTerse(dInt)}`);
  const headlineCls  =
    dMonths === null || (dMonths === 0 && Math.abs(dInt) < 0.5) ? 'is-zero' :
    (dMonths > 0 || dInt > 0) ? 'is-negative' : '';

  $('#sp-projection').innerHTML = `
    <div class="sp-delta-strip">
      <div class="sp-delta-row">
        <div>
          <span class="sp-mid-label">Baseline · debt-free</span>
          <div class="sp-mid-number">${baseDate || '—'}</div>
          <div class="sp-delta-detail">total interest ${fmtMoney(baseInt)}</div>
        </div>
        <div>
          <span class="sp-mid-label">Sandbox · debt-free</span>
          <div class="sp-mid-number">${sandboxDate || '—'}</div>
          <div class="sp-delta-detail">total interest ${fmtMoney(sandInt)}</div>
        </div>
      </div>
      <div class="sp-delta-headline ${headlineCls}">
        Δ ${dMonthsLabel} months  ·  ${dIntLabel} interest
      </div>
    </div>

    <div class="sp-grid-2" data-print-pair>
      ${renderTableCard('Baseline', app.baseline)}
      ${renderTableCard('Sandbox',  app.sandboxResult)}
    </div>
  `;
  showState('projection');
}

function renderTableCard(label, result) {
  const rows = result.monthlyRows;
  return `
    <div class="sp-card">
      <h2 class="sp-card-title">${label}</h2>
      <div class="sp-table-wrap">
        <table class="sp-table">
          <thead>
            <tr>
              <th class="l">Month</th>
              <th class="l">Target</th>
              <th>Start</th>
              <th>Min</th>
              <th>Attack</th>
              <th>Extra</th>
              <th>Interest</th>
              <th>End</th>
              <th class="l">Killed</th>
            </tr>
          </thead>
          <tbody>
            ${rows.map(r => {
              const extra = (r.bonusApplied || 0) + (r.extraApplied || 0) + (r.sideIncomeApplied || 0) + (r.windfallApplied || 0);
              const cls = (r.sandboxTouched ? 'is-sandbox-touched ' : '') + (r.killAccountName ? 'is-kill' : '');
              return `<tr class="${cls.trim()}">
                <td class="l">${r.month}</td>
                <td class="l">${escapeHtml(r.currentTargetName || '—')}</td>
                <td>${fmtMoneyTerse(r.startingTotal)}</td>
                <td>${fmtMoneyTerse(r.minimumsApplied)}</td>
                <td>${fmtMoneyTerse(r.attackApplied)}</td>
                <td>${extra ? fmtMoneyTerse(extra) : '—'}</td>
                <td>${fmtMoneyTerse(r.interestAccrued)}</td>
                <td>${fmtMoneyTerse(r.endingTotal)}</td>
                <td class="l">${r.killAccountName ? escapeHtml(r.killAccountName) : ''}</td>
              </tr>`;
            }).join('')}
          </tbody>
        </table>
      </div>
    </div>
  `;
}

// ---- sandbox panel ----

function renderSandbox() {
  const s = app.sandbox;
  $('#sp-sandbox-body').innerHTML = `
    <div class="sp-sandbox-grid">

      <!-- Extra monthly attack -->
      <div class="sp-ctl">
        <p class="sp-ctl-label">Extra monthly attack</p>
        <div class="sp-ctl-row">
          $<input type="number" class="sp-input sp-input-narrow" id="sb-extra" value="${s.extraMonthlyAttack || ''}" placeholder="0" min="0" step="50">
          <span class="sp-dim sp-mono">/ month</span>
        </div>
        <p class="sp-ctl-hint">Adds this to the attack pool every projected month. Cascades when the current target dies.</p>
      </div>

      <!-- Side income ramp -->
      <div class="sp-ctl">
        <p class="sp-ctl-label">Side income ramp</p>
        <div class="sp-ctl-row">
          <select class="sp-select" id="sb-side-ramp">
            ${['none', 'slow', 'realistic', 'custom'].map(opt =>
              `<option value="${opt}"${s.sideIncomeRamp === opt ? ' selected' : ''}>${opt}</option>`
            ).join('')}
          </select>
          <span class="sp-dim sp-mono">starts</span>
          <input type="month" class="sp-input" id="sb-side-start" value="${monthIdxToYM(s.sideIncomeStartMonthIdx)}">
          ${s.sideIncomeRamp === 'custom'
            ? `<span class="sp-dim sp-mono">flat</span>$<input type="number" class="sp-input sp-input-narrow" id="sb-side-flat" value="${s.sideIncomeFlatAmount || ''}" placeholder="0" min="0" step="50">`
            : ''}
        </div>
        <p class="sp-ctl-hint">Slow: ramps $0 → $1,500 over 12 months. Realistic: $0 → $2,000 over 8 months. Custom: a flat amount.</p>
      </div>

      <!-- Bonuses -->
      <div class="sp-ctl">
        <p class="sp-ctl-label">Bonus redirect (manual)</p>
        <div class="sp-rows" id="sb-bonuses">
          ${s.bonuses.map((b, idx) => bonusRowHtml(b, idx)).join('')}
        </div>
        <button class="sp-btn-secondary" id="sb-add-bonus" style="margin-top:10px;">+ Add bonus</button>
        <p class="sp-ctl-hint">Each bonus lands once on its month and cascades onto the current attack target.</p>
      </div>

      <!-- Windfalls -->
      <div class="sp-ctl" style="grid-column: 1 / -1;">
        <p class="sp-ctl-label">One-time windfalls</p>
        <div class="sp-rows" id="sb-windfalls">
          ${s.windfalls.map((w, idx) => windfallRowHtml(w, idx)).join('')}
        </div>
        <button class="sp-btn-secondary" id="sb-add-windfall" style="margin-top:10px;">+ Add windfall</button>
        <p class="sp-ctl-hint">Tax refund, sale of an asset, unexpected reimbursement — anything that lands once.</p>
      </div>

    </div>
  `;
  wireSandboxInputs();
}

function bonusRowHtml(b, idx) {
  return `<div class="sp-row" data-bonus-idx="${idx}">
    <input type="month" class="sp-input" data-field="ym" value="${monthIdxToYM(b.monthIdx)}">
    <div class="sp-ctl-row">$<input type="number" class="sp-input" data-field="amount" value="${b.amount || ''}" placeholder="0" min="0" step="100"></div>
    <button data-remove>×</button>
  </div>`;
}

function windfallRowHtml(w, idx) {
  return `<div class="sp-row" data-windfall-idx="${idx}">
    <input type="month" class="sp-input" data-field="ym" value="${monthIdxToYM(w.monthIdx)}">
    <div class="sp-ctl-row">$<input type="number" class="sp-input" data-field="amount" value="${w.amount || ''}" placeholder="0" min="0" step="100"></div>
    <button data-remove>×</button>
  </div>`;
}

let debounceTimer = null;
function recomputeDebounced() {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(() => {
    persistSandbox();
    // Re-render projection without letting the sandbox visually drift —
    // when "Extra monthly attack" goes from 0 → some value, the projection
    // area swaps from one table to two, growing taller and pushing the
    // controls down. Anchor the sandbox panel's top to where the user sees
    // it, then re-render, then scroll-correct by the delta.
    const sb = document.getElementById('sp-sandbox');
    const beforeTop = sb ? sb.getBoundingClientRect().top : null;
    runProjection();
    if (sb && beforeTop !== null) {
      const afterTop = sb.getBoundingClientRect().top;
      const delta = afterTop - beforeTop;
      if (Math.abs(delta) > 0.5) window.scrollBy(0, delta);
    }
  }, 150);
}

function wireSandboxInputs() {
  $('#sb-extra').addEventListener('input', e => {
    app.sandbox.extraMonthlyAttack = Number(e.target.value) || 0;
    recomputeDebounced();
  });
  $('#sb-side-ramp').addEventListener('change', e => {
    app.sandbox.sideIncomeRamp = e.target.value;
    renderSandbox();
    recomputeDebounced();
  });
  $('#sb-side-start').addEventListener('change', e => {
    const idx = ymToMonthIdx(e.target.value);
    if (idx !== null) app.sandbox.sideIncomeStartMonthIdx = Math.max(0, idx);
    recomputeDebounced();
  });
  const flat = $('#sb-side-flat');
  if (flat) flat.addEventListener('input', e => {
    app.sandbox.sideIncomeFlatAmount = Number(e.target.value) || 0;
    recomputeDebounced();
  });
  $('#sb-add-bonus').addEventListener('click', () => {
    app.sandbox.bonuses.push({ monthIdx: 1, amount: 0 });
    renderSandbox();
  });
  $('#sb-add-windfall').addEventListener('click', () => {
    app.sandbox.windfalls.push({ monthIdx: 6, amount: 0 });
    renderSandbox();
  });

  $$('#sb-bonuses .sp-row').forEach(row => wireRepeaterRow(row, 'bonus'));
  $$('#sb-windfalls .sp-row').forEach(row => wireRepeaterRow(row, 'windfall'));
}

function wireRepeaterRow(row, kind) {
  const idxAttr = kind === 'bonus' ? 'data-bonus-idx' : 'data-windfall-idx';
  const idx = Number(row.getAttribute(idxAttr));
  const list = kind === 'bonus' ? app.sandbox.bonuses : app.sandbox.windfalls;
  row.querySelector('[data-field="ym"]').addEventListener('change', e => {
    const mi = ymToMonthIdx(e.target.value);
    if (mi !== null) list[idx].monthIdx = mi;
    recomputeDebounced();
  });
  row.querySelector('[data-field="amount"]').addEventListener('input', e => {
    list[idx].amount = Number(e.target.value) || 0;
    recomputeDebounced();
  });
  row.querySelector('[data-remove]').addEventListener('click', () => {
    list.splice(idx, 1);
    renderSandbox();
    recomputeDebounced();
  });
}

// ---- persistence ----

function persistSandbox() {
  try { localStorage.setItem(SANDBOX_KEY, JSON.stringify(app.sandbox)); }
  catch (_) { /* private browsing or quota — silently ignore */ }
}

function restoreSandbox() {
  try {
    const raw = localStorage.getItem(SANDBOX_KEY);
    if (raw) {
      const restored = JSON.parse(raw);
      app.sandbox = { ...defaultSandboxState(), ...restored };
    }
  } catch (_) { /* malformed — start fresh */ }
}

function resetSandbox() {
  app.sandbox = defaultSandboxState();
  try { localStorage.removeItem(SANDBOX_KEY); } catch (_) {}
  renderSandbox();
  runProjection();
}

// ---- example sheet ----

async function loadExampleSheet() {
  try {
    const res = await fetch('/assets/splinched/Ledger-Spreadsheet-v1.0-example.xlsx');
    const buf = await res.arrayBuffer();
    const wb = window.XLSX.read(buf, { type: 'array', cellDates: true });
    handleParsed(wb);
  } catch (err) {
    showFatal(new Error('Could not load example sheet: ' + err.message));
  }
}

// ---- diagnostic copy ----

async function copyDiagnostic() {
  if (!app.workbook) return;
  const parseResult = parseLedger(app.workbook);
  const text = buildSupportDiagnostic(app.workbook, parseResult);
  try {
    await navigator.clipboard.writeText(text);
    const btn = $('#sp-copy-diag');
    if (btn) { const o = btn.textContent; btn.textContent = 'Copied ✓'; setTimeout(() => btn.textContent = o, 1800); }
  } catch (_) {
    // Fallback: alert with the text so they can manually copy
    window.prompt('Copy this diagnostic for the support email:', text);
  }
}

// ---- escape ----
function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

// ---- wire up entry points ----

function init() {
  restoreSandbox();
  renderSandbox();

  // Drop zone
  const drop = $('#sp-drop');
  const fileIn = $('#sp-file');
  drop.addEventListener('click', () => fileIn.click());
  fileIn.addEventListener('change', e => { if (e.target.files[0]) loadFile(e.target.files[0]); });
  drop.addEventListener('dragover', e => { e.preventDefault(); drop.classList.add('is-dragover'); });
  drop.addEventListener('dragleave', () => drop.classList.remove('is-dragover'));
  drop.addEventListener('drop', e => {
    e.preventDefault();
    drop.classList.remove('is-dragover');
    if (e.dataTransfer.files[0]) loadFile(e.dataTransfer.files[0]);
  });

  // Try example
  $('#sp-try-example').addEventListener('click', e => { e.stopPropagation(); loadExampleSheet(); });

  // Confirm → projection
  $('#sp-go-project').addEventListener('click', runProjection);
  $('#sp-back-from-confirm').addEventListener('click', () => showState('upload'));

  // Issues → back to upload
  $('#sp-back-from-issues').addEventListener('click', () => showState('upload'));
  $('#sp-copy-diag').addEventListener('click', copyDiagnostic);

  // Projection actions
  $('#sp-print').addEventListener('click', () => window.print());
  $('#sp-reset-sandbox').addEventListener('click', resetSandbox);
  $('#sp-back-from-projection').addEventListener('click', () => showState('confirm'));

  // Sandbox open/close
  $('#sp-sandbox-head').addEventListener('click', () => {
    $('#sp-sandbox').classList.toggle('is-open');
  });

  showState('upload');
}

document.addEventListener('DOMContentLoaded', init);
