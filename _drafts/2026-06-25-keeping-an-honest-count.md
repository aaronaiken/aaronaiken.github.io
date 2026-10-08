---
layout: post
title: "Keeping an honest count"
date: 2026-06-25T22:30:00.000000+00:00
categories: [thinking]
author: aaron
description: "A friend's theater camp needed something better than a buggy check-in app. The story of what I built — and the one design decision that quietly carried all of it."
---

A friend runs a Disney-themed musical theater day camp — around a hundred kids, two camp weeks, the whole production. For check-in they'd been using the tool built into their registration platform, and it was a daily headache: buggy, inconsistent from one phone to the next, and apt to fall over right when the wifi dipped — the morning rush, a hundred kids deep. And it stopped at the gate. Once a camper was inside, nobody could say which elective they were actually in.

So we built the replacement, and it's live now, running the camp.

What it does is simple to say: check a kid in at the gate by scanning their badge or searching their name, on any staff phone, several at once. Check them out in the afternoon to an approved pickup. In between, the interns take roll at each elective so that at any moment a director can open one screen and see who's on site, who hasn't arrived, who's left, and who's in which room — and, if a kid isn't where they should be, where they were last seen. The morning reports the director used to assemble by hand became a single click. It reuses the badges the camp already printed, so no kid had to be re-badged.

## The decision the whole thing rests on

If I'm honest, the satisfying part wasn't any one feature — it was a single early decision that made the hard problems quietly disappear instead of having to be fought three separate times.

The source of truth is an append-only log. Every scan, every roll-call tap, every checkout is a permanent record that's never edited. A camper's status isn't a flag you flip and overwrite; it's *derived* by reading back the day's events. That sounds academic until you watch what it buys you. Three staff can scan the same kid at the same instant and nothing breaks — you just get three records, and "checked in" is still "checked in." A phone that loses signal keeps working, stores what happened, and replays it when the bars come back, with no way to double-count. And the question every camp eventually asks — *who did this, and when?* — is already answered, because it's baked into every record.

That's the craft I care about: not cleverness, but choosing the shape that makes the rest of the work fall into place.

## The part nobody shows you

The building was the smooth part. The real world was the friction. The domain's DNS lived somewhere that couldn't create one specific kind of record the email needed — found out the hard way, the night before going live, and worked around with a small second domain. Getting a custom address to serve securely meant coordinating DNS changes with someone across town that I couldn't see. None of it is glamorous, and all of it is the actual job. The code is maybe half the work; the other half is the plumbing between real services owned by real people, and that half is as much a part of the result as anything you can see on screen.

## What it's actually for

The camp is called Mind Steward, and there's a word in there I keep coming back to. A steward keeps faithful track of something that isn't theirs. That's the whole job of this little app — to keep an honest count of someone else's child, from the moment a parent lets go of their hand in the morning to the moment they take it again at pickup. When you put it that way, "check-in app" undersells it.

It's a privilege to be trusted with that, and a good reminder of what the work is really measured by. Not the cleverness of how it's made. Whether, at 2:45 on a Tuesday, a tired staff member can glance at a screen and know — truly know — that every kid is exactly where they're supposed to be.

There's a fuller write-up of the app itself — what it does and how it's put together — over in [the work section]({{ '/work/abacus/' | relative_url }}).

— Aaron
