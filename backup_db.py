"""
backup_db.py — Hot snapshot of command_deck.db using SQLite's online backup API.

Designed to run as a PA scheduled task daily, or manually before risky changes.
Uses sqlite3.Connection.backup() (the online backup API) — atomic, lock-aware,
safe even with concurrent writers. Unlike `cp`, this won't capture the file
mid-write or miss WAL contents.

Why this exists: 2026-05-02, prod command_deck.db went all-zeros after a
WAL/NFS race. KT-command-deck.md said "PA does not auto-backup" — that note
was a placeholder waiting for someone to actually build the backup. Built.

Usage:
  python3 backup_db.py                  # snapshot + prune (default behavior)
  python3 backup_db.py --keep 60        # retain last 60 backups instead of 30
  python3 backup_db.py --no-prune       # snapshot only, skip prune step
  python3 backup_db.py --verify-only    # verify latest backup, no new snapshot

Env overrides:
  COCKPIT_REPO_ROOT      → defaults to /home/aaronaiken/status_update
  COCKPIT_BACKUP_DIR     → defaults to ~/db-backups

PA scheduled task setup (Tasks tab):
  Hour: 03  (i.e. 3am ET — well clear of the 4am Today-list autoclear)
  Minute: 17  (offset to avoid stampedes)
  Command: python3 /home/aaronaiken/status_update/backup_db.py
"""

import argparse
import os
import sqlite3
import sys
from datetime import datetime
from glob import glob


REPO_ROOT   = os.environ.get('COCKPIT_REPO_ROOT', '/home/aaronaiken/status_update')
DB_FILE     = os.path.join(REPO_ROOT, 'assets/data/command_deck.db')
BACKUP_DIR  = os.environ.get('COCKPIT_BACKUP_DIR', os.path.expanduser('~/db-backups'))
LOG_FILE    = os.path.join(BACKUP_DIR, 'backup.log')
DEFAULT_KEEP = 30


def log(msg):
	line = f"{datetime.now().isoformat(timespec='seconds')} {msg}"
	print(line)
	try:
		os.makedirs(BACKUP_DIR, exist_ok=True)
		with open(LOG_FILE, 'a') as f:
			f.write(line + '\n')
	except Exception:
		pass  # logging is best-effort


def list_backups():
	"""Return absolute paths of all timestamped backup files, oldest → newest.
	Glob anchors on .[0-9]* and we explicitly drop -wal / -shm sidecar names
	(SQLite creates these alongside the main DB file when WAL mode is in use)."""
	pattern = os.path.join(BACKUP_DIR, 'command_deck.db.[0-9]*')
	files = [f for f in glob(pattern) if not (f.endswith('-wal') or f.endswith('-shm'))]
	return sorted(files)


def snapshot(target_path):
	"""Hot snapshot via SQLite online backup API. Won't tear under live writes.

	The backup API copies the source's journal_mode setting into the
	destination file's header, so even though we've moved live get_db() to
	DELETE mode (helpers/db.py), a backup of a file that was last opened in
	WAL mode would inherit that mode — and then any subsequent open of the
	backup file would create a -wal sidecar. We force DELETE mode on the
	destination AFTER the backup completes to keep backup files self-
	contained (no sidecars to track)."""
	src = sqlite3.connect(DB_FILE)
	try:
		dst = sqlite3.connect(target_path)
		try:
			with dst:
				src.backup(dst)
			# Flip after backup so the destination file's header records DELETE.
			# Best-effort: log mismatch but don't fail the snapshot.
			result = dst.execute('PRAGMA journal_mode = DELETE').fetchone()
			if result and result[0] != 'delete':
				log(f'  ⚠ destination journal_mode flip returned {result[0]}, expected delete')
		finally:
			dst.close()
	finally:
		src.close()


def verify(path):
	"""Open the backup, run integrity_check + spot-check the projects table.
	Returns (ok: bool, msg: str)."""
	try:
		conn = sqlite3.connect(path)
	except Exception as e:
		return False, f'cannot open: {e}'
	try:
		row = conn.execute('PRAGMA integrity_check').fetchone()
		if not row or row[0] != 'ok':
			return False, f'integrity_check: {row[0] if row else "no rows"}'
		n = conn.execute('SELECT COUNT(*) FROM projects').fetchone()[0]
		return True, f'integrity ok, {n} projects'
	except Exception as e:
		return False, f'query failed: {e}'
	finally:
		conn.close()


def prune(keep):
	"""Delete all but the `keep` most-recent backups. Returns count deleted."""
	files = list_backups()
	if len(files) <= keep:
		return 0
	to_delete = files[:-keep]
	deleted = 0
	for f in to_delete:
		try:
			os.remove(f)
			log(f'  pruned {os.path.basename(f)}')
			deleted += 1
		except Exception as e:
			log(f'  prune failed for {os.path.basename(f)}: {e}')
	return deleted


def main():
	ap = argparse.ArgumentParser(description='Backup command_deck.db.')
	ap.add_argument('--keep', type=int, default=DEFAULT_KEEP,
	                help=f'how many recent backups to retain (default {DEFAULT_KEEP})')
	ap.add_argument('--no-prune', action='store_true',
	                help='skip the prune step after snapshot')
	ap.add_argument('--verify-only', action='store_true',
	                help='verify the most recent backup; do not snapshot')
	args = ap.parse_args()

	if not os.path.exists(DB_FILE):
		log(f'× DB not found at {DB_FILE} — nothing to back up')
		return 2

	os.makedirs(BACKUP_DIR, exist_ok=True)

	if args.verify_only:
		files = list_backups()
		if not files:
			log('× no backups found')
			return 1
		target = files[-1]
		ok, msg = verify(target)
		log(f'verify {os.path.basename(target)}: {"✓" if ok else "×"} {msg}')
		return 0 if ok else 1

	stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
	target = os.path.join(BACKUP_DIR, f'command_deck.db.{stamp}')

	log(f'snapshot → {target}')
	try:
		snapshot(target)
	except Exception as e:
		log(f'× snapshot failed: {e}')
		return 3

	ok, msg = verify(target)
	if not ok:
		log(f'× verify failed for new snapshot: {msg}')
		return 4
	src_size = os.path.getsize(DB_FILE)
	bak_size = os.path.getsize(target)
	log(f'  ✓ verified ({msg}); source {src_size}b, backup {bak_size}b')

	if not args.no_prune:
		n = prune(args.keep)
		if n:
			log(f'  pruned {n} old backup{"s" if n != 1 else ""} (keeping {args.keep})')

	return 0


if __name__ == '__main__':
	sys.exit(main())
