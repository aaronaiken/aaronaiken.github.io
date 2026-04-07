---
layout: colophon
title: Colophon
author: aaron
permalink: /colophon/
page_ident: "COLOPHON · HOW THIS SHIP IS BUILT"
---

This site is a hand-built personal playground. It exists because I believe in owning your own corner of the internet — no algorithm, no engagement metrics, no ads, no platform that can disappear and take your writing with it.

Here is how it is made.

---

## The Engine

Built with [Jekyll](https://jekyllrb.com), a static site generator. No database, no server-side rendering, no CMS. Every page on this site is a flat HTML file generated from Markdown and Liquid templates. It is fast, simple, and entirely mine.

Hosted on [GitHub Pages](https://pages.github.com). The repository is public. Source code is available for anyone curious enough to look.

---

## The Words

Blog posts are written in Markdown, committed to the repository, and published via git push. No dashboard, no editor toolbar, no autosave spinner. Just a text file and a terminal.

Status updates are a different story — a publishing pipeline I built myself across three layers: a custom web app for on-the-go posting, a bash script for when I'm at the command line, and a Jekyll collection that renders everything into a page styled like an early 2007 Twitter profile, because I thought that would be fun and it was.

Each status update is its own Markdown file in `_status_updates/`. Jekyll reads the collection, sorts by date, and renders the feed. A small JavaScript lazy-loader handles the scroll. Dynamic timestamps turn UTC into "2 hours ago." The whole thing also mirrors to [omg.lol](https://omg.lol) via their API.

The publishing tool lives on [PythonAnywhere](https://pythonanywhere.com) — a private, password-protected Flask app I built called the Cockpit. It handles image uploads, resizes them for the web, writes the Markdown front matter, and handles the git operations automatically. It also surfaces context-aware messages to me from a local text file, a small easter egg I built for myself that I enjoy probably more than I should.

---

## The Look

The visual identity of this site is personal, not decorative. The amber and green CRT palette, the VHS-era photo filters, the terminal aesthetic on the status page — these are a reference to watching the original Star Wars trilogy on worn VHS tapes as a kid. Han Solo is my guy. The Millennium Falcon is the greatest ship ever put to film. This is non-negotiable.

Typography is set in [Fraunces](https://fonts.google.com/specimen/Fraunces) for display headings, [Lora](https://fonts.google.com/specimen/Lora) for body text, [VT323](https://fonts.google.com/specimen/VT323) for the terminal aesthetic, and [Share Tech Mono](https://fonts.google.com/specimen/Share+Tech+Mono) for labels and metadata.

Dark mode is the primary experience. Light mode is a respectful accommodation. The site reads your system preference and adjusts accordingly — no toggle required.

---

## The Tools

- **Editor:** [Nova](https://nova.app) by Panic, on a MacBook Air M2
- **Version control:** Git, via terminal and GitHub
- **Local preview:** `bundle exec jekyll serve`
- **Hosting:** GitHub Pages + PythonAnywhere
- **Domain:** registered and managed independently
- **Fonts:** Google Fonts, served via Bunny Fonts where privacy matters
- **Tracking:** None. Zero. [Verified independently](https://themarkup.org/blacklight?url=aaronaiken.me).

---

## The Philosophy

IndieWeb. Own your content. Publish on your own domain. Syndicate elsewhere if you want, but the canonical home is here.

This site is not optimized for growth, engagement, or discoverability. It is optimized for me — for writing when I want to write, tinkering when I want to tinker, and sharing what I want to share without asking anyone's permission.

It is also a record. Of where I have been, what I have thought, what I have built, and who I am becoming. That matters more to me than any metric.

---

## The Credit

Website made by hand in Harrisburg, Pennsylvania by Aaron Aiken.

Git commit messages are written in the voice of Han Solo. This is a hill I will die on.

*Last updated: {{ site.time | date: "%B %Y" }}*