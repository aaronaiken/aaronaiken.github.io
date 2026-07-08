---
layout: tidyaway
title: Tidy Away
permalink: /tools/tidy-away/
page_ident: "TIDY · MAC UTILITIES"
author: aaron
hero_status: "In Testing · v0.1"
description: A menu-bar auto-reply for iMessage that leaves every message unread. Replies to people you know, never groups, never reads a word you wrote. macOS, direct download.
---

*Last updated: 2026-07-07*

Tidy Away is a menu-bar utility for busy seasons. Flip it on and it quietly auto-replies to incoming iMessages from people in your Contacts with a short "here's when I'll get back to you" note — then leaves the message **unread**, so it's still sitting in your triage pile when you surface. It never replies in group threads, never double-texts the same person, and never touches your read/unread state itself.

It's the fourth app in the [Tidy family](/tidyapps/) — small, single-job Mac utilities. macOS only, direct download, currently in testing on my own machine.

---

## Why It Exists

There's a specific kind of stress in going heads-down while your phone keeps lighting up. You're not ignoring people — you just can't answer right now — but silence reads as ignoring, and every unanswered text is a small open loop nagging at the back of your mind.

An out-of-office reply solves this for email. Nothing solves it for iMessage. The Driving Focus has an auto-reply, but it's all-or-nothing, it's tied to driving, and it marks things handled. What I wanted was quieter and more honest: reply once to the people I know so they're not left hanging, but keep every message unread, so when I come up for air the pile is still there and nothing has been silently swept away.

That's the whole idea. It buys the sender a little patience without pretending, to me, that the conversation is closed.

---

## How It Works

While Away is on, Tidy Away watches your Messages database for new arrivals. Each new message runs through a rule stack, and only earns an auto-reply if **all** of these hold:

- It's **inbound** — not something you sent.
- It's a **1:1 conversation**, not a group thread.
- It's a **real message** — not a tapback, reaction, or edit.
- It's from **someone in your Contacts** — strangers and spam numbers get nothing.
- You **haven't already handled that person** this session — one note each, and the instant *you* reply in a thread yourself, the robot goes quiet there for good.

Then there are the people and senders you'd never want an auto-reply to reach, and Tidy Away filters them out three ways — none of which read a word of your messages:

- **An exclusion list.** Name the people the robot should never text — your spouse, your kids — and they're skipped. Stored as pointers to Contacts entries, so the list itself holds no phone numbers.
- **Automated senders.** Appointment confirmations, verification codes, and marketing blasts almost always come from shortcodes, business sender IDs, or toll-free numbers. Tidy Away spots those by the *shape* of the sender alone and skips them — even when they're saved in your Contacts.
- **Business contacts.** The salon or clinic you've saved as a company (rather than a person) gets skipped too, which catches the ones that text from a normal local number.

When it does reply, it sends the note directly to that person without ever opening or focusing the conversation — which is what keeps the message unread. That last part is the whole trick.

---

## Modes

"Away" isn't one thing. Heads-down-at-my-desk and off-the-grid-for-the-evening are opposite states, and they deserve opposite notes — one says "I'll surface soon," the other says "I'm not at a keyboard." So Tidy Away has **modes**.

A mode is a named bundle: a message, an optional Focus, and an optional auto-off time. It ships with **Work**, **Personal**, and **Vacation**, and you can add your own. When you turn Away on, you pick the mode right from the menu — one click sets the right tone, flips the right Focus, and schedules the right off-time all at once. You can switch modes mid-session too; the new note takes effect on the next reply.

There's also an optional setting — off by default — to **pick the mode by the clock**: your work mode during work hours on weekdays, your off-hours mode evenings and weekends. Turn it on and Away just does the right thing without you thinking about it; leave it off and you stay in full control.

---

## Privacy

This is the part that matters most, so I'll be precise about it: **Tidy Away never reads your conversations.** It learns only *that* a message arrived and who it's from — the bare minimum to decide whether to send a note. It never decodes message text, never stores it, and never sends anything anywhere. Everything stays on your Mac.

That isn't a promise layered on top of the code; it's how the code is built. The query that watches for messages pulls a row identifier and the sender's handle, and nothing else. There is no code path that reads what anyone said, because there's no reason for one to exist.

The optional diagnostics log — the thing you'd send me if something misbehaved — is scrubbed at the source: first names only, phone numbers masked to their last four digits, and no message contents of any kind.

---

## Focus

Optionally, turning Away on can drop your Mac into a Focus mode — Work, Do Not Disturb, whatever you use — and turn it back off when Away ends. macOS gives apps no direct way to set Focus, so this runs through a Shortcut you choose (one with a "Set Focus" action); Tidy Away just runs it at the right moment and restores the default afterward.

---

## The Honest Limits

- **Your Mac has to be awake and powered on.** Tidy Away holds a power assertion so the machine keeps watching, but a lid shut in a bag sends nothing. This is a tool for busy-season-at-my-desk, not away-from-machine coverage — that would be a relay running on a Mac somewhere, which is a different project.
- **iMessage only, for now.** SMS (green bubbles) needs Text Message Forwarding from your iPhone and is deferred to a later version.
- **It's not on the Mac App Store, and it can't be.** Reading the Messages database requires Full Disk Access, which the App Store's sandbox forbids. So Tidy Away is signed, notarized, and handed out directly — the one app in the Tidy family that lives outside the Store.

---

## How It's Built

**App:** Swift 6 with strict concurrency, AppKit for the menu-bar item, SwiftUI for the settings and onboarding surfaces. A hand-rolled `@main`, no scenes, no third-party dependencies. Project generated from a `project.yml` via XcodeGen.

**Watching for messages:** A read-only SQLite connection to the Messages database, polled every few seconds and tracking the highest message identifier it's seen so each poll only scans what's new. It opens read-only, never writes, never checkpoints, never opens a conversation.

**Sending:** An Apple Event to Messages, in-process, targeting the recipient without focusing a window — the no-focus path that preserves unread state.

**Contacts:** The Contacts framework, indexed once per session into memory so a sender resolves to "someone I know" without a lookup per message.

**Staying awake:** An IOKit power assertion held for the length of the session.

Three one-time permissions, walked through on first run: Full Disk Access (to see that messages arrive), Contacts (to know who's who), and Automation (to send through Messages).

---

## The Stack

- **Swift 6** — strict concurrency throughout
- **AppKit** — `NSStatusItem` menu-bar app, `LSUIElement`
- **SwiftUI** — settings + onboarding
- **SQLite** — read-only access to the Messages database
- **Apple Events** — sending via Messages, no window focus
- **Contacts (`CNContactStore`)** — sender resolution + business detection
- **Shortcuts** — optional Focus integration
- **IOKit** — keep-awake power assertion
- **XcodeGen** — project generation, zero third-party dependencies
- **Developer ID + notarization** — direct distribution

---

## What It Is Not

- Not a reader of your messages. It knows a text arrived; it never knows what it said.
- Not a group-chat auto-responder. Group threads are left entirely alone, by design.
- Not always-on coverage. It works while your Mac is awake, and it says so plainly.
- Not a Mac App Store app. Full Disk Access and the sandbox can't coexist.
- Not possible on iOS. There's no way for an app to read incoming messages or auto-send there — the whole mechanism is macOS-only.
- Not a double-texter. One note per person per session, and it defers to you the moment you step in.

The point is a smaller open loop, not a closed one. Everything stays unread because you're still the one who answers.
