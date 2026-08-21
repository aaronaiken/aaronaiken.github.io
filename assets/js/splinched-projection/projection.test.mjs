// Splinched · Projection parity test.
//
// Run: `node assets/js/splinched-projection/projection.test.mjs`
//
// Asserts the four PARSER-CONTRACT verification numbers + the seeded kill order
// against the seed dataset (2026-05-26 snapshot). If any of these drift, the
// JS port has diverged from helpers/ledger.py and readers will get wrong
// answers — fix the math, not the test.

import { projectPayoff, totalDebt, monthlyInterestBurn } from './projection.js';

// Seed data — mirrors the Ledger-Spreadsheet.xlsx Accounts + Snapshots tabs
// at the 2026-05-26 reading. Source: .kt/Ledger-Spreadsheet.xlsx.
const SEED_DEBTS = [
  { id: 1, slug: 'nordstrom',       name: 'Nordstrom',       apr: 30.15, minimumPayment: 0,      attackAllocation: 0,    currentBalance:   161.89 },
  { id: 2, slug: 'pnc',             name: 'PNC',             apr: 29.24, minimumPayment: 192,    attackAllocation: 1000, currentBalance:  5801.79 },
  { id: 3, slug: 'capital-one',     name: 'Capital One',     apr: 28.49, minimumPayment: 84,     attackAllocation: 0,    currentBalance:  2461.27 },
  { id: 4, slug: 'ikea',            name: 'IKEA',            apr: 21.99, minimumPayment: 36,     attackAllocation: 0,    currentBalance:  1012.24 },
  { id: 5, slug: 'sofi',            name: 'SoFi',            apr: 14.41, minimumPayment: 310.97, attackAllocation: 0,    currentBalance:  5979.44 },
  { id: 6, slug: 'fedloan-student', name: 'FedLoan Student', apr:  5,    minimumPayment: 0,      attackAllocation: 0,    currentBalance: 24022.00 },
  { id: 7, slug: 'apple',           name: 'Apple',           apr:  0,    minimumPayment: 375.55, attackAllocation: 0,    currentBalance: 18112.91 },
  { id: 8, slug: 'jenius',          name: 'Jenius',          apr:  0,    minimumPayment: 200,    attackAllocation: 0,    currentBalance:  5075.84 },
  { id: 9, slug: 'paypal',          name: 'PayPal',          apr:  0,    minimumPayment: 75,     attackAllocation: 0,    currentBalance:  2733.51 },
];

const EXPECTED = {
  totalOwed:           65360.89,
  monthlyInterestBurn: 394.32,
  debtFreeDate:        '2029-02',
  totalInterestPaid:   3679.23,
  killOrder: ['Nordstrom', 'PNC', 'Capital One', 'IKEA', 'SoFi', 'Jenius', 'FedLoan Student', 'PayPal', 'Apple'],
};

// Projections in helpers/ledger.py anchor on et_today(). The verification
// target was computed from the 2026-05-26 snapshot with et_today() == 2026-05-26.
// Use the same start month so we get the same number of months in the sim.
const TODAY = new Date(2026, 4, 26); // May 26, 2026 (month is 0-indexed)

const fail = [];
function expect(label, actual, expected, tolerance = 0.01) {
  const ok = Math.abs(actual - expected) <= tolerance;
  if (!ok) fail.push(`  ✗ ${label}: got ${actual}, expected ${expected} (±${tolerance})`);
  else console.log(`  ✓ ${label}: ${actual.toFixed(2)} ≈ ${expected}`);
}
function expectEq(label, actual, expected) {
  const ok = actual === expected;
  if (!ok) fail.push(`  ✗ ${label}: got ${JSON.stringify(actual)}, expected ${JSON.stringify(expected)}`);
  else console.log(`  ✓ ${label}: ${JSON.stringify(actual)}`);
}
function expectArrayEq(label, actual, expected) {
  const ok = actual.length === expected.length && actual.every((v, i) => v === expected[i]);
  if (!ok) fail.push(`  ✗ ${label}:\n      got      ${JSON.stringify(actual)}\n      expected ${JSON.stringify(expected)}`);
  else console.log(`  ✓ ${label}: ${JSON.stringify(actual)}`);
}

console.log('Splinched projection parity test\n');
console.log('Static checks:');
expect('total owed',           totalDebt(SEED_DEBTS),           EXPECTED.totalOwed,           0.01);
expect('monthly interest burn', monthlyInterestBurn(SEED_DEBTS), EXPECTED.monthlyInterestBurn, 0.05);

console.log('\nProjection (seed @ 2026-05-26, default attack $1000, no overrides):');
const result = projectPayoff({
  debts: SEED_DEBTS,
  defaultAttack: 1000,
  today: TODAY,
});

expectEq('debt-free date',  result.debtFreeDate,             EXPECTED.debtFreeDate);
expect('total interest paid', result.totalInterestPaid,      EXPECTED.totalInterestPaid, 1.00);
expectEq('months simulated until debt-free',
  result.monthlyRows[result.monthlyRows.length - 1].month, EXPECTED.debtFreeDate);

const killOrder = result.monthlyRows
  .filter(r => r.killAccountName)
  .map(r => r.killAccountName);
expectArrayEq('kill order', killOrder, EXPECTED.killOrder);

if (fail.length === 0) {
  console.log('\nAll checks passed.');
  process.exit(0);
} else {
  console.error('\nFailures:');
  for (const f of fail) console.error(f);
  process.exit(1);
}
