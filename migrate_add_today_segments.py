"""
migrate_add_today_segments.py
Adds the `today_segments` table (persistent, user-defined parts of the day)
and a nullable `today_segment_id` column on tasks, checklist_items, blocks,
and tickets (NULL = unassigned / "Unassigned" bucket in the My Day view).

Safe to run multiple times — each step is guarded and skips if already applied.

Run from PythonAnywhere bash:
    cd /home/aaronaiken/status_update
    python migrate_add_today_segments.py
"""

import sqlite3
import os

DB_FILE = os.path.join(
    os.environ.get('COCKPIT_REPO_ROOT', '/home/aaronaiken/status_update'),
    'assets/data/command_deck.db'
)

# Tables that gain a today_segment_id FK to today_segments.
_SEGMENT_TABLES = ('tasks', 'checklist_items', 'blocks', 'tickets')


def run():
	conn = sqlite3.connect(DB_FILE)
	cursor = conn.cursor()

	# 1. today_segments table — persistent named parts of the day.
	cursor.execute('''
		CREATE TABLE IF NOT EXISTS today_segments (
			id         INTEGER PRIMARY KEY AUTOINCREMENT,
			title      TEXT NOT NULL,
			"order"    INTEGER NOT NULL DEFAULT 0,
			created_at TEXT
		)
	''')
	print("today_segments table ready.")

	# 2. today_segment_id column on each Today-citizen table.
	for table in _SEGMENT_TABLES:
		cols = [row[1] for row in cursor.execute(f"PRAGMA table_info({table})").fetchall()]
		if 'today_segment_id' in cols:
			print(f"  {table}.today_segment_id already exists — skipping.")
			continue
		cursor.execute(f'ALTER TABLE {table} ADD COLUMN today_segment_id INTEGER')
		print(f"  Added today_segment_id to {table}.")

	conn.commit()
	conn.close()
	print("Done.")


if __name__ == '__main__':
	run()
