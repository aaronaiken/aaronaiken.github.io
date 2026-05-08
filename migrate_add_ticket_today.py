"""
migrate_add_ticket_today.py
Tickets follow-on — see .kt/spec-tickets.md.

What it does (idempotent):

  + tickets.today   INTEGER NOT NULL DEFAULT 0

Lets a ticket be ★-ed for Today the same way tasks / items / blocks
already can. /today/data picks up starred non-closed tickets in
today_open + closed-and-starred ones in today_done; autoclear
clears the flag when a ticket has been closed past the 4am ET cutoff.

Run from PythonAnywhere bash:
    cd /home/aaronaiken/status_update
    python migrate_add_ticket_today.py
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
	if column_exists(cur, 'tickets', 'today'):
		print("— tickets.today already in place — no changes")
	else:
		cur.execute(
			'ALTER TABLE tickets ADD COLUMN today INTEGER NOT NULL DEFAULT 0'
		)
		conn.commit()
		print("✓ Added: tickets.today")
	conn.close()


if __name__ == '__main__':
	run()
