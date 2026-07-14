#!/usr/bin/env python3
"""Additive, idempotent migration: Splinched public-feed settings.

Adds two columns to the single-row ledger `settings` table so the operator can
drive the public Splinched sales-page stats feed (/ledger/public/splinched.json):

  splinched_publish     INTEGER  0/1 master switch (the feed 404s until it's on)
  splinched_accel_date  TEXT     'YYYY-MM' accelerated/sandbox payoff month, set
                                 by hand (the current sandbox result)

Everything else the feed reports — current balance and the baseline (minimum-pace)
payoff date — is computed live from the ledger; only these two are operator-set.
Re-runnable: skips columns that already exist.
"""
import sqlite3
from helpers.db import LEDGER_DB_FILE

COLUMNS = [
    ('splinched_publish', 'INTEGER NOT NULL DEFAULT 0'),
    ('splinched_accel_date', 'TEXT'),
]


def run():
    conn = sqlite3.connect(LEDGER_DB_FILE)
    existing = {row[1] for row in conn.execute('PRAGMA table_info(settings)')}
    added = []
    for name, decl in COLUMNS:
        if name not in existing:
            conn.execute(f'ALTER TABLE settings ADD COLUMN {name} {decl}')
            added.append(name)
    conn.commit()
    conn.close()
    print('splinched public settings — added:', ', '.join(added) if added else '(nothing, already present)')


if __name__ == '__main__':
    run()
