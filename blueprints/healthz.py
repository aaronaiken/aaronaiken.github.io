"""
healthz — public DB-health endpoint for external uptime monitoring.

Auth-free by design: monitoring services hit this without credentials and
get a definitive 200/500 based on whether command_deck.db opens AND its
schema is queryable. The query (SELECT COUNT(*) FROM projects) catches
both file-level corruption (fails to open) and the all-zeros / empty-schema
case we hit on 2026-05-02 (opens but nothing inside).

Response is intentionally minimal — no internal state leak, no row counts,
no file paths. The exception is logged server-side for triage; the client
just sees ok or fail.
"""
import logging
import sqlite3

from flask import Blueprint, jsonify

from helpers.db import get_db, get_ledger_db


healthz_bp = Blueprint('healthz', __name__)
logger = logging.getLogger(__name__)


@healthz_bp.route('/healthz')
def healthz():
	try:
		conn = get_db()
		try:
			conn.execute('SELECT COUNT(*) FROM projects').fetchone()
		finally:
			conn.close()
	except (sqlite3.Error, OSError) as e:
		logger.warning('healthz DB check failed: %s', e)
		return jsonify(status='fail'), 500
	return jsonify(status='ok'), 200


@healthz_bp.route('/healthz/ledger')
def healthz_ledger():
	"""The Ledger's separate DB has its own health check — same shape, no auth."""
	try:
		conn = get_ledger_db()
		try:
			conn.execute('SELECT COUNT(*) FROM accounts').fetchone()
		finally:
			conn.close()
	except (sqlite3.Error, OSError) as e:
		logger.warning('healthz ledger DB check failed: %s', e)
		return jsonify(status='fail'), 500
	return jsonify(status='ok'), 200
