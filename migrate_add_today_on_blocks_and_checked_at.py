"""
migrate_add_today_on_blocks_and_checked_at.py
Phase 2.2 of the time-tracking spec — see .kt/spec-time-tracking-phase-2-2.md.

What it does (idempotent — safe to run multiple times):

  - blocks.today INTEGER NOT NULL DEFAULT 0
      Block-level Today flag. A starred block renders as a peer in
      /today/ with progress (`3/8 done`). Mirrors tasks.today and
      checklist_items.today.

  - checklist_items.checked_at TEXT
      Stamps when an item was checked. ISO 8601 UTC with microseconds
      and Z suffix (matches time_entries.started_at convention).
      Replaces Phase 2.1's "clear every checked item past 4am"
      sloppiness with `checked_at < cutoff` precision.

  - Backfill on existing checked items:
      For checklist_items where checked = 1 AND checked_at IS NULL,
      copy the parent block's `created` timestamp into checked_at.
      Best-available proxy for "we don't know when this was checked,
      but it was sometime after the block existed." Future checks
      stamp accurately.

Companion to migrate_add_today_on_items.py (Phase 2.1, which added
checklist_items.today).

Prints a summary. Running it again prints "no changes."

Run from PythonAnywhere bash:
    cd /home/aaronaiken/status_update
    python migrate_add_today_on_blocks_and_checked_at.py
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
		print("  Run migrate_to_sqlite.py first.")
		return

	conn = sqlite3.connect(DB_FILE)
	cur = conn.cursor()

	for table in ('blocks', 'checklist_items'):
		exists = cur.execute(
			"SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
		).fetchone() is not None
		if not exists:
			print(f"× {table} table not found. Run migrate_to_sqlite.py first.")
			conn.close()
			return

	added = []
	skipped = []

	if column_exists(cur, 'blocks', 'today'):
		skipped.append('blocks.today')
	else:
		cur.execute("ALTER TABLE blocks ADD COLUMN today INTEGER NOT NULL DEFAULT 0")
		added.append('blocks.today')

	if column_exists(cur, 'checklist_items', 'checked_at'):
		skipped.append('checklist_items.checked_at')
	else:
		cur.execute("ALTER TABLE checklist_items ADD COLUMN checked_at TEXT")
		added.append('checklist_items.checked_at')

	# Backfill — only touches rows that need it. Idempotent: if the column
	# was just added the predicate matches every checked row; if the column
	# was already there from a prior run, the WHERE checked_at IS NULL
	# clause skips already-stamped rows.
	backfilled = cur.execute('''
		UPDATE checklist_items
		SET checked_at = (
			SELECT created FROM blocks WHERE blocks.id = checklist_items.block_id
		)
		WHERE checked = 1 AND checked_at IS NULL
	''').rowcount

	conn.commit()
	conn.close()

	print()
	print("Migration: migrate_add_today_on_blocks_and_checked_at.py")
	print(f"DB:        {DB_FILE}")
	print()
	if added:
		print(f"✓ Added ({len(added)}):")
		for item in added:
			print(f"    + {item}")
	if skipped:
		print(f"— Already in place ({len(skipped)}):")
		for item in skipped:
			print(f"    · {item}")
	if backfilled:
		print(f"✓ Backfilled checked_at on {backfilled} existing checked item(s)")
	if not added and not backfilled:
		print("No changes — schema already up to date.")
	print()


if __name__ == '__main__':
	run()
