"""
migrate_init_ledger.py
The Ledger — separate SQLite DB at assets/data/ledger.db. See .kt/spec-ledger.md.

What it does (idempotent — safe to re-run):

  Creates ledger.db with the following tables + indexes:

    accounts             — debt + checking accounts; current balance is
                            derived from latest balance_snapshots row.
    balance_snapshots    — every balance recorded for an account.
    debt_transactions    — every payment / charge; pending autopay rows
                            live here as confirmed=0 until the user
                            confirms them on the payday session.
    income_events        — paychecks, bonuses, side income (with
                            recurrence patterns).
    recurring_expenses   — fixed monthly outflows (rent, subs, utilities).
    plan_months          — denormalized monthly projection cache.
    one_time_events      — known upcoming or past one-off events.
    leak_imports         — record of leak-hunt CSV sessions.
    settings             — single-row config (id = 1).

  Indexes:
    idx_snap_account_at        balance_snapshots(account_id, snapshot_at DESC)
    idx_tx_account_date        debt_transactions(account_id, tx_date DESC)
    idx_tx_pending             debt_transactions(confirmed) WHERE confirmed = 0
    idx_income_date            income_events(event_date)
    idx_recurring_active       recurring_expenses(active)
    idx_onetime_date           one_time_events(event_date)

Run from PythonAnywhere bash:
    cd /home/aaronaiken/status_update
    python migrate_init_ledger.py

Pairs with seed_ledger.py for first-run setup.
"""

import os
import sqlite3


LEDGER_DB_FILE = os.path.join(
	os.environ.get('COCKPIT_REPO_ROOT', '/home/aaronaiken/status_update'),
	'assets/data/ledger.db'
)


def table_exists(cur, name):
	row = cur.execute(
		"SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,)
	).fetchone()
	return row is not None


def index_exists(cur, name):
	row = cur.execute(
		"SELECT name FROM sqlite_master WHERE type='index' AND name=?", (name,)
	).fetchone()
	return row is not None


TABLES = [
	('accounts', """
		CREATE TABLE accounts (
			id                  INTEGER PRIMARY KEY AUTOINCREMENT,
			name                TEXT NOT NULL,
			slug                TEXT NOT NULL UNIQUE,
			account_type        TEXT NOT NULL,
			status              TEXT NOT NULL DEFAULT 'active',
			apr                 REAL,
			minimum_payment     REAL,
			attack_allocation   REAL NOT NULL DEFAULT 0,
			autopay_enabled     INTEGER NOT NULL DEFAULT 0,
			autopay_amount      REAL,
			autopay_cadence     TEXT,
			autopay_day         INTEGER,
			autopay_next_date   TEXT,
			opened_date         TEXT,
			notes               TEXT,
			created             TEXT NOT NULL,
			updated             TEXT NOT NULL
		)
	"""),
	('balance_snapshots', """
		CREATE TABLE balance_snapshots (
			id          INTEGER PRIMARY KEY AUTOINCREMENT,
			account_id  INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
			balance     REAL NOT NULL,
			snapshot_at TEXT NOT NULL,
			source      TEXT NOT NULL DEFAULT 'manual',
			notes       TEXT,
			created     TEXT NOT NULL
		)
	"""),
	('debt_transactions', """
		CREATE TABLE debt_transactions (
			id           INTEGER PRIMARY KEY AUTOINCREMENT,
			account_id   INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
			tx_date      TEXT NOT NULL,
			amount       REAL NOT NULL,
			tx_type      TEXT NOT NULL,
			source       TEXT NOT NULL DEFAULT 'manual',
			confirmed    INTEGER NOT NULL DEFAULT 1,
			description  TEXT,
			notes        TEXT,
			created      TEXT NOT NULL,
			updated      TEXT NOT NULL
		)
	"""),
	('income_events', """
		CREATE TABLE income_events (
			id                 INTEGER PRIMARY KEY AUTOINCREMENT,
			event_date         TEXT NOT NULL,
			amount             REAL NOT NULL,
			income_type        TEXT NOT NULL,
			source             TEXT,
			recurring          INTEGER NOT NULL DEFAULT 0,
			recurrence_pattern TEXT,
			notes              TEXT,
			created            TEXT NOT NULL
		)
	"""),
	('recurring_expenses', """
		CREATE TABLE recurring_expenses (
			id            INTEGER PRIMARY KEY AUTOINCREMENT,
			name          TEXT NOT NULL,
			amount        REAL NOT NULL,
			day_of_month  INTEGER NOT NULL,
			category      TEXT,
			active        INTEGER NOT NULL DEFAULT 1,
			notes         TEXT,
			created       TEXT NOT NULL,
			updated       TEXT NOT NULL
		)
	"""),
	('plan_months', """
		CREATE TABLE plan_months (
			id                  INTEGER PRIMARY KEY AUTOINCREMENT,
			month               TEXT NOT NULL UNIQUE,
			projected_income    REAL,
			projected_recurring REAL,
			projected_minimums  REAL,
			projected_attack    REAL,
			target_account_id   INTEGER REFERENCES accounts(id) ON DELETE SET NULL,
			override_notes      TEXT,
			generated_at        TEXT NOT NULL,
			updated_at          TEXT NOT NULL
		)
	"""),
	('one_time_events', """
		CREATE TABLE one_time_events (
			id             INTEGER PRIMARY KEY AUTOINCREMENT,
			event_date     TEXT NOT NULL,
			amount         REAL NOT NULL,
			direction      TEXT NOT NULL,
			description    TEXT NOT NULL,
			status         TEXT NOT NULL DEFAULT 'planned',
			affects_attack INTEGER NOT NULL DEFAULT 1,
			notes          TEXT,
			created        TEXT NOT NULL
		)
	"""),
	('leak_imports', """
		CREATE TABLE leak_imports (
			id                      INTEGER PRIMARY KEY AUTOINCREMENT,
			imported_at             TEXT NOT NULL,
			source                  TEXT NOT NULL,
			period_start            TEXT NOT NULL,
			period_end              TEXT NOT NULL,
			total_amount            REAL NOT NULL,
			category_breakdown_json TEXT NOT NULL,
			notes                   TEXT
		)
	"""),
	('settings', """
		CREATE TABLE settings (
			id                         INTEGER PRIMARY KEY CHECK (id = 1),
			checking_account_id        INTEGER REFERENCES accounts(id) ON DELETE SET NULL,
			debt_free_target_date      TEXT,
			show_runway_card_on_glance INTEGER NOT NULL DEFAULT 1,
			show_attack_card_on_glance INTEGER NOT NULL DEFAULT 1,
			default_attack_amount      REAL NOT NULL DEFAULT 1000,
			created                    TEXT NOT NULL,
			updated                    TEXT NOT NULL
		)
	"""),
]


INDEXES = [
	('idx_snap_account_at',
	 'CREATE INDEX idx_snap_account_at ON balance_snapshots(account_id, snapshot_at DESC)'),
	('idx_tx_account_date',
	 'CREATE INDEX idx_tx_account_date ON debt_transactions(account_id, tx_date DESC)'),
	('idx_tx_pending',
	 'CREATE INDEX idx_tx_pending ON debt_transactions(confirmed) WHERE confirmed = 0'),
	('idx_income_date',
	 'CREATE INDEX idx_income_date ON income_events(event_date)'),
	('idx_recurring_active',
	 'CREATE INDEX idx_recurring_active ON recurring_expenses(active)'),
	('idx_onetime_date',
	 'CREATE INDEX idx_onetime_date ON one_time_events(event_date)'),
]


def run():
	os.makedirs(os.path.dirname(LEDGER_DB_FILE), exist_ok=True)
	conn = sqlite3.connect(LEDGER_DB_FILE)
	conn.execute("PRAGMA foreign_keys = ON")
	conn.execute("PRAGMA journal_mode = DELETE")
	cur = conn.cursor()

	added = []
	skipped = []

	for name, sql in TABLES:
		if table_exists(cur, name):
			skipped.append(f'{name} (table)')
		else:
			cur.execute(sql)
			added.append(f'{name} (table)')

	for name, sql in INDEXES:
		if index_exists(cur, name):
			skipped.append(name)
		else:
			cur.execute(sql)
			added.append(name)

	conn.commit()
	conn.close()

	print()
	print("Migration: migrate_init_ledger.py")
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
	if not added:
		print("No changes — schema already up to date.")
	print()


if __name__ == '__main__':
	run()
