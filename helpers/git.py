"""Git helpers — status indicator + stash-safe pull/commit/push for status updates."""
import subprocess


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
