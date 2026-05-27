"""
helpers/ledger.py — math for The Ledger.

All money-state derivation lives here. The blueprint stays a thin layer
on top: routes assemble context, helpers do the computing.

Source of truth for any account's current balance is the most recent
balance_snapshots row for that account (no current_balance column).

Spec: .kt/spec-ledger.md sections 3 (data model) and 4 (core math).
"""
import calendar
from collections import namedtuple
from datetime import datetime, date, timedelta
import pytz

from helpers.db import get_ledger_db


ET = pytz.timezone('US/Eastern')

DEBT_TYPES = ('credit_card', 'loan', 'student_loan', 'bnpl')
# 'unknown' counted as debt — Aaron still owes it; status just signals
# "operational details (min, cadence) are TBD." Excluding it would hide
# $24k+ of FedLoan from the total, which would defeat the point.
DEBT_STATUSES = ('active', 'unknown')


# ---- time helpers ----

def et_now():
	return datetime.now(ET)


def et_today():
	return et_now().date()


def utc_now_iso():
	return datetime.utcnow().isoformat(timespec='microseconds') + 'Z'


def et_now_iso():
	return et_now().isoformat()


# ---- structured returns ----

CashRunway = namedtuple('CashRunway', [
	'checking_balance', 'next_payday', 'days_to_next_payday',
	'obligations', 'total_obligations', 'free_to_attack', 'runway_status',
])

AttackBudget = namedtuple('AttackBudget', [
	'current_monthly', 'current_target', 'kill_sequence',
])

Projection = namedtuple('Projection', [
	'monthly_rows', 'debt_free_date', 'total_interest_paid',
])


# ---- basic queries ----

def latest_balance(conn, account_id):
	row = conn.execute("""
		SELECT balance FROM balance_snapshots
		WHERE account_id = ?
		ORDER BY snapshot_at DESC, id DESC
		LIMIT 1
	""", (account_id,)).fetchone()
	return row['balance'] if row else None


def latest_snapshot_at(conn, account_id):
	row = conn.execute("""
		SELECT snapshot_at FROM balance_snapshots
		WHERE account_id = ?
		ORDER BY snapshot_at DESC, id DESC
		LIMIT 1
	""", (account_id,)).fetchone()
	return row['snapshot_at'] if row else None


def get_setting(conn, key, default=None):
	row = conn.execute(f"SELECT {key} FROM settings WHERE id = 1").fetchone()
	if not row:
		return default
	val = row[key]
	return val if val is not None else default


def list_active_debts(conn):
	"""Active or unknown-status debt accounts. Order: avalanche."""
	placeholders = ','.join('?' for _ in DEBT_TYPES)
	rows = conn.execute(f"""
		SELECT * FROM accounts
		WHERE status IN ('active', 'unknown')
		  AND account_type IN ({placeholders})
		ORDER BY COALESCE(apr, 0) DESC, id ASC
	""", DEBT_TYPES).fetchall()
	return [dict(r) for r in rows]


# ---- top-line numbers ----

def total_debt(conn):
	debts = list_active_debts(conn)
	total = 0.0
	for d in debts:
		bal = latest_balance(conn, d['id'])
		if bal is not None:
			total += bal
	return total


def monthly_interest_burn(conn):
	"""Dollars/month bleeding to interest at current APRs and balances."""
	debts = list_active_debts(conn)
	burn = 0.0
	for d in debts:
		apr = d.get('apr') or 0
		bal = latest_balance(conn, d['id']) or 0
		if apr > 0 and bal > 0:
			burn += bal * apr / 100.0 / 12.0
	return burn


def total_debt_n_days_ago(conn, days):
	"""For trend display — sum of latest snapshot per account ≤ N days ago.

	Returns None if no debt account has a snapshot from before the cutoff
	(i.e., we have no baseline to compare against — first weeks of using
	the Ledger). Returning 0 would falsely render as "debt grew by total"
	on the first-run Glance.
	"""
	cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat(
		timespec='microseconds') + 'Z'
	debts = list_active_debts(conn)
	total = 0.0
	any_baseline = False
	for d in debts:
		row = conn.execute("""
			SELECT balance FROM balance_snapshots
			WHERE account_id = ? AND snapshot_at <= ?
			ORDER BY snapshot_at DESC, id DESC
			LIMIT 1
		""", (d['id'], cutoff)).fetchone()
		if row is not None:
			total += row['balance']
			any_baseline = True
	return total if any_baseline else None


# ---- avalanche order + attack budget ----

def avalanche_order(conn):
	"""Active debts sorted by APR desc, ties broken by current balance asc
	(kill the smaller one first so its minimum frees up sooner).
	Excludes accounts with current balance == 0."""
	debts = list_active_debts(conn)
	debts_with_bal = []
	for d in debts:
		bal = latest_balance(conn, d['id']) or 0
		if bal <= 0:
			continue
		d2 = dict(d)
		d2['current_balance'] = bal
		debts_with_bal.append(d2)
	debts_with_bal.sort(
		key=lambda x: (-(x.get('apr') or 0), x['current_balance'], x['id'])
	)
	return debts_with_bal


def current_primary_target(conn):
	"""Walk avalanche order once. The first debt that either:

	  - has balance ≤ default_attack_amount (one-payday kill range), OR
	  - has attack_allocation > 0

	wins. Avalanche priority is preserved — a small low-APR balance never
	cuts in line ahead of a higher-APR debt that already has an allocation.

	The imminent-kill check catches "Nordstrom is $161, of course it's
	next" without requiring the user to maintain attack_allocation as a
	debt winds down.

	Fallback: first alive avalanche-ordered debt.
	"""
	debts = avalanche_order(conn)
	if not debts:
		return None
	default_attack = get_setting(conn, 'default_attack_amount', 1000) or 0
	for d in debts:
		if d['current_balance'] <= default_attack:
			return d
		if (d.get('attack_allocation') or 0) > 0:
			return d
	return debts[0]


def attack_budget(conn):
	"""Forward-looking snowball view.

	Returns AttackBudget with:
	  current_monthly: this month's total attack on the primary target
	                   (its minimum + its attack_allocation)
	  current_target:  the primary-target account dict
	  kill_sequence:   list of {account, monthly_budget_after_kill,
	                            projected_kill_month} — how the attack
	                   grows as each debt dies, in avalanche order.

	The kill_sequence runs a lightweight forward simulation that
	cascades allocation as each debt dies. It uses project_payoff() under
	the hood so the kill months match the projection page.
	"""
	target = current_primary_target(conn)
	if not target:
		return AttackBudget(0, None, [])

	target_min = target.get('minimum_payment') or 0
	target_alloc = target.get('attack_allocation') or 0
	current_monthly = target_min + target_alloc

	projection = project_payoff(conn)
	kills_by_id = {row['kill_account_id']: row
	               for row in projection.monthly_rows
	               if row.get('kill_account_id')}

	# Build the kill sequence: walk debts in projected kill order
	kill_sequence = []
	# accumulate allocation as kills happen
	avalanche = avalanche_order(conn)
	freed_so_far = 0.0
	for d in avalanche:
		kill_row = kills_by_id.get(d['id'])
		if not kill_row:
			continue
		freed_so_far += (d.get('attack_allocation') or 0) + (
			d.get('minimum_payment') or 0)
		# next-target attack = current attack + everything freed up to now
		monthly_after = current_monthly + freed_so_far - (
			(target.get('attack_allocation') or 0) +
			(target.get('minimum_payment') or 0)
		) if d['id'] != target['id'] else current_monthly
		kill_sequence.append({
			'account':                 d,
			'projected_kill_month':    kill_row['month'],
			'monthly_budget_after_kill': monthly_after,
		})

	return AttackBudget(
		current_monthly=current_monthly,
		current_target=target,
		kill_sequence=kill_sequence,
	)


# ---- autopay expectations ----

def _advance_autopay_date(prev_date_iso, cadence, day_of_month):
	"""Return the next autopay date (ISO YYYY-MM-DD) after prev_date_iso."""
	try:
		d = date.fromisoformat(prev_date_iso)
	except (ValueError, TypeError):
		d = et_today()

	if cadence == 'biweekly':
		return (d + timedelta(days=14)).isoformat()
	if cadence == 'monthly_eom':
		# next month's last day
		nxt_month = d.month % 12 + 1
		nxt_year  = d.year + (1 if d.month == 12 else 0)
		last_day  = calendar.monthrange(nxt_year, nxt_month)[1]
		return date(nxt_year, nxt_month, last_day).isoformat()
	# default: monthly
	dom = day_of_month or d.day
	nxt_month = d.month % 12 + 1
	nxt_year  = d.year + (1 if d.month == 12 else 0)
	last_day  = calendar.monthrange(nxt_year, nxt_month)[1]
	return date(nxt_year, nxt_month, min(dom, last_day)).isoformat()


def _initial_autopay_date(account):
	"""Pick a sensible first autopay date for an account that has none set."""
	today = et_today()
	cadence = account.get('autopay_cadence') or 'monthly'
	if cadence == 'biweekly':
		# Aaron's biweekly cadence: known 5/22 anchor for Jenius.
		anchor = date(2026, 5, 22)
		# step forward in 14-day increments until we're >= today.
		while anchor < today:
			anchor += timedelta(days=14)
		return anchor.isoformat()
	if cadence == 'monthly_eom':
		last_day = calendar.monthrange(today.year, today.month)[1]
		eom = date(today.year, today.month, last_day)
		if eom < today:
			nxt_month = today.month % 12 + 1
			nxt_year  = today.year + (1 if today.month == 12 else 0)
			last_day  = calendar.monthrange(nxt_year, nxt_month)[1]
			eom = date(nxt_year, nxt_month, last_day)
		return eom.isoformat()
	dom = account.get('autopay_day') or today.day
	last_day = calendar.monthrange(today.year, today.month)[1]
	dom = min(dom, last_day)
	candidate = date(today.year, today.month, dom)
	if candidate < today:
		nxt_month = today.month % 12 + 1
		nxt_year  = today.year + (1 if today.month == 12 else 0)
		last_day  = calendar.monthrange(nxt_year, nxt_month)[1]
		candidate = date(nxt_year, nxt_month, min(dom, last_day))
	return candidate.isoformat()


def generate_autopay_expectations(conn):
	"""For each autopay-enabled active debt where autopay_next_date is
	today or has passed: create a pending debt_transactions row (if not
	already present) and roll autopay_next_date forward by one cadence.

	Idempotent — bails out if a pending row already exists for that
	account+date. Returns the number of new pending rows created.

	Called on every Ledger page load — cheap, no scheduler needed."""
	now_iso = et_now_iso()
	today = et_today().isoformat()
	debts = list_active_debts(conn)
	created = 0

	for d in debts:
		if not d.get('autopay_enabled'):
			continue
		if not d.get('autopay_amount'):
			# autopay enabled but no amount — skip silently (user needs to fill it in)
			continue
		next_date = d.get('autopay_next_date')
		if not next_date:
			next_date = _initial_autopay_date(d)
			conn.execute(
				"UPDATE accounts SET autopay_next_date = ?, updated = ? WHERE id = ?",
				(next_date, now_iso, d['id']))

		# Materialize all due autopays up to today.
		safety = 60  # don't loop forever if data is weird
		while next_date <= today and safety > 0:
			safety -= 1
			exists = conn.execute("""
				SELECT id FROM debt_transactions
				WHERE account_id = ? AND tx_date = ? AND tx_type = 'payment'
				  AND source IN ('autopay_expected', 'autopay_confirmed')
			""", (d['id'], next_date)).fetchone()
			if not exists:
				conn.execute("""
					INSERT INTO debt_transactions (
						account_id, tx_date, amount, tx_type, source,
						confirmed, description, created, updated
					) VALUES (?, ?, ?, 'payment', 'autopay_expected', 0,
					          'Expected autopay', ?, ?)
				""", (d['id'], next_date, d['autopay_amount'], now_iso, now_iso))
				created += 1
			next_date = _advance_autopay_date(
				next_date, d.get('autopay_cadence'), d.get('autopay_day'))
			conn.execute(
				"UPDATE accounts SET autopay_next_date = ?, updated = ? WHERE id = ?",
				(next_date, now_iso, d['id']))

	conn.commit()
	return created


# ---- cash runway ----

def _next_paycheck_date(conn):
	"""Best estimate of the next paycheck date based on recurring income."""
	today = et_today()
	# Look for an explicitly future income event first.
	row = conn.execute("""
		SELECT * FROM income_events
		WHERE event_date >= ? AND income_type = 'paycheck'
		ORDER BY event_date ASC LIMIT 1
	""", (today.isoformat(),)).fetchone()
	if row:
		return date.fromisoformat(row['event_date'])

	# Otherwise, look at the most recent paycheck + recurrence pattern.
	row = conn.execute("""
		SELECT * FROM income_events
		WHERE income_type = 'paycheck'
		ORDER BY event_date DESC LIMIT 1
	""").fetchone()
	if row:
		last = date.fromisoformat(row['event_date'])
		pattern = row['recurrence_pattern'] or 'biweekly'
		while last <= today:
			if pattern == 'monthly':
				nxt_month = last.month % 12 + 1
				nxt_year  = last.year + (1 if last.month == 12 else 0)
				last_day  = calendar.monthrange(nxt_year, nxt_month)[1]
				last = date(nxt_year, nxt_month, min(last.day, last_day))
			else:  # biweekly default
				last = last + timedelta(days=14)
		return last

	# No income events at all — fall back to "two weeks from today."
	return today + timedelta(days=14)


def cash_runway(conn):
	checking_id = get_setting(conn, 'checking_account_id')
	checking_balance = latest_balance(conn, checking_id) if checking_id else None
	today = et_today()
	next_payday = _next_paycheck_date(conn)
	days_to = (next_payday - today).days

	obligations = []

	# 1. Already-materialized pending autopays (rows generated by
	# generate_autopay_expectations for today-or-past dates that the user
	# hasn't confirmed yet).
	autopay_rows = conn.execute("""
		SELECT t.*, a.name AS account_name
		FROM debt_transactions t
		JOIN accounts a ON a.id = t.account_id
		WHERE t.confirmed = 0
		  AND t.tx_type = 'payment'
		  AND t.tx_date >= ?
		  AND t.tx_date <= ?
		ORDER BY t.tx_date
	""", (today.isoformat(), next_payday.isoformat())).fetchall()
	materialized = set()
	for r in autopay_rows:
		obligations.append({
			'description': f"{r['account_name']} autopay",
			'amount':      r['amount'],
			'date':        r['tx_date'],
			'type':        'autopay',
		})
		materialized.add((r['account_id'], r['tx_date']))

	# 2. Forward-dated autopays between today+1 and next_payday. These
	# don't have materialized rows yet (generate_autopay_expectations only
	# materializes past-or-today). Walk each autopay-enabled debt and
	# project its next dates from the account's autopay fields. Skip any
	# date already covered by a materialized row to avoid double-count.
	for d in list_active_debts(conn):
		if not d.get('autopay_enabled') or not d.get('autopay_amount'):
			continue
		next_iso = d.get('autopay_next_date')
		if not next_iso:
			continue
		try:
			cursor_date = date.fromisoformat(next_iso)
		except (TypeError, ValueError):
			continue
		safety = 30
		while cursor_date <= next_payday and safety > 0:
			safety -= 1
			if cursor_date >= today and (d['id'], cursor_date.isoformat()) not in materialized:
				obligations.append({
					'description': f"{d['name']} autopay",
					'amount':      d['autopay_amount'],
					'date':        cursor_date.isoformat(),
					'type':        'autopay',
				})
				materialized.add((d['id'], cursor_date.isoformat()))
			nxt_iso = _advance_autopay_date(
				cursor_date.isoformat(),
				d.get('autopay_cadence'),
				d.get('autopay_day'))
			try:
				cursor_date = date.fromisoformat(nxt_iso)
			except (TypeError, ValueError):
				break

	# recurring expenses with day-of-month falling in window
	recurring_rows = conn.execute(
		"SELECT * FROM recurring_expenses WHERE active = 1 ORDER BY day_of_month"
	).fetchall()
	cursor = today
	while cursor <= next_payday:
		last_day = calendar.monthrange(cursor.year, cursor.month)[1]
		for r in recurring_rows:
			dom = r['day_of_month']
			eff_dom = last_day if dom == 0 else min(dom, last_day)
			if eff_dom < cursor.day:
				# already passed this month
				continue
			d = date(cursor.year, cursor.month, eff_dom)
			if today <= d <= next_payday:
				obligations.append({
					'description': r['name'],
					'amount':      r['amount'],
					'date':        d.isoformat(),
					'type':        'recurring',
				})
		# advance to next month
		nxt_month = cursor.month % 12 + 1
		nxt_year  = cursor.year + (1 if cursor.month == 12 else 0)
		cursor = date(nxt_year, nxt_month, 1)

	# one-time outflows in window that are still planned
	onetime = conn.execute("""
		SELECT * FROM one_time_events
		WHERE status = 'planned' AND direction = 'outflow'
		  AND event_date >= ? AND event_date <= ?
		ORDER BY event_date
	""", (today.isoformat(), next_payday.isoformat())).fetchall()
	for r in onetime:
		obligations.append({
			'description': r['description'],
			'amount':      r['amount'],
			'date':        r['event_date'],
			'type':        'one_time',
		})

	obligations.sort(key=lambda x: x['date'])
	total_oblig = sum(o['amount'] for o in obligations)
	free_to_attack = (checking_balance or 0) - total_oblig

	if checking_balance is None:
		status = 'unknown'
	elif free_to_attack < 0:
		status = 'underwater'
	elif free_to_attack < 200:
		status = 'tight'
	else:
		status = 'healthy'

	return CashRunway(
		checking_balance=checking_balance,
		next_payday=next_payday.isoformat(),
		days_to_next_payday=days_to,
		obligations=obligations,
		total_obligations=total_oblig,
		free_to_attack=free_to_attack,
		runway_status=status,
	)


def expected_checking_balance(conn):
	"""Compute what The Ledger expects checking to hold right now, given
	the last checking snapshot and activity since.

	expected = last_snapshot
	         + income_events posted between snapshot_at and now
	         - confirmed autopay payments between snapshot_at and now
	         - recurring_expenses whose day-of-month passed in the interval

	The delta between this and the user's just-entered checking value is
	the leak signal.
	"""
	checking_id = get_setting(conn, 'checking_account_id')
	if not checking_id:
		return None
	last = conn.execute("""
		SELECT balance, snapshot_at FROM balance_snapshots
		WHERE account_id = ?
		ORDER BY snapshot_at DESC, id DESC LIMIT 1
	""", (checking_id,)).fetchone()
	if not last:
		return None

	snap_dt = datetime.fromisoformat(last['snapshot_at'].replace('Z', '+00:00'))
	snap_date = snap_dt.date()
	today = et_today()
	bal = last['balance']

	income = conn.execute("""
		SELECT COALESCE(SUM(amount), 0) AS s FROM income_events
		WHERE event_date >= ? AND event_date <= ?
	""", (snap_date.isoformat(), today.isoformat())).fetchone()['s']
	bal += income

	# autopays confirmed since snapshot
	paid = conn.execute("""
		SELECT COALESCE(SUM(amount), 0) AS s FROM debt_transactions
		WHERE confirmed = 1 AND tx_type = 'payment'
		  AND tx_date >= ? AND tx_date <= ?
	""", (snap_date.isoformat(), today.isoformat())).fetchone()['s']
	bal -= paid

	# recurring expenses whose day fell in the window
	recurring = conn.execute(
		"SELECT * FROM recurring_expenses WHERE active = 1"
	).fetchall()
	cursor = snap_date
	while cursor <= today:
		last_day = calendar.monthrange(cursor.year, cursor.month)[1]
		for r in recurring:
			dom = r['day_of_month']
			eff_dom = last_day if dom == 0 else min(dom, last_day)
			d = date(cursor.year, cursor.month, eff_dom)
			if snap_date < d <= today:
				bal -= r['amount']
		nxt_month = cursor.month % 12 + 1
		nxt_year  = cursor.year + (1 if cursor.month == 12 else 0)
		cursor = date(nxt_year, nxt_month, 1)

	return bal


# ---- projection (month by month) ----

def project_payoff(conn, max_months=240, overrides=None):
	"""
	Run the interest-aware avalanche-snowball simulation month by month
	from today until every debt is at zero (or max_months reached).

	overrides (optional dict for the Phase 2 sandbox — None = pure baseline):
	  redirect_bonuses                  bool — add bonus income_events to
	                                          attack budget in their month
	  extra_monthly_attack              float — add to attack pool every
	                                            month, on top of allocation
	  side_income_by_month              dict {month_idx: amount} — add to
	                                          attack pool in those months
	  windfalls                         list of {month_idx, amount} — one-shot
	                                          adds in specific months
	  fedloan_minimum                   float — override FedLoan minimum
	  fedloan_minimum_starts_month_idx  int — first month_idx where the
	                                          override applies (0 = now)

	month_idx is zero-based from today's month (0 = current month).

	Each extra contributor (bonus / extra-attack / side-income / windfall)
	stacks onto whatever the current primary target is getting that month
	— same imminent-kill / allocation / fallback priority order.

	Returns Projection(monthly_rows, debt_free_date, total_interest_paid).

	Each monthly_row is a dict:
	  month                 'YYYY-MM'
	  starting_total        sum of debt balances at month start
	  minimums_applied      sum of minimums applied to debts
	  attack_applied        attack allocation applied
	  bonus_applied         redirected-bonus amount this month (sandbox)
	  extra_applied         extra-monthly-attack amount applied (sandbox)
	  side_income_applied   side-income amount applied (sandbox)
	  windfall_applied      windfall amount applied (sandbox)
	  interest_accrued      interest added this month
	  ending_total          sum of debt balances after the month
	  current_target_id     primary target at month start
	  current_target_name
	  kill_account_id       id of debt killed this month (if any)
	  kill_account_name
	  sandbox_touched       True if any sandbox contributor fired in this month
	"""
	o = overrides or {}
	redirect_bonuses          = bool(o.get('redirect_bonuses'))
	extra_monthly_attack      = float(o.get('extra_monthly_attack') or 0)
	side_income_by_month      = o.get('side_income_by_month') or {}
	windfalls                 = o.get('windfalls') or []
	fedloan_min_override      = o.get('fedloan_minimum')
	fedloan_min_starts_at     = int(o.get('fedloan_minimum_starts_month_idx') or 0)

	# Resolve windfalls into {month_idx: total_amount}
	windfalls_by_idx = {}
	for w in windfalls:
		try:
			mi = int(w.get('month_idx'))
			amt = float(w.get('amount') or 0)
		except (TypeError, ValueError):
			continue
		if amt > 0:
			windfalls_by_idx[mi] = windfalls_by_idx.get(mi, 0) + amt

	# Resolve bonus events into {month_idx: amount} for the sim window.
	bonus_by_idx = {}
	if redirect_bonuses:
		bonus_by_idx = _project_bonus_amounts_by_month_idx(conn, max_months)

	debts = avalanche_order(conn)
	# Local mutable state: balances + allocations per account.
	state = []
	fedloan_idx = None
	for d in debts:
		s = {
			'id':       d['id'],
			'name':     d['name'],
			'slug':     d.get('slug'),
			'balance':  d['current_balance'],
			'apr':      d.get('apr') or 0,
			'minimum':  d.get('minimum_payment') or 0,
			'alloc':    d.get('attack_allocation') or 0,
			'killed_month': None,
		}
		state.append(s)
		if s.get('slug') == 'fedloan-student':
			fedloan_idx = len(state) - 1

	# Default attack from settings — applied to whichever debt is primary
	# (i.e., the head of state list with allocation > 0; if none, head).
	default_attack = get_setting(conn, 'default_attack_amount', 1000) or 0

	rows = []
	total_interest = 0.0
	today = et_today()
	month_cursor = date(today.year, today.month, 1)

	def primary_idx():
		# Walk avalanche order once. Per-debt: match if imminent-kill OR
		# allocation > 0 — whichever fires first. This preserves avalanche
		# priority (a small low-APR debt won't cut in line ahead of a
		# higher-APR debt that already has allocation).
		for i, s in enumerate(state):
			if s['balance'] <= 0:
				continue
			if s['balance'] <= default_attack:
				return i
			if s['alloc'] > 0:
				return i
		# Fallback: first alive
		for i, s in enumerate(state):
			if s['balance'] > 0:
				return i
		return None

	for month_num in range(max_months):
		alive = [s for s in state if s['balance'] > 0]
		if not alive:
			break

		# Apply FedLoan minimum override at its activation month (idempotent —
		# we'll re-set every loop but that's cheap).
		if fedloan_idx is not None and fedloan_min_override is not None:
			if month_num >= fedloan_min_starts_at and state[fedloan_idx]['balance'] > 0:
				state[fedloan_idx]['minimum'] = float(fedloan_min_override)

		starting_total = sum(s['balance'] for s in state)
		minimums_applied = 0.0
		attack_applied   = 0.0
		bonus_applied    = 0.0
		extra_applied    = 0.0
		side_applied     = 0.0
		windfall_applied = 0.0
		interest_accrued = 0.0
		killed_id        = None
		killed_name      = None
		pidx             = primary_idx()
		target           = state[pidx] if pidx is not None else None

		# 1. apply minimums to each alive debt
		for s in state:
			if s['balance'] <= 0:
				continue
			pay = min(s['minimum'], s['balance'])
			s['balance'] -= pay
			minimums_applied += pay

		# 2. apply normal attack to primary (single-shot, no spill — preserves
		# the Phase 1 baseline behavior exactly).
		if target and target['balance'] > 0:
			attack_pool = target['alloc']
			# If no per-account allocation set, fall back to default_attack
			# on the avalanche-top debt.
			if attack_pool == 0 and target is state[primary_idx() or 0]:
				attack_pool = default_attack
			pay = min(attack_pool, target['balance'])
			target['balance'] -= pay
			attack_applied += pay

		# 2b. Sandbox contributors stack on top AND spill: if the current
		# primary dies mid-payment, the remainder cascades to the next alive
		# avalanche-ordered debt. Otherwise a windfall on a dying target
		# would be silently absorbed and the user's "what if?" wouldn't
		# reflect the actual extra firepower they'd have.
		def _stack(amount):
			if amount <= 0:
				return 0
			remaining = amount
			applied = 0
			safety = len(state) + 2
			while remaining > 0.005 and safety > 0:
				safety -= 1
				pi = primary_idx()
				if pi is None:
					break
				t = state[pi]
				if t['balance'] <= 0:
					break
				p = min(remaining, t['balance'])
				t['balance'] -= p
				applied += p
				remaining -= p
			return applied

		extra_applied    += _stack(extra_monthly_attack)
		bonus_applied    += _stack(bonus_by_idx.get(month_num, 0))
		side_applied     += _stack(float(side_income_by_month.get(month_num, 0) or 0))
		windfall_applied += _stack(windfalls_by_idx.get(month_num, 0))

		# 3. interest on remaining balances (month-end)
		for s in state:
			if s['balance'] > 0 and s['apr'] > 0:
				inc = s['balance'] * s['apr'] / 100.0 / 12.0
				s['balance'] += inc
				interest_accrued += inc

		# 4. kills + cascade
		for s in state:
			if s['killed_month'] is None and s['balance'] <= 0.005:
				s['balance'] = 0
				s['killed_month'] = month_cursor.isoformat()[:7]
				killed_id = s['id']
				killed_name = s['name']
				# Cascade: move alloc + minimum to next-highest-APR alive debt
				freed = s['alloc'] + s['minimum']
				s['alloc'] = 0
				s['minimum'] = 0
				for nxt in state:
					if nxt['balance'] > 0:
						nxt['alloc'] += freed
						break

		ending_total = sum(s['balance'] for s in state)
		total_interest += interest_accrued

		rows.append({
			'month':              month_cursor.isoformat()[:7],
			'starting_total':     starting_total,
			'minimums_applied':   minimums_applied,
			'attack_applied':     attack_applied,
			'bonus_applied':      bonus_applied,
			'extra_applied':      extra_applied,
			'side_income_applied': side_applied,
			'windfall_applied':   windfall_applied,
			'interest_accrued':   interest_accrued,
			'ending_total':       ending_total,
			'current_target_id':  target['id'] if target else None,
			'current_target_name': target['name'] if target else None,
			'kill_account_id':    killed_id,
			'kill_account_name':  killed_name,
			'sandbox_touched':    (bonus_applied + extra_applied +
			                       side_applied + windfall_applied) > 0,
		})

		# advance month
		nxt_month = month_cursor.month % 12 + 1
		nxt_year  = month_cursor.year + (1 if month_cursor.month == 12 else 0)
		month_cursor = date(nxt_year, nxt_month, 1)

	# debt-free date = first day of the month after the last alive month
	debt_free_date = None
	if rows:
		# last month where any debt died
		for r in reversed(rows):
			if r['ending_total'] <= 0.01:
				debt_free_date = r['month']
				break

	return Projection(
		monthly_rows=rows,
		debt_free_date=debt_free_date,
		total_interest_paid=total_interest,
	)


def _project_bonus_amounts_by_month_idx(conn, max_months):
	"""Project future bonus income into the simulation window.

	For each income_events row with income_type='bonus':
	  - If event_date is in the future, take it at face value (one shot).
	  - If recurring=1 with a recognized recurrence_pattern, extrapolate
	    forward through the sim window.

	Returns {month_idx: total_amount}. month_idx is zero-based from
	today's month boundary (matches project_payoff's month indexing).
	"""
	today = et_today()
	month_anchor = date(today.year, today.month, 1)
	end_anchor = month_anchor
	for _ in range(max_months):
		nm = end_anchor.month % 12 + 1
		ny = end_anchor.year + (1 if end_anchor.month == 12 else 0)
		end_anchor = date(ny, nm, 1)
	# end_anchor is exclusive upper bound

	out = {}

	def month_idx_for(d):
		# zero-based months from month_anchor
		return (d.year - month_anchor.year) * 12 + (d.month - month_anchor.month)

	rows = conn.execute("""
		SELECT * FROM income_events WHERE income_type = 'bonus'
	""").fetchall()
	for r in rows:
		try:
			d = date.fromisoformat(r['event_date'])
		except (TypeError, ValueError):
			continue
		amt = float(r['amount'] or 0)
		if amt <= 0:
			continue
		pattern = (r['recurrence_pattern'] or '').lower()

		if r['recurring']:
			# Extrapolate forward through the sim window starting from the
			# first occurrence at or after month_anchor.
			cursor = d
			# Roll cursor forward to >= month_anchor.
			step_safety = 200
			while cursor < month_anchor and step_safety > 0:
				step_safety -= 1
				cursor = _advance_by_pattern(cursor, pattern)
				if cursor is None:
					break
			while cursor and cursor < end_anchor and step_safety > 0:
				step_safety -= 1
				mi = month_idx_for(cursor)
				if 0 <= mi < max_months:
					out[mi] = out.get(mi, 0) + amt
				cursor = _advance_by_pattern(cursor, pattern)
		else:
			# One-shot bonus — only counts if it's still in the future.
			if d >= month_anchor and d < end_anchor:
				out[month_idx_for(d)] = out.get(month_idx_for(d), 0) + amt

	return out


def _advance_by_pattern(d, pattern):
	"""Move a date forward by one recurrence cycle. Returns None on unknown."""
	if not d:
		return None
	if pattern == 'biweekly':
		return d + timedelta(days=14)
	if pattern == 'monthly':
		nm = d.month % 12 + 1
		ny = d.year + (1 if d.month == 12 else 0)
		last_day = calendar.monthrange(ny, nm)[1]
		return date(ny, nm, min(d.day, last_day))
	if pattern == 'quarterly':
		# add 3 months
		m = d.month + 3
		ny = d.year + (m - 1) // 12
		nm = (m - 1) % 12 + 1
		last_day = calendar.monthrange(ny, nm)[1]
		return date(ny, nm, min(d.day, last_day))
	return None


def next_future_bonus(conn):
	"""Return the next future bonus income_event as a dict, or None.

	Used by the sandbox UI to render "Your next bonus lands [Jul 2026, $X]"
	hint text under the Redirect Bonuses toggle.
	"""
	today_iso = et_today().isoformat()
	row = conn.execute("""
		SELECT * FROM income_events
		WHERE income_type = 'bonus' AND event_date >= ?
		ORDER BY event_date ASC LIMIT 1
	""", (today_iso,)).fetchone()
	if row:
		return dict(row)
	# No future one-shot — look for a recurring bonus and extrapolate next date.
	row = conn.execute("""
		SELECT * FROM income_events
		WHERE income_type = 'bonus' AND recurring = 1
		ORDER BY event_date DESC LIMIT 1
	""").fetchone()
	if not row:
		return None
	try:
		d = date.fromisoformat(row['event_date'])
	except (TypeError, ValueError):
		return None
	pattern = (row['recurrence_pattern'] or '').lower()
	today = et_today()
	safety = 200
	while d <= today and safety > 0:
		safety -= 1
		d = _advance_by_pattern(d, pattern)
		if d is None:
			return None
	r = dict(row)
	r['projected_next_date'] = d.isoformat()
	return r


# ---- cascade on manual kill ----

def cascade_attack_allocation(conn, killed_account_id):
	"""Called when a debt is manually marked paid_off. Moves its freed
	attack_allocation (and minimum_payment, conceptually) onto the next
	avalanche target.

	Returns the (next_account dict, freed_amount) or (None, 0).
	"""
	killed = conn.execute(
		"SELECT * FROM accounts WHERE id = ?", (killed_account_id,)
	).fetchone()
	if not killed:
		return None, 0
	freed = (killed['attack_allocation'] or 0) + (killed['minimum_payment'] or 0)
	if freed <= 0:
		return None, 0

	# next-highest-APR active debt
	placeholders = ','.join('?' for _ in DEBT_TYPES)
	row = conn.execute(f"""
		SELECT * FROM accounts
		WHERE status IN ('active', 'unknown')
		  AND account_type IN ({placeholders})
		  AND id != ?
		ORDER BY COALESCE(apr, 0) DESC, id ASC
		LIMIT 1
	""", DEBT_TYPES + (killed_account_id,)).fetchone()
	if not row:
		return None, freed

	now = et_now_iso()
	new_alloc = (row['attack_allocation'] or 0) + freed
	conn.execute("""
		UPDATE accounts SET attack_allocation = ?, updated = ?
		WHERE id = ?
	""", (new_alloc, now, row['id']))

	# null out the killed account's alloc so it doesn't double-count
	conn.execute("""
		UPDATE accounts SET attack_allocation = 0, updated = ?
		WHERE id = ?
	""", (now, killed_account_id))

	conn.commit()
	return dict(row), freed


# ---- recommendation helpers (used by glance + payday + AI) ----

def stale_snapshot(conn, account_id, days=14):
	"""True if the latest snapshot is older than `days` days."""
	at = latest_snapshot_at(conn, account_id)
	if not at:
		return True
	try:
		dt = datetime.fromisoformat(at.replace('Z', '+00:00'))
	except ValueError:
		return True
	age = (datetime.utcnow() - dt.replace(tzinfo=None)).total_seconds() / 86400
	return age > days


def footer_summary():
	"""Cheap read for the cross-app footer pill. Returns:
	{'total': float, 'delta_7d': float, 'arrow': 'down'|'up'|'flat', 'has_data': bool}

	Opens its own connection. Returns has_data=False if the DB is missing
	or has no snapshots yet — the pill renders 'LEDGER · —' in that case.
	Never raises: any error returns the empty shape."""
	try:
		conn = get_ledger_db()
	except Exception:
		return {'total': 0, 'delta_7d': 0, 'arrow': 'flat', 'has_data': False}
	try:
		td = total_debt(conn)
		# Don't generate autopay rows here — read-only call.
		# 30-day window matches the Glance card's "30-day Δ" — one window,
		# one mental model across the app.
		td_30 = total_debt_n_days_ago(conn, 30)
		# Need at least one snapshot to call this meaningful.
		row = conn.execute("""
			SELECT 1 FROM balance_snapshots LIMIT 1
		""").fetchone()
		has_data = row is not None and td > 0
	except Exception:
		conn.close()
		return {'total': 0, 'delta_30d': 0, 'arrow': 'flat', 'has_data': False}
	conn.close()
	if td_30 is None:
		# No baseline yet — show neutral arrow rather than a misleading up/down.
		return {'total': td, 'delta_30d': 0, 'arrow': 'flat', 'has_data': has_data}
	delta = td - td_30
	if delta < -1:
		arrow = 'down'
	elif delta > 1:
		arrow = 'up'
	else:
		arrow = 'flat'
	return {'total': td, 'delta_30d': delta, 'arrow': arrow, 'has_data': has_data}


def stale_autopay(conn, account_id, days=3):
	"""True if there's an unconfirmed autopay row older than `days` days."""
	row = conn.execute("""
		SELECT tx_date FROM debt_transactions
		WHERE account_id = ? AND confirmed = 0 AND tx_type = 'payment'
		ORDER BY tx_date ASC LIMIT 1
	""", (account_id,)).fetchone()
	if not row:
		return False
	try:
		d = date.fromisoformat(row['tx_date'])
	except ValueError:
		return False
	return (et_today() - d).days > days
