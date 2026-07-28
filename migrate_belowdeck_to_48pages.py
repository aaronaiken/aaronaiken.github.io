#!/usr/bin/env python3
"""One-shot: copy open Below Deck tasks → the 48pages rolled task list.

Below Deck is left UNTOUCHED (copy, not move) — clean it up on the 48pages side afterward.
Dry-run by default: prints what it WOULD copy. Pass --go to actually create the tasks.

COPY-ONCE: re-running with --go duplicates in 48pages (there's no idempotency marker), so
run it a single time. Needs NOTEBOOK_SLIP_TOKEN in the environment (loaded from .env).

    python3 migrate_belowdeck_to_48pages.py           # dry-run
    python3 migrate_belowdeck_to_48pages.py --go       # actually migrate
"""
import sys

from dotenv import load_dotenv

load_dotenv()

from helpers.db import get_db          # noqa: E402
from helpers import notebook as nb      # noqa: E402


def main():
    go = '--go' in sys.argv
    conn = get_db()
    rows = conn.execute(
        'SELECT title FROM tasks WHERE project_id IS NULL AND status = "open" ORDER BY "order"'
    ).fetchall()
    titles = [(r['title'] or '').strip() for r in rows]
    titles = [t for t in titles if t]
    print('open Below Deck tasks: %d' % len(titles))

    if go and not nb._nb():
        print('48pages client unavailable — set NOTEBOOK_SLIP_TOKEN in .env')
        return 1

    created = 0
    for t in titles:
        print(('CREATE: ' if go else 'would create: ') + t[:90])
        if go:
            try:
                nb.task_create(t)
                created += 1
            except Exception as e:
                print('  ! failed: %s' % e)

    if go:
        print('\nmigrated %d/%d tasks into the 48pages list. Below Deck untouched — tidy up there.'
              % (created, len(titles)))
    else:
        print('\ndry-run — nothing written. Re-run with --go to migrate.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
