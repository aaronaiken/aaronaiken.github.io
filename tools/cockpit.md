---
layout: page
title: The Cockpit
permalink: /tools/cockpit/
page_ident: "WORKSHOP · TOOLS & EXPERIMENTS"
author: aaron
---

The Cockpit is a private, password-protected web application I built to publish status updates to this site from anywhere — a phone, a tablet, a borrowed computer. It lives on [PythonAnywhere](https://pythonanywhere.com) and handles everything from writing the update to pushing it live.

It is not publicly accessible. This page is just the technical manual.

---

## Why It Exists

Status updates on this site are Markdown files. Each one lives in a `_status_updates/` collection in the Jekyll repository. To publish one, you need to create a file with the right front matter, commit it, and push it to GitHub — at which point GitHub Pages rebuilds the site and the update goes live.

That's a fine workflow at a desk. It is not a fine workflow on a phone.

The Cockpit solves that. It is a form on the web that does all of the above automatically. Type a status, optionally attach a photo, hit transmit. Done.

---

## How It's Built

**Backend:** Python, using the [Flask](https://flask.palletsprojects.com) framework. Hosted on PythonAnywhere, which provides a persistent environment where the Jekyll repository lives as a local clone.

**Authentication:** Cookie-based. A password form sets an `auth_token` cookie on success. Every route checks for it. Simple and sufficient for a personal tool.

**The publishing flow:**

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

## The Stack

- **Python** — core language
- **Flask** — web framework
- **Pillow** — image processing
- **GitPython / subprocess** — git operations
- **PythonAnywhere** — hosting
- **omg.lol API** — status mirroring
- **Jekyll** — the site that receives the published files

---

## What It Is Not

The Cockpit is not a CMS. It does not have a dashboard, an edit history, a delete function, or a draft mode. It publishes and that is all. Every update is permanent and public the moment it is transmitted.

That is a feature, not a limitation. It encourages writing things worth saying.

---

*The Cockpit is one part of a three-way publishing pipeline. Status updates can also be posted via a bash script run locally from the command line. Both methods end up in the same place: a Markdown file in the Jekyll collection, committed and pushed, live on the site.*
