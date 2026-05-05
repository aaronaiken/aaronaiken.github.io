"""
migrate_add_templates.py
Phase 2.3 of the time-tracking spec — see .kt/spec-time-tracking-phase-2-3.md.

What it does (idempotent — safe to run multiple times):

  - templates table:
      id          INTEGER PRIMARY KEY AUTOINCREMENT
      kind        TEXT NOT NULL CHECK(kind IN ('project', 'checklist'))
      name        TEXT NOT NULL
      description TEXT
      body_json   TEXT NOT NULL    -- JSON: blocks/items/tasks for project
                                    -- kind, items for checklist kind
      created     TEXT NOT NULL
      updated     TEXT NOT NULL

  - idx_templates_kind on templates(kind) — supports the
    GET /command-deck/templates/list?kind=… picker queries.

Single-table design: templates aren't queried granularly. The body
is read whole at spawn time + parsed in app code. JSON in a TEXT
column buys us schema flexibility (variants of project vs checklist
body shapes) without 5 tables. Per spec §1 Decision #1.

Prints a summary. Running it again prints "no changes."

Run from PythonAnywhere bash:
    cd /home/aaronaiken/status_update
    python migrate_add_templates.py
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


def index_exists(cur, name):
	row = cur.execute(
		"SELECT name FROM sqlite_master WHERE type='index' AND name=?", (name,)
	).fetchone()
	return row is not None


def run():
	if not os.path.exists(DB_FILE):
		print(f"× DB not found at {DB_FILE}")
		print("  Run migrate_to_sqlite.py first.")
		return

	conn = sqlite3.connect(DB_FILE)
	cur = conn.cursor()

	added = []
	skipped = []

	if table_exists(cur, 'templates'):
		skipped.append('templates table')
	else:
		cur.execute('''
			CREATE TABLE templates (
				id          INTEGER PRIMARY KEY AUTOINCREMENT,
				kind        TEXT NOT NULL CHECK(kind IN ('project', 'checklist')),
				name        TEXT NOT NULL,
				description TEXT,
				body_json   TEXT NOT NULL,
				created     TEXT NOT NULL,
				updated     TEXT NOT NULL
			)
		''')
		added.append('templates table')

	if index_exists(cur, 'idx_templates_kind'):
		skipped.append('idx_templates_kind')
	else:
		cur.execute('CREATE INDEX idx_templates_kind ON templates(kind)')
		added.append('idx_templates_kind')

	conn.commit()
	conn.close()

	print()
	print("Migration: migrate_add_templates.py")
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
