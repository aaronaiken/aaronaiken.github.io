"""
migrate_add_checklist_item_order.py
Adds `"order"` column to checklist_items so items can be drag-reordered
within a block (parallels the existing blocks."order" pattern).

  checklist_items:
    + "order"  INTEGER NOT NULL DEFAULT 0

Default 0 means all existing items sort by id-ASC as a tiebreaker (same
behavior as before this migration). The first time a block is reordered,
all items in that block get explicit `"order"` values written by the
reorder endpoint.

Idempotent — safe to run multiple times.

Run from PythonAnywhere bash:
    cd /home/aaronaiken/status_update
    python migrate_add_checklist_item_order.py
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
	added = []
	if column_exists(cur, 'checklist_items', 'order'):
		print('— checklist_items."order" already in place — no changes')
	else:
		cur.execute('ALTER TABLE checklist_items ADD COLUMN "order" INTEGER NOT NULL DEFAULT 0')
		added.append('checklist_items."order"')
	conn.commit()
	conn.close()
	print()
	print('Migration: migrate_add_checklist_item_order.py')
	print(f'DB:        {DB_FILE}')
	if added:
		print(f'✓ Added ({len(added)}):')
		for x in added: print(f'    + {x}')
	print()


if __name__ == '__main__':
	run()
