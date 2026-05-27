"""
The Ledger blueprint — personal debt elimination + cash runway.

See .kt/spec-ledger.md for the canonical spec and .kt/KT-ledger.md for
ongoing maintenance notes.

Cardinal design rule: this is the chart-room, not the cockpit. The user
opens it twice a month, around paydays, to answer "where am I and what
do I do next?" — never the daily logging app. Every route should make
that question easier to answer.
"""
import os
import io
import csv
import json
import logging
import re
from datetime import datetime, date, timedelta

import pytz
from flask import Blueprint, request, redirect, url_for, render_template, jsonify, flash

from helpers.auth import is_authenticated, cd_auth_required
from helpers.db import get_ledger_db
from helpers import ledger as L


logger = logging.getLogger(__name__)

ledger_bp = Blueprint('ledger', __name__, url_prefix='/ledger')


# ---- small utilities ----

def _form_float(name, default=None):
	"""Parse a form value as float, accepting blank/None."""
	v = request.form.get(name, '').strip()
	if v == '':
		return default
	try:
		return float(v)
	except ValueError:
		return default


def _form_int(name, default=None):
	v = request.form.get(name, '').strip()
	if v == '':
		return default
	try:
		return int(v)
	except ValueError:
		return default


def _slugify(text):
	text = (text or '').lower().strip()
	text = re.sub(r'[^\w\s-]', '', text)
	text = re.sub(r'[\s_-]+', '-', text)
	text = re.sub(r'^-+|-+$', '', text)
	return text or 'account'


def _unique_slug(conn, base, exclude_id=None):
	slug = base
	n = 2
	while True:
		if exclude_id:
			row = conn.execute(
				"SELECT id FROM accounts WHERE slug = ? AND id != ?",
				(slug, exclude_id)
			).fetchone()
		else:
			row = conn.execute(
				"SELECT id FROM accounts WHERE slug = ?", (slug,)
			).fetchone()
		if not row:
			return slug
		slug = f'{base}-{n}'
		n += 1


def _accounts_with_balances(conn, include_paid_off=False, types=None):
	"""Return list of account dicts with current_balance + stale flags."""
	rows = conn.execute("SELECT * FROM accounts ORDER BY status, name").fetchall()
	out = []
	for r in rows:
		d = dict(r)
		if not include_paid_off and d['status'] == 'paid_off':
			continue
		if types and d['account_type'] not in types:
			continue
		d['current_balance'] = L.latest_balance(conn, d['id'])
		d['snapshot_at']     = L.latest_snapshot_at(conn, d['id'])
		d['stale_snapshot']  = L.stale_snapshot(conn, d['id'])
		d['stale_autopay']   = L.stale_autopay(conn, d['id']) if d['autopay_enabled'] else False
		out.append(d)
	return out


# ---- main display ----

@ledger_bp.route('/')
@cd_auth_required
def glance():
	conn = get_ledger_db()
	# Materialize any due autopay expectations before reading state.
	L.generate_autopay_expectations(conn)

	td = L.total_debt(conn)
	td_30 = L.total_debt_n_days_ago(conn, 30)
	delta_30 = (td - td_30) if td_30 is not None else None
	interest_burn = L.monthly_interest_burn(conn)
	runway = L.cash_runway(conn)
	budget = L.attack_budget(conn)
	projection = L.project_payoff(conn)
	avalanche = L.avalanche_order(conn)

	# Pending autopay rows (with account name for display)
	pending = conn.execute("""
		SELECT t.*, a.name AS account_name, a.slug AS account_slug
		FROM debt_transactions t
		JOIN accounts a ON a.id = t.account_id
		WHERE t.confirmed = 0 AND t.tx_type = 'payment'
		ORDER BY t.tx_date ASC
	""").fetchall()

	# Coming up — one-time events in next 30 days
	today = L.et_today()
	horizon = (today + timedelta(days=30)).isoformat()
	coming_up = conn.execute("""
		SELECT * FROM one_time_events
		WHERE status = 'planned' AND event_date >= ? AND event_date <= ?
		ORDER BY event_date
	""", (today.isoformat(), horizon)).fetchall()

	# This-month activity: count + last payment
	month_start = date(today.year, today.month, 1).isoformat()
	this_month = conn.execute("""
		SELECT COUNT(*) AS n, COALESCE(SUM(amount), 0) AS s
		FROM debt_transactions
		WHERE tx_type = 'payment' AND confirmed = 1 AND tx_date >= ?
	""", (month_start,)).fetchone()
	last_payment = conn.execute("""
		SELECT t.*, a.name AS account_name
		FROM debt_transactions t JOIN accounts a ON a.id = t.account_id
		WHERE t.tx_type = 'payment' AND t.confirmed = 1
		ORDER BY t.tx_date DESC, t.id DESC LIMIT 1
	""").fetchone()

	# avalanche order rows with stale flags merged in for the table
	for d in avalanche:
		d['snapshot_at']    = L.latest_snapshot_at(conn, d['id'])
		d['stale_snapshot'] = L.stale_snapshot(conn, d['id'])

	# all accounts (with checking) for sidebar / debug
	all_accounts = _accounts_with_balances(conn, include_paid_off=False)

	conn.close()

	return render_template(
		'ledger_glance.html',
		total_debt=td,
		delta_30=delta_30,
		interest_burn=interest_burn,
		runway=runway,
		budget=budget,
		projection=projection,
		avalanche=avalanche,
		pending=pending,
		coming_up=coming_up,
		this_month=this_month,
		last_payment=last_payment,
		all_accounts=all_accounts,
		today=today.isoformat(),
	)


@ledger_bp.route('/payday/')
@cd_auth_required
def payday_form():
	conn = get_ledger_db()
	L.generate_autopay_expectations(conn)

	runway = L.cash_runway(conn)
	expected_checking = L.expected_checking_balance(conn)
	budget = L.attack_budget(conn)
	projection = L.project_payoff(conn)

	pending = conn.execute("""
		SELECT t.*, a.name AS account_name, a.slug AS account_slug
		FROM debt_transactions t
		JOIN accounts a ON a.id = t.account_id
		WHERE t.confirmed = 0 AND t.tx_type = 'payment'
		ORDER BY t.tx_date ASC
	""").fetchall()

	# Most-recent income event of type paycheck — pre-fill amount
	last_paycheck = conn.execute("""
		SELECT * FROM income_events
		WHERE income_type = 'paycheck'
		ORDER BY event_date DESC LIMIT 1
	""").fetchone()

	debts = L.list_active_debts(conn)
	for d in debts:
		d['current_balance'] = L.latest_balance(conn, d['id'])

	conn.close()

	return render_template(
		'ledger_payday.html',
		runway=runway,
		expected_checking=expected_checking,
		budget=budget,
		projection=projection,
		pending=pending,
		last_paycheck=last_paycheck,
		debts=debts,
		today=L.et_today().isoformat(),
	)


@ledger_bp.route('/payday/session', methods=['POST'])
@cd_auth_required
def payday_session():
	"""Atomic write of a complete payday session.

	Form payload (subset — see template for full list):
	  checking_balance              float, optional (creates snapshot for checking)
	  checking_notes                text
	  confirm[<tx_id>]              'as_expected' | 'different' | 'skip'
	  actual_amount[<tx_id>]        float (only when 'different')
	  income_amount[<i>]            float
	  income_source[<i>]            text
	  income_type[<i>]              'paycheck' | 'bonus' | ...
	  income_date[<i>]              ISO date
	  manual_account_slug[<j>]      account slug
	  manual_amount[<j>]            float
	  manual_date[<j>]              ISO date
	  manual_notes[<j>]             text
	  balance_account_slug[<k>]     slug
	  balance_value[<k>]            float
	  balance_notes[<k>]            text
	"""
	conn = get_ledger_db()
	now = L.et_now_iso()
	checking_id = L.get_setting(conn, 'checking_account_id')

	# 1. Checking snapshot
	cb = _form_float('checking_balance')
	if cb is not None and checking_id:
		snap_at = L.utc_now_iso()
		conn.execute("""
			INSERT INTO balance_snapshots (
				account_id, balance, snapshot_at, source, notes, created
			) VALUES (?, ?, ?, 'manual', ?, ?)
		""", (checking_id, cb, snap_at,
		      request.form.get('checking_notes', '').strip() or None, now))

	# 2. Confirm pending autopay rows
	for key, val in request.form.items():
		if not key.startswith('confirm['):
			continue
		try:
			tx_id = int(key[len('confirm['):-1])
		except ValueError:
			continue
		row = conn.execute(
			"SELECT * FROM debt_transactions WHERE id = ?", (tx_id,)
		).fetchone()
		if not row or row['confirmed']:
			continue

		if val == 'as_expected':
			conn.execute("""
				UPDATE debt_transactions
				SET confirmed = 1, source = 'autopay_confirmed', updated = ?
				WHERE id = ?
			""", (now, tx_id))
		elif val == 'different':
			actual = _form_float(f'actual_amount[{tx_id}]', row['amount'])
			notes  = request.form.get(f'actual_notes[{tx_id}]', '').strip() or None
			conn.execute("""
				UPDATE debt_transactions
				SET amount = ?, notes = ?, confirmed = 1,
				    source = 'autopay_confirmed', updated = ?
				WHERE id = ?
			""", (actual, notes, now, tx_id))
		elif val == 'skip':
			# Mark as confirmed but zero — autopay didn't run.
			conn.execute("""
				UPDATE debt_transactions
				SET amount = 0, notes = COALESCE(notes,'') || ' [skipped on payday]',
				    confirmed = 1, source = 'autopay_confirmed', updated = ?
				WHERE id = ?
			""", (now, tx_id))

	# 3. Income events
	i = 0
	while True:
		amt = _form_float(f'income_amount[{i}]')
		if amt is None:
			break
		if amt > 0:
			conn.execute("""
				INSERT INTO income_events (
					event_date, amount, income_type, source,
					recurring, recurrence_pattern, notes, created
				) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
			""", (
				request.form.get(f'income_date[{i}]') or L.et_today().isoformat(),
				amt,
				request.form.get(f'income_type[{i}]', 'paycheck'),
				request.form.get(f'income_source[{i}]', '').strip() or None,
				1 if request.form.get(f'income_recurring[{i}]') else 0,
				request.form.get(f'income_pattern[{i}]', '').strip() or None,
				request.form.get(f'income_notes[{i}]', '').strip() or None,
				now,
			))
		i += 1

	# 4. Manual debt payments
	j = 0
	while True:
		slug = request.form.get(f'manual_account_slug[{j}]', '').strip()
		if not slug:
			break
		amt = _form_float(f'manual_amount[{j}]')
		if amt and amt > 0:
			row = conn.execute(
				"SELECT id FROM accounts WHERE slug = ?", (slug,)
			).fetchone()
			if row:
				conn.execute("""
					INSERT INTO debt_transactions (
						account_id, tx_date, amount, tx_type, source,
						confirmed, description, notes, created, updated
					) VALUES (?, ?, ?, 'payment', 'manual', 1, ?, ?, ?, ?)
				""", (row['id'],
				      request.form.get(f'manual_date[{j}]') or L.et_today().isoformat(),
				      amt,
				      request.form.get(f'manual_desc[{j}]', '').strip() or 'Manual payment',
				      request.form.get(f'manual_notes[{j}]', '').strip() or None,
				      now, now))
		j += 1

	# 5. Balance snapshots (other accounts)
	k = 0
	while True:
		slug = request.form.get(f'balance_account_slug[{k}]', '').strip()
		if not slug:
			break
		val = _form_float(f'balance_value[{k}]')
		if val is not None:
			row = conn.execute(
				"SELECT id FROM accounts WHERE slug = ?", (slug,)
			).fetchone()
			if row:
				conn.execute("""
					INSERT INTO balance_snapshots (
						account_id, balance, snapshot_at, source, notes, created
					) VALUES (?, ?, ?, 'manual', ?, ?)
				""", (row['id'], val, L.utc_now_iso(),
				      request.form.get(f'balance_notes[{k}]', '').strip() or None,
				      now))
		k += 1

	conn.commit()
	conn.close()

	flash('Payday session saved. Take a deep breath.', 'ok')
	return redirect(url_for('ledger.glance'))


# ---- account list + detail ----

@ledger_bp.route('/accounts/')
@cd_auth_required
def accounts_list():
	conn = get_ledger_db()
	accounts = _accounts_with_balances(conn, include_paid_off=True)
	conn.close()
	return render_template('ledger_accounts.html', accounts=accounts)


@ledger_bp.route('/accounts/<slug>/')
@cd_auth_required
def account_detail(slug):
	conn = get_ledger_db()
	row = conn.execute(
		"SELECT * FROM accounts WHERE slug = ?", (slug,)
	).fetchone()
	if not row:
		conn.close()
		return redirect(url_for('ledger.accounts_list'))
	acc = dict(row)
	acc['current_balance'] = L.latest_balance(conn, acc['id'])
	acc['snapshot_at']     = L.latest_snapshot_at(conn, acc['id'])

	snapshots = conn.execute("""
		SELECT * FROM balance_snapshots
		WHERE account_id = ?
		ORDER BY snapshot_at DESC, id DESC LIMIT 100
	""", (acc['id'],)).fetchall()

	transactions = conn.execute("""
		SELECT * FROM debt_transactions
		WHERE account_id = ?
		ORDER BY tx_date DESC, id DESC LIMIT 100
	""", (acc['id'],)).fetchall()

	# Build a sparkline series — oldest → newest, capped at 30 most recent.
	spark = [{'at': s['snapshot_at'], 'balance': s['balance']}
	         for s in reversed(list(snapshots)[-30:])]

	conn.close()
	return render_template(
		'ledger_account.html',
		account=acc,
		snapshots=snapshots,
		transactions=transactions,
		spark=spark,
	)


@ledger_bp.route('/accounts/new', methods=['POST'])
@cd_auth_required
def account_new():
	conn = get_ledger_db()
	name = request.form.get('name', '').strip()
	if not name:
		conn.close()
		flash('Account needs a name.', 'error')
		return redirect(url_for('ledger.accounts_list'))
	slug = _unique_slug(conn, _slugify(name))
	now = L.et_now_iso()
	conn.execute("""
		INSERT INTO accounts (
			name, slug, account_type, status, apr, minimum_payment,
			attack_allocation, autopay_enabled, autopay_amount,
			autopay_cadence, autopay_day, opened_date, notes,
			created, updated
		) VALUES (?, ?, ?, 'active', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
	""", (
		name, slug,
		request.form.get('account_type', 'credit_card'),
		_form_float('apr'),
		_form_float('minimum_payment'),
		_form_float('attack_allocation', 0) or 0,
		1 if request.form.get('autopay_enabled') else 0,
		_form_float('autopay_amount'),
		request.form.get('autopay_cadence', '').strip() or None,
		_form_int('autopay_day'),
		request.form.get('opened_date', '').strip() or None,
		request.form.get('notes', '').strip() or None,
		now, now,
	))

	# Optional opening balance
	opening = _form_float('opening_balance')
	if opening is not None:
		acc_row = conn.execute(
			"SELECT id FROM accounts WHERE slug = ?", (slug,)
		).fetchone()
		conn.execute("""
			INSERT INTO balance_snapshots (
				account_id, balance, snapshot_at, source, notes, created
			) VALUES (?, ?, ?, 'manual', 'Opening balance', ?)
		""", (acc_row['id'], opening, L.utc_now_iso(), now))

	conn.commit()
	conn.close()
	flash(f'{name} added.', 'ok')
	return redirect(url_for('ledger.account_detail', slug=slug))


@ledger_bp.route('/accounts/<slug>/edit', methods=['POST'])
@cd_auth_required
def account_edit(slug):
	conn = get_ledger_db()
	row = conn.execute(
		"SELECT * FROM accounts WHERE slug = ?", (slug,)
	).fetchone()
	if not row:
		conn.close()
		return redirect(url_for('ledger.accounts_list'))

	now = L.et_now_iso()
	new_name = request.form.get('name', row['name']).strip() or row['name']
	conn.execute("""
		UPDATE accounts
		SET name = ?,
		    account_type = ?,
		    status = ?,
		    apr = ?,
		    minimum_payment = ?,
		    attack_allocation = ?,
		    autopay_enabled = ?,
		    autopay_amount = ?,
		    autopay_cadence = ?,
		    autopay_day = ?,
		    autopay_next_date = ?,
		    opened_date = ?,
		    notes = ?,
		    updated = ?
		WHERE id = ?
	""", (
		new_name,
		request.form.get('account_type', row['account_type']),
		request.form.get('status', row['status']),
		_form_float('apr', row['apr']),
		_form_float('minimum_payment', row['minimum_payment']),
		_form_float('attack_allocation', row['attack_allocation']) or 0,
		1 if request.form.get('autopay_enabled') else 0,
		_form_float('autopay_amount', row['autopay_amount']),
		request.form.get('autopay_cadence', row['autopay_cadence'] or '') or None,
		_form_int('autopay_day', row['autopay_day']),
		request.form.get('autopay_next_date', row['autopay_next_date'] or '') or None,
		request.form.get('opened_date', row['opened_date'] or '') or None,
		request.form.get('notes', row['notes'] or '') or None,
		now, row['id']
	))
	conn.commit()
	conn.close()
	flash(f'{new_name} updated.', 'ok')
	return redirect(url_for('ledger.account_detail', slug=slug))


@ledger_bp.route('/accounts/<slug>/mark-paid-off', methods=['POST'])
@cd_auth_required
def account_mark_paid_off(slug):
	conn = get_ledger_db()
	row = conn.execute(
		"SELECT * FROM accounts WHERE slug = ?", (slug,)
	).fetchone()
	if not row:
		conn.close()
		return redirect(url_for('ledger.accounts_list'))
	now = L.et_now_iso()
	conn.execute(
		"UPDATE accounts SET status = 'paid_off', updated = ? WHERE id = ?",
		(now, row['id']))
	# Final zero snapshot for clarity.
	conn.execute("""
		INSERT INTO balance_snapshots (
			account_id, balance, snapshot_at, source, notes, created
		) VALUES (?, 0, ?, 'manual', 'Marked paid off', ?)
	""", (row['id'], L.utc_now_iso(), now))
	conn.commit()
	next_account, freed = L.cascade_attack_allocation(conn, row['id'])
	conn.close()
	if next_account and freed > 0:
		flash(f'{row["name"]} killed. ${freed:.2f}/month inherited by {next_account["name"]}.', 'ok')
	else:
		flash(f'{row["name"]} marked paid off.', 'ok')
	return redirect(url_for('ledger.account_detail', slug=slug))


@ledger_bp.route('/accounts/<slug>/delete', methods=['POST'])
@cd_auth_required
def account_delete(slug):
	conn = get_ledger_db()
	row = conn.execute(
		"SELECT * FROM accounts WHERE slug = ?", (slug,)
	).fetchone()
	if not row:
		conn.close()
		return redirect(url_for('ledger.accounts_list'))
	now = L.et_now_iso()
	conn.execute(
		"UPDATE accounts SET status = 'closed', updated = ? WHERE id = ?",
		(now, row['id']))
	conn.commit()
	conn.close()
	flash(f'{row["name"]} closed (history retained).', 'ok')
	return redirect(url_for('ledger.accounts_list'))


# ---- balance snapshots ----

@ledger_bp.route('/snapshot', methods=['POST'])
@cd_auth_required
def snapshot_one():
	conn = get_ledger_db()
	slug = request.form.get('account_slug', '').strip()
	bal = _form_float('balance')
	row = conn.execute(
		"SELECT id FROM accounts WHERE slug = ?", (slug,)
	).fetchone()
	if not row or bal is None:
		conn.close()
		flash('Snapshot needs account and balance.', 'error')
		return redirect(url_for('ledger.glance'))
	conn.execute("""
		INSERT INTO balance_snapshots (
			account_id, balance, snapshot_at, source, notes, created
		) VALUES (?, ?, ?, 'manual', ?, ?)
	""", (row['id'], bal, L.utc_now_iso(),
	      request.form.get('notes', '').strip() or None,
	      L.et_now_iso()))
	conn.commit()
	conn.close()
	flash('Snapshot saved.', 'ok')
	next_url = request.form.get('next') or url_for('ledger.account_detail', slug=slug)
	return redirect(next_url)


# ---- transactions ----

@ledger_bp.route('/transactions/new', methods=['POST'])
@cd_auth_required
def tx_new():
	conn = get_ledger_db()
	slug = request.form.get('account_slug', '').strip()
	row = conn.execute(
		"SELECT id FROM accounts WHERE slug = ?", (slug,)
	).fetchone()
	if not row:
		conn.close()
		flash('Transaction needs a valid account.', 'error')
		return redirect(url_for('ledger.glance'))
	now = L.et_now_iso()
	conn.execute("""
		INSERT INTO debt_transactions (
			account_id, tx_date, amount, tx_type, source, confirmed,
			description, notes, created, updated
		) VALUES (?, ?, ?, ?, 'manual', 1, ?, ?, ?, ?)
	""", (
		row['id'],
		request.form.get('tx_date') or L.et_today().isoformat(),
		_form_float('amount', 0) or 0,
		request.form.get('tx_type', 'payment'),
		request.form.get('description', '').strip() or None,
		request.form.get('notes', '').strip() or None,
		now, now,
	))
	conn.commit()
	conn.close()
	flash('Transaction recorded.', 'ok')
	return redirect(request.form.get('next') or url_for('ledger.account_detail', slug=slug))


@ledger_bp.route('/transactions/<int:tx_id>/confirm', methods=['POST'])
@cd_auth_required
def tx_confirm(tx_id):
	conn = get_ledger_db()
	now = L.et_now_iso()
	amt = _form_float('amount')
	if amt is not None:
		conn.execute("""
			UPDATE debt_transactions
			SET amount = ?, confirmed = 1, source = 'autopay_confirmed', updated = ?
			WHERE id = ?
		""", (amt, now, tx_id))
	else:
		conn.execute("""
			UPDATE debt_transactions
			SET confirmed = 1, source = 'autopay_confirmed', updated = ?
			WHERE id = ?
		""", (now, tx_id))
	conn.commit()
	conn.close()
	if request.headers.get('X-Requested-With') == 'fetch':
		return jsonify({'ok': True})
	return redirect(request.form.get('next') or url_for('ledger.glance'))


@ledger_bp.route('/transactions/<int:tx_id>/edit', methods=['POST'])
@cd_auth_required
def tx_edit(tx_id):
	conn = get_ledger_db()
	now = L.et_now_iso()
	conn.execute("""
		UPDATE debt_transactions
		SET tx_date = ?, amount = ?, tx_type = ?, description = ?,
		    notes = ?, updated = ?
		WHERE id = ?
	""", (
		request.form.get('tx_date') or L.et_today().isoformat(),
		_form_float('amount', 0) or 0,
		request.form.get('tx_type', 'payment'),
		request.form.get('description', '').strip() or None,
		request.form.get('notes', '').strip() or None,
		now, tx_id,
	))
	conn.commit()
	conn.close()
	return redirect(request.form.get('next') or url_for('ledger.glance'))


@ledger_bp.route('/transactions/<int:tx_id>/delete', methods=['POST'])
@cd_auth_required
def tx_delete(tx_id):
	conn = get_ledger_db()
	conn.execute("DELETE FROM debt_transactions WHERE id = ?", (tx_id,))
	conn.commit()
	conn.close()
	return redirect(request.form.get('next') or url_for('ledger.glance'))


# ---- income ----

@ledger_bp.route('/income/')
@cd_auth_required
def income_list():
	conn = get_ledger_db()
	rows = conn.execute(
		"SELECT * FROM income_events ORDER BY event_date DESC, id DESC"
	).fetchall()
	conn.close()
	return render_template('ledger_income.html', events=rows)


@ledger_bp.route('/income/<int:eid>/edit', methods=['POST'])
@cd_auth_required
def income_edit(eid):
	conn = get_ledger_db()
	conn.execute("""
		UPDATE income_events
		SET event_date = ?, amount = ?, income_type = ?, source = ?,
		    recurring = ?, recurrence_pattern = ?, notes = ?
		WHERE id = ?
	""", (
		request.form.get('event_date') or L.et_today().isoformat(),
		_form_float('amount', 0) or 0,
		request.form.get('income_type', 'paycheck'),
		request.form.get('source', '').strip() or None,
		1 if request.form.get('recurring') else 0,
		request.form.get('recurrence_pattern', '').strip() or None,
		request.form.get('notes', '').strip() or None,
		eid,
	))
	conn.commit()
	conn.close()
	return redirect(request.form.get('next') or url_for('ledger.income_list'))


@ledger_bp.route('/income/new', methods=['POST'])
@cd_auth_required
def income_new():
	conn = get_ledger_db()
	now = L.et_now_iso()
	conn.execute("""
		INSERT INTO income_events (
			event_date, amount, income_type, source, recurring,
			recurrence_pattern, notes, created
		) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
	""", (
		request.form.get('event_date') or L.et_today().isoformat(),
		_form_float('amount', 0) or 0,
		request.form.get('income_type', 'paycheck'),
		request.form.get('source', '').strip() or None,
		1 if request.form.get('recurring') else 0,
		request.form.get('recurrence_pattern', '').strip() or None,
		request.form.get('notes', '').strip() or None,
		now,
	))
	conn.commit()
	conn.close()
	return redirect(request.form.get('next') or url_for('ledger.income_list'))


@ledger_bp.route('/income/<int:eid>/delete', methods=['POST'])
@cd_auth_required
def income_delete(eid):
	conn = get_ledger_db()
	conn.execute("DELETE FROM income_events WHERE id = ?", (eid,))
	conn.commit()
	conn.close()
	return redirect(request.form.get('next') or url_for('ledger.income_list'))


# ---- recurring expenses ----

@ledger_bp.route('/recurring/')
@cd_auth_required
def recurring_list():
	conn = get_ledger_db()
	rows = conn.execute(
		"SELECT * FROM recurring_expenses ORDER BY active DESC, day_of_month, name"
	).fetchall()
	conn.close()
	return render_template('ledger_recurring.html', expenses=rows)


@ledger_bp.route('/recurring/new', methods=['POST'])
@cd_auth_required
def recurring_new():
	conn = get_ledger_db()
	name = request.form.get('name', '').strip()
	if not name:
		conn.close()
		flash('Need a name.', 'error')
		return redirect(url_for('ledger.recurring_list'))
	now = L.et_now_iso()
	conn.execute("""
		INSERT INTO recurring_expenses (
			name, amount, day_of_month, category, active, notes, created, updated
		) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
	""", (
		name,
		_form_float('amount', 0) or 0,
		_form_int('day_of_month', 1) or 1,
		request.form.get('category', '').strip() or None,
		1, # active
		request.form.get('notes', '').strip() or None,
		now, now,
	))
	conn.commit()
	conn.close()
	flash(f'{name} added.', 'ok')
	return redirect(url_for('ledger.recurring_list'))


@ledger_bp.route('/recurring/<int:eid>/edit', methods=['POST'])
@cd_auth_required
def recurring_edit(eid):
	conn = get_ledger_db()
	now = L.et_now_iso()
	conn.execute("""
		UPDATE recurring_expenses
		SET name = ?, amount = ?, day_of_month = ?, category = ?,
		    active = ?, notes = ?, updated = ?
		WHERE id = ?
	""", (
		request.form.get('name', '').strip() or 'Unnamed',
		_form_float('amount', 0) or 0,
		_form_int('day_of_month', 1) or 1,
		request.form.get('category', '').strip() or None,
		1 if request.form.get('active') else 0,
		request.form.get('notes', '').strip() or None,
		now, eid,
	))
	conn.commit()
	conn.close()
	return redirect(url_for('ledger.recurring_list'))


@ledger_bp.route('/recurring/<int:eid>/delete', methods=['POST'])
@cd_auth_required
def recurring_delete(eid):
	"""Smart delete: if the row is still active, soft-delete it (active = 0)
	— preserves the safety net of restoring later. If it's already
	inactive, hard-delete it from the table entirely. Two clicks to
	fully remove; the confirm text in the template tells the user
	which action they're about to take."""
	conn = get_ledger_db()
	row = conn.execute(
		"SELECT name, active FROM recurring_expenses WHERE id = ?", (eid,)
	).fetchone()
	if not row:
		conn.close()
		return redirect(url_for('ledger.recurring_list'))
	if row['active']:
		conn.execute(
			"UPDATE recurring_expenses SET active = 0, updated = ? WHERE id = ?",
			(L.et_now_iso(), eid))
		flash(f'{row["name"]} deactivated. Click × again to delete permanently.', 'ok')
	else:
		conn.execute("DELETE FROM recurring_expenses WHERE id = ?", (eid,))
		flash(f'{row["name"]} deleted.', 'ok')
	conn.commit()
	conn.close()
	return redirect(url_for('ledger.recurring_list'))


# ---- one-time events ----

@ledger_bp.route('/one-time/')
@cd_auth_required
def onetime_list():
	conn = get_ledger_db()
	rows = conn.execute(
		"SELECT * FROM one_time_events ORDER BY event_date DESC"
	).fetchall()
	conn.close()
	return render_template('ledger_one_time.html', events=rows)


@ledger_bp.route('/one-time/new', methods=['POST'])
@cd_auth_required
def onetime_new():
	conn = get_ledger_db()
	desc = request.form.get('description', '').strip()
	if not desc:
		conn.close()
		flash('Need a description.', 'error')
		return redirect(url_for('ledger.onetime_list'))
	now = L.et_now_iso()
	conn.execute("""
		INSERT INTO one_time_events (
			event_date, amount, direction, description, status,
			affects_attack, notes, created
		) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
	""", (
		request.form.get('event_date') or L.et_today().isoformat(),
		_form_float('amount', 0) or 0,
		request.form.get('direction', 'outflow'),
		desc,
		request.form.get('status', 'planned'),
		1 if request.form.get('affects_attack') else 0,
		request.form.get('notes', '').strip() or None,
		now,
	))
	conn.commit()
	conn.close()
	return redirect(url_for('ledger.onetime_list'))


@ledger_bp.route('/one-time/<int:eid>/edit', methods=['POST'])
@cd_auth_required
def onetime_edit(eid):
	conn = get_ledger_db()
	conn.execute("""
		UPDATE one_time_events
		SET event_date = ?, amount = ?, direction = ?, description = ?,
		    status = ?, affects_attack = ?, notes = ?
		WHERE id = ?
	""", (
		request.form.get('event_date') or L.et_today().isoformat(),
		_form_float('amount', 0) or 0,
		request.form.get('direction', 'outflow'),
		request.form.get('description', '').strip() or 'Untitled',
		request.form.get('status', 'planned'),
		1 if request.form.get('affects_attack') else 0,
		request.form.get('notes', '').strip() or None,
		eid,
	))
	conn.commit()
	conn.close()
	return redirect(url_for('ledger.onetime_list'))


@ledger_bp.route('/one-time/<int:eid>/delete', methods=['POST'])
@cd_auth_required
def onetime_delete(eid):
	conn = get_ledger_db()
	conn.execute("DELETE FROM one_time_events WHERE id = ?", (eid,))
	conn.commit()
	conn.close()
	return redirect(url_for('ledger.onetime_list'))


# ---- history + projection ----

@ledger_bp.route('/history/')
@cd_auth_required
def history():
	conn = get_ledger_db()
	# All snapshots, grouped by month, summed across active debts
	rows = conn.execute("""
		SELECT a.id AS account_id, a.name, a.account_type, a.status,
		       bs.balance, bs.snapshot_at
		FROM balance_snapshots bs
		JOIN accounts a ON a.id = bs.account_id
		ORDER BY bs.snapshot_at
	""").fetchall()

	kill_log = conn.execute("""
		SELECT a.name, a.slug, a.status, a.attack_allocation,
		       (SELECT MAX(snapshot_at) FROM balance_snapshots
		        WHERE account_id = a.id) AS killed_at
		FROM accounts a
		WHERE a.status = 'paid_off'
		ORDER BY killed_at DESC
	""").fetchall()

	tx_history = conn.execute("""
		SELECT t.*, a.name AS account_name, a.slug AS account_slug
		FROM debt_transactions t
		JOIN accounts a ON a.id = t.account_id
		WHERE t.confirmed = 1 AND t.tx_type = 'payment'
		ORDER BY t.tx_date DESC, t.id DESC LIMIT 200
	""").fetchall()

	conn.close()
	return render_template(
		'ledger_history.html',
		snapshot_rows=rows,
		kill_log=kill_log,
		tx_history=tx_history,
	)


# ---- projection + sandbox (Phase 2) ----

# Side-income ramp presets from the spec. Plateau at the last value.
_SIDE_INCOME_RAMPS = {
	'slow':      [0, 50, 100, 200, 350, 500, 650, 800, 950, 1100, 1250, 1500],
	'realistic': [0, 100, 250, 500, 800, 1200, 1600, 2000],
}


def _resolve_side_income(spec, max_months):
	"""Resolve a side-income spec dict from the sandbox form into a
	{month_idx: amount} dict for project_payoff overrides.

	spec shape: {preset: 'none'|'slow'|'realistic'|'custom',
	             start_month_idx: int,
	             custom_amount: float,        # for preset='custom' flat start
	             custom_ramp: float}          # for preset='custom' monthly bump
	"""
	if not spec:
		return {}
	preset = (spec.get('preset') or 'none').lower()
	if preset == 'none':
		return {}
	try:
		start = int(spec.get('start_month_idx', 3))
	except (TypeError, ValueError):
		start = 3
	start = max(0, start)

	if preset in _SIDE_INCOME_RAMPS:
		amounts = _SIDE_INCOME_RAMPS[preset]
		plateau = amounts[-1]
		out = {}
		for i in range(max_months - start):
			amt = amounts[i] if i < len(amounts) else plateau
			if amt > 0:
				out[start + i] = float(amt)
		return out

	if preset == 'custom':
		try:
			base = float(spec.get('custom_amount') or 0)
			ramp = float(spec.get('custom_ramp') or 0)
		except (TypeError, ValueError):
			base = ramp = 0
		out = {}
		for i in range(max_months - start):
			amt = base + i * ramp
			if amt > 0:
				out[start + i] = amt
		return out

	return {}


def _build_overrides_from_request(body, max_months=240):
	"""Build the project_payoff overrides dict from the sandbox JSON body."""
	if not body:
		return None
	wins = []
	for w in (body.get('windfalls') or []):
		try:
			mi = int(w.get('month_idx'))
			amt = float(w.get('amount') or 0)
		except (TypeError, ValueError):
			continue
		if amt > 0:
			wins.append({'month_idx': mi, 'amount': amt})

	fedloan_amount = body.get('fedloan_override', {}).get('amount') if isinstance(body.get('fedloan_override'), dict) else body.get('fedloan_minimum')
	fedloan_starts = 0
	if isinstance(body.get('fedloan_override'), dict):
		try:
			fedloan_starts = int(body['fedloan_override'].get('starts_month_idx') or 0)
		except (TypeError, ValueError):
			fedloan_starts = 0
	if fedloan_amount in ('', None):
		fedloan_amount = None
	else:
		try:
			fedloan_amount = float(fedloan_amount)
			if fedloan_amount < 0:
				fedloan_amount = None
		except (TypeError, ValueError):
			fedloan_amount = None

	overrides = {
		'redirect_bonuses':     bool(body.get('redirect_bonuses')),
		'extra_monthly_attack': float(body.get('extra_monthly_attack') or 0),
		'side_income_by_month': _resolve_side_income(body.get('side_income') or {}, max_months),
		'windfalls':            wins,
	}
	if fedloan_amount is not None:
		overrides['fedloan_minimum'] = fedloan_amount
		overrides['fedloan_minimum_starts_month_idx'] = fedloan_starts
	return overrides


def _bonus_count(conn):
	row = conn.execute(
		"SELECT COUNT(*) AS n FROM income_events WHERE income_type = 'bonus'"
	).fetchone()
	return row['n'] if row else 0


@ledger_bp.route('/projection/')
@cd_auth_required
def projection_view():
	conn = get_ledger_db()
	projection = L.project_payoff(conn)
	target = L.current_primary_target(conn)
	next_bonus = L.next_future_bonus(conn)
	bonus_count = _bonus_count(conn)
	fedloan_row = conn.execute(
		"SELECT minimum_payment FROM accounts WHERE slug = 'fedloan-student'"
	).fetchone()
	current_fedloan_min = fedloan_row['minimum_payment'] if fedloan_row else None
	conn.close()
	return render_template(
		'ledger_projection.html',
		projection=projection,
		current_target=target,
		next_bonus=next_bonus,
		bonus_count=bonus_count,
		current_fedloan_min=current_fedloan_min,
	)


@ledger_bp.route('/projection/sandbox', methods=['POST'])
@cd_auth_required
def projection_sandbox():
	"""Re-run the projection with sandbox overrides and return both
	baseline and sandbox projections + the delta strip data as JSON."""
	body = request.get_json(silent=True) or {}
	conn = get_ledger_db()
	overrides = _build_overrides_from_request(body)
	baseline = L.project_payoff(conn)
	sandbox  = L.project_payoff(conn, overrides=overrides)
	conn.close()

	def _serialize(p):
		return {
			'debt_free_date':      p.debt_free_date,
			'total_interest_paid': round(p.total_interest_paid, 2),
			'monthly_rows':        [{
				'month':             r['month'],
				'starting_total':    round(r['starting_total'], 2),
				'minimums_applied':  round(r['minimums_applied'], 2),
				'attack_applied':    round(r['attack_applied'], 2),
				'bonus_applied':     round(r.get('bonus_applied') or 0, 2),
				'extra_applied':     round(r.get('extra_applied') or 0, 2),
				'side_income_applied': round(r.get('side_income_applied') or 0, 2),
				'windfall_applied':  round(r.get('windfall_applied') or 0, 2),
				'interest_accrued':  round(r['interest_accrued'], 2),
				'ending_total':      round(r['ending_total'], 2),
				'current_target_name': r.get('current_target_name'),
				'kill_account_name': r.get('kill_account_name'),
				'sandbox_touched':   bool(r.get('sandbox_touched')),
			} for r in p.monthly_rows],
		}

	# Months delta — negative number = sandbox finishes earlier.
	def _months_between(a, b):
		if not a or not b:
			return None
		try:
			ay, am = map(int, a.split('-'))
			by, bm = map(int, b.split('-'))
		except ValueError:
			return None
		return (by - ay) * 12 + (bm - am)

	months_delta = _months_between(baseline.debt_free_date, sandbox.debt_free_date)
	interest_saved = round(baseline.total_interest_paid - sandbox.total_interest_paid, 2)

	return jsonify({
		'baseline': _serialize(baseline),
		'sandbox':  _serialize(sandbox),
		'delta': {
			'months':          months_delta,
			'interest_saved':  interest_saved,
		},
	})


@ledger_bp.route('/projection/sandbox/apply', methods=['POST'])
@cd_auth_required
def projection_sandbox_apply():
	"""Apply the user-confirmed subset of sandbox changes to live config.

	Accepts JSON:
	  {
	    "apply_extra_attack":  500,        # bump current primary's alloc by this
	    "apply_windfalls":     [{month_idx, amount, description}, ...],
	    "apply_fedloan_min":   366
	  }

	Each field is optional. Returns the list of changes actually made.
	"""
	body = request.get_json(silent=True) or {}
	conn = get_ledger_db()
	now = L.et_now_iso()
	changes = []

	# 1. Bump current primary target's allocation
	try:
		extra = float(body.get('apply_extra_attack') or 0)
	except (TypeError, ValueError):
		extra = 0
	if extra > 0:
		target = L.current_primary_target(conn)
		if target:
			new_alloc = (target.get('attack_allocation') or 0) + extra
			conn.execute(
				"UPDATE accounts SET attack_allocation = ?, updated = ? WHERE id = ?",
				(new_alloc, now, target['id']))
			changes.append({
				'kind':    'allocation_bump',
				'account': target['name'],
				'from':    round(target.get('attack_allocation') or 0, 2),
				'to':      round(new_alloc, 2),
			})

	# 2. Windfalls → one_time_events rows
	today = L.et_today()
	month_anchor = date(today.year, today.month, 1)
	for w in (body.get('apply_windfalls') or []):
		try:
			mi = int(w.get('month_idx'))
			amt = float(w.get('amount') or 0)
		except (TypeError, ValueError):
			continue
		if amt <= 0:
			continue
		# Resolve month_idx → ISO date (15th of that month, arbitrary midpoint).
		nm = month_anchor.month + mi
		ny = month_anchor.year + (nm - 1) // 12
		nm = (nm - 1) % 12 + 1
		from calendar import monthrange
		last = monthrange(ny, nm)[1]
		ev_date = date(ny, nm, min(15, last)).isoformat()
		desc = (w.get('description') or 'Sandbox windfall').strip() or 'Sandbox windfall'
		conn.execute("""
			INSERT INTO one_time_events (
				event_date, amount, direction, description, status,
				affects_attack, notes, created
			) VALUES (?, ?, 'inflow', ?, 'planned', 1, ?, ?)
		""", (ev_date, amt, desc, 'Applied from projection sandbox', now))
		changes.append({
			'kind':        'windfall',
			'date':        ev_date,
			'amount':      round(amt, 2),
			'description': desc,
		})

	# 3. FedLoan minimum override
	fl = body.get('apply_fedloan_min')
	if fl not in (None, ''):
		try:
			fl_amount = float(fl)
		except (TypeError, ValueError):
			fl_amount = None
		if fl_amount is not None and fl_amount >= 0:
			row = conn.execute(
				"SELECT id, minimum_payment FROM accounts WHERE slug = 'fedloan-student'"
			).fetchone()
			if row:
				conn.execute(
					"UPDATE accounts SET minimum_payment = ?, updated = ? WHERE id = ?",
					(fl_amount, now, row['id']))
				changes.append({
					'kind': 'fedloan_minimum',
					'from': round(row['minimum_payment'] or 0, 2),
					'to':   round(fl_amount, 2),
				})

	conn.commit()
	conn.close()
	return jsonify({'ok': True, 'changes': changes})


# ---- JSON feeds ----

@ledger_bp.route('/total')
def ledger_total():
	"""Public-ish (still auth-gated) JSON feed for the Cockpit footer."""
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 401
	conn = get_ledger_db()
	td = L.total_debt(conn)
	td_30 = L.total_debt_n_days_ago(conn, 30)
	# pick last snapshot timestamp across active debts
	row = conn.execute("""
		SELECT MAX(bs.snapshot_at) AS last_at
		FROM balance_snapshots bs
		JOIN accounts a ON a.id = bs.account_id
		WHERE a.status IN ('active', 'unknown')
		  AND a.account_type IN ('credit_card','loan','student_loan','bnpl')
	""").fetchone()
	conn.close()
	return jsonify({
		'total':            round(td, 2),
		'delta_30d':        round(td - td_30, 2) if td_30 is not None else None,
		'last_snapshot_at': row['last_at'] if row else None,
	})


@ledger_bp.route('/runway')
def ledger_runway_feed():
	if not is_authenticated():
		return jsonify({'error': 'unauthorized'}), 401
	conn = get_ledger_db()
	r = L.cash_runway(conn)
	conn.close()
	return jsonify({
		'checking_balance':    r.checking_balance,
		'next_payday':         r.next_payday,
		'days_to_next_payday': r.days_to_next_payday,
		'total_obligations':   round(r.total_obligations, 2),
		'free_to_attack':      round(r.free_to_attack, 2),
		'runway_status':       r.runway_status,
		'obligations':         r.obligations,
	})


# ---- leak hunt (Phase 3) ----
# Spec: .kt/spec-ledger-phase-3-leak-hunt.md.

from helpers import leak_hunt as LH


def _active_rules(conn):
	"""Active rules ordered by priority ASC (lower number = wins first)."""
	return conn.execute(
		"SELECT * FROM leak_rules WHERE active = 1 ORDER BY priority ASC, id ASC"
	).fetchall()


def _available_categories(conn):
	"""Union of default categories + any user-created categories already
	present in leak_transactions. Sorted, default-list-first."""
	defaults = list(LH.DEFAULT_CATEGORIES)
	used = conn.execute(
		"SELECT DISTINCT category FROM leak_transactions ORDER BY category"
	).fetchall()
	for r in used:
		if r['category'] and r['category'] not in defaults:
			defaults.append(r['category'])
	return defaults


@ledger_bp.route('/leak-hunt/')
@cd_auth_required
def leak_hunt():
	conn = get_ledger_db()
	past = conn.execute("""
		SELECT li.*, COUNT(lt.id) AS tx_count
		FROM leak_imports li
		LEFT JOIN leak_transactions lt ON lt.leak_import_id = li.id
		WHERE li.deleted_at IS NULL
		GROUP BY li.id
		ORDER BY li.imported_at DESC LIMIT 30
	""").fetchall()
	conn.close()
	return render_template('ledger_leak_hunt.html', past=past)


@ledger_bp.route('/leak-hunt/new')
@cd_auth_required
def leak_hunt_new():
	conn = get_ledger_db()
	# Offer the checking-style accounts as the source dropdown.
	accts = conn.execute("""
		SELECT id, name, slug FROM accounts
		WHERE account_type IN ('checking', 'savings') AND status != 'closed'
		ORDER BY (account_type = 'checking') DESC, name
	""").fetchall()
	conn.close()
	return render_template('ledger_leak_hunt_new.html', accounts=accts)


@ledger_bp.route('/leak-hunt/upload', methods=['POST'])
@cd_auth_required
def leak_hunt_upload():
	"""Parse CSV → create leak_imports + leak_transactions rows →
	auto-categorize each → flag recurring → redirect to /review."""
	file = request.files.get('csv')
	if not file or not file.filename:
		flash('Pick a CSV to upload.', 'error')
		return redirect(url_for('ledger.leak_hunt_new'))

	try:
		content = file.read().decode('utf-8', errors='ignore')
	except Exception as e:
		flash(f'Could not read file: {e}', 'error')
		return redirect(url_for('ledger.leak_hunt_new'))

	records, fmt = LH.parse_csv(content)
	if not records:
		flash(f'No rows parsed from CSV (format detected: {fmt}). Try a different file or format.', 'error')
		return redirect(url_for('ledger.leak_hunt_new'))

	# Period bounds from the parsed dates (sorted, valid ISO).
	dates = sorted([r['date'] for r in records if r['date'] and re.match(r'^\d{4}-\d{2}-\d{2}$', r['date'])])
	period_start = dates[0]  if dates else L.et_today().isoformat()
	period_end   = dates[-1] if dates else L.et_today().isoformat()

	# Detect recurring before insert (returns list-index set).
	recurring_indices = LH.detect_recurring(records)

	conn = get_ledger_db()
	rules = _active_rules(conn)
	now = L.et_now_iso()

	# Account hint (optional from form — POST may include 'account_id').
	try:
		account_id = int(request.form.get('account_id') or 0) or None
	except (TypeError, ValueError):
		account_id = None

	# Total outflow (positive amounts only, excluding internal transfers — but
	# we don't know categories yet, so compute simple "sum positives" here.
	# Will be refined when category_breakdown_json is populated on save.)
	total_outflow = sum(r['amount'] for r in records if r['amount'] > 0)

	conn.execute("""
		INSERT INTO leak_imports (
			imported_at, source, period_start, period_end, total_amount,
			category_breakdown_json, notes, csv_filename, csv_format,
			transaction_count, checking_account_id
		) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
	""", (
		L.utc_now_iso(),
		fmt,
		period_start, period_end, total_outflow,
		json.dumps({}),  # populated on save
		None,
		file.filename,
		fmt,
		len(records),
		account_id,
	))
	leak_id = conn.execute("SELECT last_insert_rowid() AS id").fetchone()['id']

	for i, rec in enumerate(records):
		cat, subcat, rule_id = LH.categorize_with_rules(rec['description'], rules)
		conn.execute("""
			INSERT INTO leak_transactions (
				leak_import_id, tx_date, description, amount, category,
				subcategory, is_recurring, rule_id, manually_set, created
			) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
		""", (
			leak_id, rec['date'], rec['description'], rec['amount'],
			cat, subcat, 1 if i in recurring_indices else 0, rule_id, now,
		))

	conn.commit()
	conn.close()
	flash(f'{len(records)} transactions imported from {file.filename} ({fmt}). Review and categorize.', 'ok')
	return redirect(url_for('ledger.leak_hunt_review', leak_id=leak_id))


@ledger_bp.route('/leak-hunt/<int:leak_id>/review')
@cd_auth_required
def leak_hunt_review(leak_id):
	conn = get_ledger_db()
	imp = conn.execute(
		"SELECT * FROM leak_imports WHERE id = ? AND deleted_at IS NULL",
		(leak_id,)
	).fetchone()
	if not imp:
		conn.close()
		return redirect(url_for('ledger.leak_hunt'))

	txs = conn.execute("""
		SELECT * FROM leak_transactions
		WHERE leak_import_id = ?
		ORDER BY tx_date DESC, id DESC
	""", (leak_id,)).fetchall()
	categories = _available_categories(conn)
	conn.close()

	# Useful counts for the header.
	total_outflow = sum(t['amount'] for t in txs if t['amount'] > 0)
	total_inflow  = -sum(t['amount'] for t in txs if t['amount'] < 0)
	uncategorized_count = sum(1 for t in txs if (t['category'] or '') == 'Uncategorized')

	return render_template(
		'ledger_leak_hunt_review.html',
		imp=imp,
		transactions=txs,
		categories=categories,
		total_outflow=total_outflow,
		total_inflow=total_inflow,
		uncategorized_count=uncategorized_count,
	)


@ledger_bp.route('/leak-hunt/<int:leak_id>/transactions/<int:tx_id>/update', methods=['POST'])
@cd_auth_required
def leak_hunt_tx_update(leak_id, tx_id):
	"""Update a single transaction's category / subcategory / notes / recurring flag.

	Form fields (all optional; only present ones get updated):
	  category, subcategory, notes, is_recurring,
	  make_rule (1 to also create a rule for this description)
	"""
	conn = get_ledger_db()
	row = conn.execute(
		"SELECT * FROM leak_transactions WHERE id = ? AND leak_import_id = ?",
		(tx_id, leak_id)
	).fetchone()
	if not row:
		conn.close()
		return jsonify({'error': 'not found'}), 404

	now = L.et_now_iso()
	cat = request.form.get('category')
	subcat = request.form.get('subcategory')
	notes = request.form.get('notes')
	is_rec = request.form.get('is_recurring')

	new_cat = cat if cat is not None else row['category']
	new_subcat = subcat if subcat is not None else row['subcategory']
	new_notes = notes if notes is not None else row['notes']
	if is_rec is not None:
		new_recurring = 1 if is_rec in ('1', 'true', 'on') else 0
	else:
		new_recurring = row['is_recurring']

	# manually_set flips to 1 whenever the user touches the category.
	manually = 1 if (cat is not None and cat != row['category']) else row['manually_set']

	conn.execute("""
		UPDATE leak_transactions
		SET category = ?, subcategory = ?, notes = ?, is_recurring = ?,
		    manually_set = ?
		WHERE id = ?
	""", (new_cat, new_subcat or None, new_notes or None, new_recurring,
	      manually, tx_id))

	# Optionally also create a rule from this transaction.
	make_rule = request.form.get('make_rule') in ('1', 'true', 'on')
	rule_created  = None
	retro_updates = []  # list of {id, category} for matching rows updated in-place
	if make_rule and new_cat and new_cat != 'Uncategorized':
		desc = (row['description'] or '').strip()
		if desc:
			# Use the full description as a `contains` rule (case-insensitive).
			existing = conn.execute("""
				SELECT id FROM leak_rules
				WHERE match_type = 'contains' AND lower(match_value) = lower(?)
			""", (desc,)).fetchone()
			if not existing:
				conn.execute("""
					INSERT INTO leak_rules (
						match_type, match_value, category, subcategory,
						priority, active, note, created, updated
					) VALUES ('contains', ?, ?, ?, 100, 1, 'Created from review', ?, ?)
				""", (desc, new_cat, new_subcat or None, now, now))
				rule_created = desc

			# Apply the new rule retroactively to other UNCATEGORIZED rows
			# in the same hunt whose description contains the match string.
			# Skip rows the user has already manually set — those reflect
			# explicit choices we shouldn't overwrite.
			match_rows = conn.execute("""
				SELECT id FROM leak_transactions
				WHERE leak_import_id = ?
				  AND category = 'Uncategorized'
				  AND manually_set = 0
				  AND id != ?
				  AND instr(lower(description), lower(?)) > 0
			""", (row['leak_import_id'], tx_id, desc)).fetchall()
			retro_ids = [r['id'] for r in match_rows]
			if retro_ids:
				placeholders = ','.join('?' for _ in retro_ids)
				conn.execute(f"""
					UPDATE leak_transactions
					SET category = ?, subcategory = ?, manually_set = 0
					WHERE id IN ({placeholders})
				""", [new_cat, new_subcat or None] + retro_ids)
				retro_updates = [{'id': i, 'category': new_cat} for i in retro_ids]

	conn.commit()
	conn.close()
	if request.headers.get('X-Requested-With') == 'fetch':
		return jsonify({
			'ok':            True,
			'rule_created':  rule_created,
			'retro_updates': retro_updates,
		})
	return redirect(url_for('ledger.leak_hunt_review', leak_id=leak_id))


@ledger_bp.route('/leak-hunt/<int:leak_id>/transactions/bulk', methods=['POST'])
@cd_auth_required
def leak_hunt_tx_bulk(leak_id):
	"""Bulk-update category for selected transaction IDs.

	Body (JSON or form): {ids: [...], category: '...', is_recurring: 0|1}
	"""
	data = request.get_json(silent=True) or request.form.to_dict(flat=False)
	# Handle either JSON or form-array
	if isinstance(data.get('ids'), list):
		ids = data['ids']
	else:
		ids = request.form.getlist('ids')
	ids = [int(x) for x in ids if str(x).isdigit()]
	if not ids:
		return jsonify({'ok': False, 'error': 'no ids'}), 400

	cat = data.get('category') if isinstance(data, dict) else request.form.get('category')
	if isinstance(cat, list):
		cat = cat[0] if cat else None
	is_rec = data.get('is_recurring') if isinstance(data, dict) else request.form.get('is_recurring')
	if isinstance(is_rec, list):
		is_rec = is_rec[0] if is_rec else None

	conn = get_ledger_db()
	placeholders = ','.join('?' for _ in ids)
	if cat is not None and cat != '':
		conn.execute(f"""
			UPDATE leak_transactions
			SET category = ?, manually_set = 1
			WHERE leak_import_id = ? AND id IN ({placeholders})
		""", [cat, leak_id] + ids)
	if is_rec is not None and str(is_rec) != '':
		val = 1 if str(is_rec) in ('1', 'true', 'on') else 0
		conn.execute(f"""
			UPDATE leak_transactions
			SET is_recurring = ?
			WHERE leak_import_id = ? AND id IN ({placeholders})
		""", [val, leak_id] + ids)
	conn.commit()
	conn.close()
	return jsonify({'ok': True, 'updated': len(ids)})


@ledger_bp.route('/leak-hunt/<int:leak_id>/save', methods=['POST'])
@cd_auth_required
def leak_hunt_save(leak_id):
	"""Finalize: populate category_breakdown_json cache + redirect to results."""
	conn = get_ledger_db()
	txs = conn.execute(
		"SELECT category, amount FROM leak_transactions WHERE leak_import_id = ?",
		(leak_id,)
	).fetchall()
	breakdown = {}
	total_outflow = 0.0
	for t in txs:
		cat = t['category'] or 'Uncategorized'
		amt = t['amount'] or 0
		if amt > 0 and cat not in LH.EXCLUDED_FROM_LEAK:
			breakdown[cat] = breakdown.get(cat, 0) + amt
			total_outflow += amt
	conn.execute("""
		UPDATE leak_imports
		SET category_breakdown_json = ?, total_amount = ?
		WHERE id = ?
	""", (json.dumps(breakdown), total_outflow, leak_id))
	conn.commit()
	conn.close()
	flash('Leak hunt saved.', 'ok')
	return redirect(url_for('ledger.leak_hunt_detail', leak_id=leak_id))


@ledger_bp.route('/leak-hunt/<int:leak_id>/notes', methods=['POST'])
@cd_auth_required
def leak_hunt_notes(leak_id):
	conn = get_ledger_db()
	conn.execute(
		"UPDATE leak_imports SET notes = ? WHERE id = ?",
		(request.form.get('notes', '').strip() or None, leak_id))
	conn.commit()
	conn.close()
	return redirect(url_for('ledger.leak_hunt_detail', leak_id=leak_id))


@ledger_bp.route('/leak-hunt/<int:leak_id>/delete', methods=['POST'])
@cd_auth_required
def leak_hunt_delete(leak_id):
	conn = get_ledger_db()
	conn.execute(
		"UPDATE leak_imports SET deleted_at = ? WHERE id = ?",
		(L.utc_now_iso(), leak_id))
	conn.commit()
	conn.close()
	flash('Hunt deleted.', 'ok')
	return redirect(url_for('ledger.leak_hunt'))


@ledger_bp.route('/leak-hunt/<int:leak_id>/')
@cd_auth_required
def leak_hunt_detail(leak_id):
	conn = get_ledger_db()
	imp = conn.execute(
		"SELECT * FROM leak_imports WHERE id = ? AND deleted_at IS NULL",
		(leak_id,)
	).fetchone()
	if not imp:
		conn.close()
		return redirect(url_for('ledger.leak_hunt'))

	txs = conn.execute("""
		SELECT * FROM leak_transactions
		WHERE leak_import_id = ?
		ORDER BY tx_date DESC, id DESC
	""", (leak_id,)).fetchall()

	# Convert Rows to dicts for the helpers (which use .get).
	tx_dicts = [dict(t) for t in txs]
	breakdown, total_outflow = LH.category_breakdown(tx_dicts)
	biggest = LH.biggest_transactions(tx_dicts, n=10)
	recurring = LH.recurring_charges_summary(tx_dicts)

	# Mark each recurring item with whether its cleaned_name is already
	# in recurring_expenses — drives the "✓ In Bills" inline state so the
	# user can see at a glance what's already covered.
	existing_bills = {r['name'].strip().lower(): r['active'] for r in conn.execute(
		"SELECT name, active FROM recurring_expenses"
	).fetchall()}
	for r in recurring:
		key = (r.get('cleaned_name') or '').strip().lower()
		if not key:
			r['in_bills'] = False
			r['in_bills_inactive'] = False
			continue
		r['in_bills'] = key in existing_bills and bool(existing_bills[key])
		r['in_bills_inactive'] = key in existing_bills and not existing_bills[key]

	total_inflow = -sum(t['amount'] for t in txs if t['amount'] < 0)

	# Prior hunt (most recent before this one, alive only)
	prior = conn.execute("""
		SELECT * FROM leak_imports
		WHERE id != ? AND deleted_at IS NULL
		  AND imported_at < (SELECT imported_at FROM leak_imports WHERE id = ?)
		ORDER BY imported_at DESC LIMIT 1
	""", (leak_id, leak_id)).fetchone()
	prior_breakdown = None
	prior_breakdown_map = {}
	if prior:
		try:
			prior_breakdown_map = json.loads(prior['category_breakdown_json'] or '{}')
		except (ValueError, TypeError):
			prior_breakdown_map = {}
		prior_breakdown = [{'category': k, 'total': v} for k, v in prior_breakdown_map.items()]

	# Per-category delta vs prior (only categories that appear in either side).
	delta_rows = []
	if prior:
		this_map = {r['category']: r['total'] for r in breakdown if not r['is_excluded']}
		cats = sorted(set(list(this_map.keys()) + list(prior_breakdown_map.keys())))
		for cat in cats:
			t_now = this_map.get(cat, 0)
			t_prior = prior_breakdown_map.get(cat, 0)
			delta_rows.append({
				'category': cat,
				'now':      t_now,
				'prior':    t_prior,
				'delta':    t_now - t_prior,
			})
		delta_rows.sort(key=lambda r: abs(r['delta']), reverse=True)

	conn.close()

	return render_template(
		'ledger_leak_hunt_results.html',
		imp=imp,
		breakdown=breakdown,
		total_outflow=total_outflow,
		total_inflow=total_inflow,
		biggest=biggest,
		recurring=recurring,
		prior=prior,
		delta_rows=delta_rows,
	)


@ledger_bp.route('/leak-hunt/<int:leak_id>/recurring/add', methods=['POST'])
@cd_auth_required
def leak_hunt_add_recurring(leak_id):
	"""Add a detected recurring charge to recurring_expenses as a bill.

	Idempotent by name (case-insensitive). Form fields:
	  name, amount, day_of_month, category
	"""
	name   = (request.form.get('name', '') or '').strip()
	amount = _form_float('amount', 0) or 0
	day    = _form_int('day_of_month', 1) or 1
	cat    = (request.form.get('category', '') or '').strip() or None

	is_fetch = request.headers.get('X-Requested-With') == 'fetch'

	def _resp(ok, msg, status='ok'):
		if is_fetch:
			return jsonify({'ok': ok, 'message': msg, 'name': name})
		flash(msg, status)
		return redirect(url_for('ledger.leak_hunt_detail', leak_id=leak_id) + '#recurring')

	if not name or amount <= 0:
		return _resp(False, 'Need a name and a positive amount.', 'error')

	conn = get_ledger_db()
	existing = conn.execute(
		"SELECT id, active FROM recurring_expenses WHERE lower(name) = lower(?)",
		(name,)
	).fetchone()
	now = L.et_now_iso()
	if existing:
		if not existing['active']:
			conn.execute(
				"UPDATE recurring_expenses SET active = 1, updated = ? WHERE id = ?",
				(now, existing['id']))
			conn.commit()
			conn.close()
			return _resp(True, f'{name} reactivated in recurring bills.')
		conn.close()
		return _resp(True, f'{name} is already in your recurring bills.')

	conn.execute("""
		INSERT INTO recurring_expenses (
			name, amount, day_of_month, category, active, notes, created, updated
		) VALUES (?, ?, ?, ?, 1, ?, ?, ?)
	""", (name, amount, day, cat, 'Added from leak hunt', now, now))
	conn.commit()
	conn.close()
	return _resp(True, f'Added {name} (${amount:,.2f}/mo) to recurring bills.')


@ledger_bp.route('/leak-hunt/rules')
@cd_auth_required
def leak_hunt_rules():
	conn = get_ledger_db()
	rules = conn.execute(
		"SELECT * FROM leak_rules ORDER BY active DESC, priority ASC, id ASC"
	).fetchall()
	categories = _available_categories(conn)
	conn.close()
	return render_template('ledger_leak_hunt_rules.html', rules=rules, categories=categories)


@ledger_bp.route('/leak-hunt/rules/new', methods=['POST'])
@cd_auth_required
def leak_hunt_rules_new():
	conn = get_ledger_db()
	now = L.et_now_iso()
	conn.execute("""
		INSERT INTO leak_rules (
			match_type, match_value, category, subcategory, priority,
			active, note, created, updated
		) VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?)
	""", (
		request.form.get('match_type', 'contains'),
		(request.form.get('match_value', '') or '').strip(),
		(request.form.get('category', '') or 'Other').strip() or 'Other',
		(request.form.get('subcategory', '') or '').strip() or None,
		_form_int('priority', 100) or 100,
		(request.form.get('note', '') or '').strip() or None,
		now, now,
	))
	conn.commit()
	conn.close()
	return redirect(url_for('ledger.leak_hunt_rules'))


@ledger_bp.route('/leak-hunt/rules/<int:rule_id>/edit', methods=['POST'])
@cd_auth_required
def leak_hunt_rules_edit(rule_id):
	conn = get_ledger_db()
	now = L.et_now_iso()
	conn.execute("""
		UPDATE leak_rules
		SET match_type = ?, match_value = ?, category = ?, subcategory = ?,
		    priority = ?, active = ?, note = ?, updated = ?
		WHERE id = ?
	""", (
		request.form.get('match_type', 'contains'),
		(request.form.get('match_value', '') or '').strip(),
		(request.form.get('category', '') or 'Other').strip() or 'Other',
		(request.form.get('subcategory', '') or '').strip() or None,
		_form_int('priority', 100) or 100,
		1 if request.form.get('active') else 0,
		(request.form.get('note', '') or '').strip() or None,
		now, rule_id,
	))
	conn.commit()
	conn.close()
	return redirect(url_for('ledger.leak_hunt_rules'))


@ledger_bp.route('/leak-hunt/rules/<int:rule_id>/delete', methods=['POST'])
@cd_auth_required
def leak_hunt_rules_delete(rule_id):
	conn = get_ledger_db()
	conn.execute("DELETE FROM leak_rules WHERE id = ?", (rule_id,))
	conn.commit()
	conn.close()
	return redirect(url_for('ledger.leak_hunt_rules'))


# ---- AI payday assistant ----

@ledger_bp.route('/payday/assistant', methods=['POST'])
@cd_auth_required
def payday_assistant():
	"""Single-shot Claude call. Returns 2-3 recommendations with cited math.

	On any failure (API error, JSON parse, validation), return the
	rule-based avalanche recommendation as a single card so the UI
	never goes empty.
	"""
	conn = get_ledger_db()
	debts   = L.avalanche_order(conn)
	runway  = L.cash_runway(conn)
	budget  = L.attack_budget(conn)
	target  = budget.current_target

	# Build a rule-based fallback first — used on failure AND as a sanity check.
	fallback = _fallback_recommendations(target, runway, debts)

	api_key = os.environ.get('ANTHROPIC_API_KEY')
	if not api_key:
		conn.close()
		return jsonify({'source': 'rule', 'recommendations': fallback})

	try:
		import anthropic
		client = anthropic.Anthropic(api_key=api_key)
	except Exception as e:
		logger.warning(f'ledger ai: anthropic import failed: {e}')
		conn.close()
		return jsonify({'source': 'rule', 'recommendations': fallback})

	today = L.et_today()
	thirty_back = (today - timedelta(days=30)).isoformat()
	thirty_ahead = (today + timedelta(days=30)).isoformat()

	recent_payments = conn.execute("""
		SELECT t.tx_date, t.amount, t.description, a.name AS account_name
		FROM debt_transactions t
		JOIN accounts a ON a.id = t.account_id
		WHERE t.confirmed = 1 AND t.tx_type = 'payment'
		  AND t.tx_date >= ?
		ORDER BY t.tx_date DESC LIMIT 50
	""", (thirty_back,)).fetchall()

	upcoming_one_time = conn.execute("""
		SELECT event_date, amount, direction, description
		FROM one_time_events
		WHERE status = 'planned'
		  AND event_date >= ? AND event_date <= ?
		ORDER BY event_date
	""", (today.isoformat(), thirty_ahead)).fetchall()

	context = {
		'today':         today.isoformat(),
		'free_to_attack': round(runway.free_to_attack, 2),
		'checking':      round(runway.checking_balance or 0, 2),
		'next_payday':   runway.next_payday,
		'days_to_next_payday': runway.days_to_next_payday,
		'debts': [{
			'name':              d['name'],
			'apr':               d['apr'],
			'current_balance':   round(d['current_balance'], 2),
			'minimum_payment':   d.get('minimum_payment') or 0,
			'attack_allocation': d.get('attack_allocation') or 0,
		} for d in debts],
		'current_target': target['name'] if target else None,
		'obligations':    runway.obligations,
		'recent_payments_30d': [{
			'date':        r['tx_date'],
			'amount':      round(r['amount'], 2),
			'account':     r['account_name'],
			'description': r['description'] or '',
		} for r in recent_payments],
		'upcoming_one_time_30d': [{
			'date':        r['event_date'],
			'amount':      round(r['amount'], 2),
			'direction':   r['direction'],
			'description': r['description'],
		} for r in upcoming_one_time],
	}

	system = (
		"You are a payday strategy assistant for personal debt payoff. "
		"Recommend 2-3 actions for this paycheck. Constraints: "
		"(1) base every number you cite on the JSON context I provide — never invent figures; "
		"(2) one recommendation must be the strict avalanche default "
		"(extra to the highest-APR active debt with non-zero allocation); "
		"(3) if any active debt has current_balance <= free_to_attack, include a 'kill it' option that closes that account and frees its minimum; "
		"(4) the third (optional) can be your judgment — e.g. paying down a newer high-APR card harder, or a runway-protective hold; "
		"(5) reply ONLY with a JSON array of objects with keys: "
		"headline (one line), action (string), impact (string), rationale (2-3 sentences). "
		"No markdown, no preamble, no extra prose. "
	)
	user = (
		"Context JSON:\n" + json.dumps(context, indent=2) +
		"\n\nReturn the JSON array now."
	)

	try:
		resp = client.messages.create(
			model='claude-sonnet-4-5',
			max_tokens=1200,
			system=system,
			messages=[{'role': 'user', 'content': user}],
		)
		text = ''.join(b.text for b in resp.content if getattr(b, 'type', '') == 'text')
		# Strip ```json fences if present
		text = re.sub(r'^```(?:json)?', '', text.strip())
		text = re.sub(r'```$', '', text.strip()).strip()
		recs = json.loads(text)
		if not isinstance(recs, list):
			raise ValueError('Expected list')
		conn.close()
		return jsonify({'source': 'claude', 'recommendations': recs})
	except Exception as e:
		logger.warning(f'ledger ai failure, falling back: {e}')
		conn.close()
		return jsonify({'source': 'rule', 'recommendations': fallback,
		                'error': str(e)})


def _fallback_recommendations(target, runway, debts):
	recs = []
	free = max(0, runway.free_to_attack or 0)
	if target:
		recs.append({
			'headline': f'Avalanche default: ${free:,.0f} → {target["name"]}',
			'action':   f'Send ${free:,.2f} to {target["name"]}',
			'impact':   f'Cuts {target["name"]} balance to ${max(0, target["current_balance"] - free):,.2f}.',
			'rationale': f'{target["name"]} is the highest-APR active debt with non-zero allocation ({target["apr"]:.2f}%). Every dollar to it saves the most interest.',
		})
	for d in debts:
		if d.get('current_balance', 0) > 0 and d['current_balance'] <= free:
			recs.append({
				'headline':  f'Kill it: clear {d["name"]} for ${d["current_balance"]:,.2f}',
				'action':    f'Send ${d["current_balance"]:,.2f} to {d["name"]}',
				'impact':    f'Closes {d["name"]}. Frees ${(d.get("minimum_payment") or 0):,.2f}/month into the next target.',
				'rationale': f'You have enough this payday to wipe this account entirely. The recurring minimum disappears from your monthly obligations.',
			})
			break
	return recs[:3]
