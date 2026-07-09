"""
migrate_add_ticket_notes.py
Creates the `ticket_notes` table — an append-only, timestamped work-log per
ticket. Each time you work a ticket you jot a note; it stores as its own row
with a timestamp. Safe to run multiple times (idempotent).

Run from PythonAnywhere bash:
    cd /home/aaronaiken/status_update
    python migrate_add_ticket_notes.py
"""

import sqlite3
import os

DB_FILE = os.path.join(os.environ.get('COCKPIT_REPO_ROOT', '/home/aaronaiken/status_update'), 'assets/data/command_deck.db')


def run():
	conn = sqlite3.connect(DB_FILE)
	cur = conn.cursor()

	existing = [r[0] for r in cur.execute(
		"SELECT name FROM sqlite_master WHERE type='table' AND name='ticket_notes'"
	).fetchall()]
	if existing:
		print("Table 'ticket_notes' already exists — nothing to do.")
		conn.close()
		return

	cur.execute("""
		CREATE TABLE ticket_notes (
			id         INTEGER PRIMARY KEY AUTOINCREMENT,
			ticket_id  INTEGER NOT NULL,
			body       TEXT NOT NULL,
			created    TEXT NOT NULL,
			FOREIGN KEY (ticket_id) REFERENCES tickets(id)
		)
	""")
	cur.execute("CREATE INDEX idx_ticket_notes_ticket ON ticket_notes(ticket_id)")
	conn.commit()
	conn.close()
	print("Done — 'ticket_notes' table created.")


if __name__ == '__main__':
	run()
