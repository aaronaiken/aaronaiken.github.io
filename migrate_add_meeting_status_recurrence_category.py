"""
migrate_add_meeting_status_recurrence_category.py
Adds status, recurrence chain, and default time-category to meetings.

  meetings:
    + status                TEXT  -- 'scheduled' | 'complete' | 'canceled' | 'no_show'
                                  -- existing rows backfilled to 'scheduled'
    + recurrence            TEXT  -- NULL | 'weekly' | 'biweekly' | 'monthly'
    + recurrence_anchor_id  INTEGER REFERENCES meetings(id) ON DELETE SET NULL
                                  -- points at the first meeting in the series;
                                  -- spawned instances copy the anchor's id
                                  -- (self-referential on the original)
    + time_category_id      INTEGER REFERENCES time_categories(id)
                                  ON DELETE SET NULL
                                  -- default category propagated to timers
                                  -- started against this meeting (mirrors
                                  -- tasks.time_category_id, tickets.time_category_id)

  + indexes:
    idx_meetings_status   meetings(status)
    idx_meetings_anchor   meetings(recurrence_anchor_id)
                              WHERE recurrence_anchor_id IS NOT NULL

Idempotent — safe to run multiple times.

Run on PythonAnywhere:
    cd /home/aaronaiken/status_update
    python migrate_add_meeting_status_recurrence_category.py
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
	('meetings', 'status',               "TEXT NOT NULL DEFAULT 'scheduled'"),
	('meetings', 'recurrence',           'TEXT'),
	('meetings', 'recurrence_anchor_id', 'INTEGER REFERENCES meetings(id) ON DELETE SET NULL'),
	('meetings', 'time_category_id',     'INTEGER REFERENCES time_categories(id) ON DELETE SET NULL'),
]

INDEXES = [
	(
		'idx_meetings_status',
		'CREATE INDEX IF NOT EXISTS idx_meetings_status ON meetings(status)',
	),
	(
		'idx_meetings_anchor',
		'CREATE INDEX IF NOT EXISTS idx_meetings_anchor '
		'ON meetings(recurrence_anchor_id) WHERE recurrence_anchor_id IS NOT NULL',
	),
]


def run():
	if not os.path.exists(DB_FILE):
		print(f"× DB not found at {DB_FILE}")
		print("  Run migrate_to_sqlite.py and migrate_add_meetings.py first.")
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

	# Belt-and-suspenders backfill: SQLite's DEFAULT applies to new INSERTs and
	# to existing rows when the column is added with a NOT NULL DEFAULT, but
	# guard against ALTERed rows that somehow ended up NULL.
	cur.execute("UPDATE meetings SET status = 'scheduled' WHERE status IS NULL")

	for name, sql in INDEXES:
		if index_exists(cur, name):
			skipped.append(name)
		else:
			cur.execute(sql)
			added.append(name)

	conn.commit()
	conn.close()

	print()
	print("Migration: migrate_add_meeting_status_recurrence_category.py")
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
