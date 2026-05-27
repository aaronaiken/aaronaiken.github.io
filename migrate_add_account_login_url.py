"""
migrate_add_account_login_url.py
Phase 3.5 of The Ledger — bank/creditor login link per account.

Adds accounts.login_url TEXT. Drives the "Open Nordstrom →" buttons on
the snapshot-all page so the payday-sweep workflow doesn't require
re-finding URLs each time.

Idempotent — safe to re-run.

Run from PythonAnywhere bash:
    cd /home/aaronaiken/status_update
    python migrate_add_account_login_url.py
"""

import os
import sqlite3


LEDGER_DB_FILE = os.path.join(
	os.environ.get('COCKPIT_REPO_ROOT', '/home/aaronaiken/status_update'),
	'assets/data/ledger.db'
)


def column_exists(cur, table, col):
	cols = [r[1] for r in cur.execute(f"PRAGMA table_info({table})").fetchall()]
	return col in cols


def run():
	if not os.path.exists(LEDGER_DB_FILE):
		print(f"× Ledger DB not found at {LEDGER_DB_FILE}")
		return

	conn = sqlite3.connect(LEDGER_DB_FILE)
	conn.execute("PRAGMA journal_mode = DELETE")
	cur = conn.cursor()

	if column_exists(cur, 'accounts', 'login_url'):
		print()
		print("Migration: migrate_add_account_login_url.py")
		print(f"DB:        {LEDGER_DB_FILE}")
		print("— accounts.login_url already present.")
		print()
	else:
		cur.execute("ALTER TABLE accounts ADD COLUMN login_url TEXT")
		conn.commit()
		print()
		print("Migration: migrate_add_account_login_url.py")
		print(f"DB:        {LEDGER_DB_FILE}")
		print("✓ Added accounts.login_url")
		print()

	conn.close()


if __name__ == '__main__':
	run()
