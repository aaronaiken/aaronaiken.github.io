"""
migrate_add_mileage.py
Phase 3 of the time-tracking spec — see .kt/spec-phase-3-mileage.md.

What it does (idempotent — safe to run multiple times):

  + mileage_entries table:
      id              INTEGER PRIMARY KEY AUTOINCREMENT
      project_id      INTEGER REFERENCES projects(id) ON DELETE SET NULL
                                       -- nullable; v1 UI requires, future
                                       -- personal trips can leave NULL
      date            TEXT NOT NULL    -- ISO YYYY-MM-DD (ET-local day)
      description     TEXT
      from_location   TEXT
      to_location     TEXT
      round_trip      INTEGER NOT NULL DEFAULT 0
      odometer_start  REAL
      odometer_end    REAL
      miles           REAL NOT NULL    -- canonical; form calculates, server stores
      rate_cents      INTEGER NOT NULL -- snapshot from settings at entry time
      vehicle         TEXT NOT NULL DEFAULT 'a'
      notes           TEXT
      submitted_at    TEXT             -- ISO datetime; NULL = pending reimbursement
      created         TEXT NOT NULL
      updated         TEXT NOT NULL

  + settings.default_mileage_project_id   INTEGER REFERENCES projects(id) ON DELETE SET NULL
                                          -- which project the mileage form pre-selects

  + indexes:
      idx_mileage_project          mileage_entries(project_id)
      idx_mileage_date             mileage_entries(date)
      idx_mileage_unsubmitted      mileage_entries(submitted_at)
                                       WHERE submitted_at IS NULL

  The unsubmitted partial index supports the "what haven't I submitted
  yet" query, which is the dashboard's primary mileage signal — Aaron
  reviews this monthly to catch up on reimbursements.

Cascade:
  - project delete  → mileage_entries.project_id = NULL  (entry survives;
                       it's a financial record, can't lose it just because
                       a project got cleaned up)

Prints a summary. Running it again prints "no changes."

Run from PythonAnywhere bash:
    cd /home/aaronaiken/status_update
    python migrate_add_mileage.py
"""

import os
import sqlite3

DB_FILE = os.path.join(
	os.environ.get('COCKPIT_REPO_ROOT', '/home/aaronaiken/status_update'),
	'assets/data/command_deck.db'
)


def table_exists(cur, name):
	row = cur.execute(
		"SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,)
	).fetchone()
	return row is not None


def column_exists(cur, table, col):
	cols = [row[1] for row in cur.execute(f"PRAGMA table_info({table})").fetchall()]
	return col in cols


def index_exists(cur, name):
	row = cur.execute(
		"SELECT name FROM sqlite_master WHERE type='index' AND name=?", (name,)
	).fetchone()
	return row is not None


CREATE_MILEAGE_SQL = """
CREATE TABLE mileage_entries (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id      INTEGER REFERENCES projects(id) ON DELETE SET NULL,
    date            TEXT NOT NULL,
    description     TEXT,
    from_location   TEXT,
    to_location     TEXT,
    round_trip      INTEGER NOT NULL DEFAULT 0,
    odometer_start  REAL,
    odometer_end    REAL,
    miles           REAL NOT NULL,
    rate_cents      INTEGER NOT NULL,
    vehicle         TEXT NOT NULL DEFAULT 'a',
    notes           TEXT,
    submitted_at    TEXT,
    created         TEXT NOT NULL,
    updated         TEXT NOT NULL
)
"""

COLUMNS = [
	('settings', 'default_mileage_project_id',
	 'INTEGER REFERENCES projects(id) ON DELETE SET NULL'),
]

INDEXES = [
	(
		'idx_mileage_project',
		'CREATE INDEX IF NOT EXISTS idx_mileage_project ON mileage_entries(project_id)',
	),
	(
		'idx_mileage_date',
		'CREATE INDEX IF NOT EXISTS idx_mileage_date ON mileage_entries(date)',
	),
	(
		'idx_mileage_unsubmitted',
		'CREATE INDEX IF NOT EXISTS idx_mileage_unsubmitted '
		'ON mileage_entries(submitted_at) WHERE submitted_at IS NULL',
	),
]


def run():
	if not os.path.exists(DB_FILE):
		print(f"× DB not found at {DB_FILE}")
		print("  Run migrate_to_sqlite.py first.")
		return

	conn = sqlite3.connect(DB_FILE)
	cur = conn.cursor()

	added = []
	skipped = []

	if table_exists(cur, 'mileage_entries'):
		skipped.append('mileage_entries (table)')
	else:
		cur.execute(CREATE_MILEAGE_SQL)
		added.append('mileage_entries (table)')

	for table, col, sql_type in COLUMNS:
		if column_exists(cur, table, col):
			skipped.append(f'{table}.{col}')
		else:
			cur.execute(f'ALTER TABLE {table} ADD COLUMN {col} {sql_type}')
			added.append(f'{table}.{col}')

	for name, sql in INDEXES:
		if index_exists(cur, name):
			skipped.append(name)
		else:
			cur.execute(sql)
			added.append(name)

	conn.commit()
	conn.close()

	print()
	print("Migration: migrate_add_mileage.py")
	print(f"DB:        {DB_FILE}")
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
