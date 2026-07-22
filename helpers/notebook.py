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


def load_notebook():
	"""Return {page, last_modified}. On the first ever load, migrate scratch content in."""
	try:
		with open(NOTEBOOK_FILE) as f:
			data = json.load(f)
		return {'page': data.get('page', ''), 'last_modified': data.get('last_modified')}
	except (FileNotFoundError, ValueError):
		page = _migrate_from_scratch()
		lm = save_page(page, force=True) if page else None
		return {'page': page, 'last_modified': lm}


def save_page(content, force=False):
	"""Persist the whole page buffer (autosave from the notebook fullscreen)."""
	if content is None:
		content = ''
	lm = _now_iso()
	os.makedirs(os.path.dirname(NOTEBOOK_FILE), exist_ok=True)
	tmp = NOTEBOOK_FILE + '.tmp'
	with open(tmp, 'w') as f:
		json.dump({'page': content, 'last_modified': lm}, f)
	os.replace(tmp, NOTEBOOK_FILE)
	return lm


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
