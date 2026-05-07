"""
migrate_add_tickets.py
Tickets feature — see .kt/spec-tickets.md.

What it does (idempotent — safe to run multiple times):

  + 4 lookup tables (settings-managed):
      customer_groups
      customers
      ticket_types
      time_categories

  + tickets table:
      id, ticket_number (TKT-NNNN unique), project_id (FK SET NULL),
      customer_group_id (FK SET NULL), customer_id (FK SET NULL),
      type_id (FK SET NULL), title, description, priority (default 'normal'),
      status (default 'open'), resolution, closed_date, created, updated

  + time_entries.ticket_id          INTEGER  -- FK tickets(id), ON DELETE SET NULL
  + time_entries.time_category_id   INTEGER  -- FK time_categories(id), ON DELETE SET NULL

  + indexes:
      idx_tickets_project / customer / customer_group / status / open
      idx_time_entries_ticket    (partial: WHERE ticket_id IS NOT NULL)
      idx_time_entries_category  (partial: WHERE time_category_id IS NOT NULL)

  + seed data (only if the lookup table is empty):
      customer_groups: Corp, PennDOT, FDOT
      ticket_types:    bug, feature_request, content, access, performance, other
      time_categories: support, billable, internal, development, training, other

Cascade rules:
  - project deleted   → tickets.project_id              = NULL
  - customer deleted  → tickets.customer_id             = NULL
  - group deleted     → tickets.customer_group_id       = NULL
  - type deleted      → tickets.type_id                 = NULL
  - ticket deleted    → time_entries.ticket_id          = NULL
  - category deleted  → time_entries.time_category_id   = NULL

  Lookups normally archive (is_active = 0 / archived_at = now), so the
  cascades above are belt-and-suspenders. Soft-archive is the public
  API; SET NULL is the safety net for the rare hard delete.

4-way mutex on time_entries (task / item / meeting / ticket) is enforced
in blueprints/time_tracking.py — no DB-level CHECK constraint, since SQLite
handles those awkwardly across ALTER paths.

Prints a summary. Running it again prints "no changes."

Run from PythonAnywhere bash:
    cd /home/aaronaiken/status_update
    python migrate_add_tickets.py
"""

import os
import sqlite3

DB_FILE = os.path.join(
	os.environ.get('COCKPIT_REPO_ROOT', '/home/aaronaiken/status_update'),
	'assets/data/command_deck.db'
)


def table_exists(cur, name):
	row = cur.execute(
		"SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,)
	).fetchone()
	return row is not None


def column_exists(cur, table, col):
	cols = [row[1] for row in cur.execute(f"PRAGMA table_info({table})").fetchall()]
	return col in cols


def index_exists(cur, name):
	row = cur.execute(
		"SELECT name FROM sqlite_master WHERE type='index' AND name=?", (name,)
	).fetchone()
	return row is not None


def now_iso(cur):
	# We don't have et_now() here — keep the migration self-contained.
	# Use SQLite's CURRENT_TIMESTAMP semantics (UTC), formatted as ISO.
	# Lookup rows get a created/updated timestamp at seed time; the app's
	# et_now() takes over for everything else.
	row = cur.execute("SELECT strftime('%Y-%m-%dT%H:%M:%fZ', 'now')").fetchone()
	return row[0]


# ---- Table DDL ----

CREATE_CUSTOMER_GROUPS_SQL = """
CREATE TABLE customer_groups (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT NOT NULL,
    color        TEXT,
    sort_order   INTEGER NOT NULL DEFAULT 0,
    is_active    INTEGER NOT NULL DEFAULT 1,
    created      TEXT NOT NULL,
    updated      TEXT NOT NULL
)
"""

CREATE_CUSTOMERS_SQL = """
CREATE TABLE customers (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    name               TEXT NOT NULL,
    email              TEXT,
    customer_group_id  INTEGER REFERENCES customer_groups(id) ON DELETE SET NULL,
    notes              TEXT,
    archived_at        TEXT,
    created            TEXT NOT NULL,
    updated            TEXT NOT NULL
)
"""

CREATE_TICKET_TYPES_SQL = """
CREATE TABLE ticket_types (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT NOT NULL,
    color        TEXT,
    sort_order   INTEGER NOT NULL DEFAULT 0,
    is_active    INTEGER NOT NULL DEFAULT 1,
    created      TEXT NOT NULL,
    updated      TEXT NOT NULL
)
"""

CREATE_TIME_CATEGORIES_SQL = """
CREATE TABLE time_categories (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT NOT NULL,
    color        TEXT,
    sort_order   INTEGER NOT NULL DEFAULT 0,
    is_active    INTEGER NOT NULL DEFAULT 1,
    created      TEXT NOT NULL,
    updated      TEXT NOT NULL
)
"""

CREATE_TICKETS_SQL = """
CREATE TABLE tickets (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_number      TEXT NOT NULL UNIQUE,
    project_id         INTEGER REFERENCES projects(id)         ON DELETE SET NULL,
    customer_group_id  INTEGER REFERENCES customer_groups(id)  ON DELETE SET NULL,
    customer_id        INTEGER REFERENCES customers(id)        ON DELETE SET NULL,
    type_id            INTEGER REFERENCES ticket_types(id)     ON DELETE SET NULL,
    title              TEXT NOT NULL,
    description        TEXT,
    priority           TEXT NOT NULL DEFAULT 'normal',
    status             TEXT NOT NULL DEFAULT 'open',
    resolution         TEXT,
    closed_date        TEXT,
    created            TEXT NOT NULL,
    updated            TEXT NOT NULL
)
"""

NEW_TABLES = [
	('customer_groups', CREATE_CUSTOMER_GROUPS_SQL),
	('customers',       CREATE_CUSTOMERS_SQL),
	('ticket_types',    CREATE_TICKET_TYPES_SQL),
	('time_categories', CREATE_TIME_CATEGORIES_SQL),
	('tickets',         CREATE_TICKETS_SQL),
]


# ---- Columns on time_entries ----

NEW_COLUMNS = [
	('time_entries', 'ticket_id',
	 'INTEGER REFERENCES tickets(id) ON DELETE SET NULL'),
	('time_entries', 'time_category_id',
	 'INTEGER REFERENCES time_categories(id) ON DELETE SET NULL'),
]


# ---- Indexes ----

NEW_INDEXES = [
	('idx_tickets_project',
	 'CREATE INDEX IF NOT EXISTS idx_tickets_project ON tickets(project_id)'),
	('idx_tickets_customer',
	 'CREATE INDEX IF NOT EXISTS idx_tickets_customer ON tickets(customer_id)'),
	('idx_tickets_customer_group',
	 'CREATE INDEX IF NOT EXISTS idx_tickets_customer_group ON tickets(customer_group_id)'),
	('idx_tickets_status',
	 'CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status)'),
	('idx_tickets_open',
	 'CREATE INDEX IF NOT EXISTS idx_tickets_open ON tickets(status) '
	 "WHERE status != 'closed'"),
	('idx_time_entries_ticket',
	 'CREATE INDEX IF NOT EXISTS idx_time_entries_ticket '
	 'ON time_entries(ticket_id) WHERE ticket_id IS NOT NULL'),
	('idx_time_entries_category',
	 'CREATE INDEX IF NOT EXISTS idx_time_entries_category '
	 'ON time_entries(time_category_id) WHERE time_category_id IS NOT NULL'),
]


# ---- Seed data ----

SEEDS = [
	('customer_groups', [
		('Corp',    None),
		('PennDOT', None),
		('FDOT',    None),
	]),
	('ticket_types', [
		('bug',             None),
		('feature_request', None),
		('content',         None),
		('access',          None),
		('performance',     None),
		('other',           None),
	]),
	('time_categories', [
		('support',     None),
		('billable',    None),
		('internal',    None),
		('development', None),
		('training',    None),
		('other',       None),
	]),
]


def seed_lookup(cur, table, rows, now):
	"""Insert seed rows only if the table is empty (idempotent)."""
	count = cur.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
	if count > 0:
		return 0
	for i, (name, color) in enumerate(rows):
		cur.execute(
			f'INSERT INTO {table} (name, color, sort_order, is_active, created, updated) '
			f'VALUES (?, ?, ?, 1, ?, ?)',
			(name, color, i, now, now),
		)
	return len(rows)


def run():
	if not os.path.exists(DB_FILE):
		print(f"× DB not found at {DB_FILE}")
		print("  Run migrate_to_sqlite.py first.")
		return

	conn = sqlite3.connect(DB_FILE)
	cur = conn.cursor()

	added = []
	skipped = []

	for name, ddl in NEW_TABLES:
		if table_exists(cur, name):
			skipped.append(f'{name} (table)')
		else:
			cur.execute(ddl)
			added.append(f'{name} (table)')

	for table, col, sql_type in NEW_COLUMNS:
		if column_exists(cur, table, col):
			skipped.append(f'{table}.{col}')
		else:
			cur.execute(f'ALTER TABLE {table} ADD COLUMN {col} {sql_type}')
			added.append(f'{table}.{col}')

	for name, sql in NEW_INDEXES:
		if index_exists(cur, name):
			skipped.append(name)
		else:
			cur.execute(sql)
			added.append(name)

	now = now_iso(cur)
	for table, rows in SEEDS:
		seeded = seed_lookup(cur, table, rows, now)
		if seeded:
			added.append(f'{table} (seeded {seeded} rows)')
		else:
			skipped.append(f'{table} (already populated)')

	conn.commit()
	conn.close()

	print()
	print("Migration: migrate_add_tickets.py")
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
