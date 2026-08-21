---
layout: page
title: Shift
permalink: /tools/shift/
page_ident: "WORKSHOP · TOOLS & EXPERIMENTS"
author: aaron
description: A sit/stand posture app for iPhone, Watch, and Mac — where a tap never counts as completion. A Tidy app.
---

**Sit/stand, done honestly.** Shift is a posture-cadence app for iPhone, Apple Watch,
and Mac — currently in private testing.

Every sit/stand reminder app fails the same way: it fires a timer, you dismiss it,
dismissal becomes reflex, and the app dies in three weeks. Shift has one rule that
everything else follows from:

> **Dismissal is never completion.** A prompt resolves only when a sensor confirms your
> posture actually changed — or when you explicitly declare a skip, which gets logged as
> a skip.

There's a second, quieter idea: **standing too long is a failure state too.** Prolonged
static standing is the classic risk factor for varicose veins, so the unit of success
isn't standing minutes — it's *transitions*. A ninety-minute standing block shows up in
the same warning color as a ninety-minute sitting one, and Shift will nudge you back
*down* out of a too-long stand.

### How it works

- **Watch (ideal).** Wrist haptics you can't ignore, and the sensors that verify you
  actually stood — no button required. It's the strongest surface, and it matters most
  if your work machine isn't a Mac.
- **iPhone (solid backup).** The required device: history, trends, and honest insights —
  including the longest-static-block chart that treats sitting and standing alike.
- **Mac (optional).** Ambient state in the menu bar, and a last-resort screen dim that
  behaves like a firm colleague, never a punishment. Your keyboard always still works.

### The shape of it

$20, once, all three platforms — no subscription, ever. Everything stays on your device
or in your own iCloud. No analytics, no accounts, no leaderboards.

### Get notified

It's in private testing now. Leave your email and I'll let you know when it's ready —
and whether you'd like to help test it on your own wrist first.

<form id="shift-notify" style="display:flex;gap:.5rem;flex-wrap:wrap;max-width:30rem;margin:1.25rem 0;">
  <input type="email" name="email" required autocomplete="email" placeholder="you@example.com"
    style="flex:1;min-width:15rem;padding:.65rem .85rem;border:1px solid #d8d2c4;border-radius:.6rem;font-size:1rem;">
  <button type="submit"
    style="padding:.65rem 1.2rem;border:0;border-radius:.6rem;background:#3f9a6e;color:#fff;font-weight:600;font-size:1rem;cursor:pointer;">
    Notify me
  </button>
</form>
<p id="shift-notify-done" style="display:none;color:#3f9a6e;font-weight:600;margin:1.25rem 0;">✓ You're on the list — I'll be in touch.</p>

<script>
(function(){
  var f = document.getElementById('shift-notify');
  if(!f) return;
  f.addEventListener('submit', function(e){
    e.preventDefault();
    var email = (f.email.value || '').trim();
    if(!email) return;
    var done = function(){ f.style.display='none'; document.getElementById('shift-notify-done').style.display='block'; };
    fetch('https://email.aaronaiken.me/subscribe', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({email: email, app: 'shift'})
    }).then(done).catch(done);
  });
})();
</script>

*A Tidy app.*
