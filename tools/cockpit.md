---
layout: page
title: The Cockpit
permalink: /tools/cockpit/
page_ident: "WORKSHOP · TOOLS & EXPERIMENTS"
author: aaron
---

*Last updated: 2026-06-07*

The Cockpit is a private, password-protected web application I built to publish status updates to this site from anywhere — a phone, a tablet, a borrowed computer. It lives on [PythonAnywhere](https://pythonanywhere.com) and handles everything from writing the update to pushing it live.

It has since grown far past that original brief. The Cockpit is now the bridge of a small private operating system — publishing, a task kneeboard (Below Deck), a project knowledge base (Command Deck), a daily focus view (Today), full time tracking, mileage logging, meeting records, a support-ticket queue, reports across all of it, and a private AI companion (Huyang). It runs on a single Flask app split across seventeen blueprints. None of it is publicly accessible. This page is the technical manual.

---

## Why It Exists

Status updates on this site are Markdown files. Each one lives in a `_status_updates/` collection in the Jekyll repository. To publish one, you need to create a file with the right front matter, commit it, and push it to GitHub — at which point GitHub Pages rebuilds the site and the update goes live.

That's a fine workflow at a desk. It is not a fine workflow on a phone.

The Cockpit solves that for status updates. Every feature that came after solves a similar friction somewhere else: tasks I'd forget on the way from the bedroom to the kitchen, project context I'd lose between sessions, time entries that never got typed up, mileage logs scattered across three notebooks. One application, one login, all of it.

---

## Cockpit Architecture (The May 2026 Refactor)

The Cockpit started as a single ~2,600-line `app.py`. By the time the project hit its tenth major feature, it was unmaintainable — finding a route required `Cmd+F` and patience, shared helpers were intertangled, and any change risked breaking something far away.

In May 2026 the entire app got split across three layers:

- **`app.py` (~140 lines)** — entry point only. Imports, env-var constants, the `Flask()` constructor, and the chain of `app.register_blueprint(...)` calls for each blueprint. Nothing else.
- **`helpers/`** — shared utilities, organized by concern. Auth, database, git operations, Bunny image uploads, omg.lol mirroring, comms, scratch I/O. Every helper is a leaf in the import graph — they don't import from `app.py` or from each other.
- **`blueprints/`** — one Flask Blueprint per route domain. Seventeen of them currently, each owning its own routes and any blueprint-internal helpers.

The result: routes are findable, helpers are reusable, and each blueprint is independently editable. The aesthetic and behavior of the app didn't change. Only the file structure did.

---

## The Publishing Flow

**Authentication:** Cookie-based. A password form sets an `auth_token` cookie on success. Every route checks for it. Simple and sufficient for a personal tool.

When a status update is submitted the app does the following in sequence:

- Generates a filename from the current timestamp in Eastern time — something like `2026-04-07-214532.markdown`
- Builds the Jekyll front matter: date, layout, author, source, and any hashtag-detected categories like `#movie` or `#coffee`
- If an image was attached, saves it to the assets directory, runs it through Pillow to resize and optimize it, and appends the image reference as Markdown
- Writes the complete Markdown file to the `_status_updates/` directory
- Runs `git pull --rebase`, `git add`, `git commit`, and `git push` — in that order
- If the update is text-only (no image), also posts to [omg.lol](https://omg.lol) via their API, with the leading emoji parsed out into a separate field their API expects

**Image optimization:** Uploaded images are resized to a maximum width of 1200px, converted to JPEG if needed, and saved at 85% quality. Small enough for the web, good enough to look right.

**The omg.lol mirror:** Status updates without images are automatically mirrored to my omg.lol status page. The app checks if the first character of the text is an emoji — if it is, that emoji gets extracted into a dedicated field their API uses for display, and the rest of the text becomes the content.

---

## The Comms

There is a `comms.txt` file in the repository that the Cockpit reads on every page load. It contains messages that appear in the interface as a kind of ambient context — things like time-of-day greetings, day-of-week notes, or just things I wrote to myself.

Each line is either a plain message or a pipe-delimited message with tags that determine when it appears. A line like `PM|FRIDAY|Hey, it's almost the weekend` only shows up on Friday afternoons. A plain line shows up any time.

The app builds a weighted list of valid messages based on the current time — more specific matches appear more often — and picks one at random to display. It is an easter egg for an audience of one.

---

## Below Deck

Below Deck is a private task kneeboard accessible from the Cockpit. It is intentionally minimal — no projects, no priorities, no due dates. Just a quick place to capture what needs doing.

Tasks have optional tags (work, home, errand, personal) and support drag-to-reorder. Completed tasks surface in a Today's Wins section and auto-clear at 4am. The kneeboard is a kneeboard. It does not try to be anything else.

Tasks that grow into something larger can be promoted to the Command Deck with one tap.

---

## Scratch Pad

A private cross-device notepad that lives inside the Cockpit. Notes sync to the server automatically and fall back to localStorage if the network is unavailable. Accessible from the Cockpit and from anywhere in the Command Deck via a keyboard shortcut.

---

## The Command Deck

The Command Deck is a private project knowledge base that lives inside the same application as the Cockpit. It is where tasks that outgrow the kneeboard go — projects with notes, checklists, file attachments, and context.

Each project is its own page. Notes are freeform. Checklists track what's in progress. Files are stored on a CDN. Projects can be marked private and hidden behind a PIN.

The Command Deck has its own AI companion named Huyang — named after the ancient archivist droid from *Ahsoka*. When you're on a project page, Huyang has read everything in it and can answer questions about it precisely. He does not have a personality agenda. He reads what is in front of him and answers carefully.

---

## Today

Today is a single-column daily focus view: the things I starred for this day, across tasks, checklists, meetings, and tickets. The list is auto-cleared at 4am Eastern Time so each day starts empty.

Anything in the Command Deck or Below Deck can be added to Today with a click. The Cockpit nav surfaces a Today count when there are items in it. The point is keeping the day's intentions in one place so I don't have to remember where I parked them.

---

## Time Tracking

The time-tracking layer runs across the rest of the system. A timer can be scoped to a task, a checklist item, a meeting, a ticket, or a free-form work-subproject — but only one of those at a time. A four-way mutex enforces this at the schema level.

A separate `time_category_id` runs orthogonal to the scope. It's how a single entry can be both "stop A's checklist item" and "category: Engineering." When a timer starts against a scoped entity, the entry inherits that entity's default category if one is configured and the caller didn't override it.

You cannot run two timers for the same project at once — a 409 stops you with a clear error. You can run timers on different projects simultaneously when the work genuinely splits that way.

The whole thing is queryable: what I worked on Tuesday, which categories ate the week, what's open right now.

---

## Mileage

Mileage entries link a from/to address pair to a starting odometer reading, an ending odometer reading, and a snapshot of the reimbursement rate at the time of the trip. (Rates change. The snapshot is so a stale rate doesn't invalidate old entries.)

Three flows cover the common patterns:

- **START TRIP** records the start odometer immediately, leaving the end NULL. Useful when leaving without knowing the destination odometer yet.
- **LOG FULL TRIP** captures everything at once, after the fact.
- **FINISH TRIP** closes out a previously started trip.

A bulk submit handles batches of entries. An Excel export uses openpyxl (lazy-imported) to produce a reimbursement-ready spreadsheet.

Mileage entries can optionally start a linked `time_entries` row when the trip begins, so the time is captured alongside the miles for trips where both metrics matter. The linked timer auto-stops when the trip's end odometer is filled in.

---

## Meetings

Each meeting is a project-linked record with markdown notes, action items (which are real tasks in the system, linked back to the meeting), per-meeting time tracking, and a status (`scheduled`, `complete`, `canceled`, `no_show`). A default `time_category_id` propagates to any timers started on the meeting.

Recurring meetings (`weekly`, `biweekly`, `monthly`) spawn the next instance when the current one is marked complete. Recurring instances share a `recurrence_anchor_id` so the series stays linked across time.

The notes field is markdown because meeting notes need real formatting — bullet points, sub-bullets, the occasional link — and HTML would be too much friction.

---

## Tickets

A support-ticket queue. Each ticket gets a TKT-NNNN id. Status flows: `open` → `pending` → `in_progress` → `closed`, with `reopen` back to `open`. Closed tickets require a resolution string; the form will not submit without one.

Tickets carry a priority, a customer group, a customer, a type, an optional default `time_category_id`, due and requested dates, and a `today` star. The first timer started against a ticket auto-advances it to `in_progress` so the queue stays honest about what's actively being worked.

Customer groups, customers, types, and time categories all live in the Lookups module so they can be managed centrally instead of re-entered fresh into each ticket.

---

## Reports

A read-only view layered on top of everything else. Five tabs:

- **Area** — rollup by major area (work subprojects, personal projects)
- **Project** — rollup by project
- **Day** — by-day breakdown of entries
- **Timesheet** — pivot table by week, with rows flippable between Project and Category
- **Mileage** — mileage rollups suitable for reimbursement requests

The entries table on the Day tab supports retroactive category edits — if I forgot to pick a category at start-of-timer, I can fix it from the report instead of digging back through the source.

---

## Settings & Lookups

Settings is a small configuration page. The values it manages:

- Mileage reimbursement rate (the rate that snapshots into new entries)
- Vehicle labels and the default vehicle
- Default mileage project (so I don't have to pick on every trip)
- Idle threshold (used by the timer system for warnings)

Lookups is a generic CRUD module for the small reference tables the rest of the system needs: customer groups, customers, ticket types, time categories. They sit behind a single admin surface so they're managed once, used everywhere.

---

## The Stack

- **Python** — core language
- **Flask** — web framework, organized across 17 blueprints
- **SQLite** — Below Deck, Command Deck, Today, time tracking, mileage, meetings, tickets, reports, lookups
- **Pillow** — image processing
- **subprocess** — git operations
- **openpyxl** — mileage xlsx export (lazy-imported)
- **PythonAnywhere** — hosting
- **omg.lol API** — status mirroring
- **Anthropic Claude API** — Huyang
- **Bunny.net** — file storage for Command Deck attachments and status images
- **Jekyll** — the site that receives the published files

---

## What It Is Not

The Cockpit is not a CMS. It does not have an edit history for status updates, a delete function, or a draft mode beyond a local buffer. It publishes and that is all. Every status update is permanent and public the moment it is transmitted.

It is also not a project management tool for anyone but me. Below Deck has no notion of assignment, Today has no concept of someone else's day, Tickets has no external requester portal. Everything in it is one-person scope by design.

That is a feature, not a limitation. It encourages writing things worth saying — and the rest encourages doing things worth tracking.

---

*The Cockpit is one part of a three-way publishing pipeline. Status updates can also be posted via a bash script run locally from the command line. Both methods end up in the same place: a Markdown file in the Jekyll collection, committed and pushed, live on the site.*
