#!/usr/bin/env python3
import datetime
import os
import subprocess
import pytz
import requests
import emoji

# --- Configuration ---
STATUS_FOLDER = "_status_updates"
GIT_COMMIT_MESSAGE = "Add new status update via bash"
GIT_BRANCH = "main"

def post_to_omg_lol(status_text):
	"""Pushes the status update to Omg.lol with emoji parsing."""
	# These are pulled from your ~/.zshrc or ~/.zprofile
	api_key = os.environ.get('OMG_LOL_API_KEY')
	address = os.environ.get('OMG_LOL_ADDRESS')

	if not api_key or not address:
		print("!! Omg.lol credentials missing in local environment. Skipping.")
		return

	url = f"https://api.omg.lol/address/{address}/statuses"
	headers = {
		"Authorization": f"Bearer {api_key}",
		"Content-Type": "application/json"
	}
	
	status_text = status_text.strip()
	emojis_found = emoji.emoji_list(status_text)
	
	payload = {}
	# If starts with emoji, split it out for the Omg.lol 'emoji' field
	if emojis_found and emojis_found[0]['match_start'] == 0:
		extracted_emoji = emojis_found[0]['emoji']
		payload["emoji"] = extracted_emoji
		payload["content"] = status_text[len(extracted_emoji):].strip()
	else:
		payload["content"] = status_text

	try:
		response = requests.post(url, json=payload, headers=headers)
		response.raise_for_status()
		print(">> Successfully posted to Omg.lol!")
	except Exception as e:
		print(f"!! Failed to post to Omg.lol: {e}")

# --- Get Status Update ---
status_text = input("Enter your status update: ")

# --- Generate Timezone-Aware Date/Time ---
utc_now = datetime.datetime.utcnow().replace(tzinfo=pytz.utc)
eastern = pytz.timezone('America/New_York')
now_eastern = utc_now.astimezone(eastern)
date_str = now_eastern.strftime("%Y-%m-%d %H:%M:%S %z")
filename = now_eastern.strftime(f"{STATUS_FOLDER}/%Y-%m-%d-%H%M%S-status-bash.markdown")

# --- Create Markdown File ---
front_matter = f"""---
title: Status Update
date: {date_str}
layout: status_update
categories: status
author: aaron
source: bash
---
{status_text}
"""

try:
	os.makedirs(STATUS_FOLDER, exist_ok=True)
	with open(filename, "w") as f:
		f.write(front_matter)
	print(f"Status update saved to {filename}")

	# --- Git Operations (Using SSH) ---
	try:
		print("Pulling latest changes...")
		subprocess.run(["git", "pull", "origin", GIT_BRANCH], check=True)

		print("Adding file...")
		subprocess.run(["git", "add", filename], check=True)

		print("Committing file...")
		subprocess.run(["git", "commit", "-m", GIT_COMMIT_MESSAGE], check=True)

		print("Pushing changes...")
		subprocess.run(["git", "push", "origin", GIT_BRANCH], check=True)
		print("Status update committed and pushed to GitHub.")

		# --- THE MISSING LINK: Trigger Omg.lol after successful Git Push ---
		post_to_omg_lol(status_text)

	except subprocess.CalledProcessError as e:
		print(f"Error during Git operations: {e}")
	except FileNotFoundError:
		print("Error: Git command not found.")

except Exception as e:
	print(f"An error occurred: {e}")