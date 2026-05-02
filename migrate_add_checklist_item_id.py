"""
migrate_add_checklist_item_id.py
Phase 1.5 of the time-tracking spec — see .kt/spec-time-tracking-phase-1-5.md.

What it does (idempotent — safe to run multiple times):
  - Adds checklist_item_id INTEGER NULL column to time_entries.

Schema rule (enforced in application logic, not in DB):
  At most one of (task_id, checklist_item_id) is set on a given entry.

Prints a summary of what was added vs. what was already in place.
Running it again prints "no changes."

Run from PythonAnywhere bash:
    cd /home/aaronaiken/status_update
    python migrate_add_checklist_item_id.py
"""

import sqlite3
import os

DB_FILE = os.path.join(
	os.environ.get('COCKPIT_REPO_ROOT', '/home/aaronaiken/status_update'),
	'assets/data/command_deck.db'
)


def column_exists(cur, table, col):
	cols = [row[1] for row in cur.execute(f"PRAGMA table_info({table})").fetchall()]
	return col in cols


def run():
	if not os.path.exists(DB_FILE):
		print(f"× DB not found at {DB_FILE}")
		print("  Run migrate_to_sqlite.py first.")
		return

	conn = sqlite3.connect(DB_FILE)
	cur = conn.cursor()

	# Guard: time_entries must exist (Phase 1 prerequisite)
	te_exists = cur.execute(
		"SELECT name FROM sqlite_master WHERE type='table' AND name='time_entries'"
	).fetchone() is not None
	if not te_exists:
		print("× time_entries table not found. Run migrate_add_time_tracking.py first.")
		conn.close()
		return

	added = []
	skipped = []

	if column_exists(cur, 'time_entries', 'checklist_item_id'):
		skipped.append('time_entries.checklist_item_id')
	else:
		cur.execute("ALTER TABLE time_entries ADD COLUMN checklist_item_id INTEGER")
		added.append('time_entries.checklist_item_id')

	conn.commit()
	conn.close()

	print()
	print(f"Migration: migrate_add_checklist_item_id.py")
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
