"""48pages notebook — local placeholder store (the cockpit's "side-door" client).

This is the swappable LOCAL implementation of the 48pages page/slip model. Keep the
module boundary clean: when 48pages ships as its own product, this file is replaced by
a thin client against its `/v1/*` API (GET /v1/page, POST /v1/slip, ...) and nothing
else in the cockpit should reach past these functions. Treat it as an adapter, not a fork.

Budget math is ported from the 48pages spec (NOTEBOOK_APP_SPEC §2 / notebook_tokens.css):
1 page = 20 line-units, 48 pages total, triage at page 39. A "line-unit" approximates one
rendered line on ruled paper — blank lines cost ink too (paper, not thoughts). The exact
rendered-height measurement lands with the real editor in the notebook fullscreen; this is
the placeholder estimate that drives the home-slip fill % and the PG n/48 gauge.
"""
import os
import json
from datetime import datetime
import pytz


NOTEBOOK_FILE = 'assets/data/notebook.json'
SCRATCH_FILE = 'assets/data/scratch.json'          # legacy HOME tab
SCRATCH_WORK_FILE = 'assets/data/scratch_work.json'  # legacy DESK tab

# ---- budget constants (ported — see notebook_tokens.css --np-* geometry) ----
LINES_PER_PAGE = 20
PAGE_BUDGET = 48
TRIAGE_PAGE = 39
_CHARS_PER_LINE = 60   # ruled-page wrap width for the line-unit estimate (tunable)

_PA_TZ = pytz.timezone('America/New_York')


def _now_iso():
	return datetime.now(_PA_TZ).isoformat()


def line_units(text):
	"""Approximate rendered line-units of a markdown buffer. Blank lines count as 1 unit
	(they cost ink like paper); long lines wrap at _CHARS_PER_LINE."""
	if not text:
		return 0
	units = 0
	for line in text.split('\n'):
		n = len(line)
		units += max(1, -(-n // _CHARS_PER_LINE))  # ceil(n / width), min 1
	return units


def budget(text):
	"""Capacity readout for a page buffer — drives PG n/48 + the slip's fill %."""
	units = line_units(text)
	pages_used = units / LINES_PER_PAGE
	return {
		'units': units,
		'lines_per_page': LINES_PER_PAGE,
		'pages_used': round(pages_used, 2),
		'page_budget': PAGE_BUDGET,
		'triage_page': TRIAGE_PAGE,
		'pages_left': round(max(0, PAGE_BUDGET - pages_used), 2),
		'fill': round(min(1.0, pages_used / PAGE_BUDGET), 4),
		'triage': pages_used >= TRIAGE_PAGE,
		'full': pages_used >= PAGE_BUDGET,
	}


def _read_scratch(path):
	try:
		with open(path) as f:
			return (json.load(f).get('content') or '').strip()
	except (FileNotFoundError, ValueError):
		return ''


def _migrate_from_scratch():
	"""One-time seed: fold the old HOME + DESK scratch pads into the single page with a
	visible divider (redesign §2 migration note). One-way; the scratch files are left in
	place as a backup and are simply no longer read by the cockpit after this."""
	home = _read_scratch(SCRATCH_FILE)
	desk = _read_scratch(SCRATCH_WORK_FILE)
	parts = []
	if home:
		parts.append(home)
	if desk:
		parts.append('— migrated from desk —\n\n' + desk)
	return '\n\n'.join(parts)


def _read_store():
	try:
		with open(NOTEBOOK_FILE) as f:
			return json.load(f)
	except (FileNotFoundError, ValueError):
		return None


def _write_store(data):
	os.makedirs(os.path.dirname(NOTEBOOK_FILE), exist_ok=True)
	tmp = NOTEBOOK_FILE + '.tmp'
	with open(tmp, 'w') as f:
		json.dump(data, f)
	os.replace(tmp, NOTEBOOK_FILE)


def load_notebook():
	"""Return {page, last_modified, cabinet}. On the first ever load, migrate scratch in."""
	data = _read_store()
	if data is None:
		page = _migrate_from_scratch()
		data = {'page': page, 'last_modified': _now_iso() if page else None, 'cabinet': []}
		if page:
			_write_store(data)
	return {
		'page': data.get('page', ''),
		'last_modified': data.get('last_modified'),
		'cabinet': data.get('cabinet', []),
	}


def save_page(content, force=False):
	"""Persist the page buffer (autosave). Preserves the cabinet in the same store file."""
	if content is None:
		content = ''
	data = _read_store() or {}
	data['page'] = content
	data['last_modified'] = _now_iso()
	data.setdefault('cabinet', [])
	_write_store(data)
	return data['last_modified']


# ---- cabinet (the unbounded archive; page is scarce, this isn't) ----

def _clean_tags(tags):
	out = []
	for t in (tags or []):
		t = str(t).strip().lower()
		if t and t not in out:
			out.append(t)
	return out


def cabinet_all():
	return (_read_store() or {}).get('cabinet', [])


def cabinet_tag_counts():
	counts = {}
	for c in cabinet_all():
		for t in c.get('tags', []):
			counts[t] = counts.get(t, 0) + 1
	return counts


def cabinet_list(search='', tag=''):
	items = cabinet_all()
	if tag:
		items = [c for c in items if tag in c.get('tags', [])]
	if search:
		s = search.lower()
		items = [c for c in items if s in (
			(c.get('title', '') + ' ' + c.get('body_md', '') + ' ' + ' '.join(c.get('tags', []))).lower()
		)]
	return items


def cabinet_file(title, body_md, tags):
	"""Copy a scrap into the cabinet. Mirrors the 48pages FILE verb (copy-then-tear;
	the tear from the page happens client-side). Returns the new item."""
	data = _read_store() or {'page': '', 'last_modified': None, 'cabinet': []}
	cab = data.setdefault('cabinet', [])
	body = (body_md or '').strip()
	item = {
		'id': (max([c.get('id', 0) for c in cab], default=0) + 1),
		'title': (title or '').strip() or (body.split('\n')[0][:80] if body else 'untitled'),
		'body_md': body,
		'tags': _clean_tags(tags),
		'filed': _now_iso(),
	}
	cab.insert(0, item)   # newest first
	_write_store(data)
	return item


def cabinet_delete(item_id):
	data = _read_store()
	if not data:
		return False
	cab = data.get('cabinet', [])
	kept = [c for c in cab if c.get('id') != item_id]
	data['cabinet'] = kept
	_write_store(data)
	return len(kept) < len(cab)


def cabinet_retag(item_id, tags):
	data = _read_store()
	if not data:
		return None
	for c in data.get('cabinet', []):
		if c.get('id') == item_id:
			c['tags'] = _clean_tags(tags)
			_write_store(data)
			return c
	return None


def append_slip(text):
	"""Append a captured slip to the BOTTOM of the page (the home-stack slip → page).
	Mirrors 48pages POST /v1/slip. Returns the new page + budget."""
	text = (text or '').strip()
	current = load_notebook()['page']
	if not text:
		return {'page': current, 'last_modified': None, 'budget': budget(current)}
	page = (current.rstrip() + '\n\n' + text) if current.strip() else text
	lm = save_page(page, force=True)
	return {'page': page, 'last_modified': lm, 'budget': budget(page)}
