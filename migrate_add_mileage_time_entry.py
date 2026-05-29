"""
migrate_add_mileage_time_entry.py
Links mileage entries to time-tracking entries.

When Aaron starts a trip on the phone, the Cockpit can simultaneously kick
off a time_entries row scoped to the trip's project. This migration adds
the join column.

  mileage_entries:
    + time_entry_id   INTEGER  REFERENCES time_entries(id)
                               ON DELETE SET NULL
                               -- nullable: trips logged after the fact
                               -- (LOG FULL TRIP) won't have one

Idempotent — safe to run multiple times.

Run on PythonAnywhere:
    cd /home/aaronaiken/status_update
    python migrate_add_mileage_time_entry.py
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
	if column_exists(cur, 'mileage_entries', 'time_entry_id'):
		print('— mileage_entries.time_entry_id already in place — no changes')
	else:
		cur.execute(
			'ALTER TABLE mileage_entries ADD COLUMN time_entry_id INTEGER '
			'REFERENCES time_entries(id) ON DELETE SET NULL'
		)
		print('✓ Added: mileage_entries.time_entry_id')
	conn.commit()
	conn.close()


if __name__ == '__main__':
	run()
