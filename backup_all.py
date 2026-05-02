"""
backup_all.py — sweep snapshot of every at-risk gitignored data file.

Why this exists: 2026-05-02, prod command_deck.db went all-zeros after a
WAL/NFS race. backup_db.py (added the same day) covers SQLite. This script
covers EVERYTHING — JSON files, plain-text files, the SQLite DB, all in
one timestamped sweep. Designed to run as a daily PA scheduled task.

Per-file: snapshot to ~/db-backups/<basename>.YYYYMMDD-HHMMSS, validate the
snapshot, prune all but the last N copies.

  - SQLite: online backup API (atomic, lock-aware) + integrity_check
  - JSON: cp + json.load() validate
  - Text: cp + exists check (some files may legitimately be empty)

A failure on one target doesn't abort the rest. Exit code reflects the
worst per-target outcome:
  0 → all good (or only "skipped" — file not present)
  1 → one or more --verify-only checks failed
  5 → one or more snapshots failed

Usage:
  python3 backup_all.py                  # full sweep + prune (the cron job)
  python3 backup_all.py --keep 60        # retain last 60 per file (default 30)
  python3 backup_all.py --no-prune       # snapshot only
  python3 backup_all.py --verify-only    # validate latest snapshot of each

PA scheduled task setup:
  Hour 03, Minute 17 UTC, daily
  Command: python3 /home/aaronaiken/status_update/backup_all.py

  (Switch your existing backup_db.py task to this — backup_all.py covers
   the DB plus everything else. backup_db.py stays for manual focused
   snapshots, e.g. before risky migrations.)
"""

import argparse
import json
import os
import shutil
import sqlite3
import sys
from datetime import datetime
from glob import glob


REPO_ROOT  = os.environ.get('COCKPIT_REPO_ROOT', '/home/aaronaiken/status_update')
BACKUP_DIR = os.environ.get('COCKPIT_BACKUP_DIR', os.path.expanduser('~/db-backups'))
LOG_FILE   = os.path.join(BACKUP_DIR, 'backup.log')
DEFAULT_KEEP = 30

MOZZIE_FILE = os.environ.get('MOZZIE_FILE', os.path.join(REPO_ROOT, 'mozzie_games.json'))


# Each target: (absolute path, type tag matching HANDLERS below).
# Add new at-risk files here. Order doesn't matter — sweep is per-file.
TARGETS = [
	(os.path.join(REPO_ROOT, 'assets/data/command_deck.db'), 'sqlite'),
	(os.path.join(REPO_ROOT, 'assets/data/scratch.json'),    'json'),
	(os.path.join(REPO_ROOT, 'assets/data/scratch_work.json'),'json'),
	(os.path.join(REPO_ROOT, 'assets/data/below_deck.json'), 'json'),  # retired stub
	(os.path.join(REPO_ROOT, 'ani_conversation.json'),       'json'),
	(MOZZIE_FILE,                                            'json'),
	(os.path.join(REPO_ROOT, 'static/ani_memory.txt'),       'text'),
	(os.path.join(REPO_ROOT, 'static/comms.txt'),            'text'),
	(os.path.join(REPO_ROOT, 'static/after_dark_comms.txt'), 'text'),
]


def log(msg):
	line = f"{datetime.now().isoformat(timespec='seconds')} {msg}"
	print(line)
	try:
		os.makedirs(BACKUP_DIR, exist_ok=True)
		with open(LOG_FILE, 'a') as f:
			f.write(line + '\n')
	except Exception:
		pass


# ---- SQLite handlers ----

def snapshot_sqlite(src, dst):
	s = sqlite3.connect(src)
	try:
		d = sqlite3.connect(dst)
		try:
			with d:
				s.backup(d)
			# Force destination header to DELETE journal mode so subsequent
			# opens of the backup file don't create -wal/-shm sidecars.
			d.execute('PRAGMA journal_mode = DELETE')
		finally:
			d.close()
	finally:
		s.close()


def verify_sqlite(path):
	try:
		c = sqlite3.connect(path)
	except Exception as e:
		return False, f'cannot open: {e}'
	try:
		row = c.execute('PRAGMA integrity_check').fetchone()
		if not row or row[0] != 'ok':
			return False, f'integrity_check: {row[0] if row else "no rows"}'
		return True, 'integrity ok'
	except Exception as e:
		return False, f'query failed: {e}'
	finally:
		c.close()


# ---- JSON handlers ----

def snapshot_copy(src, dst):
	shutil.copy2(src, dst)


def verify_json(path):
	try:
		with open(path, 'r', encoding='utf-8') as f:
			json.load(f)
		return True, 'parses'
	except Exception as e:
		return False, f'invalid: {e}'


# ---- Text handlers ----

def verify_text(path):
	if not os.path.exists(path):
		return False, 'missing after copy'
	return True, f'{os.path.getsize(path)}b'


HANDLERS = {
	'sqlite': (snapshot_sqlite, verify_sqlite),
	'json':   (snapshot_copy,   verify_json),
	'text':   (snapshot_copy,   verify_text),
}


# ---- Backup file management ----

def list_for(basename):
	"""Sorted list of all timestamped backups for this basename."""
	pattern = os.path.join(BACKUP_DIR, f'{basename}.[0-9]*')
	files = [f for f in glob(pattern) if not (f.endswith('-wal') or f.endswith('-shm'))]
	return sorted(files)


def prune(basename, keep):
	files = list_for(basename)
	if len(files) <= keep:
		return 0
	to_delete = files[:-keep]
	n = 0
	for f in to_delete:
		try:
			os.remove(f)
			n += 1
		except Exception as e:
			log(f'    prune failed for {os.path.basename(f)}: {e}')
	return n


# ---- Main ----

def run_verify_only():
	worst = 0
	for src, kind in TARGETS:
		basename = os.path.basename(src)
		files = list_for(basename)
		if not files:
			# No backups — only an error if the source file actually exists
			# (otherwise it's just an inactive target on this environment).
			if os.path.exists(src):
				log(f'  {basename}: × no backups found (source exists at {src})')
				worst = max(worst, 1)
			else:
				log(f'  {basename}: — n/a (source not present)')
			continue
		target = files[-1]
		_, verifier = HANDLERS[kind]
		ok, msg = verifier(target)
		marker = '✓' if ok else '×'
		log(f'  {basename}: {marker} {msg} (latest: {os.path.basename(target)})')
		if not ok:
			worst = max(worst, 1)
	return worst


def run_sweep(keep, do_prune):
	stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
	log(f'backup sweep at {stamp}')

	succeeded, failed, skipped = [], [], []

	for src, kind in TARGETS:
		basename = os.path.basename(src)
		if not os.path.exists(src):
			log(f'  {basename}: skipped (not present at {src})')
			skipped.append(basename)
			continue
		target = os.path.join(BACKUP_DIR, f'{basename}.{stamp}')
		snapshotter, verifier = HANDLERS[kind]
		try:
			snapshotter(src, target)
		except Exception as e:
			log(f'  {basename}: × snapshot failed: {e}')
			failed.append(basename)
			continue
		ok, msg = verifier(target)
		if ok:
			src_size = os.path.getsize(src)
			bak_size = os.path.getsize(target)
			log(f'  {basename}: ✓ {msg} ({src_size}b → {bak_size}b)')
			succeeded.append(basename)
		else:
			log(f'  {basename}: × verify failed: {msg}')
			failed.append(basename)
			# Remove the bad backup so verify-only doesn't pick it as "latest"
			try:
				os.remove(target)
			except Exception:
				pass

	if do_prune:
		for src, _ in TARGETS:
			basename = os.path.basename(src)
			n = prune(basename, keep)
			if n:
				log(f'  {basename}: pruned {n} old backup{"s" if n > 1 else ""}')

	log(f'sweep complete: {len(succeeded)} ok, {len(failed)} failed, {len(skipped)} skipped')
	return 0 if not failed else 5


def main():
	ap = argparse.ArgumentParser(description='Sweep backup of all at-risk data files.')
	ap.add_argument('--keep', type=int, default=DEFAULT_KEEP,
	                help=f'retain last N backups per file (default {DEFAULT_KEEP})')
	ap.add_argument('--no-prune', action='store_true', help='skip prune step')
	ap.add_argument('--verify-only', action='store_true',
	                help='validate the most recent backup of each target; do not snapshot')
	args = ap.parse_args()

	os.makedirs(BACKUP_DIR, exist_ok=True)

	if args.verify_only:
		return run_verify_only()
	return run_sweep(args.keep, not args.no_prune)


if __name__ == '__main__':
	sys.exit(main())
