#!/usr/bin/env python3
import datetime
import os
import subprocess
import pytz

# --- Configuration ---
STATUS_FOLDER = "_status_updates"
GIT_COMMIT_MESSAGE = "Add new status update"
GIT_BRANCH = "main"  # Or your main branch name

# --- Get Status Update ---
# status_text = input("Enter your status update: ")
# now = datetime.datetime.now()
# date_str = now.strftime("%Y-%m-%d %H:%M:%S %z")
# filename = now.strftime(f"{STATUS_FOLDER}/%Y-%m-%d-%H%M%S-status.markdown")

# --- Get Status Update ---
status_text = input("Enter your status update: ")

# --- Generate Timezone-Aware Date/Time ---  <-- Updated this section
utc_now = datetime.datetime.utcnow().replace(tzinfo=pytz.utc)
eastern = pytz.timezone('America/New_York') # Using the same timezone as app.py
now_eastern = utc_now.astimezone(eastern)
date_str = now_eastern.strftime("%Y-%m-%d %H:%M:%S %z") # Format includes timezone offset
filename = now_eastern.strftime(f"{STATUS_FOLDER}/%Y-%m-%d-%H%M%S-status-bash.markdown") # Suffix changed to -bash

print(f"Generated Date String: {date_str}") # Optional: Good for debugging
print(f"Generated Filename: {filename}")    # Optional: Good for debugging

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
	os.makedirs(STATUS_FOLDER, exist_ok=True)  # Ensure the folder exists
	with open(filename, "w") as f:
		f.write(front_matter)
	print(f"Status update saved to {filename}")

	# --- Git Operations ---
	try:
		# It's often better to pull before adding/committing to avoid conflicts
		print("Pulling latest changes...")
		subprocess.run(["git", "pull", "origin", GIT_BRANCH], check=True)

		print("Adding file...")
		subprocess.run(["git", "add", filename], check=True)

		print("Committing file...")
		subprocess.run(["git", "commit", "-m", GIT_COMMIT_MESSAGE], check=True)

		print("Pushing changes...")
		subprocess.run(["git", "push", "origin", GIT_BRANCH], check=True)
		print("Status update committed and pushed to GitHub.")

	except subprocess.CalledProcessError as e:
		print(f"Error during Git operations: {e}")
	except FileNotFoundError:
		print("Error: Git command not found. Make sure Git is installed and in your PATH.")

except Exception as e:
	print(f"An error occurred: {e}")