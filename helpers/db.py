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


def fetch_assign_picker_groups(conn):
	"""
	Project list for the Below Deck assign-to-project picker.
	Returns a list of {label, projects} groups:
	  - one group per work area (label = area title), containing its sub-projects
	  - one final 'Personal' group, when there are personal projects
	Excludes private projects and work_area rows (containers, not assignable).
	Same shape used by the dashboard sidebar BD panel and the standalone
	/below-deck page.
	"""
	rows = conn.execute('''
		SELECT p.id, p.title, p.project_type,
		       parent.title AS area_title
		FROM projects p
		LEFT JOIN projects parent ON p.parent_project_id = parent.id
		WHERE p.is_private = 0
		  AND p.project_type IN ('personal', 'work_subproject')
		ORDER BY p.project_type ASC, parent.title ASC, p.title ASC
	''').fetchall()
	work_groups = {}
	personal = []
	for r in rows:
		entry = {'id': r['id'], 'title': r['title']}
		if r['project_type'] == 'work_subproject':
			work_groups.setdefault(r['area_title'] or 'Work', []).append(entry)
		else:
			personal.append(entry)
	return (
		[{'label': area, 'projects': work_groups[area]} for area in sorted(work_groups)] +
		([{'label': 'Personal', 'projects': personal}] if personal else [])
	)
