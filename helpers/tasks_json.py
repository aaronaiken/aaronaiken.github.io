"""Legacy public-tasks JSON storage (assets/data/tasks.json)."""
import os
import json


TASKS_FILE = 'assets/data/tasks.json'


def load_tasks():
	try:
		with open(TASKS_FILE, 'r') as f:
			return json.load(f)
	except FileNotFoundError:
		return {"tasks": []}


def save_tasks(data):
	os.makedirs(os.path.dirname(TASKS_FILE), exist_ok=True)
	with open(TASKS_FILE, 'w') as f:
		json.dump(data, f, indent=2)
