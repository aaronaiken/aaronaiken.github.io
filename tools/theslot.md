---
layout: page
title: the slot
permalink: /tools/theslot/
page_ident: "WORKSHOP · TOOLS & EXPERIMENTS"
author: aaron
---

*Last updated: 2026-06-10*

The slot is a calm editorial planner for writers who publish across more than one place — a blog, a newsletter, a YouTube channel, a column somewhere. It is a kanban board with four columns (idea → draft → review → published), a Quick Capture input at the top, and an optional AI layer that exists only if you bring your own Anthropic API key.

Live at [theslot.ink](https://theslot.ink). It is sibling to [Endpaper](https://endpaper.day) — Endpaper is where the writing happens, the slot is where the writing is *planned*.

The code is closed-source for now while I find the rough edges. The spec lives in the repo as `spec-editorial-planner.md`.

---

## The Name

In an old newspaper copydesk, the editors sat around a U-shaped table. The editor at the inside of the U — the gap, the seam — was called *the slot*. Every piece of copy passed through the slot before it went to press. The slot read it last. The slot sent it on.

That's the metaphor. The slot is what every piece of writing passes through on the way from idea to published.

---

## Why It Exists

Writers who publish in one place have it easy — one CMS, one queue, one mental model. Writers who publish across multiple places end up with N queues that don't talk to each other, and an N+1 queue in their head trying to remember what's where. The friction isn't in the writing; it's in the meta-work of knowing what stage each piece is in across every destination.

Notion, Trello, Linear can be bent into the shape of an editorial board, but they want to be everything and they're loud about it. The slot is small, opinionated, and built for one job. No due dates, no streaks, no engagement mechanics. No notifications. Four columns and a quiet board.

---

## How It Works

The board has four columns: **Idea**, **Draft**, **Review**, **Published**. Cards move between them by drag-and-drop. Quick Capture sits at the top of the board: type a title, pick a publication, hit Enter, and a card lands in Idea. The target is under ten seconds, zero modals — the difference between a tool that gets opened daily and one that doesn't.

Each card carries a title, a one-paragraph angle, a format glyph inherited from its publication's kind, and an optional `link_url` pointing at wherever the actual writing lives — [Endpaper](https://endpaper.day), a Google Doc, a YouTube script, anywhere. **The slot is a planner, not an editor.** It does not compete with the writing tool. The real writing happens elsewhere.

Cards can be grouped under *projects* — umbrella topics that span multiple pieces. Projects have their own page with a proposal tray that the AI feeds into.

---

## The AI Layer (Optional, Client-Side, BYOK)

The slot has three AI verbs: **Scaffold** (generate an outline for a card), **Decompose** (turn a project into proposed cards across selected publications), and **Voice crafting** (a chat that drafts a publication's voice profile from sample pieces).

All three run **client-side, directly from your browser to the Anthropic API, using your own key**. The server has no `anthropic` package installed. It never sees the key. It never sees the prompts. It never sees the responses. The privacy posture is structural — it isn't a promise, it's that the code physically cannot do otherwise.

Every AI feature degrades silently when no key is present — no locked buttons, no upsell banners, no nag. The slot works as a planner with zero AI. The AI is amplification, not a gate.

---

## Auth

Magic-link sign-in via [Resend](https://resend.com), step-up to a passkey when one is enrolled, lost-passkey recovery on a 24-hour cooldown. No passwords. The step-up is the load-bearing piece: once any passkey is on the account, the magic-link alone isn't enough to sign in — a passkey tap completes the ceremony, which means a stolen email doesn't get you in.

Sessions are httpOnly cookies on the `.theslot.ink` registrable domain, so the apex frontend and the `api.` backend share state without a CORS dance.

---

## How It's Built

**Backend:** Python 3.12, [FastAPI](https://fastapi.tiangolo.com) with async SQLAlchemy 2.0 + asyncpg. Postgres on [Neon](https://neon.tech). Alembic for migrations. [Resend](https://resend.com) for transactional email. WebAuthn ceremonies via the `webauthn` package, lifted (with the E2EE machinery stripped) from Endpaper's auth layer.

**Frontend:** SvelteKit 2 + Svelte 5 (runes), `adapter-static`, deployed to [Cloudflare Pages](https://pages.cloudflare.com). Pure SPA. AI calls go browser → Anthropic via `anthropic-dangerous-direct-browser-access`. Keys live in IndexedDB on the user's device.

**Hosting:** [Fly.io](https://fly.io) for the backend (single shared-cpu-1x:512MB machine in IAD). Cloudflare Pages for the frontend. Cloudflare for DNS, with DMARC management on the domain.

---

## The Stack

- **Python 3.12** — backend language
- **FastAPI** — async web framework
- **async SQLAlchemy 2.0** — ORM
- **Postgres / asyncpg** — database, on Neon
- **Alembic** — migrations
- **SvelteKit 2 + Svelte 5** — frontend, runes mode, adapter-static
- **Anthropic API** — direct browser → Claude, BYOK
- **Resend** — transactional email (magic link + passkey notifications)
- **WebAuthn** — passkeys, via the `webauthn` package
- **Fly.io** — backend hosting
- **Cloudflare Pages** — frontend hosting
- **Fraunces / Inter Tight / JetBrains Mono** — typography

---

## What It Is Not

- Not a writing tool. It plans, links, and tracks. Endpaper and your editor of choice are the writing tools.
- Not a CMS. There is no publish-to-anywhere button. *Published* is a status the user sets manually.
- Not a scheduler or a content calendar. No due dates exist anywhere in the data model.
- Not a multi-user team tool. One user, their publications, their cards.
- Not running any analytics. No tracking pixels in emails. No third-party scripts on any page.
- Not E2EE. Card content is readable by the server — it has to be; it's CRUD. The privacy posture is honesty about that, plus zero data-mining and a full data export.

---

The slot is small on purpose. The four columns are the metaphor, the calm is the feature.
