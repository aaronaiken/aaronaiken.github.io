---
layout: page
title: Plink
permalink: /tools/plink/
page_ident: "WORKSHOP · TOOLS & EXPERIMENTS"
author: aaron
---

*Last updated: 2026-06-07*

Plink is a self-hosted tip jar for indie creators. You embed a small snippet on your site, visitors send tips directly via Stripe, and you keep everything Stripe doesn't take. No middleman, no creator-platform account, no 5% skim.

A live instance runs at [plink.aaronaiken.me/please](https://plink.aaronaiken.me/please) — that's the dogfood. The code is closed-source for now while I find the rough edges.

---

## Why It Exists

Most tip-jar services charge a percentage on top of Stripe's already-meaningful processing fees. For a $5 tip that's a non-trivial cut. Worse, they own the relationship with the supporter — the receipt comes from a third party, the tip page doesn't look like the creator's site, and the data lives in someone else's database.

Plink is the alternative. You run it. Stripe runs the payments. There is no third party in the loop, and the tip page looks like *your* page because it's served from your domain.

---

## How It's Built

**Backend:** Python 3.13, [FastAPI](https://fastapi.tiangolo.com) with async SQLAlchemy 2.0. Postgres with asyncpg. Alembic for migrations.

**Frontend:** A SvelteKit admin dashboard for the recipient (you), and a vanilla-JavaScript embed for the wider web. The embed has no framework dependencies — it loads fast, it looks like your site, and it doesn't track visitors.

**Payments:** Stripe Checkout for the actual transaction. Webhooks reconcile completed payments back to your dashboard. The visitor never leaves a Stripe-hosted page until the payment is confirmed.

**Hosting:** Docker container on [Fly.io](https://fly.io), shared-cpu-1x, 512MB RAM, deployed to the IAD region. Cheap enough to run as a personal service indefinitely.

---

## The Embed

A single script tag and a single HTML element. Drop them on any page on your site — a blog post, a landing page, an About page — and Plink renders a tip button styled to match your existing design.

When clicked, the button opens a tip flow. The visitor picks an amount, pays via Stripe Checkout, optionally leaves a note, and that's it. No account creation, no app download, no friction.

---

## The Admin Dashboard

The admin side runs as a SvelteKit app. From there you configure your Stripe account, customize the embed appearance, see your tip history, and read messages tippers leave for you. Notes arrive via Resend's inbound webhook and land in the dashboard alongside the corresponding payment.

---

## What's Coming

Plink is in dogfood mode. Once the rough edges are smoothed and the docs are written, I'll release the source so others can self-host. The trajectory is open-source, self-hosted, single-page — the same shape as the embed itself.

---

## The Stack

- **Python 3.13** — backend language
- **FastAPI** — async web framework
- **async SQLAlchemy 2.0** — ORM
- **Postgres / asyncpg** — database
- **Alembic** — migrations
- **SvelteKit** — admin dashboard
- **Vanilla JavaScript** — public embed
- **Stripe** — payment processing
- **Resend** — inbound tip notes
- **Fly.io** — hosting
- **Docker** — container

---

## What It Is Not

- Not a payment processor. Stripe is. Plink is the layer above.
- Not a SaaS. You host your own instance.
- Not a Patreon competitor. No tiers, no memberships, no community features.
- Not connected to any platform. Your tippers tip you, on your site, in your design.

Tip jars are simple things. Plink keeps them that way.
