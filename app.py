from flask import Flask, request, render_template, make_response, redirect, url_for, jsonify
from werkzeug.utils import secure_filename
from PIL import Image
import os, subprocess, pytz, requests, emoji, glob, json, time, re
from datetime import datetime, timedelta
import sqlite3
import anthropic
import requests as req_lib
import uuid
from functools import wraps

# Load .env if python-dotenv is available. load_dotenv() never overrides
# already-set env vars, so it's safe alongside whatever PA uses to populate them.
try:
	from dotenv import load_dotenv
	load_dotenv()
except ImportError:
	pass

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY')
PASSWORD = os.environ.get('FLASK_PASSWORD')

UPLOAD_FOLDER = os.environ.get('COCKPIT_UPLOAD_FOLDER', '/home/aaronaiken/status_update/assets/img/status/')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

TASKS_FILE = 'assets/data/tasks.json'
SCRATCH_FILE = 'assets/data/scratch.json'
BELOW_DECK_FILE = 'assets/data/below_deck.json'
ANI_CONVERSATION_FILE = 'ani_conversation.json'
ANI_MEMORY_FILE = 'static/ani_memory.txt'
REPO_ROOT = os.environ.get('COCKPIT_REPO_ROOT', '/home/aaronaiken/status_update')

DB_FILE           = os.path.join(REPO_ROOT, 'assets/data/command_deck.db')
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
BUNNY_STORAGE_ZONE = os.environ.get('BUNNY_STORAGE_ZONE')
BUNNY_API_KEY      = os.environ.get('BUNNY_API_KEY')
BUNNY_CDN_URL      = os.environ.get('BUNNY_CDN_URL', '').rstrip('/')

BUNNY_STATUS_STORAGE_ZONE = os.environ.get('BUNNY_STATUS_STORAGE_ZONE')
BUNNY_STATUS_API_KEY      = os.environ.get('BUNNY_STATUS_API_KEY')
BUNNY_STATUS_CDN_URL      = os.environ.get('BUNNY_STATUS_CDN_URL', '').rstrip('/')

SCRATCH_WORK_FILE        = 'assets/data/scratch_work.json'
AFTER_DARK_COMMS_FILE    = 'static/after_dark_comms.txt'

WORK_MODE_PIN            = os.environ.get('WORK_MODE_PIN', '')
AFTER_DARK_PIN           = os.environ.get('AFTER_DARK_PIN', '')
BRRR_WEBHOOK_URL         = os.environ.get('BRRR_WEBHOOK_URL', '')

BUNNY_AD_STORAGE_ZONE    = os.environ.get('BUNNY_AFTER_DARK_STORAGE_ZONE', '')
BUNNY_AD_API_KEY         = os.environ.get('BUNNY_AFTER_DARK_API_KEY', '')
BUNNY_AD_CDN_URL         = os.environ.get('BUNNY_AFTER_DARK_CDN_URL', '').rstrip('/')


PRIVATE_PROJECTS_PIN = os.environ.get('PRIVATE_PROJECTS_PIN', '')

ALLOWED_FILE_EXTENSIONS = {
	'jpg', 'jpeg', 'png', 'gif', 'webp',
	'pdf', 'txt', 'md',
	'doc', 'docx', 'xls', 'xlsx',
	'zip', 'mp4', 'mov'
}
MAX_FILE_SIZE_MB = 25

# ---- COMMS CACHE ----
_comms_cache = {'data': None, 'timestamp': 0}
COMMS_CACHE_TTL = 300  # 5 minutes


# ---- AUTH ---- (moved to helpers/auth.py)

from helpers.auth import is_authenticated, cd_auth_required
from helpers.git import get_git_status, perform_git_ops


# ---- COMMS HELPERS ---- (moved to helpers/comms.py)

from helpers.comms import get_active_tags, get_valid_comms, get_after_dark_comms


from helpers.scratch import load_scratch_work, save_scratch_work


from helpers.omg_lol import post_to_omg_lol


from helpers.bunny import (
	list_bunny_ad_folder,
	optimize_image,
	upload_status_image_to_bunny,
	_allowed_file,
	_upload_to_bunny,
)


# ---- TASKS HELPERS ---- (load/save to helpers/tasks_json.py; post_task_status stays for cockpit blueprint)

from helpers.tasks_json import load_tasks, save_tasks


# ---- ANI HELPERS ---- (moved to blueprints/ani.py)
from blueprints.ani import ani_notify_publish  # used by publish_status

# ---- TODAY ROUTES ---- (moved to blueprints/today.py)

# ---- COMMAND DECK HELPERS ---- (moved to helpers/db.py)

from helpers.db import get_db, slugify, unique_slug, et_now

# Jinja global for the CD footer pill — lazy: only invoked when the
# includes/cd_footer_status.html partial actually renders.
from helpers.backup_status import get_last_backup_status
app.jinja_env.globals['last_backup_status'] = get_last_backup_status

# Cross-app footer pill — lazy: only invoked when the include actually renders.
from helpers.ledger import footer_summary as ledger_footer_summary
app.jinja_env.globals['ledger_footer_summary'] = ledger_footer_summary

# ---- EXISTING ROUTES ----

# ---- COCKPIT ROUTES ---- (moved to blueprints/cockpit.py)

# ---- TASKS ROUTES ----

# ---- TASKS ROUTES ---- (moved to blueprints/tasks.py, registered at app.py bottom)

# ---- SCRATCH ROUTES ----

# ---- BELOW DECK ROUTES ----

# ---- BELOW DECK ROUTES ---- (moved to blueprints/below_deck.py)

# ---- COMMAND DECK ROUTES ---- (moved to blueprints/command_deck.py)

# ---- BLUEPRINT REGISTRATION ----

from blueprints.tasks import tasks_bp
from blueprints.today import today_bp
from blueprints.below_deck import below_deck_bp
from blueprints.ani import ani_bp
from blueprints.cockpit import cockpit_bp
from blueprints.command_deck import command_deck_bp
from blueprints.mozzie import mozzie_bp
from blueprints.time_tracking import time_tracking_bp
from blueprints.healthz import healthz_bp
from blueprints.reports import reports_bp
from blueprints.meetings import meetings_bp
from blueprints.mileage import mileage_bp
from blueprints.settings import settings_bp
from blueprints.tickets import tickets_bp
from blueprints.lookups import lookups_bp
from blueprints.ledger import ledger_bp
from blueprints.meet import meet_bp
from blueprints.notebook import notebook_bp
app.register_blueprint(tasks_bp)
app.register_blueprint(today_bp)
app.register_blueprint(below_deck_bp)
app.register_blueprint(ani_bp)
app.register_blueprint(cockpit_bp)
app.register_blueprint(command_deck_bp)
app.register_blueprint(mozzie_bp)
app.register_blueprint(time_tracking_bp)
app.register_blueprint(healthz_bp)
app.register_blueprint(reports_bp)
app.register_blueprint(meetings_bp)
app.register_blueprint(mileage_bp)
app.register_blueprint(settings_bp)
app.register_blueprint(tickets_bp)
app.register_blueprint(lookups_bp)
app.register_blueprint(ledger_bp)
app.register_blueprint(meet_bp)
app.register_blueprint(notebook_bp)


# Global recurrence-cycle trigger. Originally only /today/data fired the
# autoclear+spawn pass, so going straight to Command Deck after 4am ET left
# yesterday's checked items stuck at the top of recurring blocks. Now any
# authenticated request fires it — throttled to once per 60s per worker.
# Static + healthz are skipped to keep them fast. The race-safe claim in
# blueprints/today.py:_spawn_cycle makes cross-worker duplicates a no-op.
from blueprints.today import maybe_run_autoclear

@app.before_request
def _global_autoclear():
	path = request.path or ''
	if path.startswith('/static/') or path == '/healthz':
		return
	if not is_authenticated():
		return
	try:
		maybe_run_autoclear()
	except Exception:
		pass  # never break a request because of autoclear


if __name__ == "__main__": app.run(debug=True)