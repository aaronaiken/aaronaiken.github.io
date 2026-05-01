"""Database + URL slug + ET timestamp helpers."""
import os
import re
import sqlite3
from datetime import datetime
import pytz


DB_FILE = os.path.join(
	os.environ.get('COCKPIT_REPO_ROOT', '/home/aaronaiken/status_update'),
	'assets/data/command_deck.db'
)


def get_db():
	"""Open a SQLite connection with WAL mode and foreign keys on."""
	conn = sqlite3.connect(DB_FILE)
	conn.row_factory = sqlite3.Row
	conn.execute("PRAGMA foreign_keys = ON")
	conn.execute("PRAGMA journal_mode = WAL")
	return conn


def slugify(text):
	"""Turn a project title into a URL-safe slug."""
	text = text.lower().strip()
	text = re.sub(r'[^\w\s-]', '', text)
	text = re.sub(r'[\s_-]+', '-', text)
	text = re.sub(r'^-+|-+$', '', text)
	return text or 'project'


def unique_slug(title, conn, exclude_id=None):
	"""Generate a unique slug, appending -2, -3 etc. if needed."""
	base = slugify(title)
	slug = base
	n = 2
	while True:
		if exclude_id:
			row = conn.execute(
				'SELECT id FROM projects WHERE slug = ? AND id != ?', (slug, exclude_id)
			).fetchone()
		else:
			row = conn.execute('SELECT id FROM projects WHERE slug = ?', (slug,)).fetchone()
		if not row:
			return slug
		slug = f'{base}-{n}'
		n += 1


def et_now():
	"""Current time as ISO string in US/Eastern."""
	eastern = pytz.timezone('US/Eastern')
	return datetime.now(eastern).isoformat()
