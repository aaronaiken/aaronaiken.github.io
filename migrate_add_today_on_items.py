"""
migrate_add_today_on_items.py
Phase 2.1 of the time-tracking spec — see .kt/spec-time-tracking-phase-2-1.md.

What it does (idempotent — safe to run multiple times):
  - Adds checklist_items.today INTEGER NOT NULL DEFAULT 0.
    Same semantics as tasks.today: 1 = item appears in the Today list,
    0 = does not. Cleared by manual unstar OR by the 4am ET autoclear
    pass on checked items.

Companion to migrate_add_today.py (which added the column on tasks).
Phase 2.1 elevates checklist items to first-class Today citizens —
this column is the schema piece that makes that possible.

Prints a summary. Running it again prints "no changes."

Run from PythonAnywhere bash:
    cd /home/aaronaiken/status_update
    python migrate_add_today_on_items.py
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


def run():
	if not os.path.exists(DB_FILE):
		print(f"× DB not found at {DB_FILE}")
		print("  Run migrate_to_sqlite.py first.")
		return

	conn = sqlite3.connect(DB_FILE)
	cur = conn.cursor()

	ci_exists = cur.execute(
		"SELECT name FROM sqlite_master WHERE type='table' AND name='checklist_items'"
	).fetchone() is not None
	if not ci_exists:
		print("× checklist_items table not found. Run migrate_to_sqlite.py first.")
		conn.close()
		return

	added = []
	skipped = []

	if column_exists(cur, 'checklist_items', 'today'):
		skipped.append('checklist_items.today')
	else:
		cur.execute("ALTER TABLE checklist_items ADD COLUMN today INTEGER NOT NULL DEFAULT 0")
		added.append('checklist_items.today')

	conn.commit()
	conn.close()

	print()
	print("Migration: migrate_add_today_on_items.py")
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
