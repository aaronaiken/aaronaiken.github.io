"""
migrate_add_group_default_project.py
Tickets follow-on — see .kt/spec-tickets.md.

What it does (idempotent):

  + customer_groups.default_project_id   INTEGER
                                          REFERENCES projects(id)
                                          ON DELETE SET NULL

When a customer group has a default project set, the new-ticket modal
auto-fills the project field as soon as the group is picked (or
auto-filled from a chosen customer). Removes one tap on the most common
ticket flow — Corp / PennDOT / FDOT each route to their own support
sub-project automatically. Not auto-filled on edit (explicit only).

Set the default per group via /command-deck/settings/.

Run from PythonAnywhere bash:
    cd /home/aaronaiken/status_update
    python migrate_add_group_default_project.py
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
	if column_exists(cur, 'customer_groups', 'default_project_id'):
		print("— customer_groups.default_project_id already in place — no changes")
	else:
		cur.execute(
			'ALTER TABLE customer_groups ADD COLUMN default_project_id INTEGER '
			'REFERENCES projects(id) ON DELETE SET NULL'
		)
		conn.commit()
		print("✓ Added: customer_groups.default_project_id")
	conn.close()


if __name__ == '__main__':
	run()
