// Splinched · Spreadsheet parser.
//
// Takes a SheetJS workbook (the result of XLSX.read), runs a pre-flight
// diagnostic pass, and returns either parsed data or a list of issues with
// row/column references the reader can act on without emailing support.
//
// Schema source: .kt/PARSER-CONTRACT.md (v1.0).

export const SUPPORTED_FORMAT_VERSION = '1.0';

const REQUIRED_TABS = [
  'Read Me', 'Accounts', 'Snapshots', 'Glance',
];
const DEBT_TYPES   = new Set(['credit_card', 'loan', 'student_loan', 'bnpl']);
const VALID_TYPES  = new Set([...DEBT_TYPES, 'checking', 'savings']);
const VALID_STATUS = new Set(['active', 'unknown', 'paid_off', 'closed']);

// ---- cell helpers ----

function getCell(sheet, addr) {
  if (!sheet) return null;
  const c = sheet[addr];
  if (!c) return null;
  return c;
}

function cellValue(sheet, addr) {
  const c = getCell(sheet, addr);
  return c ? c.v : null;
}

// SheetJS may give us numbers as numbers, dates as JS Dates (cellDates: true)
// or as Excel serials (default), strings with whitespace, etc. Coerce.
function toNumber(v) {
  if (v === null || v === undefined || v === '') return null;
  if (typeof v === 'number') return v;
  if (typeof v === 'string') {
    const cleaned = v.trim().replace(/[$,\s]/g, '');
    if (cleaned === '') return null;
    const n = Number(cleaned);
    return Number.isFinite(n) ? n : null;
  }
  return null;
}

function toText(v) {
  if (v === null || v === undefined) return '';
  return String(v).trim();
}

// Excel date serial → 'YYYY-MM-DD'. SheetJS w/ cellDates:true gives JS Date,
// but in case the workbook is read raw we handle both.
function toIsoDate(v) {
  if (!v && v !== 0) return null;
  if (v instanceof Date && !Number.isNaN(v.getTime())) {
    const y = v.getUTCFullYear();
    const m = String(v.getUTCMonth() + 1).padStart(2, '0');
    const d = String(v.getUTCDate()).padStart(2, '0');
    return `${y}-${m}-${d}`;
  }
  if (typeof v === 'number') {
    // Excel serial: days since 1899-12-30 (handles the 1900 leap bug)
    const ms = (v - 25569) * 86400 * 1000;
    return toIsoDate(new Date(ms));
  }
  if (typeof v === 'string') {
    const t = v.trim();
    if (/^\d{4}-\d{2}-\d{2}/.test(t)) return t.slice(0, 10);
    const d = new Date(t);
    if (!Number.isNaN(d.getTime())) return toIsoDate(d);
  }
  return null;
}

// ---- issue builder ----

function issue(severity, tab, cell, message, suggestion = '') {
  return { severity, tab, cell, message, suggestion };
}

// ---- main entry ----

/**
 * @param {Object} workbook — SheetJS workbook: {SheetNames, Sheets}
 * @returns {{ok: true, data} | {ok: false, issues}}
 */
export function parseLedger(workbook) {
  const issues  = [];
  const warns   = [];
  const sheetNames = workbook.SheetNames || [];
  const sheets     = workbook.Sheets     || {};

  // 1. Tab presence + naming
  for (const required of REQUIRED_TABS) {
    if (!sheetNames.includes(required)) {
      // Look for case-mismatched candidates to suggest a rename
      const guess = sheetNames.find(
        n => n.toLowerCase().trim() === required.toLowerCase()
      );
      issues.push(issue(
        'error',
        '(workbook)',
        '—',
        `Missing required tab "${required}".`,
        guess
          ? `Looks like the tab is named "${guess}" — rename it to "${required}" (case- and space-sensitive).`
          : `Add a tab named "${required}" matching the v${SUPPORTED_FORMAT_VERSION} template.`
      ));
    }
  }
  if (issues.length) return { ok: false, issues };

  // 2. Format version
  const formatVersionRaw = cellValue(sheets['Read Me'], 'A4');
  const formatVersion    = toText(formatVersionRaw);
  if (!formatVersion) {
    issues.push(issue(
      'error',
      'Read Me',
      'A4',
      'Format version cell is empty.',
      `Cell A4 of the "Read Me" tab should contain the spreadsheet format version (currently expected: ${SUPPORTED_FORMAT_VERSION}). Download a fresh template if you've lost this cell.`
    ));
    return { ok: false, issues };
  }
  if (formatVersion !== SUPPORTED_FORMAT_VERSION) {
    issues.push(issue(
      'version-mismatch',
      'Read Me',
      'A4',
      `Spreadsheet format version is "${formatVersion}", this tool expects "${SUPPORTED_FORMAT_VERSION}".`,
      'Download the latest template from your Splinched bundle, copy your account + snapshot rows across, and re-upload.'
    ));
    return { ok: false, issues, formatVersion };
  }

  // 3. Accounts tab
  const accountsSheet = sheets['Accounts'];
  const accountsHeaderRow = 4;
  const expectedHeaders = {
    A: 'Slug', B: 'Name', C: 'Type', D: 'Status',
    E: 'APR %', F: 'Min Payment', G: 'Attack Alloc',
  };
  for (const [col, expected] of Object.entries(expectedHeaders)) {
    const got = toText(cellValue(accountsSheet, `${col}${accountsHeaderRow}`));
    if (got.toLowerCase() !== expected.toLowerCase()) {
      issues.push(issue(
        'error',
        'Accounts',
        `${col}${accountsHeaderRow}`,
        `Header mismatch in column ${col}: found "${got}", expected "${expected}".`,
        `Row ${accountsHeaderRow} is the header row. If you renamed a column, restore the header text exactly.`
      ));
    }
  }
  if (issues.length) return { ok: false, issues };

  const accounts = [];
  let nextId = 1;
  for (let r = 5; r < 5 + 200; r++) {
    const slug = toText(cellValue(accountsSheet, `A${r}`));
    if (!slug) break;
    const name = toText(cellValue(accountsSheet, `B${r}`));
    const type = toText(cellValue(accountsSheet, `C${r}`));
    const status = toText(cellValue(accountsSheet, `D${r}`));
    const apr  = toNumber(cellValue(accountsSheet, `E${r}`)) || 0;
    const min  = toNumber(cellValue(accountsSheet, `F${r}`)) || 0;
    const alloc = toNumber(cellValue(accountsSheet, `G${r}`)) || 0;

    if (!name) {
      issues.push(issue('error', 'Accounts', `B${r}`,
        `Account "${slug}" is missing a display Name.`,
        `Add a name in cell B${r}.`));
    }
    if (!VALID_TYPES.has(type)) {
      issues.push(issue('error', 'Accounts', `C${r}`,
        `Account "${slug}" has Type "${type}" — must be one of: ${[...VALID_TYPES].join(', ')}.`,
        `Set cell C${r} from the dropdown.`));
    }
    if (!VALID_STATUS.has(status)) {
      issues.push(issue('error', 'Accounts', `D${r}`,
        `Account "${slug}" has Status "${status}" — must be one of: ${[...VALID_STATUS].join(', ')}.`,
        `Set cell D${r} from the dropdown.`));
    }
    accounts.push({
      id: nextId++,
      slug, name, type, status,
      apr, minimumPayment: min, attackAllocation: alloc,
      _row: r,
    });
  }
  if (!accounts.length) {
    issues.push(issue('error', 'Accounts', 'A5',
      'No account rows found.',
      `Row 5 onward should list one account per row, starting with a Slug in column A.`));
  }
  if (issues.length) return { ok: false, issues };

  // 4. Snapshots tab
  const snapshotsSheet = sheets['Snapshots'];
  const snapHeaderRow = 4;
  const snapExpectedHeaders = { A: 'Slug', B: 'Account', C: 'Date', D: 'Balance' };
  for (const [col, expected] of Object.entries(snapExpectedHeaders)) {
    const got = toText(cellValue(snapshotsSheet, `${col}${snapHeaderRow}`));
    if (got.toLowerCase() !== expected.toLowerCase()) {
      issues.push(issue('error', 'Snapshots', `${col}${snapHeaderRow}`,
        `Header mismatch in column ${col}: found "${got}", expected "${expected}".`,
        `Row ${snapHeaderRow} is the header row.`));
    }
  }
  if (issues.length) return { ok: false, issues };

  const snapshots = [];
  const accountSlugs = new Set(accounts.map(a => a.slug));
  for (let r = 5; r < 5 + 2000; r++) {
    const slug = toText(cellValue(snapshotsSheet, `A${r}`));
    if (!slug) break;
    const rawDate = cellValue(snapshotsSheet, `C${r}`);
    const date    = toIsoDate(rawDate);
    const balance = toNumber(cellValue(snapshotsSheet, `D${r}`));
    if (!date) {
      issues.push(issue('error', 'Snapshots', `C${r}`,
        `Row ${r}: Date is empty or unreadable.`,
        `Cell C${r} must be a date — enter it as a date, not text.`));
      continue;
    }
    if (balance === null) {
      issues.push(issue('error', 'Snapshots', `D${r}`,
        `Row ${r}: Balance is empty or unreadable.`,
        `Cell D${r} must be a number (no $ sign needed; commas okay).`));
      continue;
    }
    if (!accountSlugs.has(slug)) {
      issues.push(issue('error', 'Snapshots', `A${r}`,
        `Row ${r}: Slug "${slug}" is not in the Accounts tab.`,
        `Either add the account to the Accounts tab, or correct the spelling here. Slugs are lowercase-with-hyphens and must match exactly.`));
      continue;
    }
    snapshots.push({ slug, date, balance, _row: r });
  }
  if (issues.length) return { ok: false, issues };
  if (!snapshots.length) {
    issues.push(issue('error', 'Snapshots', 'A5',
      'No snapshot rows found.',
      'Add at least one dated balance per account in the Snapshots tab before projecting.'));
    return { ok: false, issues };
  }

  // 5. Current balance per account = latest snapshot per slug
  const latestBySlug = {};
  for (const s of snapshots) {
    const cur = latestBySlug[s.slug];
    if (!cur || s.date > cur.date) latestBySlug[s.slug] = s;
  }
  let latestSnapshotDate = '';
  for (const a of accounts) {
    const latest = latestBySlug[a.slug];
    a.currentBalance = latest ? latest.balance : 0;
    a.latestSnapshotDate = latest ? latest.date : null;
    if (latest && latest.date > latestSnapshotDate) latestSnapshotDate = latest.date;
  }

  // 6. Glance!B6 — default monthly attack
  const glanceB6 = cellValue(sheets['Glance'], 'B6');
  let defaultAttack = toNumber(glanceB6);
  if (defaultAttack === null) {
    // Cell may contain a formula like "=1000"; SheetJS gives .v as the
    // cached calc result, but if uncalc'd it may be a string formula.
    const cell = getCell(sheets['Glance'], 'B6');
    if (cell && cell.f) {
      const m = cell.f.match(/^=?\s*(\d+(?:\.\d+)?)\s*$/);
      if (m) defaultAttack = Number(m[1]);
    }
    if (defaultAttack === null) {
      warns.push(issue('warning', 'Glance', 'B6',
        `Default monthly attack not readable — defaulting to $1,000.`,
        `Glance!B6 should be a number (the baseline monthly attack budget). The tool will use $1,000 for now.`));
      defaultAttack = 1000;
    }
  }

  // 7. Derived: debt list for projection
  const debts = accounts.filter(
    a => DEBT_TYPES.has(a.type)
      && (a.status === 'active' || a.status === 'unknown')
      && (a.currentBalance || 0) > 0
  );

  // 8. Soft warnings
  if (latestSnapshotDate) {
    const ageMs = Date.now() - new Date(latestSnapshotDate).getTime();
    const ageDays = Math.floor(ageMs / 86400000);
    if (ageDays > 60) {
      warns.push(issue('warning', 'Snapshots', '—',
        `Latest snapshot is ${ageDays} days old (${latestSnapshotDate}).`,
        `The projection will start from today using stale balances. For an accurate forecast, snapshot your accounts and re-upload.`));
    }
  }

  return {
    ok: true,
    data: {
      formatVersion,
      defaultAttack,
      accounts,
      debts,
      snapshots,
      latestSnapshotDate,
      warnings: warns,
    },
  };
}

// ---- sanitized diagnostic for support ----

/**
 * Produces a copy-pasteable summary that contains zero balance / dollar
 * figures — only structure (tab names, row counts, headers found, issues).
 * Reader can paste this into a support email without leaking their numbers.
 */
export function buildSupportDiagnostic(workbook, parseResult) {
  const sheetNames = workbook.SheetNames || [];
  const lines = [];
  lines.push('# Splinched Projection — support diagnostic');
  lines.push(`tool format version: ${SUPPORTED_FORMAT_VERSION}`);
  lines.push(`tabs found: ${JSON.stringify(sheetNames)}`);
  for (const t of REQUIRED_TABS) {
    const s = workbook.Sheets[t];
    if (!s) { lines.push(`  - "${t}": MISSING`); continue; }
    lines.push(`  - "${t}": dimensions ${s['!ref'] || '(empty)'}`);
  }
  if (parseResult && parseResult.ok === false && parseResult.issues) {
    lines.push('issues:');
    for (const i of parseResult.issues) {
      lines.push(`  - [${i.severity}] ${i.tab}!${i.cell}: ${i.message}`);
      if (i.suggestion) lines.push(`      hint: ${i.suggestion}`);
    }
  } else if (parseResult && parseResult.ok && parseResult.data) {
    const d = parseResult.data;
    lines.push(`parsed: ${d.accounts.length} accounts, ${d.snapshots.length} snapshots, ${d.debts.length} active debts`);
    lines.push(`latest snapshot date: ${d.latestSnapshotDate || '(none)'}`);
    if (d.warnings && d.warnings.length) {
      lines.push('warnings:');
      for (const w of d.warnings) {
        lines.push(`  - [${w.severity}] ${w.tab}!${w.cell}: ${w.message}`);
      }
    }
  }
  lines.push('(no balance amounts, slugs, or account names are included in this diagnostic.)');
  return lines.join('\n');
}
