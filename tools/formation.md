---
layout: page
title: Formation
permalink: /tools/formation/
page_ident: "WORKSHOP · TOOLS & EXPERIMENTS"
author: aaron
---

*Last updated: 2026-08-19*

Formation is a homemade video-meeting tool that lives inside [the Cockpit](/tools/cockpit/). I got tired of sending people to install-this, sign-up-for-that meeting apps for a five-minute call, so I built the smallest thing that works: you make a room, share a link, and whoever clicks it is in — camera and mic, right in the browser, nothing to download. This page is the technical manual.

None of it is a product. It's a private utility I use to run real meetings; the guest room is the only public surface, and only to people I hand a link.

## The idea

A meeting should be a link, not an onboarding funnel. Formation is built around that:

- **No accounts, no installs.** Guests open a URL, type a name, and join. The host is just me, authenticated into the Cockpit.
- **Peer-to-peer media.** Video and audio go directly between browsers over WebRTC. My server never sees the stream — it only passes the connection handshakes back and forth.
- **Everything ephemeral.** Rooms, participants, and signaling live in a tiny throwaway database that tidies itself after 48 hours. Recordings and notes are yours to keep; nothing is retained server-side.

## The flight theme

The whole thing wears an air-traffic-control skin, because a meeting tool is a little control tower. Rooms are **departures**. Joining is **boarding**. The shared notes are the **logbook**. The end screen is the **debrief**. The mark is a drawn tower.

## What's in a meeting

- **Departures board** — my private lobby: name a meeting, pick a time, get a shareable link that works now and at meeting time both.
- **The stage** — a control rail down the left (mic, camera, screen share, background blur, invite, notes, record, leave) and the video grid filling the rest. When someone shares their screen it fills the stage and the cameras reflow into a strip.
- **The logbook** — shared meeting notes. Anyone jots a note, hits enter, and it lands in one running log stamped with their name and the time. Everyone in the room sees it build. At the end you can copy it, download it as Markdown, email it to yourself, or — my favorite — save it straight into my [48pages](https://48pages.app) notebook.
- **Recording** — the host can record the call. It's composited and captured entirely in the browser and saved to my own computer; nothing is uploaded. A pulsing indicator shows everyone when it's rolling.
- **The debrief** — when the meeting ends, everyone gets the logbook to take with them, and guests get a quiet pointer back to [the Workbench](/tools/).

## How it holds together

- **WebRTC mesh** for media — good for the small calls I actually have. Each browser sends its video to the others directly; as a room grows, each stream quietly scales itself down so a laptop uplink can keep up.
- **Flask as a signaling relay** — since the Cockpit's host has no WebSockets, the connection handshakes are passed over plain short-interval HTTP polling. It's not fancy; it's reliable.
- **TURN when the network is hostile** — locked-down corporate networks get a relay server so the call still connects.
- **Camera/mic permission handled gracefully** — a pre-join camera check, and if a browser blocks the camera you can still join audio-only; the others just see your callsign.

Formation is one of several things the Cockpit has grown into — a comms room next to the publishing bridge, the task kneeboard, and the chart room. It's small on purpose, and it does the one job I needed it to.
