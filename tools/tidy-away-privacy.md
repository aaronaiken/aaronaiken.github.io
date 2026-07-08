---
layout: tidyaway
title: Tidy Away — Privacy
permalink: /tools/tidy-away/privacy/
page_ident: "TIDY · MAC UTILITIES"
author: aaron
breadcrumb:
  - { label: Tools, url: /tools/ }
  - { label: Tidy, url: /tidyapps/ }
  - { label: Tidy Away, url: /tools/tidy-away/ }
  - { label: Privacy }
hero_title: "PRIVACY"
tagline: "How Tidy Away treats your data. The short version: it barely touches it."
hide_cta: true
description: Tidy Away's privacy policy. It never reads your messages, keeps everything on your Mac, and sends nothing anywhere.
---

*Last updated: 2026-07-07*

This is the privacy policy for [Tidy Away](/tools/tidy-away/), the menu-bar iMessage auto-responder. It's written in plain language on purpose. If anything here is unclear, [email me](mailto:aaron@omg.lol).

The one-sentence version: **Tidy Away runs entirely on your Mac, never reads your messages, and sends nothing to me or anyone else.**

---

## What It Can See

To do its job, Tidy Away needs to notice when a new message arrives and who it's from. That's it. It reads two things from your Messages database: a message's internal row number, and the sender's phone number or email. **It never reads the contents of any message** — there is no code path that decodes what anyone said, because it never needs to know.

It also reads your Contacts, so it can tell whether a sender is someone you know before replying, and skip businesses. Contact data is used in the moment and held in memory only for the current session.

---

## What It Does With It

Nothing leaves your Mac. Tidy Away has no server, no account, no analytics, no telemetry, and makes no network connections of its own. When it sends an away note, it does so through Messages on your Mac, exactly as if you'd typed it — the message goes to your recipient and nowhere else.

Your away note, your exclusion list, and your settings are stored in your Mac's standard preferences. The exclusion list is stored as references to Contacts entries, not as phone numbers, so the list itself holds no personal data.

---

## The Diagnostics Log

Tidy Away keeps a small local log so that if something misbehaves, you can send it to me to debug. That log lives on your Mac and is never transmitted anywhere unless *you* choose to email it.

Even then, it's scrubbed before it's ever written: first names only, phone numbers reduced to their last four digits, and **no message contents of any kind**. If you email a log to me, I see decisions the app made — "replied to Aaron," "skipped a business contact" — never conversations.

---

## What It Never Does

- Never reads, stores, or transmits the contents of your messages.
- Never sends your Contacts, phone numbers, or any personal data off your Mac.
- Never uses analytics, tracking, or telemetry of any kind.
- Never talks to a server — there isn't one.
- Never marks a message read or writes to your Messages database.

---

## Permissions

Tidy Away asks for three system permissions on first run, and uses each for exactly one thing:

- **Full Disk Access** — to notice that a message arrived (read-only; never contents).
- **Contacts** — to know whether a sender is someone you know.
- **Automation** — to send your away note through Messages.

You can revoke any of them at any time in System Settings, and Tidy Away simply stops doing the part that needed it.

---

## Changes

If this policy ever changes, the date at the top changes with it. Since Tidy Away collects nothing and sends nothing, there isn't much here that *can* change — but if it does, it'll be stated plainly.

Tidy Away is built so that trusting it doesn't require trusting me. The privacy isn't a promise bolted on top; it's how the thing is made.
