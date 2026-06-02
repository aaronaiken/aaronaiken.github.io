"""
import_mileage_csv.py
One-shot importer for backfilling Feb-May 2026 mileage from a Notion CSV
export into command_deck.db as drafts (submitted_at=NULL).

Usage:
    python import_mileage_csv.py            # dry-run: prints what would import
    python import_mileage_csv.py --commit   # actually inserts

What it does:
  - Looks up project "Equipment Management & Logistics" by title (case-insensitive).
    Fails loudly if not found — does not create projects.
  - Snapshots rate_cents from settings.reimbursement_rate_cents.
  - Maps vehicle by prefix: "Mazda*" -> 'a', "GMC*" -> 'b'.
  - Forces round_trip = 0 for every row (per import instruction).
  - submitted_at = NULL so the rows land in the "unsubmitted" filter, ready
    for bulk-submit + xlsx export.

Safe to run multiple times against an empty target, but it does NOT
deduplicate — re-running with --commit will create duplicate rows. The
dry-run output is the gate.
"""

import argparse
import csv
import io
import os
import sqlite3
import sys
from datetime import datetime

DB_FILE = os.path.join(
    os.environ.get('COCKPIT_REPO_ROOT', os.path.dirname(os.path.abspath(__file__))),
    'assets/data/command_deck.db'
)

PROJECT_TITLE = 'Equipment Management & Logistics'

CSV_DATA = """Date,Trip,From,To,Miles,Round Trip,Vehicle,Project,Purpose,Rate
2026-02-04,"equipment dropoff pickup and shipment","Home","KB and FedEx",25,Yes,"Mazda GX90",,,
2026-02-09,"Equipment pickup and shipment","Home","KB, FedEx",25,Yes,"Mazda GX90",,,
2026-02-13,"Equipment dropoff, pickup, and shipment","Home","KB, FedEx",17,No,"GMC Terrain",,,
2026-02-17,"Equipment dropoff/pickup/shipping (Shipments + return to inventory)","Home","KB, FX, Home",25,Yes,"Mazda GX90",,"Equipment",
2026-02-24,"Shipment pickup and shipment for Smitha Iddalgave","Home","KB, Fedex",23,Yes,"Mazda GX90",,,
2026-02-25,"Laptop Replacement for Kavitha Dasari","Home","KB, FedEx",25,Yes,"Mazda GX90",,,
2026-03-02,"Replacement for Ian Benn","Home","KB, FedEx",25,Yes,"GMC Terrain",,,
2026-03-06,"Dropping off and picking up to ship","Home","KB, FedEx",25,Yes,"GMC Terrain",,,
2026-03-20,"To office to meet with Sri","Home","KB",20,Yes,"GMC Terrain",,,
2026-03-25,"Equipment return and Retirement Party drop-in","Home","KB",20,Yes,"Mazda GX90",,,
2026-03-26,"to FedEx office to pickup package from CAI/Sidney Franklin","Home","Jonestown Rd FedEx Office",7,Yes,"Mazda GX90",,,
2026-03-27,"Sidney Franklin laptop into office","Home","KB",20,Yes,"GMC Terrain",,,
2026-04-02,"shipments for  and","Home","KB, FedEx",25,Yes,"Mazda GX90",,,
2026-04-09,"dropping off, picking up, shipping","Home","KB, FX",26,Yes,"Mazda GX90",,,
2026-04-13,"Russel Riley overnight laptop","Home","Lab, FX, Home",27,Yes,"Mazda GX90",,,
2026-04-17,"dropping off, picking up, shipping","Home","KB, FX",26,Yes,"GMC Terrain",,,
2026-04-23,"Dropoff, Pickup, and Shipment","Home","KB, FX",25,Yes,"Mazda GX90",,,
"""


def vehicle_code(s):
    s = (s or '').strip().lower()
    if s.startswith('mazda'):
        return 'a'
    if s.startswith('gmc'):
        return 'b'
    return None


def parse_rows():
    reader = csv.DictReader(io.StringIO(CSV_DATA))
    rows = []
    errors = []
    for i, raw in enumerate(reader, start=2):  # start=2 to match spreadsheet line numbers
        try:
            date = (raw['Date'] or '').strip()
            datetime.strptime(date, '%Y-%m-%d')  # validate
            miles = float((raw['Miles'] or '').strip())
            vcode = vehicle_code(raw['Vehicle'])
            if vcode is None:
                errors.append(f"  line {i}: unknown vehicle '{raw['Vehicle']}'")
                continue
            rows.append({
                'date': date,
                'description': (raw['Trip'] or '').strip() or None,
                'from_location': (raw['From'] or '').strip() or None,
                'to_location': (raw['To'] or '').strip() or None,
                'miles': miles,
                'vehicle': vcode,
            })
        except Exception as e:
            errors.append(f"  line {i}: {e}")
    return rows, errors


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--commit', action='store_true',
                    help='actually insert rows (default is dry-run)')
    args = ap.parse_args()

    if not os.path.exists(DB_FILE):
        print(f"x DB not found at {DB_FILE}")
        sys.exit(1)

    rows, errors = parse_rows()
    if errors:
        print("Parse errors:")
        for e in errors:
            print(e)
        sys.exit(1)

    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    proj = cur.execute(
        "SELECT id, title FROM projects WHERE LOWER(title) = LOWER(?)",
        (PROJECT_TITLE,)
    ).fetchone()
    project_id = proj['id'] if proj else None
    project_label = (
        f"{proj['title']} (id={project_id})" if proj
        else f"!! '{PROJECT_TITLE}' NOT FOUND in this DB"
    )

    s = cur.execute("SELECT reimbursement_rate_cents FROM settings WHERE id = 1").fetchone()
    rate_cents = int(s['reimbursement_rate_cents']) if s else 67

    print()
    print(f"DB:           {DB_FILE}")
    print(f"Project:      {project_label}")
    print(f"Rate:         {rate_cents}c/mi")
    print(f"Round trip:   forced to NO for all rows")
    print(f"submitted_at: NULL (drafts)")
    print()
    print(f"{'Date':<12} {'Veh':<4} {'Miles':>6}  {'$':>8}  Description")
    print('-' * 90)
    total_miles = 0.0
    for r in rows:
        amt = r['miles'] * rate_cents / 100.0
        total_miles += r['miles']
        desc = (r['description'] or '')[:55]
        print(f"{r['date']:<12} {r['vehicle']:<4} {r['miles']:>6.1f}  ${amt:>7.2f}  {desc}")
    total_amt = total_miles * rate_cents / 100.0
    print('-' * 90)
    print(f"{'TOTAL':<17} {total_miles:>6.1f}  ${total_amt:>7.2f}   ({len(rows)} rows)")
    print()

    if not args.commit:
        print("Dry-run only. Re-run with --commit to insert.")
        conn.close()
        return

    if project_id is None:
        print(f"x Cannot commit: project '{PROJECT_TITLE}' not found.")
        conn.close()
        sys.exit(1)

    now = datetime.now().isoformat(timespec='seconds')
    inserted = 0
    for r in rows:
        cur.execute("""
            INSERT INTO mileage_entries
              (project_id, date, description, from_location, to_location,
               round_trip, odometer_start, odometer_end, miles, rate_cents,
               vehicle, notes, submitted_at, created, updated)
            VALUES (?, ?, ?, ?, ?, 0, NULL, NULL, ?, ?, ?, NULL, NULL, ?, ?)
        """, (
            project_id, r['date'], r['description'],
            r['from_location'], r['to_location'],
            r['miles'], rate_cents, r['vehicle'],
            now, now,
        ))
        inserted += 1
    conn.commit()
    conn.close()
    print(f"+ Inserted {inserted} rows as drafts (submitted_at IS NULL).")
    print("  View at /command-deck/mileage/ (unsubmitted filter) then bulk-submit")
    print("  and export.xlsx for the Feb-May reimbursement packet.")


if __name__ == '__main__':
    main()
