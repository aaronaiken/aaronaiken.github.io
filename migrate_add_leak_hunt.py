"""
migrate_add_leak_hunt.py
Phase 3 of The Ledger — see .kt/spec-ledger-phase-3-leak-hunt.md.

What it does (idempotent — safe to run multiple times):

  + leak_transactions table:
      id              INTEGER PRIMARY KEY AUTOINCREMENT
      leak_import_id  INTEGER NOT NULL REFERENCES leak_imports(id) ON DELETE CASCADE
      tx_date         TEXT NOT NULL                 -- ISO date
      description     TEXT NOT NULL                 -- raw merchant string from CSV
      amount          REAL NOT NULL                 -- positive = outflow, negative = inflow
      category        TEXT NOT NULL
      subcategory     TEXT
      notes           TEXT
      is_recurring    INTEGER NOT NULL DEFAULT 0
      rule_id         INTEGER REFERENCES leak_rules(id) ON DELETE SET NULL
      manually_set    INTEGER NOT NULL DEFAULT 0
      created         TEXT NOT NULL

  + leak_rules table:
      id          INTEGER PRIMARY KEY AUTOINCREMENT
      match_type  TEXT NOT NULL           -- 'contains' | 'starts_with' | 'equals' | 'regex'
      match_value TEXT NOT NULL
      category    TEXT NOT NULL
      subcategory TEXT
      priority    INTEGER NOT NULL DEFAULT 100  -- lower = higher priority
      active      INTEGER NOT NULL DEFAULT 1
      note        TEXT
      created     TEXT NOT NULL
      updated     TEXT NOT NULL

  + leak_imports new columns:
      csv_filename        TEXT
      csv_format          TEXT
      transaction_count   INTEGER NOT NULL DEFAULT 0
      checking_account_id INTEGER REFERENCES accounts(id)
      deleted_at          TEXT

  + indexes:
      idx_leak_tx_import_cat      leak_transactions(leak_import_id, category)
      idx_leak_tx_desc            leak_transactions(description)
      idx_leak_rules_active       leak_rules(active, priority)
      idx_leak_imports_alive      leak_imports(deleted_at) WHERE deleted_at IS NULL

  + seed minimal default rules:
      contains 'TRANSFER TO'    → Internal transfer
      contains 'TRANSFER FROM'  → Internal transfer
      contains 'ATM WITHDRAWAL' → Other (subcategory 'Cash')

Run from PythonAnywhere bash:
    cd /home/aaronaiken/status_update
    python migrate_add_leak_hunt.py
"""

import os
import sqlite3
from datetime import datetime
import pytz


LEDGER_DB_FILE = os.path.join(
	os.environ.get('COCKPIT_REPO_ROOT', '/home/aaronaiken/status_update'),
	'assets/data/ledger.db'
)


def table_exists(cur, name):
	row = cur.execute(
		"SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,)
	).fetchone()
	return row is not None


def column_exists(cur, table, col):
	cols = [r[1] for r in cur.execute(f"PRAGMA table_info({table})").fetchall()]
	return col in cols


def index_exists(cur, name):
	row = cur.execute(
		"SELECT name FROM sqlite_master WHERE type='index' AND name=?", (name,)
	).fetchone()
	return row is not None


CREATE_LEAK_RULES = """
CREATE TABLE leak_rules (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    match_type  TEXT NOT NULL,
    match_value TEXT NOT NULL,
    category    TEXT NOT NULL,
    subcategory TEXT,
    priority    INTEGER NOT NULL DEFAULT 100,
    active      INTEGER NOT NULL DEFAULT 1,
    note        TEXT,
    created     TEXT NOT NULL,
    updated     TEXT NOT NULL
)
"""

CREATE_LEAK_TX = """
CREATE TABLE leak_transactions (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    leak_import_id INTEGER NOT NULL REFERENCES leak_imports(id) ON DELETE CASCADE,
    tx_date        TEXT NOT NULL,
    description    TEXT NOT NULL,
    amount         REAL NOT NULL,
    category       TEXT NOT NULL,
    subcategory    TEXT,
    notes          TEXT,
    is_recurring   INTEGER NOT NULL DEFAULT 0,
    rule_id        INTEGER REFERENCES leak_rules(id) ON DELETE SET NULL,
    manually_set   INTEGER NOT NULL DEFAULT 0,
    created        TEXT NOT NULL
)
"""

NEW_LEAK_IMPORTS_COLUMNS = [
	('csv_filename',        'TEXT'),
	('csv_format',          'TEXT'),
	('transaction_count',   'INTEGER NOT NULL DEFAULT 0'),
	('checking_account_id', 'INTEGER REFERENCES accounts(id)'),
	('deleted_at',          'TEXT'),
]

INDEXES = [
	('idx_leak_tx_import_cat',
	 'CREATE INDEX idx_leak_tx_import_cat ON leak_transactions(leak_import_id, category)'),
	('idx_leak_tx_desc',
	 'CREATE INDEX idx_leak_tx_desc ON leak_transactions(description)'),
	('idx_leak_rules_active',
	 'CREATE INDEX idx_leak_rules_active ON leak_rules(active, priority)'),
	('idx_leak_imports_alive',
	 'CREATE INDEX idx_leak_imports_alive ON leak_imports(deleted_at) WHERE deleted_at IS NULL'),
]


SEED_RULES = [
	# (match_type, match_value, category, subcategory, priority, note)
	('contains', 'TRANSFER TO',     'Internal transfer', None, 10,
	 'Default — transfers between own accounts; excluded from leak math.'),
	('contains', 'TRANSFER FROM',   'Internal transfer', None, 10,
	 'Default — transfers between own accounts; excluded from leak math.'),
	('contains', 'ATM WITHDRAWAL',  'Other',             'Cash', 20,
	 'Default — cash withdrawals.'),
]


def et_now_iso():
	return datetime.now(pytz.timezone('US/Eastern')).isoformat()


def run():
	if not os.path.exists(LEDGER_DB_FILE):
		print(f"× Ledger DB not found at {LEDGER_DB_FILE}")
		print("  Run migrate_init_ledger.py first.")
		return

	conn = sqlite3.connect(LEDGER_DB_FILE)
	conn.execute("PRAGMA foreign_keys = ON")
	conn.execute("PRAGMA journal_mode = DELETE")
	cur = conn.cursor()

	added, skipped = [], []

	# leak_rules first (leak_transactions FK references it)
	if table_exists(cur, 'leak_rules'):
		skipped.append('leak_rules (table)')
	else:
		cur.execute(CREATE_LEAK_RULES)
		added.append('leak_rules (table)')

	if table_exists(cur, 'leak_transactions'):
		skipped.append('leak_transactions (table)')
	else:
		cur.execute(CREATE_LEAK_TX)
		added.append('leak_transactions (table)')

	for col, sql_type in NEW_LEAK_IMPORTS_COLUMNS:
		if column_exists(cur, 'leak_imports', col):
			skipped.append(f'leak_imports.{col}')
		else:
			cur.execute(f"ALTER TABLE leak_imports ADD COLUMN {col} {sql_type}")
			added.append(f'leak_imports.{col}')

	for name, sql in INDEXES:
		if index_exists(cur, name):
			skipped.append(name)
		else:
			cur.execute(sql)
			added.append(name)

	# Seed rules — only insert if none already exist for that match_value
	now = et_now_iso()
	seeded, skipped_seeds = [], []
	for mtype, mvalue, cat, subcat, prio, note in SEED_RULES:
		existing = cur.execute(
			"SELECT id FROM leak_rules WHERE match_value = ? AND match_type = ?",
			(mvalue, mtype)
		).fetchone()
		if existing:
			skipped_seeds.append(f'{mvalue} ({mtype} → {cat})')
			continue
		cur.execute("""
			INSERT INTO leak_rules (
				match_type, match_value, category, subcategory, priority,
				active, note, created, updated
			) VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?)
		""", (mtype, mvalue, cat, subcat, prio, note, now, now))
		seeded.append(f'{mvalue} ({mtype} → {cat})')

	conn.commit()
	conn.close()

	print()
	print("Migration: migrate_add_leak_hunt.py")
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
	print()
	if seeded:
		print(f"✓ Seeded rules ({len(seeded)}):")
		for s in seeded:
			print(f"    + {s}")
	if skipped_seeds:
		print(f"— Rules already present ({len(skipped_seeds)}):")
		for s in skipped_seeds:
			print(f"    · {s}")
	if not added and not seeded:
		print("No changes — schema and seed already up to date.")
	print()


if __name__ == '__main__':
	run()
