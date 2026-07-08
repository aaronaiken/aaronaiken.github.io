---
layout: tidy-stage
title: Tidy Stage
permalink: /tools/tidy-stage/
page_ident: "TIDY · MAC UTILITIES"
author: aaron
hero_status: "Coming Soon"
breadcrumb:
  - { label: Tools, url: /tools/ }
  - { label: Tidy, url: /tidyapps/ }
  - { label: Tidy Stage }
description: One toggle covers your cluttered desktop with a clean background for screen recording and sharing, then restores everything when you're done. Native macOS.
---

*Last updated: 2026-07-07*

Tidy Stage makes your Mac presentable in one click. Flip it on and every desktop is covered with a clean, neutral background — no icons, no clutter, no half-open windows peeking from behind — ready for a screen recording or a share. Flip it off and everything comes back exactly as it was.

It's the second app in the [Tidy family](/tidyapps/) — native, sandboxed, no telemetry.

---

## Why It Exists

The moment before you hit record is always the same little scramble: drag the messy files off the desktop, close the personal tabs, hope nothing embarrassing is sitting in the corner. Then you record, and afterward you drag it all back. Every single time.

Tidy Stage collapses that into a toggle. Your desktop becomes a calm, neutral stage the instant you need it, and your actual working setup is untouched underneath — waiting for you to turn the stage back off.

---

## How It Works

Activating Tidy Stage covers each of your displays with a clean background image, hiding the desktop icons and everything sitting on them. It's a cover, not a cleanup: nothing is moved, deleted, or rearranged. When you deactivate, the covers come off and your desktop is exactly where you left it.

It's a menu-bar toggle with a **global hotkey**, so you can go presenter-ready without even reaching for the mouse — hit the shortcut right before you start recording. You pick the background; it handles every screen at once, including external displays.

---

## How It's Built

**App:** Swift and AppKit, a menu-bar agent (`LSUIElement`) with no dock icon. Zero third-party dependencies, the family rule. Generated from a `project.yml` via XcodeGen.

**The cover:** A borderless window per display, sized to the screen and layered above the desktop, showing your chosen background. Desktop icons are hidden while the stage is up and revealed again when it comes down.

**Distribution:** Sandboxed for the Mac App Store, using only the access it needs to place its covers and remember your preferences.

---

## The Stack

- **Swift** — core language
- **AppKit** — per-display cover windows, menu-bar item
- **SwiftUI** — settings + onboarding
- **Global hotkey** — presenter-ready without the mouse
- **LSUIElement** — menu-bar agent, no dock presence
- **XcodeGen** — project generation, zero third-party dependencies
- **App Sandbox** — Mac App Store distribution

---

## What It Is Not

- Not a cleanup tool. It covers your desktop; it never moves or deletes a thing.
- Not a recorder. Bring your own screen-recording app — Tidy Stage just makes the frame clean.
- Not a wallpaper manager. The background is a temporary stage, not a new desktop.
- Not tracking anything. No analytics, no telemetry, no network calls.

The scramble before you record should be one keystroke. Tidy Stage makes it one.
