"""
helpers/leak_hunt.py — CSV parsers + auto-categorizer + recurring-charge
detector for The Ledger Phase 3 leak-hunt feature.

Source-of-truth lives in .kt/spec-ledger-phase-3-leak-hunt.md. The
blueprint stays thin; the math is here.
"""
import csv
import io
import re
from collections import defaultdict
from datetime import datetime


# ---- default categories (suggested values, NOT an enforced enum) ----
# Stored as free-text on leak_transactions.category. This list seeds the
# UI dropdown; "available categories" at runtime is SELECT DISTINCT.
DEFAULT_CATEGORIES = [
	'Housing', 'Groceries', 'Dining out', 'Coffee',
	'Streaming & subscriptions', 'Transportation', 'Health',
	'Shopping', 'Family', 'Travel', 'Bills',
	'Debt payments', 'Income', 'Internal transfer', 'Other',
	'Uncategorized',
]


# Categories EXCLUDED from leak math (sum-by-category-of-outflows). These
# show up in the breakdown but get a separate label so they don't appear
# as "leaks." Internal transfer is the cleanest example — it's not a real
# outflow, just movement between own accounts.
EXCLUDED_FROM_LEAK = {'Internal transfer', 'Income', 'Debt payments'}


# ---- format detection ----

_DATE_ALIASES   = ('date', 'posted', 'posted date', 'transaction date')
_DESC_ALIASES   = ('description', 'memo', 'name', 'payee', 'merchant',
                   'transaction description')
_AMOUNT_ALIASES = ('amount', 'transaction amount')


def detect_format(header_row, sample_rows):
	"""Inspect the header row (and a few data rows) to guess the format.

	Returns one of:
	  'pnc'           — older PNC export with Withdrawals + Deposits columns
	  'pnc_activity'  — newer "Account Activity" export, single signed Amount
	                     column with Transaction Date / Transaction Description
	  'generic_v1'    — any other CSV with date + description + amount columns
	  'unknown'       — can't tell
	"""
	if not header_row:
		return 'unknown'
	header_norm = [(c or '').strip().lower() for c in header_row]
	header_set  = set(header_norm)

	# Older PNC: separate Withdrawals + Deposits columns.
	if {'withdrawals', 'deposits'}.issubset(header_set):
		return 'pnc'

	# Newer PNC Account Activity: Transaction Date / Transaction Description /
	# Amount [/ Category / Balance]. Single signed Amount column.
	if ('transaction date' in header_set and
	    'transaction description' in header_set and
	    'amount' in header_set):
		return 'pnc_activity'

	# Generic — any CSV with date + description + amount.
	has_date   = any(c in header_set for c in _DATE_ALIASES)
	has_desc   = any(c in header_set for c in _DESC_ALIASES)
	has_amount = any(c in header_set for c in _AMOUNT_ALIASES)
	if has_date and has_desc and has_amount:
		return 'generic_v1'

	return 'unknown'


def parse_csv(content, format_hint=None, column_map=None):
	"""Parse CSV content into a list of normalized {date, description, amount}
	records. Amounts normalized so positive = outflow (money leaving
	checking), negative = inflow (income / refund / transfer-in).

	Dialect (comma / tab / semicolon / pipe) is auto-detected via
	csv.Sniffer. PNC sometimes ships tab-separated content with a .csv
	extension; this handles both transparently.

	If format_hint is None, format is auto-detected. If detection fails
	and column_map is provided, falls back to that mapping.

	column_map shape (for the generic fallback):
	  {'date': 'Posted', 'description': 'Memo', 'amount': 'Amount'}

	Returns (records, detected_format).
	"""
	# Sniff dialect from a representative chunk; fall back to comma on failure.
	try:
		dialect = csv.Sniffer().sniff(content[:8192], delimiters=',\t;|')
	except csv.Error:
		class _D(csv.Dialect):
			delimiter = ','
			quotechar = '"'
			doublequote = True
			skipinitialspace = True
			lineterminator = '\n'
			quoting = csv.QUOTE_MINIMAL
		dialect = _D
	reader = csv.reader(io.StringIO(content), dialect=dialect)
	rows = list(reader)
	if not rows:
		return [], 'unknown'

	header = rows[0]
	body   = rows[1:]
	sample = body[:5]

	fmt = format_hint or detect_format(header, sample)

	if fmt == 'pnc':
		records = _parse_pnc(header, body)
	elif fmt == 'pnc_activity':
		records = _parse_pnc_activity(header, body)
	elif fmt == 'generic_v1':
		records = _parse_generic(header, body)
	elif column_map:
		records = _parse_generic(header, body, column_map=column_map)
		fmt = 'generic_v1'
	else:
		records = []
		fmt = 'unknown'

	return records, fmt


def _find_col(header_norm, *names):
	for n in names:
		if n in header_norm:
			return header_norm.index(n)
	return None


def _to_float(s):
	if s is None:
		return 0.0
	s = str(s).strip()
	if not s:
		return 0.0
	# Strip $ and commas; handle parens for negatives.
	neg = s.startswith('(') and s.endswith(')')
	s = s.replace('$', '').replace(',', '').replace('(', '').replace(')', '')
	try:
		v = float(s)
	except ValueError:
		return 0.0
	return -v if neg else v


def _normalize_date(s):
	"""Parse a date string and return ISO format YYYY-MM-DD, or '' if unparseable.

	Strips the 'PENDING - ' / 'Pending - ' prefix that PNC's
	accountActivityExport adds to as-yet-unposted transaction dates.
	The pending status is captured separately by the parser (see
	_is_pending_date) so the cleaned date reads as ISO."""
	if not s:
		return ''
	s = s.strip()
	# Strip 'PENDING - ' / 'Pending - ' prefix (PNC accountActivityExport).
	stripped = re.sub(r'^pending\s*-\s*', '', s, flags=re.IGNORECASE).strip()
	for fmt in ('%Y-%m-%d', '%m/%d/%Y', '%m/%d/%y', '%Y/%m/%d', '%d-%b-%Y'):
		try:
			return datetime.strptime(stripped, fmt).date().isoformat()
		except ValueError:
			continue
	return stripped or s


def _is_pending_date(s):
	"""True if the raw date column is a PNC 'PENDING - …' marker."""
	if not s:
		return False
	return bool(re.match(r'^\s*pending\s*-', s, flags=re.IGNORECASE))


def _parse_pnc(header, body):
	"""PNC personal checking format. Withdrawals (outflows) - Deposits (inflows)."""
	header_norm = [(c or '').strip().lower() for c in header]
	i_date  = _find_col(header_norm, 'date', 'posted', 'posted date', 'transaction date')
	i_desc  = _find_col(header_norm, 'description', 'memo', 'payee')
	i_with  = _find_col(header_norm, 'withdrawals', 'withdrawal')
	i_dep   = _find_col(header_norm, 'deposits', 'deposit')
	out = []
	for r in body:
		if not r or all(not (c or '').strip() for c in r):
			continue
		date_s = r[i_date] if i_date is not None and i_date < len(r) else ''
		desc   = r[i_desc] if i_desc is not None and i_desc < len(r) else ''
		wd     = _to_float(r[i_with]) if i_with is not None and i_with < len(r) else 0
		dp     = _to_float(r[i_dep])  if i_dep  is not None and i_dep  < len(r) else 0
		amount = wd - dp  # outflow positive, inflow negative
		out.append({
			'date':        _normalize_date(date_s),
			'description': (desc or '').strip(),
			'amount':      amount,
		})
	return out


def _parse_pnc_activity(header, body):
	"""PNC 'accountActivityExport.csv' format.

	Headers: Transaction Date, Transaction Description, Amount, Category, Balance.

	Sign convention (confirmed from real Aaron data 2026-05-26):
	  POSTED row, parens   ($500)  → outflow (debit)
	  POSTED row, positive  $2,194.24 → inflow (credit / deposit)
	  PENDING row, positive $238.60 → outflow (pending charge — will
	                                  become parens when it posts)
	  PENDING row, parens   ($500)  → outflow (already-debited pending)

	We always store positive = outflow downstream. Translate accordingly:
	  - Parens-negative anywhere  → outflow (flip to positive)
	  - Positive on PENDING       → outflow (keep positive)
	  - Positive on POSTED        → inflow  (negate to negative)
	"""
	header_norm = [(c or '').strip().lower() for c in header]
	i_date = _find_col(header_norm, 'transaction date', 'date', 'posted date')
	i_desc = _find_col(header_norm, 'transaction description', 'description', 'memo')
	i_amt  = _find_col(header_norm, 'amount')
	out = []
	for r in body:
		if not r or all(not (c or '').strip() for c in r):
			continue
		raw_date = r[i_date] if i_date is not None and i_date < len(r) else ''
		desc     = r[i_desc] if i_desc is not None and i_desc < len(r) else ''
		raw_amt  = r[i_amt]  if i_amt  is not None and i_amt  < len(r) else ''
		raw_amt_s = (raw_amt or '').strip()
		parsed    = _to_float(raw_amt_s)
		is_parens = raw_amt_s.startswith('(') and raw_amt_s.endswith(')')
		pending   = _is_pending_date(raw_date)
		if is_parens:
			amount = abs(parsed)              # parens → outflow
		elif pending:
			amount = abs(parsed)              # pending charge → outflow
		else:
			amount = -abs(parsed)             # posted positive → inflow
		out.append({
			'date':        _normalize_date(raw_date),
			'description': (desc or '').strip(),
			'amount':      amount,
		})
	return out


def _parse_generic(header, body, column_map=None):
	"""Generic CSV with date/description/amount columns.

	Convention: amount column positive = outflow. If your CSV uses the
	opposite convention (positive deposits, negative withdrawals), the
	user can correct via column_map or a future format flag — v1 assumes
	the conventional sign.
	"""
	header_norm = [(c or '').strip().lower() for c in header]
	if column_map:
		i_date  = header_norm.index(column_map['date'].lower()) if column_map.get('date') and column_map['date'].lower() in header_norm else None
		i_desc  = header_norm.index(column_map['description'].lower()) if column_map.get('description') and column_map['description'].lower() in header_norm else None
		i_amt   = header_norm.index(column_map['amount'].lower()) if column_map.get('amount') and column_map['amount'].lower() in header_norm else None
	else:
		i_date  = _find_col(header_norm, 'date', 'posted', 'posted date', 'transaction date')
		i_desc  = _find_col(header_norm, 'description', 'memo', 'name', 'payee', 'merchant')
		i_amt   = _find_col(header_norm, 'amount', 'transaction amount')

	out = []
	for r in body:
		if not r or all(not (c or '').strip() for c in r):
			continue
		date_s = r[i_date] if i_date is not None and i_date < len(r) else ''
		desc   = r[i_desc] if i_desc is not None and i_desc < len(r) else ''
		amount = _to_float(r[i_amt]) if i_amt is not None and i_amt < len(r) else 0
		out.append({
			'date':        _normalize_date(date_s),
			'description': (desc or '').strip(),
			'amount':      amount,
		})
	return out


# ---- auto-categorization ----

def categorize_with_rules(description, rules):
	"""Run priority-ordered rules. First match wins. Returns (category,
	subcategory, rule_id) or ('Uncategorized', None, None) if no match.

	`rules` is an iterable of dict-like rows from leak_rules with keys:
	id, match_type, match_value, category, subcategory, priority.
	Assumes rules already filtered to active=1 and ordered by priority ASC.
	"""
	desc = (description or '')
	desc_lower = desc.lower()
	for r in rules:
		mtype  = (r['match_type'] or 'contains').lower()
		mvalue = (r['match_value'] or '')
		if not mvalue:
			continue
		mlower = mvalue.lower()
		hit = False
		if mtype == 'contains':
			hit = mlower in desc_lower
		elif mtype == 'starts_with':
			hit = desc_lower.startswith(mlower)
		elif mtype == 'equals':
			hit = desc.strip().lower() == mlower
		elif mtype == 'regex':
			try:
				hit = re.search(mvalue, desc) is not None
			except re.error:
				hit = False
		if hit:
			return (r['category'], r.get('subcategory') if isinstance(r, dict) else r['subcategory'], r['id'])
	return ('Uncategorized', None, None)


# ---- recurring-charge detection ----

def detect_recurring(transactions, amount_tolerance=0.05):
	"""Flag transactions whose description appears ≥2 times in the import
	with amounts within ±5% of each other.

	Returns a set of transaction list-indices (zero-based positions in
	the passed-in list) that should be flagged as recurring.
	"""
	by_desc = defaultdict(list)
	for i, t in enumerate(transactions):
		key = (t.get('description') or '').strip().upper()
		if not key:
			continue
		# Only outflows can be "recurring charges" in the subscription sense.
		# Inflows being recurring (paychecks) isn't useful here.
		if (t.get('amount') or 0) <= 0:
			continue
		by_desc[key].append(i)

	flagged = set()
	for key, idxs in by_desc.items():
		if len(idxs) < 2:
			continue
		amts = [transactions[i]['amount'] for i in idxs]
		mean = sum(amts) / len(amts)
		if mean <= 0:
			continue
		within = all(abs(a - mean) / mean <= amount_tolerance for a in amts)
		if within:
			for i in idxs:
				flagged.add(i)
	return flagged


# ---- breakdown / stats for results view ----

def category_breakdown(transactions):
	"""Compute the breakdown used by the results page.

	`transactions` is a list of dict-like rows with keys:
	  category, amount, is_recurring

	Returns a list of dicts, sorted by total desc:
	  {category, total, percent_of_outflow, count, avg, is_excluded}
	"""
	totals = defaultdict(lambda: {'total': 0.0, 'count': 0})
	total_outflow = 0.0
	for t in transactions:
		cat = (t.get('category') if isinstance(t, dict) else t['category']) or 'Uncategorized'
		amt = (t.get('amount') if isinstance(t, dict) else t['amount']) or 0
		totals[cat]['total'] += amt
		totals[cat]['count'] += 1
		if amt > 0 and cat not in EXCLUDED_FROM_LEAK:
			total_outflow += amt

	rows = []
	for cat, agg in totals.items():
		pct = (agg['total'] / total_outflow * 100) if (total_outflow > 0 and agg['total'] > 0 and cat not in EXCLUDED_FROM_LEAK) else 0
		rows.append({
			'category':           cat,
			'total':              agg['total'],
			'percent_of_outflow': pct,
			'count':              agg['count'],
			'avg':                agg['total'] / agg['count'] if agg['count'] else 0,
			'is_excluded':        cat in EXCLUDED_FROM_LEAK,
		})
	rows.sort(key=lambda r: r['total'], reverse=True)
	return rows, total_outflow


def biggest_transactions(transactions, n=10):
	"""Top N transactions by absolute outflow amount."""
	outs = [t for t in transactions if (t.get('amount') if isinstance(t, dict) else t['amount']) > 0]
	outs.sort(key=lambda t: (t.get('amount') if isinstance(t, dict) else t['amount']) or 0, reverse=True)
	return outs[:n]


def recurring_charges_summary(transactions):
	"""Group recurring-flagged transactions by description for the
	"Recurring charges detected" callout. Returns list of
	{description, count, avg_amount, total} sorted by avg_amount desc."""
	groups = defaultdict(lambda: {'count': 0, 'total': 0.0})
	for t in transactions:
		is_rec = (t.get('is_recurring') if isinstance(t, dict) else t['is_recurring']) or 0
		if not is_rec:
			continue
		amt = (t.get('amount') if isinstance(t, dict) else t['amount']) or 0
		if amt <= 0:
			continue
		desc = (t.get('description') if isinstance(t, dict) else t['description']) or ''
		key = desc.strip().upper()
		groups[key]['count'] += 1
		groups[key]['total'] += amt
		groups[key]['description'] = desc  # preserve original case from first match
	out = []
	for key, g in groups.items():
		g['avg_amount'] = g['total'] / g['count'] if g['count'] else 0
		out.append(g)
	out.sort(key=lambda g: g['avg_amount'], reverse=True)
	return out
