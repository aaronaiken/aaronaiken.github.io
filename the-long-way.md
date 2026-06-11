---
layout: long-way
title: The Long Way
permalink: /the-long-way
page_ident: "LETTERS · THE LONG WAY"
subtitle: Debt. Marriage. Faith. Fatherhood. Reconciliation. A letter from Aaron about the harder, slower, more honest path.
description: The Long Way — a personal newsletter from Aaron about taking the harder path through debt, marriage, faith, fatherhood, and the daily work of not taking shortcuts. Roughly every two weeks.
---

Five years ago my world crumbled.

By the end of 2024 I had piled up $110,000 in mostly consumer debt and a marriage that had come apart. In November of that year, I started walking back. On December 23, 2025, my wife and I remarried.

I'm still walking.

This is the correspondence.

---

The Long Way arrives roughly every two weeks. It is not optimization. It is not tips. It is not a five-step framework for anything.

It is one person mid-story, writing it down honestly enough that someone else might recognize their own.

Some weeks the letter is about a number — the exact dollar amount, the months until debt-free, the days since the worst day. Some weeks it is about a kitchen, a parsonage, a house we used to live in. Some weeks it is about Mozzie. Some weeks it is about God, though I won't preach to you. Some weeks it is about a tool I built when the off-the-shelf thing wouldn't do.

All of them are about the same thing: the harder path. I didn't choose it — it's been my default setting up to here. I've stayed on it on purpose, forging my own way through. At forty, I'm ready to get off the highway and onto a slower local road.

---

The Long Way is being written. The first letter goes out when it's ready — and not before. If you'd like a heads-up when it lands, drop your email here. It joins my general updates list — rarely used, only when I really have something to say.

<!-- ============================================================
     SIGNUP FORM — POSTs to Dispatch's generic signal endpoint
     (same shape as /tools/updates/). Subscribers get the
     heads-up when The Long Way's first letter goes out, along
     with anything else worth saying.
     ============================================================ -->
<form class="lw__form" id="lw-form" onsubmit="handleLongWaySubscribe(event)" novalidate>
  <p class="lw__form-label">// SIGN UP</p>
  <div class="lw__form-row">
    <input type="email" id="lw-email" required class="lw__form-input" placeholder="your.email@somewhere.com">
    <button type="submit" id="lw-btn" class="lw__form-button">Send it →</button>
  </div>
  <p class="lw__form-note" id="lw-status">No tracking. Rarely sent. Unsubscribe by reply.</p>
</form>

<script>
async function handleLongWaySubscribe(event) {
  event.preventDefault();
  const btn = document.getElementById('lw-btn');
  const status = document.getElementById('lw-status');
  const email = document.getElementById('lw-email').value.trim();

  if (!email || !email.includes('@')) {
    status.textContent = '⚠ please enter a valid email address';
    return;
  }

  btn.disabled = true;
  btn.textContent = 'Sending…';

  try {
    const resp = await fetch('https://email.aaronaiken.me/subscribe', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, tools: ['signal'] })
    });

    if (resp.ok) {
      btn.textContent = 'Sent ✓';
      status.textContent = 'Thank you. I\'ll let you know when the first letter goes out.';
      document.getElementById('lw-email').value = '';
    } else {
      throw new Error('server error');
    }
  } catch (e) {
    status.textContent = '⚠ something didn\'t go through — try again or email me directly';
    btn.disabled = false;
    btn.textContent = 'Send it →';
  }
}
</script>

<div class="lw__signoff">
  <p>until then, cheers!</p>
  <span class="lw__signoff-name">~ Aaron</span>
</div>
