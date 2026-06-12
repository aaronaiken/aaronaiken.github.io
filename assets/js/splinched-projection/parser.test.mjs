// Splinched · Parser tests.
//
// Run: `node assets/js/splinched-projection/parser.test.mjs`
//
// Constructs SheetJS-shaped workbook objects in memory (no real .xlsx read)
// and verifies parseLedger() against the contract. Integration with the
// real .xlsx happens via the browser; this test pins the contract.

import { parseLedger, SUPPORTED_FORMAT_VERSION, buildSupportDiagnostic } from './parser.js';

// SheetJS sheet cells: { v: value, t: type }. Type 's' string, 'n' number, 'd' date, etc.
// We only set .v here — the parser doesn't depend on .t.
function makeSheet(cellMap, refRange = 'A1:M50') {
  const sheet = { '!ref': refRange };
  for (const [addr, value] of Object.entries(cellMap)) {
    sheet[addr] = { v: value };
  }
  return sheet;
}

function seedWorkbook() {
  return {
    SheetNames: ['Read Me', 'Accounts', 'Snapshots', 'Glance', 'Runway', 'Recurring', 'Projection & Sandbox', 'Milestones'],
    Sheets: {
      'Read Me': makeSheet({
        A1: 'The Ledger',
        A3: 'SPREADSHEET FORMAT VERSION',
        A4: SUPPORTED_FORMAT_VERSION,
      }, 'A1:A40'),
      'Accounts': makeSheet({
        A4: 'Slug', B4: 'Name', C4: 'Type', D4: 'Status',
        E4: 'APR %', F4: 'Min Payment', G4: 'Attack Alloc',
        A5: 'nordstrom',       B5: 'Nordstrom',       C5: 'credit_card',  D5: 'active',  E5: 30.15, F5: 0,      G5: 0,
        A6: 'pnc',             B6: 'PNC',             C6: 'credit_card',  D6: 'active',  E6: 29.24, F6: 192,    G6: 1000,
        A7: 'capital-one',     B7: 'Capital One',     C7: 'credit_card',  D7: 'active',  E7: 28.49, F7: 84,     G7: 0,
        A8: 'ikea',            B8: 'IKEA',            C8: 'credit_card',  D8: 'active',  E8: 21.99, F8: 36,     G8: 0,
        A9: 'sofi',            B9: 'SoFi',            C9: 'loan',         D9: 'active',  E9: 14.41, F9: 310.97, G9: 0,
        A10: 'fedloan-student', B10: 'FedLoan Student', C10: 'student_loan', D10: 'unknown', E10: 5, F10: 0,     G10: 0,
        A11: 'apple',          B11: 'Apple',          C11: 'bnpl',        D11: 'active',  E11: 0,    F11: 375.55, G11: 0,
        A12: 'jenius',         B12: 'Jenius',         C12: 'credit_card', D12: 'active',  E12: 0,    F12: 200,   G12: 0,
        A13: 'paypal',         B13: 'PayPal',         C13: 'bnpl',        D13: 'active',  E13: 0,    F13: 75,    G13: 0,
        A14: 'amex',           B14: 'Amex',           C14: 'credit_card', D14: 'paid_off', E14: 29.99, F14: 0,   G14: 0,
        A15: 'checking',       B15: 'Checking',       C15: 'checking',    D15: 'active',  E15: 0,    F15: 0,     G15: 0,
      }, 'A1:M15'),
      'Snapshots': makeSheet({
        A4: 'Slug', B4: 'Account', C4: 'Date', D4: 'Balance', E4: 'Notes',
        A5:  'nordstrom',       C5:  new Date(Date.UTC(2026, 4, 26)), D5:    161.89,
        A6:  'pnc',             C6:  new Date(Date.UTC(2026, 4, 26)), D6:   5801.79,
        A7:  'capital-one',     C7:  new Date(Date.UTC(2026, 4, 26)), D7:   2461.27,
        A8:  'ikea',            C8:  new Date(Date.UTC(2026, 4, 26)), D8:   1012.24,
        A9:  'sofi',            C9:  new Date(Date.UTC(2026, 4, 26)), D9:   5979.44,
        A10: 'fedloan-student', C10: new Date(Date.UTC(2026, 4, 26)), D10: 24022.00,
        A11: 'apple',           C11: new Date(Date.UTC(2026, 4, 26)), D11: 18112.91,
        A12: 'jenius',          C12: new Date(Date.UTC(2026, 4, 26)), D12:  5075.84,
        A13: 'paypal',          C13: new Date(Date.UTC(2026, 4, 26)), D13:  2733.51,
        A14: 'amex',            C14: new Date(Date.UTC(2026, 4, 26)), D14:     0.00,
      }, 'A1:E16'),
      'Glance': makeSheet({ A4: 'Total owed', A5: 'Monthly interest burn', A6: 'Default monthly attack', B6: 1000 }, 'A1:B13'),
      'Runway': makeSheet({}),
      'Recurring': makeSheet({}),
      'Projection & Sandbox': makeSheet({}),
      'Milestones': makeSheet({}),
    },
  };
}

const fail = [];
function check(label, cond, detail = '') {
  if (cond) console.log(`  ✓ ${label}`);
  else fail.push(`  ✗ ${label}${detail ? ' — ' + detail : ''}`);
}

console.log('Splinched parser test\n');

console.log('Happy path:');
{
  const wb = seedWorkbook();
  const r = parseLedger(wb);
  check('ok=true', r.ok === true);
  check('formatVersion=1.0', r.ok && r.data.formatVersion === '1.0');
  check('defaultAttack=1000', r.ok && r.data.defaultAttack === 1000);
  check('11 accounts parsed', r.ok && r.data.accounts.length === 11, `got ${r.ok && r.data.accounts.length}`);
  check('9 active debts (excludes amex/checking)', r.ok && r.data.debts.length === 9, `got ${r.ok && r.data.debts.length}`);
  check('latestSnapshotDate=2026-05-26', r.ok && r.data.latestSnapshotDate === '2026-05-26');
  check('nordstrom currentBalance=161.89',
    r.ok && r.data.accounts.find(a => a.slug === 'nordstrom').currentBalance === 161.89);
}

console.log('\nMissing tab:');
{
  const wb = seedWorkbook();
  delete wb.Sheets['Accounts'];
  wb.SheetNames = wb.SheetNames.filter(n => n !== 'Accounts');
  const r = parseLedger(wb);
  check('ok=false', r.ok === false);
  check('reports missing Accounts tab',
    !r.ok && r.issues.some(i => i.tab === '(workbook)' && i.message.includes('Accounts')));
}

console.log('\nMisnamed tab (case mismatch suggests rename):');
{
  const wb = seedWorkbook();
  wb.Sheets['accounts'] = wb.Sheets['Accounts'];
  delete wb.Sheets['Accounts'];
  wb.SheetNames = wb.SheetNames.map(n => n === 'Accounts' ? 'accounts' : n);
  const r = parseLedger(wb);
  check('ok=false', r.ok === false);
  check('suggests rename',
    !r.ok && r.issues.some(i => i.suggestion && i.suggestion.includes('accounts')));
}

console.log('\nFormat version mismatch:');
{
  const wb = seedWorkbook();
  wb.Sheets['Read Me'].A4 = { v: '2.5' };
  const r = parseLedger(wb);
  check('ok=false with version-mismatch severity',
    !r.ok && r.issues[0].severity === 'version-mismatch');
}

console.log('\nFormat version blank:');
{
  const wb = seedWorkbook();
  wb.Sheets['Read Me'].A4 = { v: '' };
  const r = parseLedger(wb);
  check('ok=false', !r.ok);
  check('points at Read Me!A4', !r.ok && r.issues[0].tab === 'Read Me' && r.issues[0].cell === 'A4');
}

console.log('\nInvalid Type enum:');
{
  const wb = seedWorkbook();
  wb.Sheets['Accounts'].C5 = { v: 'kreditkort' };
  const r = parseLedger(wb);
  check('ok=false', !r.ok);
  check('points at C5', !r.ok && r.issues.some(i => i.cell === 'C5'));
}

console.log('\nOrphan snapshot slug:');
{
  const wb = seedWorkbook();
  wb.Sheets['Snapshots'].A5 = { v: 'mystery-card' };
  const r = parseLedger(wb);
  check('ok=false', !r.ok);
  check('reports orphan slug',
    !r.ok && r.issues.some(i => i.message.includes('mystery-card')));
}

console.log('\nGlance!B6 with formula string + cached value:');
{
  const wb = seedWorkbook();
  wb.Sheets['Glance'].B6 = { v: 1500, f: '=1500' };
  const r = parseLedger(wb);
  check('reads cached value', r.ok && r.data.defaultAttack === 1500);
}

console.log('\nGlance!B6 with formula string only (no cached value):');
{
  const wb = seedWorkbook();
  wb.Sheets['Glance'].B6 = { f: '=1000' };
  const r = parseLedger(wb);
  check('falls back to formula constant', r.ok && r.data.defaultAttack === 1000);
}

console.log('\nGlance!B6 missing entirely:');
{
  const wb = seedWorkbook();
  delete wb.Sheets['Glance'].B6;
  const r = parseLedger(wb);
  check('ok=true with warning + $1000 default',
    r.ok && r.data.defaultAttack === 1000 && r.data.warnings.length > 0);
}

console.log('\nSupport diagnostic redacts numbers:');
{
  const wb = seedWorkbook();
  const r = parseLedger(wb);
  const diag = buildSupportDiagnostic(wb, r);
  check('contains tab list', diag.includes('Accounts'));
  check('contains row counts', diag.includes('11 accounts'));
  check('contains no balance amounts',
    !/\$?\d+\.\d{2}|18112\.91|5801\.79|161\.89/.test(diag));
  check('contains no account names',
    !diag.includes('Nordstrom') && !diag.includes('PNC') && !diag.includes('Apple'));
}

if (fail.length === 0) {
  console.log('\nAll parser checks passed.');
  process.exit(0);
} else {
  console.error('\nFailures:');
  for (const f of fail) console.error(f);
  process.exit(1);
}
