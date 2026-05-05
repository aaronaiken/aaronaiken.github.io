"""
backup_status — parse ~/db-backups/backup.log to surface freshness in the UI.

Both backup_all.py (cron sweep) and backup_db.py (manual snapshot, also
called from perform_git_ops on every publish) append to the same log
file. Each emits a predictable success marker on a clean run:

  backup_all.py: '<ISO> sweep complete: N ok, 0 failed, P skipped'
  backup_db.py:  '<ISO>   ✓ verified (integrity ok, ...)'

We scan for the most recent of either pattern, compute age against
datetime.now() (both are naive local time — same TZ produced both ends
of the comparison so no conversion needed), and bucket into a status
class the footer pill colours by.

Failure modes (log missing, log unparseable, no successful entries
found, parse error on timestamp) all return ('UNKNOWN', 'fail') —
explicit red, never silent.
"""
import os
import re
from datetime import datetime


BACKUP_DIR = os.environ.get(
	'COCKPIT_BACKUP_DIR', os.path.expanduser('~/db-backups'))
LOG_FILE = os.path.join(BACKUP_DIR, 'backup.log')

_SUCCESS_RE = re.compile(
	r'^(?P<ts>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}) '
	r'(?:sweep complete: \d+ ok, 0 failed| *✓ verified)',
	re.MULTILINE,
)

_OK_THRESHOLD_HOURS = 36
_WARN_THRESHOLD_HOURS = 72


def _format_age(delta):
	s = max(0, int(delta.total_seconds()))
	if s < 60:
		return f'{s}s'
	if s < 3600:
		return f'{s // 60}m'
	if s < 48 * 3600:
		return f'{s // 3600}h'
	return f'{s // 86400}d'


def get_last_backup_status():
	"""Return {age_str, status} for the footer pill.

	status ∈ {'ok', 'warn', 'fail'}. Always returns a dict — the helper
	never raises, so templates can call it without a try/except guard."""
	try:
		with open(LOG_FILE, 'r', encoding='utf-8') as f:
			content = f.read()
	except OSError:
		return {'age_str': 'UNKNOWN', 'status': 'fail'}

	matches = list(_SUCCESS_RE.finditer(content))
	if not matches:
		return {'age_str': 'UNKNOWN', 'status': 'fail'}

	try:
		last = datetime.fromisoformat(matches[-1].group('ts'))
	except ValueError:
		return {'age_str': 'UNKNOWN', 'status': 'fail'}

	delta = datetime.now() - last
	hours = delta.total_seconds() / 3600
	if hours < _OK_THRESHOLD_HOURS:
		status = 'ok'
	elif hours < _WARN_THRESHOLD_HOURS:
		status = 'warn'
	else:
		status = 'fail'
	return {'age_str': _format_age(delta), 'status': status}
