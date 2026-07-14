---
layout: abacus
title: Mindsteward Abacus
permalink: /work/abacus/
page_ident: "WORK · BUILT FOR OTHERS"
description: "Mindsteward Abacus — a camp check-in, check-out, and movement-tracking system built for Mind Steward, a ~100-camper musical theater day camp."
author: aaron
published: true
---

*A camp check-in, check-out, and movement-tracking system, built for Mind Steward — a ~100-camper musical theater day camp.*

Live at [abacus.mindsteward.com](https://abacus.mindsteward.com) — behind a login, for camp staff. Closed-source.

---

## The Problem

The camp ran daily check-in on the tool built into their registration platform, and it was a recurring headache: buggy, inconsistent device-to-device, and prone to failing during the morning rush when connectivity dropped. It also stopped at the gate — once a camper was inside, there was no way to know which elective they were actually in. And it couldn't gracefully handle many staff checking kids in at the same time, which is exactly what a hundred-kid morning demands.

The camp needed something reliable across a dozen staff devices at once, that kept working when the wifi blinked, that added elective-level attendance, and that produced their existing daily reports without the manual spreadsheet ritual.

## What I Built

- **Gate check-in & check-out** — QR badge scan (reusing the existing badges) or name search, on any staff phone or tablet, many at once. Check-out captures who the camper was released to, verified against the approved-pickup list, plus staff initials.
- **Elective roll call** — each elective's intern marks present/absent for their room, with a flag for any camper who's expected there but never checked in at the gate.
- **Live movement dashboard** — on-site / not-arrived / checked-out counts, and a per-period view of who's in which elective and who's unaccounted for, each missing camper showing their last-seen event. The single pane of glass for the middle of the day.
- **One-click reports** — Daily Roster, Daily Checkout, Health, Missing-Info, and Full Roster, generated live as Excel or PDF in the exact shape of the spreadsheets they already used. The hand-built morning reports became a button.
- **Offline-first** — the gate and roll-call screens keep working with no network; actions queue on the device and sync when it returns, with no double-counting and no silent data loss.

## The Approach

The whole system rests on one decision: **an append-only event log is the source of truth.** Every scan, roll-call tap, and checkout is an immutable record; a camper's current status is *derived* by folding the day's events rather than stored as a mutable flag.

That single choice solves the three hardest requirements at once. Concurrent multi-device use needs no locking — two devices scanning the same camper just write two events, and the derived state converges. Offline sync is safe to replay because each event is idempotent on a client-generated id. And the audit trail (who, when, which device) is intrinsic to every record. The feature the old system most struggled with — everyone checking in at once — became the easy case.

The system also handles the parts that don't show up in a demo: a custom domain with TLS, transactional email on its own verified sending domain, and a database that scales to near-zero cost the fifty weeks a year the camp isn't in session.

## How It's Built

**Backend:** Python 3.12 / [Flask](https://flask.palletsprojects.com), Flask-SQLAlchemy, Flask-Login. Postgres on [Neon](https://neon.tech), Alembic migrations, gunicorn.

**Frontend:** No framework, no build step. Server-rendered Jinja for admin and reports; a focused vanilla-JS app for the offline-capable Scanner, Roll Call, and Dashboard screens, backed by IndexedDB with a service worker. QR scanning via the native `BarcodeDetector` with [ZXing](https://github.com/zxing-js/library) as fallback, plus USB/Bluetooth scanner support at the gate.

**Reports:** openpyxl (Excel) + reportlab (PDF). **Email:** [Resend](https://resend.com). **Hosting:** Docker on [Fly.io](https://fly.io) + Neon, Cloudflare DNS.

## Outcome

Live and in production for the camp's two-week season — reliable across a stack of staff devices scanning at once, resilient to dropped wifi, with the elective-level visibility the old tool never had and the daily reports reduced to a single click. It does the one job it was built for: keep an honest count of every camper, all day, from drop-off to pickup.

---

## The Stack

- **Python 3.12 / Flask** — backend
- **Flask-SQLAlchemy + Flask-Login** — ORM + auth
- **Postgres / Neon** — database
- **Alembic** — migrations
- **Vanilla JS + IndexedDB + Service Worker** — offline PWA screens
- **BarcodeDetector / ZXing / HID** — QR scanning
- **openpyxl + reportlab** — Excel + PDF reports
- **Resend** — transactional email
- **Fly.io + Docker** — hosting
- **Cloudflare** — DNS

---

## Scope

The system of record for *attendance* — it reads a one-way roster export from the registration platform and never writes back. Not a registration or payment tool, not parent-facing, not public. It handles minors' PII and health data, and is built accordingly.
