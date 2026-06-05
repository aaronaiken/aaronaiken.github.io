#!/usr/bin/env python3
"""One-shot recovery for skipped autopay rows that pre-date the carry-forward fix.

The original `skip` branch in the payday session zeroed amount + marked
confirmed, which removed the obligation from runway despite the money still
being owed. The fix (commit 2e8e4a8) carries them forward on submit, but
rows processed before the fix are stranded.

This script finds those stranded rows (`notes LIKE '%[skipped on payday]%'`,
`amount = 0`, `confirmed = 1`) and, for any without an existing carry-forward
sibling, inserts a fresh pending `debt_transactions` row dated `today + 1`
with the amount re-derived from `accounts.autopay_amount`.

Idempotent. Safe to re-run.
"""

import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from helpers.db import get_ledger_db  # noqa: E402
from helpers import ledger as L  # noqa: E402


def main():
	conn = get_ledger_db()
	today = L.et_today()
	carry_date = (today + timedelta(days=1)).isoformat()
	now = L.et_now_iso()

	stranded = conn.execute("""
		SELECT t.*, a.name AS account_name, a.autopay_amount
		FROM debt_transactions t
		JOIN accounts a ON a.id = t.account_id
		WHERE t.confirmed = 1
		  AND t.amount = 0
		  AND t.notes LIKE '%[skipped on payday]%'
		ORDER BY t.tx_date
	""").fetchall()

	if not stranded:
		print('No stranded skipped rows found. Nothing to do.')
		conn.close()
		return

	created = 0
	skipped = 0
	for row in stranded:
		existing = conn.execute("""
			SELECT 1 FROM debt_transactions
			WHERE account_id = ?
			  AND confirmed = 0
			  AND notes LIKE ?
		""", (row['account_id'],
		      f'%[carried from skipped autopay on {row["tx_date"]}]%')
		).fetchone()
		if existing:
			print(f'  · {row["account_name"]} ({row["tx_date"]}): carry already exists, skipping')
			skipped += 1
			continue

		amount = row['autopay_amount']
		if not amount or amount <= 0:
			print(f'  ! {row["account_name"]} ({row["tx_date"]}): no autopay_amount on file, skipping (set it on the account and re-run, or add the obligation by hand)')
			skipped += 1
			continue

		carry_notes = (
			(row['notes'] + ' ' if row['notes'] else '')
			+ f"[carried from skipped autopay on {row['tx_date']}]"
		).strip()
		conn.execute("""
			INSERT INTO debt_transactions (
				account_id, tx_date, amount, tx_type, source,
				confirmed, description, notes, created, updated
			) VALUES (?, ?, ?, 'payment', 'autopay_expected', 0, ?, ?, ?, ?)
		""", (
			row['account_id'], carry_date, amount,
			row['description'], carry_notes, now, now,
		))
		print(f'  ✓ {row["account_name"]} ({row["tx_date"]}): carried forward ${amount:.2f} → {carry_date}')
		created += 1

	conn.commit()
	conn.close()
	print(f'\nDone. Created {created} carry-forward row(s); skipped {skipped}.')


if __name__ == '__main__':
	main()
