"""
migrate_add_today_order.py
Adds a `today_order` column (INTEGER DEFAULT 0) to tasks, checklist_items,
blocks, and tickets — the manual sort position of an entity *within its My Day
segment*. Reordering a segment rewrites these to 0..n; entities never dragged
keep 0 and fall back to the due-date/id default ordering.

Safe to run multiple times — each column add is guarded.

Run from PythonAnywhere bash:
    cd /home/aaronaiken/status_update
    python migrate_add_today_order.py
"""

import sqlite3
import os

DB_FILE = os.path.join(
    os.environ.get('COCKPIT_REPO_ROOT', '/home/aaronaiken/status_update'),
    'assets/data/command_deck.db'
)

_ORDER_TABLES = ('tasks', 'checklist_items', 'blocks', 'tickets')


def run():
	conn = sqlite3.connect(DB_FILE)
	cursor = conn.cursor()
	for table in _ORDER_TABLES:
		cols = [row[1] for row in cursor.execute(f"PRAGMA table_info({table})").fetchall()]
		if 'today_order' in cols:
			print(f"  {table}.today_order already exists — skipping.")
			continue
		cursor.execute(f'ALTER TABLE {table} ADD COLUMN today_order INTEGER NOT NULL DEFAULT 0')
		print(f"  Added today_order to {table}.")
	conn.commit()
	conn.close()
	print("Done.")


if __name__ == '__main__':
	run()
