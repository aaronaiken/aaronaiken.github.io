"""Git helpers — status indicator + stash-safe pull/commit/push for status updates."""
import os
import subprocess


REPO_ROOT = os.environ.get('COCKPIT_REPO_ROOT', '/home/aaronaiken/status_update')


def _snapshot_db_best_effort():
	"""Fire backup_db.py before the publish flow runs.

	Defense-in-depth: every status update publish becomes a backup-trigger
	event in addition to a content-publish event. Pairs with the daily
	cron sweep (backup_all.py) and the manual CLI. Snapshots are cheap
	(SQLite online backup API) and pruned to last 30, so over-snapshotting
	is fine — under-snapshotting is what bit us 2026-05-02.

	Best-effort: any failure logs and is swallowed. The publish must not
	be blocked by a backup hiccup."""
	try:
		subprocess.run(
			['python3', os.path.join(REPO_ROOT, 'backup_db.py')],
			capture_output=True, timeout=30, check=True,
		)
	except Exception as e:
		print(f'snapshot-on-publish failed (continuing anyway): {e}')


def get_git_status():
	try:
		subprocess.run(["git", "fetch"], check=True, capture_output=True, timeout=5)
		status = subprocess.check_output(["git", "status", "-sb"], encoding='utf-8')
		if "ahead" in status:
			return "syncing"
		elif "behind" in status:
			return "offline"
		else:
			return "online"
	except Exception as e:
		print(f"Git Status Error: {e}")
		return False


def perform_git_ops(filename):
	_snapshot_db_best_effort()

	stash = subprocess.run(
		["git", "stash"], capture_output=True, encoding='utf-8'
	)
	stashed = "No local changes" not in stash.stdout

	subprocess.run(["git", "pull", "--rebase", "origin", "main"], check=True)

	if stashed:
		subprocess.run(["git", "stash", "pop"], check=True)

	subprocess.run(["git", "add", "."], check=True)
	subprocess.run(["git", "commit", "-m", "update from cockpit"], check=True)
	subprocess.run(["git", "push", "origin", "main"], check=True)
