#!/usr/bin/env python3
"""
migrate_to_sqlite.py
Run once from /home/aaronaiken/status_update to:
1. Create command_deck.db with full schema
2. Migrate below_deck.json tasks into the tasks table

Usage:
  cd /home/aaronaiken/status_update
  python migrate_to_sqlite.py

Safe to run multiple times — uses INSERT OR IGNORE on tasks.
"""

import sqlite3
import json
import os
from datetime import datetime

DB_PATH         = 'assets/data/command_deck.db'
BELOW_DECK_JSON = 'assets/data/below_deck.json'


def create_schema(conn):
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS projects (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            title       TEXT    NOT NULL,
            slug        TEXT    NOT NULL UNIQUE,
            description TEXT,
            created     TEXT    NOT NULL,
            updated     TEXT    NOT NULL
        );

        CREATE TABLE IF NOT EXISTS tasks (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            title          TEXT    NOT NULL,
            tag            TEXT,
            status         TEXT    NOT NULL DEFAULT 'open',
            created        TEXT    NOT NULL,
            completed_date TEXT,
            "order"        INTEGER DEFAULT 0,
            project_id     INTEGER REFERENCES projects(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS blocks (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            type       TEXT    NOT NULL CHECK(type IN ('note', 'checklist')),
            content    TEXT,
            "order"    INTEGER DEFAULT 0,
            created    TEXT    NOT NULL
        );

        CREATE TABLE IF NOT EXISTS checklist_items (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            block_id INTEGER NOT NULL REFERENCES blocks(id) ON DELETE CASCADE,
            text     TEXT    NOT NULL,
            checked  INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS files (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            filename   TEXT    NOT NULL,
            bunny_url  TEXT    NOT NULL,
            uploaded   TEXT    NOT NULL
        );

        CREATE TABLE IF NOT EXISTS chat_messages (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            role       TEXT    NOT NULL CHECK(role IN ('user', 'assistant')),
            content    TEXT    NOT NULL,
            project_id INTEGER REFERENCES projects(id) ON DELETE SET NULL,
            created    TEXT    NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_tasks_project    ON tasks(project_id);
        CREATE INDEX IF NOT EXISTS idx_tasks_status     ON tasks(status);
        CREATE INDEX IF NOT EXISTS idx_blocks_project   ON blocks(project_id);
        CREATE INDEX IF NOT EXISTS idx_chat_project     ON chat_messages(project_id);
    ''')
    conn.commit()
    print("✓ Schema created (or already exists)")


def migrate_below_deck(conn):
    if not os.path.exists(BELOW_DECK_JSON):
        print("  below_deck.json not found — skipping migration")
        return

    with open(BELOW_DECK_JSON, 'r', encoding='utf-8') as f:
        data = json.load(f)

    tasks = data.get('tasks', [])
    if not tasks:
        print("  below_deck.json is empty — nothing to migrate")
        return

    migrated = 0
    skipped  = 0
    now = datetime.now().isoformat()

    for task in tasks:
        # Use the original id as a uniqueness check via a temp unique index
        # We store original JSON id in a comment field — just use title+created
        # to avoid duplicates on re-run
        existing = conn.execute(
            'SELECT id FROM tasks WHERE title = ? AND created = ? AND project_id IS NULL',
            (task.get('title', ''), task.get('created', now))
        ).fetchone()

        if existing:
            skipped += 1
            continue

        conn.execute('''
            INSERT INTO tasks (title, tag, status, created, completed_date, "order", project_id)
            VALUES (?, ?, ?, ?, ?, ?, NULL)
        ''', (
            task.get('title', ''),
            task.get('tag'),
            task.get('status', 'open'),
            task.get('created', now),
            task.get('completed_date'),
            task.get('order', 0)
        ))
        migrated += 1

    conn.commit()
    print(f"✓ Migration complete: {migrated} tasks imported, {skipped} skipped (already exist)")


def verify(conn):
    count = conn.execute('SELECT COUNT(*) FROM tasks WHERE project_id IS NULL').fetchone()[0]
    print(f"✓ Below Deck tasks in SQLite: {count}")

    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    print(f"✓ Tables: {', '.join(t[0] for t in tables)}")


def main():
    print(f"\nCommand Deck — SQLite Setup + Migration")
    print(f"Database: {DB_PATH}\n")

    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")

    create_schema(conn)
    migrate_below_deck(conn)
    verify(conn)

    conn.close()
    print("\nDone. You can now reload the web app.\n")


if __name__ == '__main__':
    main()