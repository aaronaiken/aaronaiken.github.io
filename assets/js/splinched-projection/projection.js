// Splinched · Projection math.
//
// Hand-port of helpers/ledger.py::project_payoff (and avalanche_order).
// Source of truth: that Python file. This file MUST stay in parity —
// projection.test.mjs runs against PARSER-CONTRACT.md's verification target
// to catch drift before it reaches readers.
//
// No external deps. ES module. Runs in browser and Node.

const DEBT_TYPES    = new Set(['credit_card', 'loan', 'student_loan', 'bnpl']);
const DEBT_STATUSES = new Set(['active', 'unknown']);

// ---- avalanche ordering ----

export function avalancheOrder(debts) {
  // APR desc, then current balance asc, then stable id asc.
  // Excludes anything with balance <= 0.
  return debts
    .filter(d => (d.currentBalance || 0) > 0)
    .map(d => ({ ...d }))
    .sort((a, b) => {
      const aprDiff = (b.apr || 0) - (a.apr || 0);
      if (aprDiff !== 0) return aprDiff;
      const balDiff = a.currentBalance - b.currentBalance;
      if (balDiff !== 0) return balDiff;
      return a.id - b.id;
    });
}

export function isDebt(account) {
  return DEBT_TYPES.has(account.type) && DEBT_STATUSES.has(account.status);
}

// ---- projection ----

/**
 * Run the monthly avalanche-snowball simulation.
 *
 * @param {Object} input
 * @param {Array<{id, name, slug, currentBalance, apr, minimumPayment, attackAllocation}>} input.debts
 *        Already filtered to active debts with currentBalance > 0.
 * @param {number} [input.defaultAttack=1000]
 * @param {Date}   [input.today=new Date()]  Used only for the YYYY-MM column.
 * @param {number} [input.maxMonths=240]
 *
 * @param {Object} [overrides]
 *   redirectBonuses                 bool — sandbox-spill
 *   extraMonthlyAttack              number — every month, sandbox-spill
 *   sideIncomeByMonth               { [monthIdx: number]: number }
 *   windfalls                       Array<{monthIdx, amount}>
 *   fedloanMinimum                  number
 *   fedloanMinimumStartsMonthIdx    number (0 = current month)
 *   bonusByMonth                    { [monthIdx: number]: number }  // when redirectBonuses is true
 *
 *   Note: the Python helper computes bonusByMonth from income_events itself.
 *   The Splinched spreadsheet doesn't carry that table, so the UI lets the
 *   reader enter expected bonuses manually and passes them in pre-resolved.
 *
 * @returns {{ monthlyRows, debtFreeDate, totalInterestPaid }}
 */
export function projectPayoff(input, overrides = {}) {
  const defaultAttack = input.defaultAttack ?? 1000;
  const today         = input.today ?? new Date();
  const maxMonths     = input.maxMonths ?? 240;

  const redirectBonuses       = !!overrides.redirectBonuses;
  const extraMonthlyAttack    = Number(overrides.extraMonthlyAttack || 0);
  const sideIncomeByMonth     = overrides.sideIncomeByMonth || {};
  const windfalls             = overrides.windfalls || [];
  const fedloanMinOverride    = overrides.fedloanMinimum;
  const fedloanMinStartsAt    = Number(overrides.fedloanMinimumStartsMonthIdx || 0);
  const bonusByMonth          = redirectBonuses ? (overrides.bonusByMonth || {}) : {};

  // Resolve windfalls into { monthIdx: totalAmount }
  const windfallsByIdx = {};
  for (const w of windfalls) {
    const mi  = Number(w.monthIdx);
    const amt = Number(w.amount || 0);
    if (Number.isFinite(mi) && amt > 0) {
      windfallsByIdx[mi] = (windfallsByIdx[mi] || 0) + amt;
    }
  }

  // Local mutable state — one entry per debt, in avalanche order.
  const ordered = avalancheOrder(input.debts);
  let fedloanIdx = null;
  const state = ordered.map((d, i) => {
    if (d.slug === 'fedloan-student') fedloanIdx = i;
    return {
      id:          d.id,
      name:        d.name,
      slug:        d.slug,
      balance:     d.currentBalance,
      apr:         d.apr || 0,
      minimum:     d.minimumPayment || 0,
      alloc:       d.attackAllocation || 0,
      killedMonth: null,
    };
  });

  // primaryIdx: walk avalanche order once.
  // - first alive debt with balance <= defaultAttack (imminent-kill range), OR
  // - first alive debt with alloc > 0
  // Whichever fires first. Fallback: first alive.
  function primaryIdx() {
    for (let i = 0; i < state.length; i++) {
      const s = state[i];
      if (s.balance <= 0) continue;
      if (s.balance <= defaultAttack) return i;
      if (s.alloc > 0) return i;
    }
    for (let i = 0; i < state.length; i++) {
      if (state[i].balance > 0) return i;
    }
    return null;
  }

  const rows = [];
  let totalInterest = 0;
  const monthCursor = new Date(today.getFullYear(), today.getMonth(), 1);

  function ymOf(d) {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    return `${y}-${m}`;
  }

  let debtFreeMonth = null;

  for (let monthNum = 0; monthNum < maxMonths; monthNum++) {
    const aliveCount = state.filter(s => s.balance > 0).length;
    if (aliveCount === 0) {
      // Already paid off. monthCursor is one past the kill month, so back up.
      const finalDate = new Date(monthCursor.getFullYear(), monthCursor.getMonth() - 1, 1);
      debtFreeMonth = ymOf(finalDate);
      break;
    }

    // FedLoan minimum override kicks in at its start month.
    if (fedloanIdx !== null && fedloanMinOverride !== undefined && fedloanMinOverride !== null) {
      if (monthNum >= fedloanMinStartsAt && state[fedloanIdx].balance > 0) {
        state[fedloanIdx].minimum = Number(fedloanMinOverride);
      }
    }

    const startingTotal = state.reduce((sum, s) => sum + s.balance, 0);
    let minimumsApplied = 0;
    let attackApplied   = 0;
    let bonusApplied    = 0;
    let extraApplied    = 0;
    let sideApplied     = 0;
    let windfallApplied = 0;
    let interestAccrued = 0;
    let killedId        = null;
    let killedName      = null;
    let sandboxTouched  = false;

    const pidx   = primaryIdx();
    const target = pidx !== null ? state[pidx] : null;
    const targetIdAtStart = target ? target.id : null;
    const targetNameAtStart = target ? target.name : null;

    // 1. minimums to each alive debt
    for (const s of state) {
      if (s.balance <= 0) continue;
      const pay = Math.min(s.minimum, s.balance);
      s.balance -= pay;
      minimumsApplied += pay;
    }

    // 2. normal attack to primary — single-shot, no spill (Phase 1 baseline).
    if (target && target.balance > 0) {
      let attackPool = target.alloc;
      // If no per-account allocation, fall back to defaultAttack for the
      // current primary target (matches the Python check, which collapses
      // to "primary with no alloc gets the default pool").
      if (attackPool === 0) {
        attackPool = defaultAttack;
      }
      const pay = Math.min(attackPool, target.balance);
      target.balance -= pay;
      attackApplied += pay;
    }

    // 2b. Sandbox contributors — these DO spill. If the current primary dies
    // mid-stack, the remainder cascades to the next alive avalanche-ordered
    // debt. Without spill, a windfall on a dying target would silently
    // vanish and the user's "what if?" would be wrong.
    function stack(amount) {
      if (amount <= 0) return 0;
      let remaining = amount;
      let applied   = 0;
      let safety    = state.length + 2;
      while (remaining > 0.005 && safety > 0) {
        safety--;
        const pi = primaryIdx();
        if (pi === null) break;
        const t = state[pi];
        if (t.balance <= 0) break;
        const p = Math.min(remaining, t.balance);
        t.balance -= p;
        applied   += p;
        remaining -= p;
      }
      return applied;
    }

    extraApplied    += stack(extraMonthlyAttack);
    bonusApplied    += stack(bonusByMonth[monthNum]  || 0);
    sideApplied     += stack(Number(sideIncomeByMonth[monthNum] || 0));
    windfallApplied += stack(windfallsByIdx[monthNum] || 0);

    if (extraApplied || bonusApplied || sideApplied || windfallApplied) {
      sandboxTouched = true;
    }

    // 3. interest on remaining balances (month-end)
    for (const s of state) {
      if (s.balance > 0 && s.apr > 0) {
        const inc = s.balance * s.apr / 100 / 12;
        s.balance += inc;
        interestAccrued += inc;
      }
    }

    // 4. kills + cascade
    for (const s of state) {
      if (s.killedMonth === null && s.balance <= 0.005) {
        s.balance = 0;
        s.killedMonth = ymOf(monthCursor);
        killedId   = s.id;
        killedName = s.name;
        // Cascade: alloc + minimum freed onto next alive (avalanche order)
        const freed = s.alloc + s.minimum;
        s.alloc   = 0;
        s.minimum = 0;
        for (const nxt of state) {
          if (nxt.balance > 0) {
            nxt.alloc += freed;
            break;
          }
        }
      }
    }

    const endingTotal = state.reduce((sum, s) => sum + s.balance, 0);
    totalInterest += interestAccrued;

    rows.push({
      month:             ymOf(monthCursor),
      startingTotal,
      minimumsApplied,
      attackApplied,
      bonusApplied,
      extraApplied,
      sideIncomeApplied: sideApplied,
      windfallApplied,
      interestAccrued,
      endingTotal,
      currentTargetId:   targetIdAtStart,
      currentTargetName: targetNameAtStart,
      killAccountId:     killedId,
      killAccountName:   killedName,
      sandboxTouched,
    });

    // advance month cursor
    monthCursor.setMonth(monthCursor.getMonth() + 1);

    if (endingTotal <= 0.005) {
      debtFreeMonth = ymOf(new Date(monthCursor.getFullYear(), monthCursor.getMonth() - 1, 1));
      break;
    }
  }

  return {
    monthlyRows:       rows,
    debtFreeDate:      debtFreeMonth,
    totalInterestPaid: totalInterest,
  };
}

// ---- summary helpers ----

export function totalDebt(debts) {
  return debts.reduce((sum, d) => sum + (d.currentBalance || 0), 0);
}

export function monthlyInterestBurn(debts) {
  return debts.reduce((sum, d) => {
    return sum + (d.currentBalance || 0) * (d.apr || 0) / 100 / 12;
  }, 0);
}
