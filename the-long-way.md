---
layout: long-way-v1
title: The Long Way
permalink: /the-long-way
favicon: /assets/the-long-way/tlw.svg
theme_color: "#FAF5EC"
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

<div id="cad-the-long-way" style="max-width:440px;font-family:Georgia,'Times New Roman',serif;text-align:center">
  <style>#cad-the-long-way{color:#1a1c20}#cad-the-long-way input{border:1px solid #d8d2c4;background:#fff;color:#1a1c20}#cad-the-long-way input::placeholder{color:#9a948a}@media(prefers-color-scheme:dark){#cad-the-long-way{color:#ece7dc}#cad-the-long-way input{border-color:#3d4046;background:transparent;color:#ece7dc}}</style>
  <div style="font-size:15px;color:#8a8474;margin-bottom:16px">Debt. Marriage. Divorce. Reconciliation. Faith. Fatherhood. A letter from Aaron about the harder, slower, more honest path.</div>
  <form onsubmit="return cad_the_long_way(event)" style="display:flex;gap:8px;flex-wrap:wrap">
    <input type="email" name="email" required placeholder="you@email.com" style="flex:1;min-width:200px;padding:12px 14px;border-radius:3px;font-size:15px">
    <button style="padding:12px 22px;border:none;border-radius:3px;background:#C98A3D;color:#fff;font-size:15px;font-weight:500;cursor:pointer">Begin at chapter 1</button>
    <p data-s style="width:100%;margin:10px 0 0;font-size:13px;color:#8a8474">One chapter at a time · no tracking · unsubscribe anytime</p>
  </form>
  <a href="https://cadencestories.com" style="display:inline-flex;align-items:center;gap:5px;margin-top:14px;font-size:10.5px;letter-spacing:.1em;text-transform:uppercase;color:#8a8474;text-decoration:none;opacity:.7"><svg width="11" height="11" viewBox="0 0 32 32" fill="#8a8474" style="flex:none"><rect x="2.5" y="9" width="3" height="14"/><rect x="8.5" y="6" width="3" height="20"/><rect x="14.5" y="3" width="3" height="26"/><rect x="20.5" y="6" width="3" height="20"/><rect x="26.5" y="9" width="3" height="14"/></svg>delivered on cadence</a>
</div>
<script>function cad_the_long_way(e){e.preventDefault();var f=e.target,s=f.querySelector('[data-s]'),b=f.querySelector('button'),m=f.email.value.trim();if(!m||m.indexOf('@')<0){s.textContent='Please enter a valid email.';return false}b.disabled=true;fetch('https://cadencestories.com/p/the-long-way/subscribe',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email:m})}).then(function(r){if(!r.ok)throw 0;s.textContent='Check your inbox to confirm.';f.querySelector('input').style.display='none';b.style.display='none'}).catch(function(){s.textContent='Something went wrong — try again.';b.disabled=false});return false}</script>
