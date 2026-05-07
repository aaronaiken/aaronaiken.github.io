"""
migrate_add_ticket_category.py
Tickets feature follow-on — see .kt/spec-tickets.md.

What it does (idempotent):

  + tickets.time_category_id   INTEGER  -- FK time_categories(id), ON DELETE SET NULL

Aaron flagged that tasks / items / tickets should carry a default time
category that propagates to the timer's category when starting from the
source. This migration ships the ticket half (tasks + items can land later
without further rework — same column shape).

Server-side propagation: blueprints/time_tracking.py:time_start, when
given a ticket_id but no explicit time_category_id, looks up the ticket's
category and applies it. The user can still override by passing a category
explicitly (panel picker, etc.).

Run from PythonAnywhere bash:
    cd /home/aaronaiken/status_update
    python migrate_add_ticket_category.py
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

	if column_exists(cur, 'tickets', 'time_category_id'):
		print("— tickets.time_category_id already in place — no changes")
	else:
		cur.execute(
			'ALTER TABLE tickets ADD COLUMN time_category_id INTEGER '
			'REFERENCES time_categories(id) ON DELETE SET NULL'
		)
		conn.commit()
		print("✓ Added: tickets.time_category_id")

	conn.close()


if __name__ == '__main__':
	run()
