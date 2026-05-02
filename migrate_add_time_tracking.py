"""
migrate_add_time_tracking.py
Phase 1 of the time-tracking spec — see .kt/spec-time-tracking-phase-1.md.

What it does (idempotent — safe to run multiple times):
  1. Adds 5 columns to projects: project_type, parent_project_id,
     tracking_enabled, is_favorite, area_color
  2. Creates time_entries table (with task_id insurance col per §0a.2 #1)
     plus three indexes incl. partial active-entry index
  3. Creates settings table + seeds the single row (id=1, defaults)
  4. Adds 'mode' column to chat_messages (per §0a.2 #5)
  5. Seeds the three Work Areas (Corporate, PennDOT, FDOT) with the
     locked area colors from §0a.3

Prints a clear summary of what was added vs. what was already in place.
Running it again prints "no changes."

Run from PythonAnywhere bash:
    cd /home/aaronaiken/status_update
    python migrate_add_time_tracking.py
"""

import sqlite3
import os
from datetime import datetime
import pytz

DB_FILE = os.path.join(
	os.environ.get('COCKPIT_REPO_ROOT', '/home/aaronaiken/status_update'),
	'assets/data/command_deck.db'
)

# Locked area colors per .kt/spec-time-tracking-phase-1.md §0a.3
WORK_AREAS = [
	{'title': 'Corporate', 'slug': 'corporate', 'area_color': '#5b7a99'},
	{'title': 'PennDOT',   'slug': 'penndot',   'area_color': '#1f3a5f'},
	{'title': 'FDOT',      'slug': 'fdot',      'area_color': '#e07050'},
]

PROJECTS_NEW_COLS = [
	('project_type',      "TEXT NOT NULL DEFAULT 'personal'"),
	('parent_project_id', "INTEGER REFERENCES projects(id) ON DELETE CASCADE"),
	('tracking_enabled',  "INTEGER NOT NULL DEFAULT 0"),
	('is_favorite',       "INTEGER NOT NULL DEFAULT 0"),
	('area_color',        "TEXT"),
]


def et_now():
	return datetime.now(pytz.timezone('US/Eastern')).isoformat()


def table_exists(cur, name):
	row = cur.execute(
		"SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,)
	).fetchone()
	return row is not None


def column_exists(cur, table, col):
	cols = [row[1] for row in cur.execute(f"PRAGMA table_info({table})").fetchall()]
	return col in cols


def add_column_if_missing(cur, table, col_name, col_def, added, skipped):
	if column_exists(cur, table, col_name):
		skipped.append(f"{table}.{col_name}")
		return False
	cur.execute(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_def}")
	added.append(f"{table}.{col_name}")
	return True


def run():
	if not os.path.exists(DB_FILE):
		print(f"× DB not found at {DB_FILE}")
		print("  Run migrate_to_sqlite.py first.")
		return

	conn = sqlite3.connect(DB_FILE)
	conn.execute("PRAGMA foreign_keys = ON")
	cur = conn.cursor()
	added = []
	skipped = []

	# 1. ALTER projects — 5 new columns
	for col_name, col_def in PROJECTS_NEW_COLS:
		add_column_if_missing(cur, 'projects', col_name, col_def, added, skipped)

	# 2. CREATE time_entries
	te_existed = table_exists(cur, 'time_entries')
	cur.execute("""
		CREATE TABLE IF NOT EXISTS time_entries (
			id               INTEGER PRIMARY KEY AUTOINCREMENT,
			project_id       INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
			task_id          INTEGER,
			description      TEXT NOT NULL DEFAULT '',
			started_at       TEXT NOT NULL,
			ended_at         TEXT,
			duration_seconds INTEGER,
			created          TEXT NOT NULL,
			updated          TEXT NOT NULL
		)
	""")
	cur.execute(
		"CREATE INDEX IF NOT EXISTS idx_time_entries_project_id ON time_entries(project_id)"
	)
	cur.execute(
		"CREATE INDEX IF NOT EXISTS idx_time_entries_started_at ON time_entries(started_at)"
	)
	cur.execute(
		"CREATE INDEX IF NOT EXISTS idx_time_entries_active "
		"ON time_entries(ended_at) WHERE ended_at IS NULL"
	)
	(skipped if te_existed else added).append("time_entries (table + indexes)")

	# 3. CREATE settings + seed row
	settings_existed = table_exists(cur, 'settings')
	cur.execute("""
		CREATE TABLE IF NOT EXISTS settings (
			id                       INTEGER PRIMARY KEY CHECK (id = 1),
			idle_threshold_minutes   INTEGER NOT NULL DEFAULT 15,
			reimbursement_rate_cents INTEGER NOT NULL DEFAULT 67,
			vehicle_a_label          TEXT NOT NULL DEFAULT 'Vehicle A',
			vehicle_b_label          TEXT NOT NULL DEFAULT 'Vehicle B',
			default_vehicle          TEXT NOT NULL DEFAULT 'a',
			created                  TEXT NOT NULL,
			updated                  TEXT NOT NULL
		)
	""")
	(skipped if settings_existed else added).append("settings (table)")

	now = et_now()
	row_existed = cur.execute("SELECT id FROM settings WHERE id = 1").fetchone() is not None
	cur.execute(
		"INSERT OR IGNORE INTO settings (id, created, updated) VALUES (1, ?, ?)",
		(now, now)
	)
	(skipped if row_existed else added).append("settings row id=1")

	# 4. ALTER chat_messages — add 'mode'
	if table_exists(cur, 'chat_messages'):
		add_column_if_missing(cur, 'chat_messages', 'mode', 'TEXT', added, skipped)
	else:
		print("⚠  chat_messages table not found — run migrate_to_sqlite.py first.")
		print("   Skipping chat_messages.mode for now.")

	# 5. Seed Work Areas (idempotent on slug)
	for area in WORK_AREAS:
		row = cur.execute(
			"SELECT id FROM projects WHERE slug = ?", (area['slug'],)
		).fetchone()
		if row:
			skipped.append(f"work area '{area['title']}'")
			continue
		cur.execute("""
			INSERT INTO projects
				(title, slug, description, is_private,
				 project_type, parent_project_id, tracking_enabled,
				 is_favorite, area_color, created, updated)
			VALUES (?, ?, '', 0, 'work_area', NULL, 0, 0, ?, ?, ?)
		""", (area['title'], area['slug'], area['area_color'], now, now))
		added.append(f"work area '{area['title']}'")

	conn.commit()
	conn.close()

	print()
	print(f"Migration: migrate_add_time_tracking.py")
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
	if not added:
		print("No changes — schema already up to date.")
	print()


if __name__ == '__main__':
	run()
