---
layout: tidy-cal
title: Tidy Calendar
permalink: /tools/tidy-cal/
page_ident: "TIDY · MAC UTILITIES"
author: aaron
hero_status: "Free · Coming Soon"
breadcrumb:
  - { label: Tools, url: /tools/ }
  - { label: Tidy, url: /tidyapps/ }
  - { label: Tidy Calendar }
description: A glanceable calendar in your Mac menu bar. Click the date for a clean month grid — today highlighted, locale-correct, optional ISO week numbers. Free, no permissions.
---

*Last updated: 2026-07-07*

Tidy Calendar puts the month one glance away. Click the date in your menu bar and a clean grid drops down — today highlighted, the week starting on the right day for where you are. No app to launch, no window to manage, no permissions to grant.

It's the third app in the [Tidy family](/tidyapps/), and it's the free front door: the one you can hand to anyone.

---

## Why It Exists

You don't need a calendar app to answer "wait, what's the date on Thursday?" You need a calendar you can *glance* at. But the menu-bar clock only shows today, and opening a full calendar app to check a date two weeks out is a heavy answer to a light question.

Tidy Calendar is the light answer. The month, right there, the instant you click — and then it's gone again. It does one small thing that you do a dozen times a day, and it does it without ceremony.

---

## How It Works

Your menu bar shows the date (in the format you choose — from a full weekday-and-month down to just a clean day-number badge). Click it and a month grid appears: today highlighted, the surrounding days laid out in a fixed six-week grid so it never jumps around as you page between months.

It's **locale-correct** where it counts — the week starts on Sunday or Monday according to your region (or your override), because that's the thing calendar apps most often get wrong. Optional **ISO 8601 week numbers** run down the side for the people who live by them. And it refreshes itself at midnight and after your Mac wakes, so the highlighted day is never stale.

---

## How It's Built

**App:** Swift 6 with strict concurrency, AppKit for the menu-bar item, SwiftUI for the month grid and settings. A menu-bar agent (`LSUIElement`), no dock icon, no third-party dependencies. Generated from a `project.yml` via XcodeGen.

**The grid:** Always six rows by seven columns — leading days from the previous month, the current month, trailing days from the next — so the popover is the same size every month. Weekday order and week numbers both derive from your locale's calendar, not hardcoded.

**Permissions:** None. Tidy Calendar draws a calendar; it asks for nothing. That's the point — it's the free, no-questions front door to the rest of the family.

---

## The Stack

- **Swift 6** — strict concurrency
- **AppKit** — `NSStatusItem`, the menu-bar date
- **SwiftUI** — month grid + settings
- **Locale-aware date math** — first-day-of-week, ISO 8601 weeks
- **LSUIElement** — menu-bar agent, no dock presence
- **XcodeGen** — project generation, zero third-party dependencies
- **App Sandbox** — Mac App Store distribution, free

---

## What It Is Not

- Not an events app. No EventKit, no meetings, no reminders — just the grid. (That may come later; the free version stays free.)
- Not a launcher for a heavier calendar. It answers the date question and gets out of the way.
- Not permission-hungry. It reads nothing and asks for nothing.
- Not tracking anything. No analytics, no telemetry, no network calls.

A calendar you glance at should be free and frictionless. This one is both.
