# migrate_add_block_titles.py
# Safe to run multiple times — checks if column exists before altering.
import sqlite3, os

DB_FILE = os.path.join('/home/aaronaiken/status_update', 'assets/data/command_deck.db')

conn = sqlite3.connect(DB_FILE)
cur = conn.cursor()

cur.execute("PRAGMA table_info(blocks)")
columns = [row[1] for row in cur.fetchall()]

if 'title' not in columns:
    cur.execute("ALTER TABLE blocks ADD COLUMN title TEXT")
    conn.commit()
    print("✓ Added title column to blocks")
else:
    print("— title column already exists, nothing to do")

conn.close()