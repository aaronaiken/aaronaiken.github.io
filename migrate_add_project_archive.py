"""
migrate_add_project_archive.py
Project archive — soft-delete pattern.

What it does (idempotent):

  + projects.archived_at   TEXT   -- ISO 8601 ET-local datetime; NULL = active

Archived projects:
  - Hide from active views by default (dashboard, projects list, area pages,
    project pickers everywhere — tickets / meetings / mileage / time tracking).
  - Time entries continue to surface in reports — that's the whole point.
    Your timesheet history stays intact while the project clears out of the
    workspace.
  - Are reachable via the projects page's "Show archived" toggle, where a
    one-click UNARCHIVE button restores them.

Hard-delete still exists; archive is the gentler primary action. If a
project ever does get hard-deleted, time_entries currently CASCADE — that
question is deferred until Aaron actually wants to use hard-delete on a
project with history.

Run from PythonAnywhere bash:
    cd /home/aaronaiken/status_update
    python migrate_add_project_archive.py
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
		return
	conn = sqlite3.connect(DB_FILE)
	cur = conn.cursor()
	if column_exists(cur, 'projects', 'archived_at'):
		print("— projects.archived_at already in place — no changes")
	else:
		cur.execute('ALTER TABLE projects ADD COLUMN archived_at TEXT')
		conn.commit()
		print("✓ Added: projects.archived_at")
	conn.close()


if __name__ == '__main__':
	run()
