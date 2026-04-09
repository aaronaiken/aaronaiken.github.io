---
layout: page
title: The Dispatch
permalink: /tools/dispatch/
page_ident: "WORKSHOP · TOOLS & EXPERIMENTS"
author: aaron
---

The Dispatch is a private Flask web application I built to handle all outbound and inbound communication for this site — without exposing my email address publicly, without a third-party newsletter service, and without any tracking whatsoever.

It lives on [PythonAnywhere](https://pythonanywhere.com), separate from the Cockpit. It is not publicly accessible. This page is the technical manual.

---

## Why It Exists

Three things prompted it.

First, I didn't want my email address on the open web. A contact form is the obvious solution, but most contact form services are either overkill, require accounts, or route your mail through their infrastructure. I wanted something mine.

Second, I wanted to let people sign up for updates when I ship something new in the tools workshop — without Mailchimp, without Substack, without handing anyone's email address to a platform I don't control.

Third, once you have a subscriber list, you need a way to actually send to it. So I built that too.

The result is one Flask app, three jobs.

---

## What It Does

### Contact Form

The [contact page](/contact/) on this site submits to a `/contact` endpoint on The Dispatch. The app validates the fields, composes an email with a `Reply-To` header set to the sender's address, and forwards it to my inbox. No data is stored. No copy is kept. It arrives like a normal email and I reply like a normal person.

### Tools Signup

The [Signal List](/tools/updates/) page lets visitors subscribe to tool update notifications. They enter an email address and select which tools they want to hear about — Audio Lab, Brew Lab, the Cockpit, or general updates across the workshop.

Submissions hit a `/subscribe` endpoint. The app validates the email, checks the selected channels against an allowed list, and writes the entry to a flat JSON file on the server. If an email re-subscribes, their channel list is merged rather than duplicated. No database. No third party. Just a JSON file I own.

### Newsletter Sender

A private, double-locked `/send` route serves a Markdown composer interface. HTTP Basic Auth is the first lock — the browser prompts for credentials before the page loads. A second send password is required inside the composer before anything goes out.

The composer accepts a subject, a Markdown body, and a channel target — all subscribers, or just the subset subscribed to a specific tool. Hitting Preview renders the Markdown to HTML, wraps it in the email template, and loads it in an iframe showing exactly what recipients will see, along with a recipient count. Hitting Confirm loops through the matching subscribers and sends each one a personalized email with their own unsubscribe link baked into the footer.

---

## How It's Built

**Backend:** Python, using the [Flask](https://flask.palletsprojects.com) framework. Hosted on PythonAnywhere on a separate web app from the Cockpit — different concerns, different deployments.

**Email:** Sent via SMTP through Fastmail, using a custom domain address. Standard STARTTLS on port 587. The `smtplib` module from the Python standard library handles everything — no external mail SDK.

**Subscriber storage:** A single JSON file at a fixed path on the server. Each entry contains the subscriber's email address, their selected channels, and created/updated timestamps. Simple enough to read, edit, or back up by hand.

**Markdown rendering:** The [Python-Markdown](https://python-markdown.github.io) library converts message body text to HTML before it goes into the email template. The `extra` and `nl2br` extensions are enabled — tables, fenced code blocks, and single line breaks work as expected.

**Authentication:** Two layers on the send interface. HTTP Basic Auth at the route level — handled by a custom decorator that checks an `Authorization` header against credentials stored in environment variables. A second application-level password is required in the composer form itself before preview or send will execute.

**CORS:** The `/subscribe` and `/contact` endpoints include `Access-Control-Allow-Origin` headers locked to `aaronaiken.me`. The browser enforces this — requests from any other origin are rejected before they reach the Flask logic.

**Environment variables:** All credentials — SMTP host, port, username, password, send passwords, subscriber file path — are set in the WSGI configuration file as environment variables. Nothing sensitive lives in application code.

---

## The Email Template

Outbound emails use a minimal HTML template — Georgia serif, warm off-white background, readable at any size. No tracking pixels. No web fonts loaded from external servers. No open or click tracking of any kind.

Each email includes a plain text alternative for clients that prefer it. The unsubscribe link in the footer is generated per-recipient, encoding their email address as a query parameter on a `/unsubscribe` route. Clicking it removes them from the JSON file immediately and returns a plain confirmation page.

---

## The Stack

- **Python** — core language
- **Flask** — web framework
- **Python-Markdown** — Markdown to HTML rendering
- **smtplib** — email sending, standard library
- **Fastmail** — SMTP provider, custom domain
- **PythonAnywhere** — hosting
- **JSON** — subscriber storage

---

## What It Is Not

The Dispatch is not an email marketing platform. It has no open rate tracking, no click analytics, no A/B testing, no drip sequences, no automations. It sends a message to people who asked to hear from me, and that is all.

It also has no unsubscribe management UI, no bounce handling, and no list hygiene tooling. At the scale of a personal site's tools workshop, none of that is necessary. If it ever becomes necessary, something has gone sideways.

---

*The Dispatch is one part of a broader IndieWeb philosophy on this site — own your content, own your infrastructure, don't outsource the relationship with your readers to a platform. The subscriber list is a text file. The emails come from my domain. The whole thing fits in a single Python file.*