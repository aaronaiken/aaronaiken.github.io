---
layout: page
title: The Creed
permalink: /tools/creed/
page_ident: "WORKSHOP · TOOLS & EXPERIMENTS"
author: aaron
---

*Last updated: 2026-06-07*

The Creed is a private daily-reflection web application I built for my son. Mozzie signs in with a PIN, gets a daily virtue mission, earns XP and credits, and customizes a Mandalorian-themed character. Lindsay and I get the dashboard.

It is not publicly accessible. This page is the technical manual.

---

## Why It Exists

Mozzie needed a way to engage daily with the virtues we want him to grow in — patience, courage, mercy, hope — without it feeling like homework. Worksheets get ignored. Apps get scrolled past. A blank journal is too open.

The Creed solves that with a constraint: one virtue per day, one short prompt, one short reflection, then a small reward. Small enough that he can sit with it; structured enough that he comes back.

It is not a Bible app. It is not a chore tracker. It is one thing: a daily contemplative habit with just enough delight built in to make it stick.

---

## How It's Built

**Backend:** Python, [Flask](https://flask.palletsprojects.com), SQLAlchemy ORM. Hosted on [PythonAnywhere](https://pythonanywhere.com).

**Database:** SQLite. One parent account per family, kids beneath. Mozzie has his own virtue progression, XP balance, credit balance, cosmetic inventory, and reflection history. Twelve schema versions deep so far — the app has earned its scars.

**Authentication:** Parents log in with email + password (pbkdf2:sha256). Mozzie logs in with a PIN — short, memorable, no password resets.

**The daily rollover** is timezone-aware. A new mission becomes available at the family's local midnight; the previous day's reflections lock.

---

## The Virtue Loop

Mozzie has a virtue rotation. When he logs in, the system selects the next virtue in his sequence and presents a single prompt drawn from an age-appropriate pool. He responds in whatever way feels natural — typed or dictated. There is no word count, no spell-check, no grade.

Completing the reflection earns XP and credits. XP accumulates and unlocks tier badges; it does not spend. Credits spend in the wardrobe.

---

## The Wardrobe

Mozzie has a Mandalorian-themed character that renders inline on every page he sees. Credits spend on cosmetic upgrades — helmet color, tunic color, pants color, glove color — each tracked as a per-kid field in the database (the schema supports siblings) and themed via CSS variables. Subtle WAAPI animations give the character life without distracting from the page.

The choice of aesthetic is intentional. A Mandalorian is a person who lives by a Creed. The visual layer ties the gamification surface to the contemplative practice without being heavy-handed.

---

## The Parent Dashboard

One row per kid in the dashboard — today there is one row, for Mozzie. Lindsay and I read everything he writes. We can edit his configuration — PIN, name, virtue rotation, starting cosmetic palette. We cannot edit reflections. That boundary is fixed.

---

## The Stack

- **Python** — core language
- **Flask** — web framework
- **SQLAlchemy** — ORM
- **SQLite** — database
- **Jinja2** — server-rendered HTML
- **CSS variables** — per-kid cosmetic theming
- **WAAPI** — character animations
- **PythonAnywhere** — hosting

---

## What It Is Not

- Not a Bible study app — there are better tools for that
- Not connected to any external service — no AI, no email, no notifications
- Not multi-family
- Not open-source

The constraints are the point.
