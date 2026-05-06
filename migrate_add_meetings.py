"""
migrate_add_meetings.py
Phase 5 of the Command Deck spec — see .kt/spec-phase-5-meetings.md.

What it does (idempotent — safe to run multiple times):

  + meetings table:
        id            INTEGER PRIMARY KEY AUTOINCREMENT
        project_id    INTEGER REFERENCES projects(id) ON DELETE SET NULL
        title         TEXT NOT NULL
        meeting_date  TEXT NOT NULL          -- ISO 8601 ET-local with offset
        notes         TEXT                   -- markdown source
        created       TEXT NOT NULL
        updated       TEXT NOT NULL

  + tasks.meeting_id          INTEGER  -- FK meetings(id), ON DELETE SET NULL
  + time_entries.meeting_id   INTEGER  -- FK meetings(id), ON DELETE SET NULL
                                       -- mutually exclusive with task_id /
                                       -- checklist_item_id; project_id of
                                       -- the entry must equal meeting.project_id

  + indexes:
    idx_meetings_project       meetings(project_id)
    idx_meetings_date          meetings(meeting_date)
    idx_tasks_meeting          tasks(meeting_id)
                                  WHERE meeting_id IS NOT NULL
    idx_time_entries_meeting   time_entries(meeting_id)
                                  WHERE meeting_id IS NOT NULL

Cascade rules:
  - project delete  → meetings.project_id          = NULL  (meetings go standalone)
  - meeting delete  → tasks.meeting_id             = NULL  (tasks survive)
  - meeting delete  → time_entries.meeting_id      = NULL  (entries survive,
                                                            keep their project_id
                                                            + duration)

Prints a summary. Running it again prints "no changes."

Run from PythonAnywhere bash:
    cd /home/aaronaiken/status_update
    python migrate_add_meetings.py
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


CREATE_MEETINGS_SQL = """
CREATE TABLE meetings (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id   INTEGER REFERENCES projects(id) ON DELETE SET NULL,
    title        TEXT NOT NULL,
    meeting_date TEXT NOT NULL,
    notes        TEXT,
    created      TEXT NOT NULL,
    updated      TEXT NOT NULL
)
"""

COLUMNS = [
	('tasks',        'meeting_id', 'INTEGER REFERENCES meetings(id) ON DELETE SET NULL'),
	('time_entries', 'meeting_id', 'INTEGER REFERENCES meetings(id) ON DELETE SET NULL'),
]

INDEXES = [
	(
		'idx_meetings_project',
		'CREATE INDEX IF NOT EXISTS idx_meetings_project ON meetings(project_id)',
	),
	(
		'idx_meetings_date',
		'CREATE INDEX IF NOT EXISTS idx_meetings_date ON meetings(meeting_date)',
	),
	(
		'idx_tasks_meeting',
		'CREATE INDEX IF NOT EXISTS idx_tasks_meeting '
		'ON tasks(meeting_id) WHERE meeting_id IS NOT NULL',
	),
	(
		'idx_time_entries_meeting',
		'CREATE INDEX IF NOT EXISTS idx_time_entries_meeting '
		'ON time_entries(meeting_id) WHERE meeting_id IS NOT NULL',
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

	if table_exists(cur, 'meetings'):
		skipped.append('meetings (table)')
	else:
		cur.execute(CREATE_MEETINGS_SQL)
		added.append('meetings (table)')

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
	print("Migration: migrate_add_meetings.py")
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
