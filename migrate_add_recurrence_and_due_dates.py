"""
migrate_add_recurrence_and_due_dates.py
Phase 2.4 of the time-tracking spec — see .kt/spec-time-tracking-phase-2-4.md.

What it does (idempotent — safe to run multiple times):

  blocks:
    + recurrence       TEXT     -- NULL | 'daily' | 'weekly' | 'monthly'
    + recurrence_days  TEXT     -- per-kind:
                                 --   'daily'   → comma-separated active weekdays
                                 --              (e.g. 'Mon,Tue,Wed,Thu,Fri'); NULL = all 7
                                 --   'weekly'  → single weekday this cycle is due
                                 --              (e.g. 'Fri')
                                 --   'monthly' → day-of-month string ('1','15','last')
    + last_reset_at    TEXT     -- ISO 8601 ET-local; NULL = never reset

  checklist_items:
    + due_date     TEXT          -- ISO YYYY-MM-DD; NULL = no due date
    + archived_at  TEXT          -- ISO 8601 ET-local; NULL = active

  tasks:
    + due_date     TEXT          -- ISO YYYY-MM-DD; NULL = no due date

  + 4 partial indexes:
    idx_blocks_recurrence            blocks(recurrence) WHERE recurrence IS NOT NULL
    idx_checklist_items_archived     checklist_items(archived_at) WHERE archived_at IS NOT NULL
    idx_checklist_items_due_date     checklist_items(due_date) WHERE due_date IS NOT NULL
    idx_tasks_due_date               tasks(due_date) WHERE due_date IS NOT NULL

The archive index also supports the future retention-cleanup query
(per Aaron's "keep ~1 year, then report-out + delete; lighter data
persists longer" policy — implementation deferred to a later phase).

Prints a summary. Running it again prints "no changes."

Run from PythonAnywhere bash:
    cd /home/aaronaiken/status_update
    python migrate_add_recurrence_and_due_dates.py
"""

import os
import sqlite3

DB_FILE = os.path.join(
	os.environ.get('COCKPIT_REPO_ROOT', '/home/aaronaiken/status_update'),
	'assets/data/command_deck.db'
)


def column_exists(cur, table, col):
	cols = [row[1] for row in cur.execute(f"PRAGMA table_info({table})").fetchall()]
	return col in cols


def index_exists(cur, name):
	row = cur.execute(
		"SELECT name FROM sqlite_master WHERE type='index' AND name=?", (name,)
	).fetchone()
	return row is not None


COLUMNS = [
	('blocks',          'recurrence',      'TEXT'),
	('blocks',          'recurrence_days', 'TEXT'),
	('blocks',          'last_reset_at',   'TEXT'),
	('checklist_items', 'due_date',        'TEXT'),
	('checklist_items', 'archived_at',     'TEXT'),
	('tasks',           'due_date',        'TEXT'),
]

INDEXES = [
	(
		'idx_blocks_recurrence',
		'CREATE INDEX IF NOT EXISTS idx_blocks_recurrence '
		'ON blocks(recurrence) WHERE recurrence IS NOT NULL',
	),
	(
		'idx_checklist_items_archived',
		'CREATE INDEX IF NOT EXISTS idx_checklist_items_archived '
		'ON checklist_items(archived_at) WHERE archived_at IS NOT NULL',
	),
	(
		'idx_checklist_items_due_date',
		'CREATE INDEX IF NOT EXISTS idx_checklist_items_due_date '
		'ON checklist_items(due_date) WHERE due_date IS NOT NULL',
	),
	(
		'idx_tasks_due_date',
		'CREATE INDEX IF NOT EXISTS idx_tasks_due_date '
		'ON tasks(due_date) WHERE due_date IS NOT NULL',
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
	print("Migration: migrate_add_recurrence_and_due_dates.py")
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
