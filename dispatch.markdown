---
layout: page
title: The Dispatch
permalink: /tools/dispatch/
page_ident: "WORKSHOP · TOOLS & EXPERIMENTS"
author: aaron
---

*Last updated: 2026-07-31*

The Dispatch is a private Flask web application I built to handle all outbound and inbound communication for this site — without exposing my email address publicly, without handing my subscriber list to a newsletter platform, and without any tracking whatsoever.

It lives on [PythonAnywhere](https://pythonanywhere.com), separate from the Cockpit. The composing-and-sending side is private; the pieces you touch as a reader — the signup forms, the unsubscribe and preferences links — are public. This page is the technical manual.

---

## Why It Exists

Three things prompted it.

First, I didn't want my email address on the open web. A contact form is the obvious solution, but most contact form services are either overkill, require accounts, or route your mail through their infrastructure. I wanted something mine.

Second, I wanted to let people sign up for updates when I ship something new — without Mailchimp, without Substack, without handing anyone's email address to a platform I don't control.

Third, once you have a subscriber list, you need a way to actually send to it. So I built that too.

The result is one Flask app that quietly does all of it.

---

## What It Does

### Contact Form

The [contact page](/contact/) on this site submits to a `/contact` endpoint on The Dispatch. The app validates the fields, composes an email with a `Reply-To` header set to the sender's address, and forwards it to my inbox. No data is stored. No copy is kept. It arrives like a normal email and I reply like a normal person.

### Update Signups

The signup forms around the site — the [Signal List](/tools/updates/) for the workshop, and the notify form on each [Tidy app](/tidyapps/) page — let you subscribe to just the things you actually care about. Under the hood these are interest **segments**: you land in the one you signed up from, and you're only ever emailed about that.

I tried the opposite first — one undifferentiated list, no channels, no decision at signup. Simpler to build, but wrong in practice: someone who wants to know when one specific app ships doesn't want everything else too. So segmentation came back — but built so it maintains itself. New signups route to the right segment automatically from the page they came from, I never sort anyone by hand, and you can adjust your own interests any time (see below).

Submissions hit a `/subscribe` endpoint. The app validates the email and writes the entry to a flat JSON file on the server. Re-subscribing merges your interests rather than duplicating you. No database. No third party holding the list. Just a JSON file I own.

### Newsletter Sender

A private, double-locked `/send` route serves a Markdown composer. HTTP Basic Auth is the first lock — the browser prompts for credentials before the page loads. A second send password is required before anything goes out.

I pick a **segment** to send to — a specific app, everyone on the whole-family list, or the general workshop list — write in Markdown, and hit Preview. It renders exactly what recipients will see, with a live count of who's in that segment. Confirm sends each person their own personalized copy, with manage-preferences and unsubscribe links in the footer.

The same private area has a **subscriber view** (who's on the list and what they're interested in, with the ability to add or edit people by hand), a **history** of everything that's gone out, and a **suppressed** list — more on that next.

### Keeping the List Clean

Sending real email means dealing with bounces and spam complaints, or your deliverability quietly rots. My email provider tells The Dispatch about these through a signed webhook: a hard bounce or a complaint automatically removes that address and adds it to a suppression list, so it's never emailed — or accidentally re-added — again. Temporary, soft bounces are left alone.

Every message also carries a proper one-click unsubscribe — the kind Gmail and Apple Mail render as a button — handled by an `/unsubscribe` route that just removes you. No login. The link is the key.

### Managing Your Own Subscription

Every email has a **Manage preferences** link in the footer. It opens a small page — signed with a token unique to your address, so it only ever touches *your* subscription — where you can check or uncheck which things you hear about, or leave entirely. No account, no password, no me in the middle.

---

## How It's Built

**Backend:** Python, using the [Flask](https://flask.palletsprojects.com) framework. Hosted on PythonAnywhere on a separate web app from the Cockpit — different concerns, different deployments. The source is version-controlled (it used to live only on the server).

**Email:** Sent through [Resend](https://resend.com)'s HTTPS API. I moved off Fastmail SMTP in July 2026 — same sending domain, better deliverability, and the webhook that tells me about bounces and complaints. Resend delivers the mail; it never holds my list. Every message is multipart (HTML plus a plain-text alternative), with proper `List-Unsubscribe` and one-click headers and a per-recipient `Message-ID`. The sending domain is verified with DKIM and SPF, and mail comes from my own address.

**Subscriber storage:** Flat JSON files at fixed paths on the server — the subscriber list, a send log, and the suppression list. Each subscriber entry holds an email, the interest segments they're in, and created/updated timestamps. Simple enough to read, edit, or back up by hand.

**Segments:** The whole interest taxonomy lives in one small list in the code. The composer, the counts, and the preferences page all read from it — so adding a new thing to subscribe to is a one-line change, and nothing gets managed by hand.

**Markdown rendering:** The [Python-Markdown](https://python-markdown.github.io) library converts message text to HTML before it goes into the email template. The `extra` and `nl2br` extensions are enabled — tables, fenced code blocks, and single line breaks work as expected.

**Authentication:** Two layers on the send-and-admin interface — HTTP Basic Auth at the route level, plus a second application-level send password before anything goes out. The Resend webhook is verified against a signing secret. The preferences links are HMAC-signed per address, so a link only ever manages the address it was minted for.

**CORS:** The `/subscribe` and `/contact` endpoints include `Access-Control-Allow-Origin` headers locked to `aaronaiken.me`. Requests from any other origin are rejected before they reach the Flask logic.

**Environment variables:** All credentials — the Resend API key, the webhook signing secret, the send passwords, the file paths — are set in the WSGI configuration as environment variables. Nothing sensitive lives in application code.

---

## The Email Template

Outbound emails use a minimal HTML template — Georgia serif, warm off-white background, readable at any size. No tracking pixels. No web fonts loaded from external servers. No open or click tracking of any kind.

Each email includes a plain text alternative for clients that prefer it, and a footer with two per-recipient links: **Manage preferences** and **Unsubscribe**. Both are keyed to your address alone; clicking unsubscribe removes you from the JSON file immediately and returns a plain confirmation page.

---

## The Stack

- **Python** — core language
- **Flask** — web framework
- **Python-Markdown** — Markdown to HTML rendering
- **Resend** — email delivery (HTTPS API), from a verified custom domain
- **PythonAnywhere** — hosting
- **JSON** — subscriber, send-log, and suppression storage

---

## What It Is Not

The Dispatch is not an email marketing platform. It has no open rate tracking, no click analytics, no A/B testing, no drip sequences, no automations. It sends a message to people who asked to hear from me, and that is all.

What it *does* now have — after starting deliberately spartan — is the plumbing that keeps a real list healthy: interest segments so people only get what they asked for, bounce and complaint handling so I don't email dead or annoyed addresses, and a self-service preferences page so you're never stuck writing to me to change your mind. That's about as far as it goes, and about as far as it needs to.

---

*The Dispatch is one part of a broader IndieWeb philosophy on this site — own your content, own your infrastructure, don't outsource the relationship with your readers to a platform. The subscriber list is a text file. The emails come from my domain. A delivery service carries the mail, but the list, the writing, and the relationship stay mine.*
