"""Scratch pad (DESK tab) JSON storage helpers."""
import os
import json
from datetime import datetime
import pytz


SCRATCH_WORK_FILE = 'assets/data/scratch_work.json'


def load_scratch_work():
	"""Load work scratchpad content."""
	try:
		with open(SCRATCH_WORK_FILE, 'r') as f:
			data = json.load(f)
		return data.get('content', ''), data.get('last_modified', None)
	except FileNotFoundError:
		return '', None


def save_scratch_work(content, force=False):
	"""Persist work scratchpad content."""
	if not content and not force:
		try:
			with open(SCRATCH_WORK_FILE, 'r') as f:
				existing = json.load(f)
			if existing.get('content', ''):
				return existing.get('last_modified')
		except FileNotFoundError:
			pass
	pa_tz = pytz.timezone('America/New_York')
	last_modified = datetime.now(pa_tz).isoformat()
	os.makedirs(os.path.dirname(SCRATCH_WORK_FILE), exist_ok=True)
	tmp = SCRATCH_WORK_FILE + '.tmp'
	with open(tmp, 'w') as f:
		json.dump({'content': content, 'last_modified': last_modified}, f)
	os.replace(tmp, SCRATCH_WORK_FILE)
	return last_modified
