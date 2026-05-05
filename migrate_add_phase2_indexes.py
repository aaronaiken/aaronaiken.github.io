"""
migrate_add_phase2_indexes.py
Phase 2 of the time-tracking spec — see .kt/spec-time-tracking-phase-2.md.

What it does (idempotent — safe to run multiple times):

  - idx_time_entries_project_started — composite (project_id, started_at).
    Reports queries filter by project + date range and sort by started_at;
    this covers all three predicates.

  - idx_time_entries_task — partial index on task_id WHERE NOT NULL.
    Backs the per-task lifetime SUM(duration_seconds) on the project page.

  - idx_time_entries_checklist_item — partial index on checklist_item_id
    WHERE NOT NULL. Same purpose, item scope.

The two partial indexes are deliberately partial: most time entries don't
have a task or item assignment (project-scoped only), so a full index
would waste space and slow writes for no read benefit.

Prints a summary. Running it again prints "no changes."

Run from PythonAnywhere bash:
    cd /home/aaronaiken/status_update
    python migrate_add_phase2_indexes.py
"""

import os
import sqlite3

DB_FILE = os.path.join(
	os.environ.get('COCKPIT_REPO_ROOT', '/home/aaronaiken/status_update'),
	'assets/data/command_deck.db'
)


INDEXES = [
	(
		'idx_time_entries_project_started',
		'CREATE INDEX IF NOT EXISTS idx_time_entries_project_started '
		'ON time_entries(project_id, started_at)',
	),
	(
		'idx_time_entries_task',
		'CREATE INDEX IF NOT EXISTS idx_time_entries_task '
		'ON time_entries(task_id) WHERE task_id IS NOT NULL',
	),
	(
		'idx_time_entries_checklist_item',
		'CREATE INDEX IF NOT EXISTS idx_time_entries_checklist_item '
		'ON time_entries(checklist_item_id) WHERE checklist_item_id IS NOT NULL',
	),
]


def existing_indexes(cur, table):
	rows = cur.execute(f"PRAGMA index_list({table})").fetchall()
	return {row[1] for row in rows}


def run():
	if not os.path.exists(DB_FILE):
		print(f"× DB not found at {DB_FILE}")
		print("  Run migrate_to_sqlite.py first.")
		return

	conn = sqlite3.connect(DB_FILE)
	cur = conn.cursor()

	te_exists = cur.execute(
		"SELECT name FROM sqlite_master WHERE type='table' AND name='time_entries'"
	).fetchone() is not None
	if not te_exists:
		print("× time_entries table not found. Run migrate_add_time_tracking.py first.")
		conn.close()
		return

	have = existing_indexes(cur, 'time_entries')
	added = []
	skipped = []

	for name, sql in INDEXES:
		if name in have:
			skipped.append(name)
		else:
			cur.execute(sql)
			added.append(name)

	conn.commit()
	conn.close()

	print()
	print("Migration: migrate_add_phase2_indexes.py")
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
