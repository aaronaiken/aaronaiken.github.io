---
layout: blackbox
title: Blackbox
permalink: /work/blackbox/
page_ident: "WORK · MEETING INTELLIGENCE"
tagline: "Meeting audio → minutes → draft requirements, every line traceable to the recording."
description: "Blackbox turns a recorded stakeholder meeting into structured minutes and draft software requirements — with acceptance criteria that each cite the moment in the audio they came from. A drafting assistant with citations, not an automation."
author: aaron
published: true
---

*Blackbox turns a recorded meeting into structured minutes and — for any change that was actually discussed — a draft requirement with acceptance criteria, every line traceable to a timestamp in the recording. I built it for the way a lot of teams actually work: the requirement starts life in a call, and someone has to turn it into a tracked work item afterward.*

It runs where the recording lives; nothing is filed anywhere automatically. The output is a clipboard block a reviewer reads before it becomes a work item.

---

## The Problem

A lot of requirements start life in a meeting — a call where a change gets talked through, half-decided, and left with loose ends. Turning that into a clean work item afterward is slow, and doing it from memory loses the details that matter.

The obvious fix — "feed the transcript to an LLM and ask for requirements" — has a trap in it. **Ask a model for acceptance criteria and it will produce acceptance criteria, whether or not the meeting supplied them.** A confident, well-formatted, *invented* requirement is worse than no tool at all, because it reads like work product. That failure mode is the whole design problem.

## The Principle

Blackbox is a **drafting assistant with citations, not an automation.** Two rules fall out of that:

- **Every acceptance criterion carries the timestamp span it came from.** If the model can't point to where in the recording a behavior was stated, it isn't allowed to write the criterion.
- **Ambiguity is surfaced, not smoothed.** Anything the meeting left open goes into an *unresolved questions* block instead of getting filled with a plausible guess. Fewer, better-supported items beat comprehensive coverage.

Nothing runs through the model until the speakers have real names, and nothing is trusted without review.

## What I Built

![The Review screen — drafted requirements on the left, the transcript and audio on the right. Click a citation and it seeks the audio and highlights the passage.](/assets/img/blackbox/review.png)
*The Review screen. Each criterion cites an audio span; clicking it seeks the player and lights the transcript. Unresolved questions get their own block — they're the point, not a footnote.*

A single pipeline, each stage honest about where it is:

- **Ingest & transcribe.** Chunked browser upload for large recordings, `ffmpeg` to strip and downmix the audio, and **ElevenLabs Scribe** for a diarized, word-timestamped transcript. The raw transcript is the source of truth every citation resolves against.
- **Name the speakers.** A hard gate: the user maps each detected voice to a real name (with playable sample clips), and a per-meeting-title roster pre-fills the guesses next time. "speaker_2 will own the migration" is not a usable action item.
- **Two passes, on purpose.** Minutes want compression; requirements want precision — so they're separate calls with separate prompts. Pass A writes the minutes; Pass B extracts draft requirements as As-Is / To-Be with Given/When/Then acceptance criteria, each cited, and every unsettled thing pushed to unresolved questions.
- **Review, don't file.** A split pane — items on the left, transcript and audio on the right — where clicking any citation scrubs the recording to that moment. Every item copies out as a work-item-shaped block for review before it goes anywhere.

Three refinements came out of real, messy meetings:

- **Scope.** Real meetings are cross-team — two groups each with a change to make. You only want the work item for *your* system, so you tell it which systems you own. Another team's prerequisite becomes a cited **dependency** on your item, never its own work item.
- **Supplements.** The email or spec PDF that carries the real detail can be attached and fed to the passes as *cited evidence* — a criterion can cite `doc:email-1` alongside the audio. More evidence, still no invention; a supplement that contradicts the meeting becomes an open question.
- **Refine in place.** When evidence arrives after the fact, adding it *updates* the existing requirements — resolving an open question into a cited criterion — rather than regenerating them from scratch.

## Under the Hood

- **Traceability as a data model.** Each criterion's `source` is a tagged reference — an audio span *or* a document locator — so a requirement can be backed by the recording and by an attached PDF in the same list, and the UI seeks the right thing for each.
- **Validation on receipt.** Pass B is re-checked before it's shown: malformed JSON, a citation outside the recording, or a criterion with no source triggers one repair round; a second failure flags the whole item as unverified rather than quietly trusting it.
- **Multimodal without a new stack.** Images and PDFs ride into the passes as native content blocks, so a screenshot or a spec doc is read directly — no separate OCR pipeline.
- **A UI with a point of view.** It reads as an instrument, not a chat window — cold cyan traces on graph-ruled graphite, one loud colour reserved for the gaps the meeting left open. Confidence is a quiet three-cell meter, so "low" is legible without being an alarm.

![The inbox — one row per recording, each honest about exactly where it is in the pipeline.](/assets/img/blackbox/inbox.png)
*The inbox. Passive states show a real number ("22:10 of 45:40"); the naming gate is the one row that asks something of you, and it's the one that looks it.*

## Stack

<ul class="bx-stack">
  <li>Python + Flask</li>
  <li>SQLite</li>
  <li>ffmpeg / ffprobe</li>
  <li>ElevenLabs Scribe</li>
  <li>Claude (Anthropic)</li>
  <li>Vanilla JS + CodeMirror-free, zero build</li>
  <li>Runs local</li>
</ul>

It runs wherever the meeting audio lives — a laptop or a locked-down box — because processing recordings shouldn't mean shipping them off to a service. Honest limits are the feature: it drafts less than a naïve tool would, and everything it drafts can be read straight against the tape.

{% include work_interest.html %}
