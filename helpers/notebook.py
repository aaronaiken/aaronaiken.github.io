"""48pages notebook — thin client against the live side-door API (spec §7).

The local placeholder store is retired: page + cabinet now live in the real
zero-knowledge notebook. This module is the adapter its old docstring promised —
budget math is local (pure; it drives the PG n/48 gauge and the slip fill %),
and everything else delegates to helpers/slip_client.py, which unwraps the master
key on THIS box and encrypts/decrypts every record. The 48pages server only ever
stores ciphertext; this Flask process is the "device".

Public function signatures the blueprint calls are unchanged, and the cockpit's
entry shape ({id, title, body_md, tags, filed}) is mapped at the boundary, so the
templates and blueprint don't change (beyond cabinet ids now being UUID strings).

No NOTEBOOK_SLIP_TOKEN configured → the notebook is *unavailable* (empty), not
silently local: a true window shouldn't fork into a shadow copy.
"""
import logging
import os
from datetime import datetime

import pytz

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
		units += max(1, -(-len(line) // _CHARS_PER_LINE))  # ceil(n / width), min 1
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


# ---- the 48pages client (unwraps M once, then caches it) --------------------

_client = None
_client_ready = False


def _nb():
	"""The side-door client, or None if no token is configured (then the notebook is
	unavailable rather than silently local — set NOTEBOOK_SLIP_TOKEN). The client
	unwraps the master key once and caches it on the instance."""
	global _client, _client_ready
	if not _client_ready:
		_client_ready = True
		token = os.environ.get('NOTEBOOK_SLIP_TOKEN')
		if token:
			try:
				from helpers.slip_client import Slip
				_client = Slip(token, os.environ.get('NOTEBOOK_API_BASE') or None)
			except Exception:
				logging.exception('48pages client failed to init')
	return _client


def _entry_out(e):
	"""48pages {id,title,body,tags,filedAt} → cockpit {id,title,body_md,tags,filed}."""
	return {'id': e['id'], 'title': e.get('title', ''), 'body_md': e.get('body', ''),
	        'tags': e.get('tags', []), 'filed': e.get('filedAt')}


# ---- page -------------------------------------------------------------------

def load_notebook():
	"""Return {page, last_modified, cabinet} from the real notebook. (last_modified is
	None: the zero-knowledge server exposes no per-page mtime — the buffer is the truth.)"""
	client = _nb()
	if not client:
		return {'page': '', 'last_modified': None, 'cabinet': []}
	page = client.read_page() or ''
	return {'page': page, 'last_modified': None,
	        'cabinet': [_entry_out(e) for e in client.list_cabinet()]}


def save_page(content, force=False):
	"""Encrypt + upload the whole page (last-writer-wins, same as the app's multi-device
	behaviour). Returns a timestamp for the autosave UI."""
	client = _nb()
	if client:
		client.write_page(content or '')
	return _now_iso()


# ---- cabinet (the unbounded archive; page is scarce, this isn't) ------------

def _clean_tags(tags):
	out = []
	for t in (tags or []):
		t = str(t).strip().lower()
		if t and t not in out:
			out.append(t)
	return out


def cabinet_all():
	client = _nb()
	return [_entry_out(e) for e in client.list_cabinet()] if client else []


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
			(c.get('title', '') + ' ' + c.get('body_md', '') + ' ' + ' '.join(c.get('tags', []))).lower())]
	return items


def cabinet_file(title, body_md, tags):
	"""File a scrap into the cabinet (copy; the page-side tear is client-side)."""
	client = _nb()
	if not client:
		return None
	e = client.file_cabinet((title or '').strip() or (body_md or '').split('\n')[0][:80] or 'untitled',
	                        (body_md or '').strip(), _clean_tags(tags))
	return _entry_out(e)


def cabinet_delete(item_id):
	client = _nb()
	if not client:
		return False
	client.delete_cabinet(item_id)
	return True


def cabinet_retag(item_id, tags):
	"""Re-tag needs the entry's title + body to re-seal — fetch, then update."""
	client = _nb()
	if not client:
		return None
	for e in client.list_cabinet():
		if e['id'] == item_id:
			updated = client.update_cabinet(item_id, e['title'], e['body'],
			                                _clean_tags(tags), e.get('filedAt'))
			return _entry_out(updated)
	return None


def append_slip(text):
	"""Append a slip to the BOTTOM of the page. The cockpit is a full-access true window
	that DISPLAYS the real page, so a slip authored here should show up immediately —
	page-append is the correct "app behavior" for a display-capable client (per the
	48pages API author). Returns the new page + budget for the UI.

	`client.capture(text)` (POST /v1/slip → the app-only review queue) stays available but
	is deliberately NOT the default: reserve it for BLIND producers that can't show the
	page — Shortcuts, cron, the menu-bar bar — where the review banner is the only way in."""
	text = (text or '').strip()
	page = load_notebook()['page']
	if not text:
		return {'page': page, 'last_modified': None, 'budget': budget(page)}
	new_page = (page.rstrip() + '\n\n' + text) if page.strip() else text
	lm = save_page(new_page)
	return {'page': new_page, 'last_modified': lm, 'budget': budget(new_page)}
