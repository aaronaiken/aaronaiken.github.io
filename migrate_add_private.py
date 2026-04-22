#!/usr/bin/env python3
"""
migrate_add_private.py
Adds is_private column to the projects table.
Safe to run multiple times.

Usage:
  cd /home/aaronaiken/status_update
  python migrate_add_private.py
"""

import sqlite3
import os

DB_PATH = 'assets/data/command_deck.db'

def main():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)

    # Check if column already exists
    cols = [row[1] for row in conn.execute("PRAGMA table_info(projects)").fetchall()]
    if 'is_private' in cols:
        print("✓ is_private column already exists — nothing to do.")
        conn.close()
        return

    conn.execute("ALTER TABLE projects ADD COLUMN is_private INTEGER NOT NULL DEFAULT 0")
    conn.commit()
    conn.close()
    print("✓ Added is_private column to projects table.")

if __name__ == '__main__':
    main()