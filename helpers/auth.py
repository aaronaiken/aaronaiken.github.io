"""Auth helpers — cookie check + Command Deck gate decorator."""
from functools import wraps
from flask import request, redirect, url_for


def is_authenticated():
	return request.cookies.get('auth_token') == 'authenticated_user'


def cd_auth_required(f):
	@wraps(f)
	def decorated(*args, **kwargs):
		if not is_authenticated():
			return redirect(url_for('cockpit.login'))
		return f(*args, **kwargs)
	return decorated
