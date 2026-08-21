// Splinched · End-to-end integration test.
//
// Reads the actual .kt/Ledger-Spreadsheet.xlsx with SheetJS in Node,
// pipes through parseLedger -> projectPayoff, asserts PARSER-CONTRACT
// verification numbers hold for the real workbook (not just hand-built
// fixtures).
//
// Run: `node assets/js/splinched-projection/integration.test.mjs`

import { readFileSync } from 'fs';

// Load the vendored UMD bundle by running it in a fresh function scope and
// capturing the global it exports. Avoids forcing an npm install for tests.
const xlsxSource = readFileSync('assets/js/splinched-projection/xlsx.full.min.js', 'utf8');
const xlsxScope = new Function(xlsxSource + '; return typeof XLSX !== "undefined" ? XLSX : null;');
const XLSX = xlsxScope();
if (!XLSX) {
  console.error('Failed to load SheetJS from vendored bundle.');
  process.exit(2);
}

import { parseLedger } from './parser.js';
import { projectPayoff, totalDebt, monthlyInterestBurn } from './projection.js';

const fail = [];
function check(label, cond, detail = '') {
  if (cond) console.log(`  ✓ ${label}${detail ? ` — ${detail}` : ''}`);
  else fail.push(`  ✗ ${label}${detail ? ' — ' + detail : ''}`);
}

console.log('Splinched integration test (real .xlsx → parse → project)\n');

const buf = readFileSync('.kt/Ledger-Spreadsheet.xlsx');
const workbook = XLSX.read(buf, { type: 'buffer', cellDates: true });

const parsed = parseLedger(workbook);
check('parser ok=true', parsed.ok === true,
  parsed.ok ? `${parsed.data.accounts.length} accounts, ${parsed.data.debts.length} debts` : JSON.stringify(parsed.issues));
if (!parsed.ok) {
  console.error('Cannot continue — parser failed.');
  process.exit(1);
}

const { data } = parsed;
check('formatVersion=1.0', data.formatVersion === '1.0');
check('defaultAttack=1000', data.defaultAttack === 1000);
check('latestSnapshotDate=2026-05-26', data.latestSnapshotDate === '2026-05-26');
check('totalDebt ≈ $65,360.89', Math.abs(totalDebt(data.debts) - 65360.89) < 0.01);
check('monthlyInterestBurn ≈ $394.32', Math.abs(monthlyInterestBurn(data.debts) - 394.32) < 0.05);

const result = projectPayoff({
  debts: data.debts,
  defaultAttack: data.defaultAttack,
  today: new Date(2026, 4, 26),
});
check('debt-free date 2029-02', result.debtFreeDate === '2029-02');
check('total interest ≈ $3,679.23', Math.abs(result.totalInterestPaid - 3679.23) < 1.0);

const killOrder = result.monthlyRows.filter(r => r.killAccountName).map(r => r.killAccountName);
const expectedOrder = ['Nordstrom', 'PNC', 'Capital One', 'IKEA', 'SoFi', 'Jenius', 'FedLoan Student', 'PayPal', 'Apple'];
check('kill order matches',
  killOrder.length === expectedOrder.length && killOrder.every((v, i) => v === expectedOrder[i]),
  killOrder.join(' → '));

if (fail.length === 0) {
  console.log('\nEnd-to-end pipeline verified against PARSER-CONTRACT.');
  process.exit(0);
} else {
  console.error('\nFailures:');
  for (const f of fail) console.error(f);
  process.exit(1);
}
