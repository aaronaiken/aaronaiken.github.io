---
layout: tidy-bar
title: Tidy Bar
permalink: /tools/tidy-bar/
page_ident: "TIDY · MAC UTILITIES"
author: aaron
hero_status: "App Store · Soon"
breadcrumb:
  - { label: Tools, url: /tools/ }
  - { label: Tidy, url: /tidyapps/ }
  - { label: Tidy Bar }
description: A cleaner Mac menu bar. Hide the icons you don't need behind a movable separator, reveal them on click. Native AppKit, free, no telemetry.
---

*Last updated: 2026-07-07*

Tidy Bar cleans up your Mac's menu bar. The icons you don't need all the time get tucked away behind a movable separator; click it and they slide back into view. It's the Hidden Bar idea, rebuilt native and careful, and it's the first app in the [Tidy family](/tidyapps/).

Free, native, sandboxed, no telemetry. Coming to the Mac App Store.

---

## Why It Exists

The menu bar fills up. Every app wants a spot, and half of them you only glance at once a day — but they sit there the rest of the time, crowding the icons you actually use, and on a notched laptop they can vanish under the camera housing entirely.

Tidy Bar gives you a line in the sand. Everything to one side stays visible; everything to the other side hides until you want it. Your menu bar goes back to showing what matters, and the rest is one click away.

---

## How It Works

There are two menu-bar items: a **separator** and a **toggle**. Drag the separator to set the line — icons left of it stay, icons right of it hide. Click the toggle (or the separator) to reveal the hidden set, click again to tuck it back. That's the whole interaction.

Under the hood this is the app's defining decision: a **two-item architecture**. Rather than fake a hide with fragile tricks, Tidy Bar owns two real status items and moves the boundary between them, which is what makes the collapse stable across displays, notches, and macOS updates. It's screen-aware — it knows how much room the current display actually has — so it hides the right things when space runs out.

---

## How It's Built

**App:** Swift and AppKit, a pure menu-bar agent (`LSUIElement`) with no dock icon and no main window. No third-party dependencies — a hard rule for the whole family. The project is generated from a `project.yml` via XcodeGen.

**State:** Your separator position and collapsed/expanded state persist across launches in standard preferences. Nothing else is stored, because nothing else needs to be.

**Distribution:** Sandboxed for the Mac App Store — Tidy Bar draws a tidier menu bar and asks for no special access to do it.

---

## The Stack

- **Swift** — core language
- **AppKit** — two `NSStatusItem`s, the movable separator
- **SwiftUI** — settings + onboarding surfaces
- **LSUIElement** — menu-bar agent, no dock presence
- **XcodeGen** — project generation, zero third-party dependencies
- **App Sandbox** — Mac App Store distribution

---

## What It Is Not

- Not a menu-bar *replacement*. It hides and reveals your existing icons; it doesn't redraw the bar.
- Not a customization suite. One job — declutter — done well, not fifty settings.
- Not a resource hog. A menu-bar agent that mostly sits still and waits for a click.
- Not tracking anything. No analytics, no telemetry, no network calls.

The menu bar should show what you're using and hide what you're not. Tidy Bar draws that line and lets you move it.
