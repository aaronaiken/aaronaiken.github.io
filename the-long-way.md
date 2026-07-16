---
layout: long-way-v1
title: The Long Way
permalink: /the-long-way
subtitle: Debt. Marriage. Faith. Fatherhood. Reconciliation. A letter from Aaron about the harder, slower, more honest path.
description: The Long Way — a personal newsletter from Aaron about taking the harder path through debt, marriage, faith, fatherhood, and the daily work of not taking shortcuts. Roughly every two weeks.
---

In 2021 my world crumbled.

By the end of 2024 I had piled up $110,000 in mostly consumer debt and a marriage that had come apart. In November of that year, I started walking back. On December 23, 2025, my wife and I remarried.

I'm still walking.

*This is the correspondence.*

---

The Long Way arrives roughly every two weeks. It is not optimization. It is not tips. It is not a five-step framework for anything.

It is one person mid-story, writing it down honestly enough that someone else might recognize their own.

Some weeks the letter is about a number — the exact dollar amount, the months until debt-free, the days since the worst day. Some weeks it is about a kitchen, a parsonage, a house we used to live in. Some weeks it is about Mozzie. Some weeks it is about God, though I won't preach to you. Some weeks it is about a tool I built when the off-the-shelf thing wouldn't do.

All of them are about the same thing: the harder path. I didn't choose it — it's been my default setting up to here. I've stayed on it on purpose, forging my own way through. At forty, I'm ready to get off the highway and onto a slower local road.

<div class="lw2__reply">
  <p class="k">Post me a reply</p>
  <p>The first letter goes out when it's ready — and not before. Leave your address and I'll write when it lands.</p>
  <form id="lw2-form" onsubmit="handleLW2Subscribe(event)" novalidate>
    <div class="lw2__row">
      <input type="email" id="lw2-email" required placeholder="your.email@somewhere.com">
      <button type="submit" id="lw2-btn">Seal &amp; send →</button>
    </div>
    <p class="lw2__note" id="lw2-status">No tracking · rarely sent · unsubscribe by reply</p>
  </form>
</div>

<script>
async function handleLW2Subscribe(event){
  event.preventDefault();
  var btn=document.getElementById('lw2-btn'), status=document.getElementById('lw2-status');
  var email=document.getElementById('lw2-email').value.trim();
  if(!email||!email.includes('@')){ status.textContent='⚠ please enter a valid email address'; return; }
  btn.disabled=true; btn.textContent='Sending…';
  try{
    var resp=await fetch('https://email.aaronaiken.me/subscribe',{
      method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({email:email, tools:['signal']})
    });
    if(resp.ok){ btn.textContent='Sent ✓'; status.textContent='Thank you. I\'ll let you know when the first letter goes out.'; document.getElementById('lw2-email').value=''; }
    else{ throw new Error('server error'); }
  }catch(e){ status.textContent='⚠ something didn\'t go through — try again or email me directly'; btn.disabled=false; btn.textContent='Seal & send →'; }
}
</script>
