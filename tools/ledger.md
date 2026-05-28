---
layout: page
title: The Ledger
permalink: /tools/ledger/
page_ident: "WORKSHOP · TOOLS & EXPERIMENTS"
author: aaron
---

The Ledger is a private, password-protected web application I built to answer one question: *where am I with my debt, and what do I do next?* It lives in the same Flask app as [the Cockpit](/tools/cockpit/) but operates on its own SQLite database and behind a deliberately distinct aesthetic — the chart room of the ship, not another cockpit.

It is not publicly accessible. This page is the technical manual.

---

## Why It Exists

In January 2026 I was carrying roughly $72,000 of debt across nine accounts. I built a debt-elimination spreadsheet. I built a Notion-based transaction tracker. Both went stale within months. Despite that, I paid down about $6,800 in four months without active tracking — the financial behavior was happening at the bank, but the *visibility* into that behavior died.

The Ledger replaces both. It is not a budgeting app. It is not a transaction categorizer. It is a tool with one job: answer "where am I, and what do I do next?" in under five minutes, twice a month, around paydays.

---

## The Five Questions

The Ledger exists to answer five questions on every visit:

1. **What do I owe right now, and how fast is it shrinking?** — Total debt, monthly trend, projected debt-free date, monthly interest burn.
2. **Do I have enough in checking to cover what's due before my next payday?** — Cash runway, color-coded by status.
3. **After obligations are covered, how much do I have to attack debt with this payday?** — Free-to-attack number, computed.
4. **Where should that attack money go?** — Avalanche recommendation with the math shown.
5. **Did the autopays I'm relying on actually clear?** — Confirmation, not logging.

Everything else is secondary or out of scope.

---

## What It Is Not

A short list, because the non-goals matter as much as the goals:

- Not a budgeting app (no envelope budgets, no per-category limits)
- Not a transaction categorizer at logging time (Leak Hunt is the on-demand escape valve for when curiosity strikes)
- Not connected to any bank API — manual entry plus CSV upload only
- No email or SMS notifications — the small debt-total pill in the Cockpit footer is the only nag
- Not a multi-user app
- Not connected to the public Jekyll publishing pipeline

The simplicity is the point.

---

## The Chart Room

The Cockpit is amber CRT — transmission, broadcast, fast. The Command Deck is dim archival library — operational memory. Below Deck is sparse kneeboard — immediate task capture. The Ledger is none of these.

Money is intimate, weighted, deliberate. It does not need to be loud.

The Ledger uses a deep navy ink background (warm parchment in light mode), a single brass accent color, hairline rules instead of glowing borders, Fraunces for big numbers and Crimson Pro for body. Numbers are right-aligned and tabular. The room is quiet — like sitting down with a ledger book and a cup of coffee.

---

## How It's Built

**Stack:** Python, Flask, SQLite, hosted on the same [PythonAnywhere](https://pythonanywhere.com) instance as the Cockpit. Authenticated via the existing Cockpit session cookie — no separate login.

**Database:** A separate SQLite file (`ledger.db`), independent from the rest of the system. Twelve tables covering accounts, balance snapshots, debt transactions, recurring expenses, income events, one-time events, leak-hunt imports and per-transaction categorization, rule-based auto-categorization, and a milestone progress sequence. Current balances are never stored as columns — they are always derived from the most recent snapshot for each account, so the audit trail is the source of truth.

**Math:** All financial logic lives in a single helpers module. The most important function is the projection engine — an interest-aware month-by-month simulation that applies minimums, attacks the primary target, accrues interest, and cascades freed allocation onto the next debt when each one dies. It supports an optional overrides dict so the same function powers both the live baseline and the projection sandbox.

**The chart-room aesthetic** is implemented in a single CSS file using design tokens that respect `prefers-color-scheme`. New fonts loaded for this app only.

---

## The Four Phases

The Ledger shipped in four major phases over a week in May 2026.

**Phase 1 — Foundation.** Glance dashboard, payday session, account CRUD, recurring expenses, one-time events, history, basic projection, optional Claude-powered payday assistant with rule-based fallback. The bones.

**Phase 2 — Projection Sandbox.** Five what-if controls layered on top of the live projection (redirect bonuses to debt, extra monthly attack, side-income ramp preset, one-time windfalls, FedLoan minimum override). Side-by-side baseline vs sandbox tables with a delta hero strip. Explicit "apply to live config" flow with a confirmation modal that lists every individual change before commit.

**Phase 3 — Leak Hunt.** The escape valve for "where did the money actually go?" Upload a bank CSV, the parser autodetects format and dialect, auto-categorizes against accumulated user rules, flags recurring charges. Dense review screen with keyboard-driven categorization mode. Results page shows a horizontal stacked-bar breakdown in brass tints, a recurring-charges callout (each row has a one-click "add to bills" button), the biggest individual transactions, and a comparison strip against the prior hunt.

**Phase 4 — The Progress Map.** A sequenced milestone framework. One milestone is current at a time; earlier ones are complete; later ones are visible but not pressuring. Inspired by Dave Ramsey's Baby Steps but not faithful — avalanche-first, debt-killed-before-full-emergency-fund, with custom milestones for resolving the FedLoan unknown and reaching a sustained replacement income. Vertical timeline with a brass spine connecting cards, drag-to-reorder, sub-progress chips on the debt-free milestone, sandbox extends with per-milestone projected completion dates.

---

## Integration With the Cockpit

The Cockpit gets a `LEDGER` link in its controls row and a small `LEDGER · $XX,XXX ↓` pill that also renders on every Command Deck page and on Below Deck. The pill is a constant low-grade reminder of the total — deliberate, always-visible. Click it to enter the chart room.

The Ledger does not push notifications, send emails, or otherwise nag. The pill is the entire nag system.

---

## The AI Assistant

A single button on the payday session screen labeled *Ask Claude what to do.* It sends the current state — debts, balances, runway, obligations, recent payments, upcoming events — to Anthropic's API and returns 2–3 recommendations with the math cited. It is advice, not action — nothing reaches a bank. If the API fails or returns invalid JSON, the system falls back to a deterministic rule-based avalanche recommendation so the panel never goes empty.

It is not a chat. There is no memory between calls. Each press is a fresh request. The Ledger is not a companion — it is a tool.
