"""
migrate_add_today.py
Adds `today` column (INTEGER DEFAULT 0) to the tasks table.
Safe to run multiple times — skips if column already exists.

Run from PythonAnywhere bash:
    cd /home/aaronaiken/status_update
    python migrate_add_today.py
"""

import sqlite3
import os

DB_FILE = os.path.join('/home/aaronaiken/status_update', 'assets/data/command_deck.db')

def run():
	conn = sqlite3.connect(DB_FILE)
	cursor = conn.cursor()

	# Check if column already exists
	cols = [row[1] for row in cursor.execute("PRAGMA table_info(tasks)").fetchall()]
	if 'today' in cols:
		print("Column 'today' already exists — nothing to do.")
		conn.close()
		return

	cursor.execute("ALTER TABLE tasks ADD COLUMN today INTEGER NOT NULL DEFAULT 0")
	conn.commit()
	conn.close()
	print("Done — 'today' column added to tasks table.")

if __name__ == '__main__':
	run()