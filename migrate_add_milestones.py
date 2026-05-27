"""
migrate_add_milestones.py
Phase 4 of The Ledger — see .kt/spec-ledger-phase-4-milestones.md.

What it does (idempotent — safe to re-run):

  + milestones table:
      id              INTEGER PRIMARY KEY AUTOINCREMENT
      position        INTEGER NOT NULL                -- 1, 2, 3, …
      title           TEXT NOT NULL
      why_text        TEXT
      condition_type  TEXT NOT NULL
      condition_params TEXT NOT NULL                  -- JSON
      status          TEXT NOT NULL DEFAULT 'locked'  -- 'locked' | 'current' | 'complete'
      completed_at    TEXT
      manual_complete INTEGER NOT NULL DEFAULT 0
      deleted_at      TEXT
      created         TEXT NOT NULL
      updated         TEXT NOT NULL

  + milestone_events table (audit log):
      id           INTEGER PRIMARY KEY AUTOINCREMENT
      milestone_id INTEGER NOT NULL REFERENCES milestones(id) ON DELETE CASCADE
      event_type   TEXT NOT NULL
      details      TEXT
      created      TEXT NOT NULL

  + indexes:
      idx_milestones_position    UNIQUE on (position) WHERE deleted_at IS NULL
      idx_milestones_status      on (status)
      idx_milestone_events       on (milestone_id, created DESC)

  + seed the default 6-milestone Aaron template (see spec section 3).
    First milestone is set to 'current' if the user's checking balance
    is < $1,000 (which it is, per the testing context). Otherwise it
    starts complete and milestone 2 becomes current.

Run from PythonAnywhere bash:
    cd /home/aaronaiken/status_update
    python migrate_add_milestones.py
"""

import os
import sqlite3
import json
from datetime import datetime
import pytz


LEDGER_DB_FILE = os.path.join(
	os.environ.get('COCKPIT_REPO_ROOT', '/home/aaronaiken/status_update'),
	'assets/data/ledger.db'
)


def table_exists(cur, name):
	r = cur.execute(
		"SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,)
	).fetchone()
	return r is not None


def index_exists(cur, name):
	r = cur.execute(
		"SELECT name FROM sqlite_master WHERE type='index' AND name=?", (name,)
	).fetchone()
	return r is not None


CREATE_MILESTONES = """
CREATE TABLE milestones (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    position        INTEGER NOT NULL,
    title           TEXT NOT NULL,
    why_text        TEXT,
    condition_type  TEXT NOT NULL,
    condition_params TEXT NOT NULL DEFAULT '{}',
    status          TEXT NOT NULL DEFAULT 'locked',
    completed_at    TEXT,
    manual_complete INTEGER NOT NULL DEFAULT 0,
    deleted_at      TEXT,
    created         TEXT NOT NULL,
    updated         TEXT NOT NULL
)
"""

CREATE_EVENTS = """
CREATE TABLE milestone_events (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    milestone_id INTEGER NOT NULL REFERENCES milestones(id) ON DELETE CASCADE,
    event_type   TEXT NOT NULL,
    details      TEXT,
    created      TEXT NOT NULL
)
"""

INDEXES = [
	('idx_milestones_position',
	 "CREATE UNIQUE INDEX idx_milestones_position ON milestones(position) WHERE deleted_at IS NULL"),
	('idx_milestones_status',
	 "CREATE INDEX idx_milestones_status ON milestones(status)"),
	('idx_milestone_events',
	 "CREATE INDEX idx_milestone_events ON milestone_events(milestone_id, created DESC)"),
]


# Default 6-milestone template. See spec section 3 for the why-text and
# condition reasoning. Condition params stored as JSON.
DEFAULT_MILESTONES = [
	{
		'position': 1,
		'title': 'Starter buffer',
		'why_text': 'A $1,000 cushion in checking means the next unexpected expense doesn\'t become new debt. Without this, every refrigerator becomes a credit card.',
		'condition_type': 'account_balance_ge',
		'condition_params': {'account_slug': 'checking', 'threshold': 1000},
	},
	{
		'position': 2,
		'title': 'Resolve FedLoan status',
		'why_text': 'FedLoan is the biggest unknown in my debt picture. Until I know the real minimum payment and repayment plan, the timeline can shift by months in either direction. 20 minutes on studentaid.gov closes this.',
		'condition_type': 'account_status_known',
		'condition_params': {'account_slug': 'fedloan-student'},
	},
	{
		'position': 3,
		'title': 'Debt-free',
		'why_text': 'All debt killed. The full attack budget — minimums + allocation snowball — converts from debt service to wealth building.',
		'condition_type': 'total_debt_zero',
		'condition_params': {},
	},
	{
		'position': 4,
		'title': 'Full emergency fund (3 months expenses)',
		'why_text': 'Three months of expenses in liquid savings means a job loss, a medical event, or a major car repair doesn\'t put me back into debt. The buffer that lets the rest of life stay stable.',
		'condition_type': 'liquid_savings_months',
		'condition_params': {'months': 3, 'account_slugs': ['checking', 'savings']},
	},
	{
		'position': 5,
		'title': "Lindsay's exit ramp",
		'why_text': "Lindsay works 1.25 days/week and brings in around $30k/year from cleaning. This milestone is the point where my side income (or her new income streams) reliably replaces hers, so she can step away from the work she shouldn't be doing forever. The 3-month rolling average matters because a one-month spike doesn't prove sustainability.",
		'condition_type': 'rolling_income_sustained',
		'condition_params': {'monthly_target': 2500, 'window_months': 3,
		                     'income_types': ['side_income', 'bonus', 'other']},
	},
	{
		'position': 6,
		'title': 'Retirement on track',
		'why_text': 'Define what \'on track for retirement\' means to me. May be a specific monthly contribution rate, a target balance, or a target date. Manual completion — I decide when this is true.',
		'condition_type': 'manual_completion',
		'condition_params': {},
	},
]


def et_now_iso():
	return datetime.now(pytz.timezone('US/Eastern')).isoformat()


def utc_now_iso():
	return datetime.utcnow().isoformat(timespec='microseconds') + 'Z'


def run():
	if not os.path.exists(LEDGER_DB_FILE):
		print(f"× Ledger DB not found at {LEDGER_DB_FILE}")
		return

	conn = sqlite3.connect(LEDGER_DB_FILE)
	conn.row_factory = sqlite3.Row
	conn.execute("PRAGMA foreign_keys = ON")
	conn.execute("PRAGMA journal_mode = DELETE")
	cur = conn.cursor()

	added, skipped = [], []

	if table_exists(cur, 'milestones'):
		skipped.append('milestones (table)')
	else:
		cur.execute(CREATE_MILESTONES)
		added.append('milestones (table)')

	if table_exists(cur, 'milestone_events'):
		skipped.append('milestone_events (table)')
	else:
		cur.execute(CREATE_EVENTS)
		added.append('milestone_events (table)')

	for name, sql in INDEXES:
		if index_exists(cur, name):
			skipped.append(name)
		else:
			cur.execute(sql)
			added.append(name)

	# Seed default milestones (only if none exist — idempotent).
	now = et_now_iso()
	seeded = []
	existing = cur.execute(
		"SELECT COUNT(*) AS n FROM milestones WHERE deleted_at IS NULL"
	).fetchone()['n']
	if existing == 0:
		# Decide initial 'current' based on checking balance.
		checking_id_row = cur.execute(
			"SELECT id FROM accounts WHERE slug = 'checking'"
		).fetchone()
		checking_balance = None
		if checking_id_row:
			b = cur.execute("""
				SELECT balance FROM balance_snapshots
				WHERE account_id = ?
				ORDER BY snapshot_at DESC, id DESC LIMIT 1
			""", (checking_id_row['id'],)).fetchone()
			checking_balance = b['balance'] if b else None

		first_complete = (checking_balance is not None and checking_balance >= 1000)
		current_position = 2 if first_complete else 1

		for m in DEFAULT_MILESTONES:
			status = 'locked'
			completed_at = None
			if m['position'] < current_position:
				status = 'complete'
				completed_at = utc_now_iso()
			elif m['position'] == current_position:
				status = 'current'
			cur.execute("""
				INSERT INTO milestones (
					position, title, why_text, condition_type, condition_params,
					status, completed_at, manual_complete, created, updated
				) VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
			""", (
				m['position'], m['title'], m['why_text'],
				m['condition_type'], json.dumps(m['condition_params']),
				status, completed_at, now, now,
			))
			mid = cur.lastrowid
			cur.execute("""
				INSERT INTO milestone_events (
					milestone_id, event_type, details, created
				) VALUES (?, 'created', ?, ?)
			""", (mid, json.dumps({'seeded': True, 'status': status}), now))
			seeded.append(f'{m["position"]}. {m["title"]}  [{status}]')

	conn.commit()
	conn.close()

	print()
	print("Migration: migrate_add_milestones.py")
	print(f"DB:        {LEDGER_DB_FILE}")
	print()
	if added:
		print(f"✓ Added ({len(added)}):")
		for item in added:
			print(f"    + {item}")
	if skipped:
		print(f"— Already in place ({len(skipped)}):")
		for item in skipped:
			print(f"    · {item}")
	if seeded:
		print()
		print(f"✓ Seeded milestones ({len(seeded)}):")
		for s in seeded:
			print(f"    + {s}")
	elif existing > 0:
		print()
		print(f"— Milestones already populated ({existing} rows).")
	print()


if __name__ == '__main__':
	run()
