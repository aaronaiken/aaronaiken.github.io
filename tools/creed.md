---
layout: page
title: The Creed
permalink: /tools/creed/
page_ident: "WORKSHOP · TOOLS & EXPERIMENTS"
author: aaron
---

*Last updated: 2026-06-07*

The Creed is a private daily-reflection web application I built for my kids. Each child signs in with a PIN, gets a daily virtue mission, earns XP and credits, and customizes a Mandalorian-themed character. Parents get a dashboard.

It is not publicly accessible. This page is the technical manual.

---

## Why It Exists

The kids needed a way to engage daily with the virtues we want them to grow in — patience, courage, mercy, hope — without it feeling like homework. Worksheets get ignored. Apps get scrolled past. A blank journal is too open.

The Creed solves that with a constraint: one virtue per day, one short prompt, one short reflection, then a small reward. The structure is small enough that a four-year-old can do it and a twelve-year-old still enjoys it.

It is not a Bible app. It is not a chore tracker. It is one thing: a daily contemplative habit with just enough delight built in to make it stick.

---

## How It's Built

**Backend:** Python, [Flask](https://flask.palletsprojects.com), SQLAlchemy ORM. Hosted on [PythonAnywhere](https://pythonanywhere.com).

**Database:** SQLite. One parent account per family, multiple kids per parent. Each kid has their own virtue progression, XP balance, credit balance, cosmetic inventory, and reflection history. Twelve schema versions deep so far — the app has earned its scars.

**Authentication:** Parents log in with email + password (pbkdf2:sha256). Kids log in with a per-kid PIN — short, memorable, no password resets.

**The daily rollover** is timezone-aware. A new mission becomes available at the family's local midnight; the previous day's reflections lock.

---

## The Virtue Loop

Each kid has a virtue rotation. When they log in, the system selects the next virtue in their sequence and presents a single prompt drawn from an age-appropriate pool. The kid responds in whatever way feels natural — typed, or dictated for the youngest. There is no word count, no spell-check, no grade.

Completing the reflection earns XP and credits. XP accumulates and unlocks tier badges; it does not spend. Credits spend in the wardrobe.

---

## The Wardrobe

Each kid has a Mandalorian-themed character that renders inline on every page they see. Credits spend on cosmetic upgrades — helmet color, tunic color, pants color, glove color — each tracked as a per-kid field in the database and themed via CSS variables. Subtle WAAPI animations give the character life without distracting from the page.

The choice of aesthetic is intentional. A Mandalorian is a person who lives by a Creed. The visual layer ties the gamification surface to the contemplative practice without being heavy-handed.

---

## The Parent Dashboard

One row per kid: current virtue, today's reflection if any, recent history. Parents can read everything kids have written. Parents can edit kid configurations — PIN, name, virtue rotation, starting cosmetic palette. Parents cannot edit reflections. That boundary is fixed.

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
