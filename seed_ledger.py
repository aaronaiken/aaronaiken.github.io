"""
seed_ledger.py
Seed The Ledger with Aaron's accounts + May 26 2026 balance snapshot.

Idempotent — checks by slug before inserting. Re-run safely.

Run after migrate_init_ledger.py:
    cd /home/aaronaiken/status_update
    python seed_ledger.py

See .kt/spec-ledger.md Section 11 for the source data.
"""

import os
import sqlite3
from datetime import datetime
import pytz


LEDGER_DB_FILE = os.path.join(
	os.environ.get('COCKPIT_REPO_ROOT', '/home/aaronaiken/status_update'),
	'assets/data/ledger.db'
)


# (name, slug, type, status, apr, min, attack_alloc, autopay,
#  autopay_amt, cadence, autopay_day, notes)
ACCOUNTS = [
	("Nordstrom", "nordstrom", "credit_card", "active", 30.15, 0.00, 0, True, 0.00, "monthly", 13,
	 "Nearly paid off as of May 2026. $161.89 remaining. Was being attacked at $500/payday until April. No current minimum required."),
	("Amex", "amex", "credit_card", "paid_off", 29.99, 0.00, 0, False, None, None, None,
	 "Paid off in early 2026."),
	("PNC", "pnc", "credit_card", "active", 29.24, 192.00, 1000, True, 192.00, "monthly", 28,
	 "Next avalanche target after Nordstrom kill — full $1,000 attack ready to land here."),
	("Capital One", "capital-one", "credit_card", "active", 28.49, 84.00, 0, True, 84.00, "monthly", 27,
	 "Opened due to unexpected expense. Did not exist in January 2026. APR close to PNC's — consider as alt avalanche target."),
	("IKEA", "ikea", "credit_card", "active", 21.99, 36.00, 0, True, 36.00, "monthly", 16,
	 "Mid-priority. Small balance."),
	("SoFi", "sofi", "loan", "active", 14.41, 310.97, 0, True, 310.97, "monthly", 15,
	 "Personal loan. Fixed payment."),
	("FedLoan Student", "fedloan-student", "student_loan", "unknown", 5.00, 0.00, 0, False, None, None, None,
	 "Status unknown as of May 2026. Balance has grown ~$490 since January with no payments — likely administrative forbearance + interest accrual. Aaron to check studentaid.gov for current repayment plan, minimum, and resume date."),
	("Apple", "apple", "bnpl", "active", 0.00, 375.55, 0, True, 375.55, "monthly_eom", 0,
	 "0% APR. Apple Card BNPL or installment. Pays last day of month."),
	("Jenius", "jenius", "credit_card", "active", 0.00, 200.00, 0, True, 200.00, "biweekly", None,
	 "0% APR. Autopay biweekly on payday. Last autopay 5/22."),
	("PayPal", "paypal", "bnpl", "active", 0.00, 75.00, 0, True, 75.00, "monthly", 2,
	 "0% APR. PayPal Pay-in-N or similar."),
	("Checking", "checking", "checking", "active", None, None, 0, False, None, None, None,
	 "Primary checking. Snapshotted on every payday."),
]


SNAPSHOTS = [
	("nordstrom",          161.89),
	("amex",                 0.00),
	("pnc",               5801.79),
	("capital-one",       2461.27),
	("ikea",              1012.24),
	("sofi",              5979.44),
	("fedloan-student",  24022.00),
	("apple",            18112.91),
	("jenius",            5075.84),
	("paypal",            2733.51),
	# checking intentionally NOT seeded — Aaron snapshots on first payday session.
]


# Approximate; documented after the fact for context per spec.
ONE_TIME_EVENTS = [
	{
		"event_date":     "2026-04-15",
		"amount":         2461.27,
		"direction":      "outflow",
		"description":    "Unexpected expense → opened Capital One",
		"status":         "happened",
		"affects_attack": 0,
		"notes":          "Documented after the fact for context. Date approximate.",
	},
]


def et_now_iso():
	return datetime.now(pytz.timezone('US/Eastern')).isoformat()


def snapshot_at_iso():
	"""ISO 8601 UTC with microseconds + Z suffix, per spec."""
	return datetime.utcnow().isoformat(timespec='microseconds') + 'Z'


def run():
	if not os.path.exists(LEDGER_DB_FILE):
		print(f"× DB not found at {LEDGER_DB_FILE}")
		print("  Run migrate_init_ledger.py first.")
		return

	conn = sqlite3.connect(LEDGER_DB_FILE)
	conn.execute("PRAGMA foreign_keys = ON")
	conn.execute("PRAGMA journal_mode = DELETE")
	cur = conn.cursor()

	now = et_now_iso()
	added_accounts   = []
	skipped_accounts = []
	added_snaps      = []
	skipped_snaps    = []

	# ---- accounts ----
	for (name, slug, atype, status, apr, minp, attack, autopay,
	     autopay_amt, cadence, autopay_day, notes) in ACCOUNTS:
		existing = cur.execute(
			"SELECT id FROM accounts WHERE slug = ?", (slug,)
		).fetchone()
		if existing:
			skipped_accounts.append(slug)
			continue
		cur.execute("""
			INSERT INTO accounts (
				name, slug, account_type, status, apr, minimum_payment,
				attack_allocation, autopay_enabled, autopay_amount,
				autopay_cadence, autopay_day, autopay_next_date,
				opened_date, notes, created, updated
			) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, ?, ?, ?)
		""", (name, slug, atype, status, apr, minp, attack,
		      1 if autopay else 0, autopay_amt, cadence, autopay_day,
		      notes, now, now))
		added_accounts.append(slug)

	# ---- snapshots ----
	snap_at = snapshot_at_iso()
	for slug, balance in SNAPSHOTS:
		row = cur.execute(
			"SELECT id FROM accounts WHERE slug = ?", (slug,)
		).fetchone()
		if not row:
			continue
		account_id = row[0]
		# Skip if any snapshot already exists for this account (idempotent).
		has_snap = cur.execute(
			"SELECT 1 FROM balance_snapshots WHERE account_id = ? LIMIT 1",
			(account_id,)
		).fetchone()
		if has_snap:
			skipped_snaps.append(slug)
			continue
		cur.execute("""
			INSERT INTO balance_snapshots (
				account_id, balance, snapshot_at, source, notes, created
			) VALUES (?, ?, ?, 'manual', 'Seed snapshot (2026-05-26)', ?)
		""", (account_id, balance, snap_at, now))
		added_snaps.append(slug)

	# ---- settings (single row, id=1) ----
	checking_row = cur.execute(
		"SELECT id FROM accounts WHERE slug = 'checking'"
	).fetchone()
	checking_id = checking_row[0] if checking_row else None
	existing_settings = cur.execute(
		"SELECT id FROM settings WHERE id = 1"
	).fetchone()
	settings_added = False
	if not existing_settings:
		cur.execute("""
			INSERT INTO settings (
				id, checking_account_id, debt_free_target_date,
				show_runway_card_on_glance, show_attack_card_on_glance,
				default_attack_amount, created, updated
			) VALUES (1, ?, NULL, 1, 1, 1000.00, ?, ?)
		""", (checking_id, now, now))
		settings_added = True
	elif checking_id:
		# Backfill checking_account_id if it was NULL before checking existed.
		cur.execute("""
			UPDATE settings SET checking_account_id = COALESCE(checking_account_id, ?),
			                    updated = ?
			WHERE id = 1
		""", (checking_id, now))

	# ---- one-time events ----
	added_events   = []
	skipped_events = []
	for ev in ONE_TIME_EVENTS:
		exists = cur.execute("""
			SELECT id FROM one_time_events
			WHERE event_date = ? AND description = ?
		""", (ev['event_date'], ev['description'])).fetchone()
		if exists:
			skipped_events.append(ev['description'])
			continue
		cur.execute("""
			INSERT INTO one_time_events (
				event_date, amount, direction, description, status,
				affects_attack, notes, created
			) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
		""", (ev['event_date'], ev['amount'], ev['direction'],
		      ev['description'], ev['status'], ev['affects_attack'],
		      ev['notes'], now))
		added_events.append(ev['description'])

	conn.commit()
	conn.close()

	print()
	print("Seed: seed_ledger.py")
	print(f"DB:   {LEDGER_DB_FILE}")
	print()
	print(f"Accounts:  added {len(added_accounts)}, skipped {len(skipped_accounts)}")
	for s in added_accounts:   print(f"    + {s}")
	for s in skipped_accounts: print(f"    · {s} (already present)")
	print()
	print(f"Snapshots: added {len(added_snaps)}, skipped {len(skipped_snaps)}")
	for s in added_snaps:   print(f"    + {s}")
	for s in skipped_snaps: print(f"    · {s} (has prior snapshot)")
	print()
	print(f"One-time events: added {len(added_events)}, skipped {len(skipped_events)}")
	for s in added_events:   print(f"    + {s}")
	for s in skipped_events: print(f"    · {s} (already present)")
	print()
	if settings_added:
		print("Settings: row inserted.")
	else:
		print("Settings: already configured (checking_account_id backfilled if missing).")
	print()


if __name__ == '__main__':
	run()
