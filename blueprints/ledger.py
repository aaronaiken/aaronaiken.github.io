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
	conn = get_ledger_db()
	conn.execute(
		"UPDATE recurring_expenses SET active = 0, updated = ? WHERE id = ?",
		(L.et_now_iso(), eid))
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


@ledger_bp.route('/projection/')
@cd_auth_required
def projection_view():
	conn = get_ledger_db()
	projection = L.project_payoff(conn)
	conn.close()
	return render_template('ledger_projection.html', projection=projection)


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


# ---- leak hunt ----

DEFAULT_LEAK_CATEGORIES = [
	'groceries', 'dining', 'gas', 'shopping', 'subscription',
	'home', 'health', 'transportation', 'entertainment', 'transfer',
	'income', 'other',
]


LEAK_HEURISTICS = [
	(re.compile(r'\b(uber|lyft|gas|exxon|shell|bp |bp$|sheetz|wawa)\b', re.I), 'transportation'),
	(re.compile(r'\b(amzn|amazon|target|walmart|costco)\b', re.I), 'shopping'),
	(re.compile(r'\b(starbucks|dunkin|chick|chipotle|panera|sweetgreen|domino|pizza|grubhub|doordash|seamless|ubereat)\b', re.I), 'dining'),
	(re.compile(r'\b(kroger|whole foods|trader joe|aldi|safeway|publix|wegmans|giant|harris teeter|food lion)\b', re.I), 'groceries'),
	(re.compile(r'\b(netflix|spotify|hulu|disney|apple\.com|icloud|adobe|github)\b', re.I), 'subscription'),
	(re.compile(r'\b(cvs|walgreens|rite aid|doctor|dental|pharmacy)\b', re.I), 'health'),
	(re.compile(r'\b(home depot|lowes|ikea|wayfair)\b', re.I), 'home'),
	(re.compile(r'\b(payroll|deposit|direct dep|paycheck|salary)\b', re.I), 'income'),
	(re.compile(r'\b(transfer|xfer|venmo|zelle|paypal)\b', re.I), 'transfer'),
]


def _categorize_desc(desc):
	for pat, cat in LEAK_HEURISTICS:
		if pat.search(desc or ''):
			return cat
	return 'other'


@ledger_bp.route('/leak-hunt/')
@cd_auth_required
def leak_hunt():
	conn = get_ledger_db()
	past = conn.execute(
		"SELECT * FROM leak_imports ORDER BY imported_at DESC LIMIT 20"
	).fetchall()
	conn.close()
	return render_template('ledger_leak_hunt.html', past=past, preview=None, categories=DEFAULT_LEAK_CATEGORIES)


@ledger_bp.route('/leak-hunt/upload', methods=['POST'])
@cd_auth_required
def leak_hunt_upload():
	"""Parse an uploaded CSV and return a categorized preview.

	Best-effort parser: looks for columns named (case-insensitive) 'date',
	'description' (or 'memo' / 'name'), 'amount' (or 'debit'/'credit'). If
	debit + credit are split, debits are positive outflows, credits are
	negative. The preview is rendered for the user to review/edit, then
	committed via /leak-hunt/commit.
	"""
	file = request.files.get('csv')
	if not file or not file.filename:
		flash('Pick a CSV to upload.', 'error')
		return redirect(url_for('ledger.leak_hunt'))

	try:
		content = file.read().decode('utf-8', errors='ignore')
	except Exception as e:
		flash(f'Could not read file: {e}', 'error')
		return redirect(url_for('ledger.leak_hunt'))

	reader = csv.DictReader(io.StringIO(content))
	cols = {(c or '').strip().lower(): c for c in (reader.fieldnames or [])}

	def find_col(*names):
		for n in names:
			if n in cols:
				return cols[n]
		return None

	date_col   = find_col('date', 'posted', 'posted date', 'transaction date')
	desc_col   = find_col('description', 'memo', 'name', 'payee', 'merchant')
	amount_col = find_col('amount', 'transaction amount')
	debit_col  = find_col('debit', 'withdrawal')
	credit_col = find_col('credit', 'deposit')

	preview = []
	for r in reader:
		desc = (r.get(desc_col) or '').strip() if desc_col else ''
		raw_date = (r.get(date_col) or '').strip() if date_col else ''
		try:
			amount = float((r.get(amount_col) or '0').replace(',', '').replace('$',''))
		except (ValueError, TypeError):
			amount = 0.0
		if amount_col is None and (debit_col or credit_col):
			try:
				deb = float((r.get(debit_col) or '0').replace(',','').replace('$','') or 0) if debit_col else 0
			except (ValueError, TypeError):
				deb = 0
			try:
				cre = float((r.get(credit_col) or '0').replace(',','').replace('$','') or 0) if credit_col else 0
			except (ValueError, TypeError):
				cre = 0
			amount = deb - cre
		preview.append({
			'date': raw_date,
			'description': desc,
			'amount': amount,
			'category': _categorize_desc(desc),
		})

	if not preview:
		flash('No rows parsed from CSV.', 'error')
		return redirect(url_for('ledger.leak_hunt'))

	conn = get_ledger_db()
	past = conn.execute(
		"SELECT * FROM leak_imports ORDER BY imported_at DESC LIMIT 20"
	).fetchall()
	conn.close()
	return render_template(
		'ledger_leak_hunt.html',
		past=past,
		preview=preview,
		categories=DEFAULT_LEAK_CATEGORIES,
		source_filename=file.filename,
	)


@ledger_bp.route('/leak-hunt/commit', methods=['POST'])
@cd_auth_required
def leak_hunt_commit():
	"""Persist a categorized leak-hunt session as a single leak_imports row."""
	rows = []
	i = 0
	while True:
		desc = request.form.get(f'desc[{i}]')
		if desc is None:
			break
		try:
			amt = float(request.form.get(f'amount[{i}]', '0') or 0)
		except ValueError:
			amt = 0.0
		rows.append({
			'date':        request.form.get(f'date[{i}]', '').strip(),
			'description': desc,
			'amount':      amt,
			'category':    request.form.get(f'category[{i}]', 'other'),
		})
		i += 1
	if not rows:
		flash('Nothing to commit.', 'error')
		return redirect(url_for('ledger.leak_hunt'))

	# Category totals (outflows only — positive amounts).
	breakdown = {}
	for r in rows:
		if r['amount'] > 0:
			breakdown[r['category']] = breakdown.get(r['category'], 0) + r['amount']

	total = sum(b for b in breakdown.values())
	dates = sorted([r['date'] for r in rows if r['date']])
	period_start = dates[0] if dates else L.et_today().isoformat()
	period_end   = dates[-1] if dates else L.et_today().isoformat()

	conn = get_ledger_db()
	conn.execute("""
		INSERT INTO leak_imports (
			imported_at, source, period_start, period_end,
			total_amount, category_breakdown_json, notes
		) VALUES (?, ?, ?, ?, ?, ?, ?)
	""", (
		L.utc_now_iso(),
		request.form.get('source', 'manual'),
		period_start, period_end, total,
		json.dumps(breakdown),
		request.form.get('notes', '').strip() or None,
	))
	leak_id = conn.execute("SELECT last_insert_rowid() AS id").fetchone()['id']
	conn.commit()
	conn.close()
	flash(f'Leak hunt saved. ${total:,.2f} across {len([r for r in rows if r["amount"] > 0])} outflows.', 'ok')
	return redirect(url_for('ledger.leak_hunt_detail', leak_id=leak_id))


@ledger_bp.route('/leak-hunt/<int:leak_id>/')
@cd_auth_required
def leak_hunt_detail(leak_id):
	conn = get_ledger_db()
	row = conn.execute(
		"SELECT * FROM leak_imports WHERE id = ?", (leak_id,)
	).fetchone()
	conn.close()
	if not row:
		return redirect(url_for('ledger.leak_hunt'))
	breakdown = {}
	try:
		breakdown = json.loads(row['category_breakdown_json'])
	except (ValueError, TypeError):
		breakdown = {}
	return render_template(
		'ledger_leak_hunt.html',
		past=[],
		preview=None,
		categories=DEFAULT_LEAK_CATEGORIES,
		detail=row,
		detail_breakdown=breakdown,
	)


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
