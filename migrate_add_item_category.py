"""
migrate_add_item_category.py
Adds item-level default time category, mirroring tasks.time_category_id
(2026-05-26 migration). Timers started against a checklist item inherit
the item's default category if the caller doesn't pass one explicitly,
keeping the Category column on time reports populated automatically.

  checklist_items:
    + time_category_id  INTEGER  REFERENCES time_categories(id)
                                 ON DELETE SET NULL

Idempotent — safe to re-run.

Run on PythonAnywhere:
    cd /home/aaronaiken/status_update
    python migrate_add_item_category.py
"""

import os
import sqlite3

DB_FILE = os.path.join(
	os.environ.get('COCKPIT_REPO_ROOT', '/home/aaronaiken/status_update'),
	'assets/data/command_deck.db'
)


def column_exists(cur, table, col):
	cols = [r[1] for r in cur.execute(f"PRAGMA table_info({table})").fetchall()]
	return col in cols


def run():
	if not os.path.exists(DB_FILE):
		print(f"× DB not found at {DB_FILE}")
		return
	conn = sqlite3.connect(DB_FILE)
	cur = conn.cursor()
	if column_exists(cur, 'checklist_items', 'time_category_id'):
		print('— checklist_items.time_category_id already in place — no changes')
	else:
		cur.execute(
			'ALTER TABLE checklist_items ADD COLUMN time_category_id INTEGER '
			'REFERENCES time_categories(id) ON DELETE SET NULL'
		)
		print('✓ Added: checklist_items.time_category_id')
	conn.commit()
	conn.close()


if __name__ == '__main__':
	run()
