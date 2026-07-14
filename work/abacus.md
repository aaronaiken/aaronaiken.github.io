---
layout: abacus
title: Mindsteward Abacus
permalink: /work/abacus/
page_ident: "WORK · BUILT FOR OTHERS"
description: "Mindsteward Abacus — the operational hub (check-in, communications, health, fulfillment, reporting) built for Mind Steward, a ~100-camper musical theater day camp."
author: aaron
published: true
---

*It started as a check-in, check-out, and movement-tracking system for Mind Steward — a ~100-camper musical theater day camp. It grew into the camp office's operational hub.*

In production for the camp — behind a staff login, closed-source.

---

## The Problem

The camp ran daily check-in on the tool built into their registration platform, and it was a recurring headache: buggy, inconsistent device-to-device, and prone to failing during the morning rush when connectivity dropped. It also stopped at the gate — once a camper was inside, there was no way to know which elective they were actually in. And it couldn't gracefully handle many staff checking kids in at the same time, which is exactly what a hundred-kid morning demands.

But the check-in tool was only the loudest problem. Around it, the office ran the camp out of spreadsheets, group texts, and paper: parent emails sent by hand, staff notes passed by word of mouth, injury reports on a clipboard, scripts mailed from a personal address book, and a daily reporting ritual rebuilt every morning. The camp needed something reliable at the gate — and, once there was a single live roster, a place to run everything that hung off it.

## What I Built

**Attendance & movement**

- **Gate check-in & check-out** — QR badge scan (reusing the existing badges) or name search, on any staff phone or tablet, many at once. Every event — arrival and departure — is attributed to the staff member who logged it (by their sign-in), and check-out also captures who the camper was released to, verified against the approved-pickup list.
- **Elective roll call** — each elective's intern marks present/absent for their room, with a flag for any camper who's expected there but never checked in at the gate.
- **Live movement dashboard** — on-site / not-arrived / checked-out counts, and a per-period view of who's in which elective and who's unaccounted for, each missing camper showing their last-seen event. The single pane of glass for the middle of the day.
- **Evacuation headcount** — for a fire drill or a real emergency, a one-tap accountability screen: everyone currently on-site (straight from the event log), each tapped off as they're accounted for, with a running count and a printable list. Any staff member can pull it up, and it's built to **open offline** — because an emergency is exactly when you can't count on the network.

**Communications**

- **Parent email broadcasts** — compose to an audience, see the recipient count before sending, and deliver via a verified sending domain. Every parent email carries a one-click unsubscribe; delivery, bounces, and spam complaints are tracked back through webhooks and suppress bad addresses automatically.
- **Internal staff messaging** — daily messages to staff and interns with read receipts, an inbox, and a full-screen interstitial for the ones that must be acknowledged before anyone moves on. Lightweight reactions and replies so a note can become a short thread.

**Health, records & logistics**

- **Health & incident log** — injuries, illness, behavior, and medical events recorded as standalone entries with follow-ups and a resolved state, kept separate from attendance and visible only to health and admin staff.
- **Roster import with a diff preview** — pulls the registration export and shows exactly what will change — new campers, edits, removals — before anything is committed, and never touches attendance history on import.
- **Scripts & shipping** — the pre-camp script mailing, run from the app: every camper's home address, a record of who's had their script sent, and a courier-ready CSV export.
- **Show-day mode** — who's staying after the performance and on which night, a catering list with dietary needs, and show-day badges surfaced on the dashboard.

**Reporting & printables**

- **One-click reports** — Daily Roster, Daily Checkout, Health, Missing-Info, and Full Roster, generated live as Excel or PDF in the exact shape of the spreadsheets they already used. The hand-built morning reports became a button.
- **Printable info sheets** — a mail-merge to a bulk PDF, one per camper, using the same merge fields and formatting as the email and message composers. The principle: *anything the camp can email, it can also send home on paper.* The goal is for as close to 100% of parents as possible to know, 100% of the time, what's happening and what's needed of them on any given day — and that can't depend on whether a family checks their inbox.
- **Session insights** — attendance and elective-participation trends across the two weeks, derived from the same event log.

**Underneath**

- **Role-based access** — granular capabilities (gate, roll call, dashboard, communications, contacts, health, admin) so a gate volunteer, an elective intern, a nurse, and an administrator each see exactly what their job needs and nothing it doesn't. Every change is audited.
- **Offline-first** — the gate and roll-call screens keep working with no network; actions queue on the device and sync when it returns, with no double-counting and no silent data loss.

## The Approach

The whole system rests on one decision: **an append-only event log is the source of truth.** Every scan, roll-call tap, and checkout is an immutable record; a camper's current status is *derived* by folding the day's events rather than stored as a mutable flag.

That single choice solves the three hardest requirements at once. Concurrent multi-device use needs no locking — two devices scanning the same camper just write two events, and the derived state converges. Offline sync is safe to replay because each event is idempotent on a client-generated id. And the audit trail (who, when, which device) is intrinsic to every record. The feature the old system most struggled with — everyone checking in at once — became the easy case. And the highest-stakes one comes almost for free: "who is on-site right now" is just a fold of the day's events, so an accurate evacuation headcount is always one tap away, with no separate system to keep in sync.

The second decision shaped everything that grew on top: because Abacus holds minors' contact and health data, **access is capability-based from the ground up.** Family contacts and health records are visible only to the roles that need them; a broadcast can only be sent by someone with the communications capability; every action lands in an audit log. Handling sensitive data well isn't a feature bolted on at the end — it's the shape of the permission system the rest of the app is built inside.

The system also handles the parts that don't show up in a demo: a custom domain with TLS, transactional email on its own verified sending domain, and a database that scales to near-zero cost the fifty weeks a year the camp isn't in session.

## How It's Built

**Backend:** Python 3.12 / [Flask](https://flask.palletsprojects.com) (app-factory), Flask-SQLAlchemy, Flask-Login with a custom capability layer. Postgres on [Neon](https://neon.tech), standalone Alembic migrations, gunicorn.

**Frontend:** No framework, no build step. Server-rendered Jinja for admin, communications, health, and reports; a focused vanilla-JS app for the offline-capable Scanner, Roll Call, and Dashboard screens, backed by IndexedDB with a service worker. QR scanning via the native `BarcodeDetector` with [ZXing](https://github.com/zxing-js/library) as fallback, plus USB/Bluetooth scanner support at the gate.

**Documents:** openpyxl (Excel reports) + reportlab (PDF reports and printable badge cards). **Email:** [Resend](https://resend.com) for parent and staff mail, with Svix-verified inbound webhooks for delivery/bounce/complaint tracking. **Also:** web push for staff notifications. **Hosting:** Docker on [Fly.io](https://fly.io) + Neon, Cloudflare DNS.

## Outcome

Live and in production for the camp's two-week season — and by the end it was doing far more than counting kids. One real-time roster fed attendance, the parent and staff communications, the health and incident records, the script-mailing logistics, and the daily reporting, run by about thirty people — a dozen staff and the interns leading electives — across their own phones. It grew from a check-in replacement into the office's operational hub, and it did the thing it was first built to do without fail: keep an honest count of every camper, all day, from drop-off to pickup.

---

## The Stack

- **Python 3.12 / Flask** (app-factory) — backend
- **Flask-SQLAlchemy + Flask-Login + custom capabilities** — ORM, auth, role-based access
- **Postgres / Neon** — database
- **Alembic** — migrations
- **Vanilla JS + IndexedDB + Service Worker** — offline PWA screens
- **BarcodeDetector / ZXing / HID** — QR scanning
- **openpyxl + reportlab** — Excel reports, PDF reports, printable badge cards
- **Resend (+ Svix webhooks)** — parent & staff email, delivery tracking
- **Web Push** — staff notifications
- **Fly.io + Docker** — hosting
- **Cloudflare** — DNS

---

## Scope

The system of record for *attendance*, and the operational surface around it — it reads a one-way roster export from the registration platform and never writes back. Not a registration or payment tool. Parents receive email but never log in; the app is staff-only behind authentication. It handles minors' PII and health data, and the whole permission model is built accordingly.
