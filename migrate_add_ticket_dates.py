"""
migrate_add_ticket_dates.py
Adds two ISO YYYY-MM-DD date fields to tickets so they carry the full
intake → resolution timeline:

  tickets:
    + requested_date  TEXT     -- when the request actually came in
                                  (may differ from `created` if Aaron is
                                  catching up on a backlog)
    + due_date        TEXT     -- when the customer expects it back

`tickets.created` and `tickets.closed_date` already exist. With these two
added, tickets carry: created → requested → due → closed.

Idempotent — safe to run multiple times. Also creates a partial index on
due_date so the today-view sort doesn't full-scan once tickets grow.

Run from PythonAnywhere bash:
    cd /home/aaronaiken/status_update
    python migrate_add_ticket_dates.py
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
	('tickets', 'requested_date', 'TEXT'),
	('tickets', 'due_date',       'TEXT'),
]

INDEXES = [
	(
		'idx_tickets_due_date',
		'CREATE INDEX IF NOT EXISTS idx_tickets_due_date '
		'ON tickets(due_date) WHERE due_date IS NOT NULL',
	),
]


def run():
	if not os.path.exists(DB_FILE):
		print(f"× DB not found at {DB_FILE}")
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
	print("Migration: migrate_add_ticket_dates.py")
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
