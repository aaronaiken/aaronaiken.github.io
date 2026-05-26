"""
migrate_add_task_category.py
Adds task-level default time category, mirroring `tickets.time_category_id`.
Timer starts scoped to a task inherit the task's category if the caller
doesn't supply one explicitly, which keeps the Category column on time
reports populated without per-timer clicking.

  tasks:
    + time_category_id  INTEGER  REFERENCES time_categories(id)
                                 ON DELETE SET NULL

Idempotent — safe to run multiple times.

Run on PythonAnywhere:
    cd /home/aaronaiken/status_update
    python migrate_add_task_category.py
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
	if column_exists(cur, 'tasks', 'time_category_id'):
		print('— tasks.time_category_id already in place — no changes')
	else:
		# SQLite ALTER TABLE can't declare REFERENCES retroactively on an
		# existing column with the constraint in the column definition,
		# but it CAN add the column with a REFERENCES clause. Cascade
		# behavior is enforced by PRAGMA foreign_keys=ON in helpers/db.py.
		cur.execute(
			'ALTER TABLE tasks ADD COLUMN time_category_id INTEGER '
			'REFERENCES time_categories(id) ON DELETE SET NULL'
		)
		print('✓ Added: tasks.time_category_id')
	conn.commit()
	conn.close()


if __name__ == '__main__':
	run()
