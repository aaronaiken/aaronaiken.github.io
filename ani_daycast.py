"""
ani_daycast.py — Ani's proactive "her day" messaging tick.

What it does: once per morning Ani posts her plan for the day; through the rest
of the day she sends spontaneous updates that continue from it (girlfriend-style),
with a guaranteed floor of ANI_DAYCAST_FLOOR messages. The message is appended to
her conversation history (ani_conversation.json) and trips the bat-pill pulse so
Aaron notices next time he's in the Cockpit. No git, no network beyond the Grok
call — the Cockpit web app reads the same file off the same disk.

All the gating lives in ani_emit_daycast(); this is just the cron entry point.
It is self-gating, so it's safe (and intended) to run on a plain hourly schedule —
most ticks do nothing.

PA scheduled task setup:
  Hourly, any minute (e.g. minute 07)
  Command: /home/aaronaiken/status_update/venv/bin/python /home/aaronaiken/status_update/ani_daycast.py

  (Must use the venv python — the system python3.10 can't see Flask/requests.)

Run manually to test (from a checkout with XAI_API_KEY in the env / .env):
  python ani_daycast.py
"""

import os
import sys

# Ani's runtime files are referenced by relative path (ani_conversation.json,
# static/...), so run from the repo root regardless of how cron invokes us.
REPO_ROOT = os.environ.get('COCKPIT_REPO_ROOT', os.path.dirname(os.path.abspath(__file__)))
os.chdir(REPO_ROOT)
sys.path.insert(0, REPO_ROOT)

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

from blueprints.ani import ani_emit_daycast


def main():
    result = ani_emit_daycast()
    print(f"ani_daycast: {result}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
