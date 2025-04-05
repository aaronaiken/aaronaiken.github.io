#!/usr/bin/env python3
import datetime
import os
import subprocess

# --- Configuration ---
STATUS_FOLDER = "_status_updates"
GIT_COMMIT_MESSAGE = "Add new status update"
GIT_BRANCH = "main"  # Or your main branch name

# --- Get Status Update ---
status_text = input("Enter your status update: ")
now = datetime.datetime.now()
date_str = now.strftime("%Y-%m-%d %H:%M:%S %z")
filename = now.strftime(f"{STATUS_FOLDER}/%Y-%m-%d-%H%M%S-status.markdown")

# --- Create Markdown File ---
front_matter = f"""---
title: Status Update
date: {date_str}
layout: status_update
categories: status
author: aaron
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
		subprocess.run(["git", "add", filename], check=True)
		subprocess.run(["git", "commit", "-m", GIT_COMMIT_MESSAGE], check=True)
		subprocess.run(["git", "push", "origin", GIT_BRANCH], check=True)
		print("Status update committed and pushed to GitHub.")
	except subprocess.CalledProcessError as e:
		print(f"Error during Git operations: {e}")
	except FileNotFoundError:
		print("Error: Git command not found. Make sure Git is installed and in your PATH.")

except Exception as e:
	print(f"An error occurred: {e}")