"""
backup_offsite.py — replicate the freshest local snapshots OFF PythonAnywhere
to a Bunny storage-only zone.

Why this exists: backup_all.py protects against app bugs and accidental
deletes, but everything it writes still lives on the SAME PA/NFS disk. If PA
loses the storage (account issue, infra failure), the local ~/db-backups/
sweep goes with it. This script ships the latest snapshot of each target to
a Bunny Storage zone so there's a copy that survives PA disappearing.

  PRIVACY: point BUNNY_BACKUP_* at a Bunny STORAGE zone with NO public pull
  zone attached. Storage zones are reachable only via the AccessKey (HTTP
  API) unless you bind a CDN pull zone to them. Do NOT bind one — some of
  these files (Ani conversation/state) are private. There is no CDN_URL env
  here on purpose: we never serve this data, we only PUT/LIST/DELETE it.

The Mac-side local copy is a SEPARATE leg (tools/pull-backups/ — the Mac
pulls ~/db-backups/ from PA over SSH). This script is only the Bunny leg.

Design: for each target, take its most recent local snapshot from
~/db-backups/ (produced by backup_all.py), upload it to
  <zone>/<prefix>/<snapshot-filename>
skipping the upload if that exact name is already on the zone (dedup), then
prune the zone to the last N per basename. Reuses backup_all.TARGETS +
list_for() so the two inventories can never drift.

Exit codes:
  0 → all good, or not configured (optional leg — a missing zone isn't a failure)
  5 → one or more uploads/prunes failed

Usage:
  python3 backup_offsite.py                 # push latest of each + prune (the cron job)
  python3 backup_offsite.py --keep 30       # retain last 30 per file on the zone (default 14)
  python3 backup_offsite.py --no-prune      # upload only
  python3 backup_offsite.py --dry-run       # print what would upload, touch nothing

PA scheduled task setup (run AFTER the daily sweep):
  Hour 03, Minute 37 UTC, daily   (backup_all.py runs at 03:17 — give it 20 min)
  Command: python3 /home/aaronaiken/status_update/backup_offsite.py
"""

import argparse
import os
import sys
from datetime import datetime

import requests

# Reuse the single source of truth for what's at-risk + where local snapshots
# land. Importing backup_all only defines module-level names (argparse runs
# under its own __main__ guard), so this is side-effect-free.
from backup_all import TARGETS, BACKUP_DIR, list_for, LOG_FILE


# --- Bunny storage-only zone (no CDN pull zone — see module docstring) ---
BUNNY_BACKUP_ZONE   = os.environ.get('BUNNY_BACKUP_STORAGE_ZONE', '').strip()
BUNNY_BACKUP_KEY    = os.environ.get('BUNNY_BACKUP_API_KEY', '').strip()
BUNNY_BACKUP_HOST   = os.environ.get('BUNNY_BACKUP_HOST', 'ny.storage.bunnycdn.com').strip().rstrip('/')
BUNNY_BACKUP_PREFIX = os.environ.get('BUNNY_BACKUP_PREFIX', 'offsite').strip('/')

DEFAULT_KEEP = 14
_TIMEOUT = 120


def log(msg):
	line = f"{datetime.now().isoformat(timespec='seconds')} {msg}"
	print(line)
	try:
		os.makedirs(BACKUP_DIR, exist_ok=True)
		with open(LOG_FILE, 'a') as f:
			f.write(line + '\n')
	except Exception:
		pass


def _base_url():
	return f"https://{BUNNY_BACKUP_HOST}/{BUNNY_BACKUP_ZONE}/{BUNNY_BACKUP_PREFIX}"


def remote_list():
	"""Return {ObjectName: length} for everything under the offsite prefix.
	Raises on transport/auth error so the caller can abort cleanly."""
	r = requests.get(
		_base_url() + '/',
		headers={'AccessKey': BUNNY_BACKUP_KEY, 'Accept': 'application/json'},
		timeout=_TIMEOUT,
	)
	if r.status_code == 404:
		return {}  # prefix doesn't exist yet — first run
	if r.status_code != 200:
		raise RuntimeError(f'list failed: {r.status_code} {r.text[:200]}')
	out = {}
	for item in r.json():
		if item.get('IsDirectory'):
			continue
		out[item.get('ObjectName', '')] = item.get('Length', 0)
	return out


def remote_upload(local_path, name):
	with open(local_path, 'rb') as f:
		data = f.read()
	r = requests.put(
		f"{_base_url()}/{name}",
		data=data,
		headers={'AccessKey': BUNNY_BACKUP_KEY, 'Content-Type': 'application/octet-stream'},
		timeout=_TIMEOUT,
	)
	if r.status_code != 201:
		raise RuntimeError(f'upload failed: {r.status_code} {r.text[:200]}')
	return len(data)


def remote_delete(name):
	r = requests.delete(
		f"{_base_url()}/{name}",
		headers={'AccessKey': BUNNY_BACKUP_KEY},
		timeout=_TIMEOUT,
	)
	if r.status_code not in (200, 204):
		raise RuntimeError(f'delete failed: {r.status_code} {r.text[:200]}')


def prune_remote(basename, existing_names, keep, dry_run):
	"""Delete all but the last `keep` remote snapshots for this basename.
	Names look like '<basename>.YYYYMMDD-HHMMSS'; lexical sort == chronological."""
	mine = sorted(n for n in existing_names if n.startswith(basename + '.'))
	if len(mine) <= keep:
		return 0
	doomed = mine[:-keep]
	n = 0
	for name in doomed:
		if dry_run:
			log(f'    would prune {name}')
			n += 1
			continue
		try:
			remote_delete(name)
			n += 1
		except Exception as e:
			log(f'    prune failed for {name}: {e}')
	return n


def run(keep, do_prune, dry_run):
	if not (BUNNY_BACKUP_ZONE and BUNNY_BACKUP_KEY):
		log('offsite: not configured (set BUNNY_BACKUP_STORAGE_ZONE + '
		    'BUNNY_BACKUP_API_KEY) — skipping Bunny leg')
		return 0

	log(f'offsite sweep → bunny zone "{BUNNY_BACKUP_ZONE}/{BUNNY_BACKUP_PREFIX}"'
	    + (' [DRY RUN]' if dry_run else ''))

	try:
		existing = remote_list()
	except Exception as e:
		log(f'offsite: aborted — cannot list zone: {e}')
		return 5

	uploaded, failed, skipped = [], [], []
	# Track remote names so dedup + prune see this run's uploads too.
	present = set(existing.keys())

	for src, _kind in TARGETS:
		basename = os.path.basename(src)
		locals_ = list_for(basename)
		if not locals_:
			# No local snapshot to ship (feature never ran, or file absent).
			skipped.append(basename)
			continue
		latest = locals_[-1]
		name = os.path.basename(latest)  # '<basename>.YYYYMMDD-HHMMSS'

		if name in present:
			log(f'  {basename}: = up to date ({name} already offsite)')
			# still eligible for prune below
		elif dry_run:
			size = os.path.getsize(latest)
			log(f'  {basename}: would upload {name} ({size}b)')
			present.add(name)
			uploaded.append(basename)
		else:
			try:
				n = remote_upload(latest, name)
				log(f'  {basename}: ✓ uploaded {name} ({n}b)')
				present.add(name)
				uploaded.append(basename)
			except Exception as e:
				log(f'  {basename}: × {e}')
				failed.append(basename)
				continue

		if do_prune:
			pruned = prune_remote(basename, present, keep, dry_run)
			if pruned:
				# reflect deletions so the summary + later files stay accurate
				if not dry_run:
					mine = sorted(n for n in present if n.startswith(basename + '.'))
					for old in mine[:-keep]:
						present.discard(old)
				log(f'  {basename}: pruned {pruned} old offsite copy'
				    + ('s' if pruned > 1 else ''))

	log(f'offsite complete: {len(uploaded)} uploaded, {len(failed)} failed, '
	    f'{len(skipped)} skipped')
	return 0 if not failed else 5


def main():
	ap = argparse.ArgumentParser(
		description='Replicate latest local backups off PA to a Bunny storage-only zone.')
	ap.add_argument('--keep', type=int, default=DEFAULT_KEEP,
	                help=f'retain last N snapshots per file on the zone (default {DEFAULT_KEEP})')
	ap.add_argument('--no-prune', action='store_true', help='skip the remote prune step')
	ap.add_argument('--dry-run', action='store_true',
	                help='print what would upload/prune without touching the zone')
	args = ap.parse_args()
	return run(args.keep, not args.no_prune, args.dry_run)


if __name__ == '__main__':
	sys.exit(main())
