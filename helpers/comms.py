"""Comms helpers — time-of-day tagging + tagged-message file readers."""
from datetime import datetime
import pytz


COMMS_FILE = 'static/comms.txt'
AFTER_DARK_COMMS_FILE = 'static/after_dark_comms.txt'


def get_active_tags():
	pa_tz = pytz.timezone('America/New_York')
	now = datetime.now(pa_tz)
	hour = now.hour
	tags = ["ALL"]

	tags.append(now.strftime("%A").upper())

	if 5 <= hour < 12:
		tags.append("AM")
	if 12 <= hour < 24:
		tags.append("PM")
	if hour >= 17 or hour < 5:
		tags.append("EVE")

	day_type = "WEEKEND" if now.weekday() >= 5 else "WEEKDAY"
	tags.append(day_type)

	date_str = now.strftime("%m/%d")
	if date_str == "12/25": tags.append("CHRISTMAS")
	if date_str == "03/11": tags.append("BIRTHDAY")
	if date_str == "04/05": tags.append("EASTER")

	return tags


def get_valid_comms():
	active_tags = get_active_tags()
	valid_comms = []

	try:
		with open(COMMS_FILE, 'r') as f:
			for line in f:
				clean_line = line.strip()
				if not clean_line:
					continue

				if "|" not in clean_line:
					valid_comms.append(clean_line)
					continue

				parts = clean_line.split("|")
				message = parts[-1].strip()
				required_tags = [p.strip().upper() for p in parts[:-1] if p.strip()]

				if all(tag in active_tags for tag in required_tags):
					weight = 10 ** len(required_tags)
					for _ in range(weight):
						valid_comms.append(message)

	except FileNotFoundError:
		return ["Secure line cut."]

	return valid_comms if valid_comms else ["Scanning..."]


def get_after_dark_comms():
	"""
	Load after_dark_comms.txt — same tag/pipe format as comms.txt.
	Returns a deduplicated list of currently valid lines.
	Silently returns [] if the file doesn't exist yet.
	"""
	active_tags = get_active_tags()
	valid = []
	try:
		with open(AFTER_DARK_COMMS_FILE, 'r') as f:
			for line in f:
				clean = line.strip()
				if not clean:
					continue
				if '|' not in clean:
					valid.append(clean)
					continue
				parts = clean.split('|')
				message = parts[-1].strip()
				required_tags = [p.strip().upper() for p in parts[:-1] if p.strip()]
				if all(tag in active_tags for tag in required_tags):
					weight = 10 ** len(required_tags)
					for _ in range(weight):
						valid.append(message)
	except FileNotFoundError:
		return []
	# Deduplicate preserving order
	seen = set()
	unique = []
	for m in valid:
		if m not in seen:
			seen.add(m)
			unique.append(m)
	return unique
