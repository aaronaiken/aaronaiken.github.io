---
layout: holdfast
title: Holdfast · Keep hold of one thing
permalink: /tools/holdfast/
description: An iPhone app for keeping hold of one habit — stop it, or keep it only on reserved days. It reminds you why in your own words, walks you through the moment the pull hits, and never shames you when you slip. Local-only, no account.
image:
  path: /assets/img/holdfast/og.png
  width: 1200
  height: 630
theme_color: "#DCD7CE"
author: aaron
---

<style>
@import url('https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,300..600;1,6..72,300..500&family=Instrument+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');
html { scroll-behavior: smooth; }
/* The global stylesheet pins body to max-width:960px with side padding (and flex),
   which left-anchors the page. Reset to a full-bleed block for this page only so the
   1040px content columns center normally. */
body { margin: 0; padding: 0; max-width: none; display: block;
       background: #DCD7CE; -webkit-font-smoothing: antialiased; }
.hf-page a { color: #221F1C; text-decoration: underline; text-underline-offset: 3px; }
.hf-page a:hover { color: #6C675F; }
.hf-page input::placeholder { color: #8F887E; }
.hf-done { display: none; }
[data-tidy-notify].is-done .hf-form { display: none; }
[data-tidy-notify].is-done .hf-done { display: block; }
</style>

<div class="hf-page" style="background:#DCD7CE;color:#221F1C;font-family:'Instrument Sans',sans-serif;min-height:100vh;">
  <div style="max-width:1040px;margin:0 auto;padding:22px 24px 0;display:flex;justify-content:space-between;align-items:center;font-family:'IBM Plex Mono',monospace;font-size:11px;letter-spacing:0.05em;color:#6C675F;">
    <a href="/tools/" style="color:#6C675F;text-decoration:none;">‹ WORKBENCH</a>
    <div>A TIDY APP</div>
  </div>

  <header style="max-width:1040px;margin:0 auto;padding:64px 24px 40px;display:flex;flex-direction:column;align-items:center;text-align:center;gap:18px;">
    <img src="/assets/img/holdfast/landing/app-icon.png" alt="Holdfast app icon" style="width:88px;height:88px;border-radius:20px;box-shadow:0 10px 24px rgba(34,31,28,0.18);">
    <h1 style="margin:6px 0 0;font-family:'Newsreader',serif;font-weight:400;font-size:clamp(48px,8vw,76px);line-height:1;letter-spacing:-0.015em;">Holdfast</h1>
    <div style="font-family:'IBM Plex Mono',monospace;font-size:11px;letter-spacing:0.08em;color:#6C675F;">IPHONE · ONE HABIT · NO SHAME</div>
    <p style="margin:4px 0 0;font-family:'Newsreader',serif;font-size:clamp(22px,3vw,28px);line-height:1.3;max-width:520px;text-wrap:pretty;">Keep hold of one thing. It reminds you why, in your own words, and stays with you when the pull comes.</p>
    <div style="display:flex;gap:10px;flex-wrap:wrap;justify-content:center;margin-top:8px;">
      <a href="#notify" style="height:46px;padding:0 22px;border-radius:23px;background:#2A2724;color:#F4F1EC;text-decoration:none;display:flex;align-items:center;font-size:15px;font-weight:500;">Get notified</a>
      <a href="#moment" style="height:46px;padding:0 22px;border-radius:23px;border:1.5px solid #2A2724;color:#221F1C;text-decoration:none;display:flex;align-items:center;font-size:15px;font-weight:500;box-sizing:border-box;">See the moment</a>
    </div>
    <div style="font-family:'IBM Plex Mono',monospace;font-size:11px;letter-spacing:0.05em;color:#6C675F;">TESTFLIGHT · iOS 18+</div>
    <img src="/assets/img/holdfast/landing/phone-home.png" alt="Holdfast home screen: days kept" style="aspect-ratio:402/874;filter:drop-shadow(0 12px 24px rgba(34,31,28,0.16));width:min(340px,82vw);margin-top:28px;">
    <div style="font-size:14px;color:#6C675F;max-width:360px;line-height:1.5;">One thing, one number, one button. That's the whole home screen.</div>
  </header>

  <main style="max-width:1040px;margin:0 auto;padding:0 24px;display:flex;flex-direction:column;">

    <section style="padding:72px 0;border-top:1px solid #C9C2B6;display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,300px),1fr));gap:40px;align-items:start;">
      <div style="display:flex;flex-direction:column;gap:16px;">
        <div style="font-family:'IBM Plex Mono',monospace;font-size:11px;letter-spacing:0.08em;color:#6C675F;">WHY IT EXISTS</div>
        <h2 style="margin:0;font-family:'Newsreader',serif;font-weight:400;font-size:clamp(32px,4.4vw,44px);line-height:1.08;letter-spacing:-0.01em;text-wrap:pretty;">A friend of few words, <span style="font-style:italic;">not a dashboard.</span></h2>
      </div>
      <div style="display:flex;flex-direction:column;gap:14px;font-size:17px;line-height:1.6;color:#3A3631;text-wrap:pretty;">
        <p style="margin:0;">I made Holdfast for myself. A bourbon each evening had quietly become the evening, and I wanted Friday night to mean something again.</p>
        <p style="margin:0;">Most habit apps count. Holdfast holds. You name one thing, write down why, and it shows up at the hour the pull usually starts, carrying your reasons back to you.</p>
        <p style="margin:0;">Yours might be the phone in bed, late-night snacking, or scrolling after nine. It works the same.</p>
      </div>
    </section>

    <section style="padding:72px 0;border-top:1px solid #C9C2B6;display:flex;flex-direction:column;gap:32px;">
      <div style="display:flex;flex-direction:column;gap:14px;max-width:640px;">
        <div style="font-family:'IBM Plex Mono',monospace;font-size:11px;letter-spacing:0.08em;color:#6C675F;">HOW IT WORKS</div>
        <h2 style="margin:0;font-family:'Newsreader',serif;font-weight:400;font-size:clamp(32px,4.4vw,44px);line-height:1.08;letter-spacing:-0.01em;">A minute to set up. <span style="font-style:italic;">Then it waits.</span></h2>
      </div>
      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,230px),1fr));gap:14px;">
        <div style="background:#F2EFEA;border-radius:18px;padding:22px;display:flex;flex-direction:column;gap:10px;">
          <div style="font-family:'IBM Plex Mono',monospace;font-size:11px;color:#6C675F;">01</div>
          <div style="font-family:'Newsreader',serif;font-size:24px;line-height:1.15;">Name one thing.</div>
          <div style="font-size:15px;line-height:1.55;color:#4A463F;">Just one, said plainly. Stop it completely, or keep it for the days you choose.</div>
        </div>
        <div style="background:#F2EFEA;border-radius:18px;padding:22px;display:flex;flex-direction:column;gap:10px;">
          <div style="font-family:'IBM Plex Mono',monospace;font-size:11px;color:#6C675F;">02</div>
          <div style="font-family:'Newsreader',serif;font-size:24px;line-height:1.15;">Write down why.</div>
          <div style="font-size:15px;line-height:1.55;color:#4A463F;">Your reasons, a note to the moment, a minute of your own voice. Best done on a clear morning.</div>
        </div>
        <div style="background:#F2EFEA;border-radius:18px;padding:22px;display:flex;flex-direction:column;gap:10px;">
          <div style="font-family:'IBM Plex Mono',monospace;font-size:11px;color:#6C675F;">03</div>
          <div style="font-family:'Newsreader',serif;font-size:24px;line-height:1.15;">Hold the moment.</div>
          <div style="font-size:15px;line-height:1.55;color:#4A463F;">When the pull comes, tap I'm tempted. Ten quiet minutes, then an honest check-in.</div>
        </div>
      </div>
      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,220px),1fr));gap:24px;justify-items:center;padding-top:12px;">
        <figure style="margin:0;display:flex;flex-direction:column;gap:10px;align-items:center;max-width:280px;">
          <img src="/assets/img/holdfast/landing/phone-allowed-days.png" alt="Setup: choose allowed days" style="aspect-ratio:402/874;filter:drop-shadow(0 12px 24px rgba(34,31,28,0.16));width:100%;">
          <figcaption style="font-family:'IBM Plex Mono',monospace;font-size:11px;letter-spacing:0.05em;color:#6C675F;">ALLOWED DAYS</figcaption>
        </figure>
        <figure style="margin:0;display:flex;flex-direction:column;gap:10px;align-items:center;max-width:280px;">
          <img src="/assets/img/holdfast/landing/phone-reasons.png" alt="Setup: write your reasons" style="aspect-ratio:402/874;filter:drop-shadow(0 12px 24px rgba(34,31,28,0.16));width:100%;">
          <figcaption style="font-family:'IBM Plex Mono',monospace;font-size:11px;letter-spacing:0.05em;color:#6C675F;">YOUR REASONS</figcaption>
        </figure>
        <figure style="margin:0;display:flex;flex-direction:column;gap:10px;align-items:center;max-width:280px;">
          <img src="/assets/img/holdfast/landing/phone-lock-screen.png" alt="Lock screen reminder showing one of your reasons" style="aspect-ratio:402/874;filter:drop-shadow(0 12px 24px rgba(34,31,28,0.16));width:100%;">
          <figcaption style="font-family:'IBM Plex Mono',monospace;font-size:11px;letter-spacing:0.05em;color:#6C675F;">7:00 PM, IN YOUR WORDS</figcaption>
        </figure>
      </div>
    </section>

    <section id="moment" style="padding:72px 0;border-top:1px solid #C9C2B6;display:flex;flex-direction:column;gap:32px;">
      <div style="display:flex;flex-direction:column;gap:14px;max-width:680px;">
        <div style="font-family:'IBM Plex Mono',monospace;font-size:11px;letter-spacing:0.08em;color:#6C675F;">THE TEMPTED MOMENT</div>
        <h2 style="margin:0;font-family:'Newsreader',serif;font-weight:400;font-size:clamp(32px,4.4vw,44px);line-height:1.08;letter-spacing:-0.01em;">When the pull comes, <span style="font-style:italic;">slow it down.</span></h2>
        <p style="margin:0;font-size:17px;line-height:1.6;color:#3A3631;text-wrap:pretty;">The screen goes dark and quiet. A breath first. Then your note, your voice, your reasons, one at a time. Then something to do instead, and a timer with no digits, just a line that settles.</p>
      </div>
      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,420px),1fr));gap:18px;">
        <div style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:18px;">
          <figure style="margin:0;display:flex;flex-direction:column;gap:8px;"><img src="/assets/img/holdfast/landing/phone-m1-breathe.png" alt="Breathe" style="aspect-ratio:402/874;filter:drop-shadow(0 12px 24px rgba(34,31,28,0.16));width:100%;"><figcaption style="font-family:'IBM Plex Mono',monospace;font-size:11px;color:#6C675F;">1 · BREATHE</figcaption></figure>
          <figure style="margin:0;display:flex;flex-direction:column;gap:8px;"><img src="/assets/img/holdfast/landing/phone-m2-note.png" alt="A note from you" style="aspect-ratio:402/874;filter:drop-shadow(0 12px 24px rgba(34,31,28,0.16));width:100%;"><figcaption style="font-family:'IBM Plex Mono',monospace;font-size:11px;color:#6C675F;">2 · YOUR NOTE</figcaption></figure>
          <figure style="margin:0;display:flex;flex-direction:column;gap:8px;"><img src="/assets/img/holdfast/landing/phone-m3-memo.png" alt="Your voice memo" style="aspect-ratio:402/874;filter:drop-shadow(0 12px 24px rgba(34,31,28,0.16));width:100%;"><figcaption style="font-family:'IBM Plex Mono',monospace;font-size:11px;color:#6C675F;">3 · YOUR VOICE</figcaption></figure>
        </div>
        <div style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:18px;">
          <figure style="margin:0;display:flex;flex-direction:column;gap:8px;"><img src="/assets/img/holdfast/landing/phone-m4-reason.png" alt="One of your reasons" style="aspect-ratio:402/874;filter:drop-shadow(0 12px 24px rgba(34,31,28,0.16));width:100%;"><figcaption style="font-family:'IBM Plex Mono',monospace;font-size:11px;color:#6C675F;">4 · YOUR REASONS</figcaption></figure>
          <figure style="margin:0;display:flex;flex-direction:column;gap:8px;"><img src="/assets/img/holdfast/landing/phone-m5-timer.png" alt="The settling timer" style="aspect-ratio:402/874;filter:drop-shadow(0 12px 24px rgba(34,31,28,0.16));width:100%;"><figcaption style="font-family:'IBM Plex Mono',monospace;font-size:11px;color:#6C675F;">5 · TEN MINUTES</figcaption></figure>
          <figure style="margin:0;display:flex;flex-direction:column;gap:8px;"><img src="/assets/img/holdfast/landing/phone-m6-held.png" alt="Held." style="aspect-ratio:402/874;filter:drop-shadow(0 12px 24px rgba(34,31,28,0.16));width:100%;"><figcaption style="font-family:'IBM Plex Mono',monospace;font-size:11px;color:#6C675F;">6 · HELD</figcaption></figure>
        </div>
      </div>
      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,230px),1fr));gap:14px;">
        <div style="border-top:1.5px solid #221F1C;padding-top:14px;display:flex;flex-direction:column;gap:6px;"><div style="font-weight:600;font-size:15px;">It passed.</div><div style="font-size:15px;line-height:1.55;color:#4A463F;">A quiet "Held." One light tap. Counted as a moment held.</div></div>
        <div style="border-top:1.5px solid #221F1C;padding-top:14px;display:flex;flex-direction:column;gap:6px;"><div style="font-weight:600;font-size:15px;">Still wanting it.</div><div style="font-size:15px;line-height:1.55;color:#4A463F;">Another reason, another ten minutes. As many times as it takes.</div></div>
        <div style="border-top:1.5px solid #221F1C;padding-top:14px;display:flex;flex-direction:column;gap:6px;"><div style="font-weight:600;font-size:15px;">I had it.</div><div style="font-size:15px;line-height:1.55;color:#4A463F;">"Noted. Tomorrow's a new day." Nothing more.</div></div>
      </div>
    </section>

    <section style="padding:72px 0;border-top:1px solid #C9C2B6;display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,320px),1fr));gap:48px;align-items:center;">
      <div style="display:flex;flex-direction:column;gap:16px;">
        <div style="font-family:'IBM Plex Mono',monospace;font-size:11px;letter-spacing:0.08em;color:#6C675F;">NO SHAME</div>
        <h2 style="margin:0;font-family:'Newsreader',serif;font-weight:400;font-size:clamp(32px,4.4vw,44px);line-height:1.08;letter-spacing:-0.01em;">Days kept <span style="font-style:italic;">never go down.</span></h2>
        <p style="margin:0;font-size:17px;line-height:1.6;color:#3A3631;text-wrap:pretty;">A slip resets the streak, and that's all it does. Nothing flashes red. There are no warnings about what you'd lose, and no exclamation points, ever. Allowed days are marked as yours to enjoy, not as gaps.</p>
        <p style="margin:0;font-size:17px;line-height:1.6;color:#3A3631;text-wrap:pretty;">Only one thing gets color: warm ember, for the days you kept.</p>
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:18px;">
        <img src="/assets/img/holdfast/landing/phone-history.png" alt="History calendar with kept days" style="aspect-ratio:402/874;filter:drop-shadow(0 12px 24px rgba(34,31,28,0.16));width:100%;">
        <img src="/assets/img/holdfast/landing/phone-noted.png" alt="Noted. Tomorrow's a new day." style="aspect-ratio:402/874;filter:drop-shadow(0 12px 24px rgba(34,31,28,0.16));width:100%;">
      </div>
    </section>

    <section style="padding:72px 0;border-top:1px solid #C9C2B6;display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,320px),1fr));gap:48px;align-items:center;">
      <div style="display:flex;justify-content:center;order:0;">
        <div style="display:flex;flex-direction:column;gap:14px;width:min(400px,100%);">
          <div style="display:flex;gap:14px;align-items:stretch;">
            <div style="background:#3A3531;border-radius:26px;padding:18px;display:flex;flex:1;justify-content:center;">
              <div style="width:158px;height:158px;border-radius:22px;background:#F2EFEA;color:#221F1C;padding:13px 13px 11px;box-sizing:border-box;display:flex;flex-direction:column;">
                <div style="display:flex;justify-content:space-between;align-items:flex-start;"><div style="font-family:'Newsreader',serif;font-size:44px;line-height:0.9;font-weight:300;">36</div><svg width="15" height="15" viewBox="0 0 32 32"><path d="M9 29V12C9 7.5 12 5 16 5H24C26 5 27 6 27 8V10.5" fill="none" stroke="#6C675F" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"></path></svg></div>
                <div style="font-size:12px;color:#6C675F;margin-top:4px;">days kept</div>
                <div style="font-size:12px;margin-top:5px;">Not yet logged.</div>
                <div style="margin-top:auto;height:34px;border-radius:17px;background:#2A2724;color:#F4F1EC;font-size:13px;font-weight:500;display:flex;align-items:center;justify-content:center;">I'm tempted</div>
              </div>
            </div>
            <div style="display:flex;flex-direction:column;gap:14px;justify-content:space-between;">
              <img src="/assets/img/holdfast/landing/app-icon.png" alt="Holdfast app icon" style="width:84px;height:84px;border-radius:19px;box-shadow:0 8px 18px rgba(34,31,28,0.18);">
              <div style="width:84px;height:84px;border-radius:50%;background:#1C1A17;display:flex;align-items:center;justify-content:center;"><div style="width:56px;height:56px;border-radius:50%;background:rgba(241,236,228,0.14);display:flex;align-items:center;justify-content:center;"><svg width="24" height="24" viewBox="0 0 32 32"><path d="M9 29V12C9 7.5 12 5 16 5H24C26 5 27 6 27 8V10.5" fill="none" stroke="#F1ECE4" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"></path></svg></div></div>
            </div>
          </div>
          <div style="background:#1C1A17;border-radius:26px;padding:12px;display:flex;flex-direction:column;gap:6px;color:#F1ECE4;">
            <div style="background:rgba(58,54,50,0.9);border-radius:18px;padding:12px 14px;display:flex;gap:11px;">
              <div style="width:34px;height:34px;border-radius:8px;background:#2A2724;display:flex;align-items:center;justify-content:center;flex-shrink:0;"><svg width="19" height="19" viewBox="0 0 32 32"><path d="M9 29V12C9 7.5 12 5 16 5H24C26 5 27 6 27 8V10.5" fill="none" stroke="#F1ECE4" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"></path></svg></div>
              <div style="flex:1;display:flex;flex-direction:column;gap:2px;"><div style="display:flex;justify-content:space-between;font-size:14px;"><div style="font-weight:600;">Holdfast</div><div style="opacity:0.55;font-size:12px;">7:30 am</div></div><div style="font-size:14px;opacity:0.92;">Did you hold last night?</div></div>
            </div>
            <div style="display:flex;gap:6px;"><div style="flex:1;height:42px;border-radius:14px;background:rgba(58,54,50,0.9);display:flex;align-items:center;justify-content:center;font-size:15px;font-weight:500;">Held</div><div style="flex:1;height:42px;border-radius:14px;background:rgba(58,54,50,0.9);display:flex;align-items:center;justify-content:center;font-size:15px;font-weight:500;">Not last night</div></div>
          </div>
          <div style="background:#1C1A17;border-radius:26px;padding:12px;color:#F1ECE4;">
            <div style="background:rgba(58,54,50,0.9);border-radius:18px;padding:12px 14px;display:flex;gap:11px;">
              <div style="width:34px;height:34px;border-radius:8px;background:#2A2724;display:flex;align-items:center;justify-content:center;flex-shrink:0;"><svg width="19" height="19" viewBox="0 0 32 32"><path d="M9 29V12C9 7.5 12 5 16 5H24C26 5 27 6 27 8V10.5" fill="none" stroke="#F1ECE4" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"></path></svg></div>
              <div style="flex:1;display:flex;flex-direction:column;gap:2px;"><div style="display:flex;justify-content:space-between;font-size:14px;"><div style="font-weight:600;">Holdfast</div><div style="opacity:0.55;font-size:12px;">Fri 7:00 pm</div></div><div style="font-size:14px;opacity:0.92;">It's Friday. Enjoy it.</div></div>
            </div>
          </div>
        </div>
      </div>
      <div style="display:flex;flex-direction:column;gap:16px;">
        <div style="font-family:'IBM Plex Mono',monospace;font-size:11px;letter-spacing:0.08em;color:#6C675F;">EVERY DOOR</div>
        <h2 style="margin:0;font-family:'Newsreader',serif;font-weight:400;font-size:clamp(32px,4.4vw,44px);line-height:1.08;letter-spacing:-0.01em;">One tap from <span style="font-style:italic;">anywhere.</span></h2>
        <p style="margin:0;font-size:17px;line-height:1.6;color:#3A3631;text-wrap:pretty;">The reminder, the lock screen, a home screen widget, Control Center and the Action Button all open straight into the moment. No menus to get through when it matters.</p>
        <p style="margin:0;font-size:17px;line-height:1.6;color:#3A3631;text-wrap:pretty;">Forget to log? A single morning check-in asks, only if the night went unlogged.</p>
      </div>
    </section>

    <section style="padding:72px 0;border-top:1px solid #C9C2B6;"><div style="display:flex;flex-direction:column;gap:16px;max-width:680px;">
      <div style="font-family:'IBM Plex Mono',monospace;font-size:11px;letter-spacing:0.08em;color:#6C675F;">PRIVATE</div>
      <h2 style="margin:0;font-family:'Newsreader',serif;font-weight:400;font-size:clamp(32px,4.4vw,44px);line-height:1.08;letter-spacing:-0.01em;">It stays <span style="font-style:italic;">on your phone.</span></h2>
      <p style="margin:0;font-size:17px;line-height:1.6;color:#3A3631;text-wrap:pretty;">Your reasons, your voice, your days. Reminders are scheduled on the device. Export everything as plain JSON whenever you like.</p>
      </div></section>

    <section id="notify" data-tidy-notify data-app="holdfast" data-endpoint="https://email.aaronaiken.me/subscribe" style="margin:24px 0 72px;background:#2A2724;color:#EDE7DD;border-radius:28px;padding:clamp(28px,5vw,56px);display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,300px),1fr));gap:32px;align-items:end;">
      <div style="display:flex;flex-direction:column;gap:14px;">
        <div style="font-family:'IBM Plex Mono',monospace;font-size:11px;letter-spacing:0.08em;color:#A39C91;">WHEN IT'S READY</div>
        <h2 style="margin:0;font-family:'Newsreader',serif;font-weight:400;font-size:clamp(30px,4vw,40px);line-height:1.1;">Hear when Holdfast launches.</h2>
        <p style="margin:0;font-size:16px;line-height:1.55;color:#C9C2B6;">One note at launch. That's it.</p>
      </div>
      <div style="display:flex;flex-direction:column;gap:10px;">
        <form class="hf-form" style="display:flex;gap:8px;flex-wrap:wrap;">
          <input type="email" name="email" required autocomplete="email" placeholder="you@example.com" aria-label="Email address" style="flex:1 1 220px;min-width:0;height:50px;padding:0 18px;border-radius:25px;border:1px solid #4A4540;background:#1C1A17;color:#EDE7DD;font:16px 'Instrument Sans',sans-serif;outline:none;">
          <button type="submit" style="height:50px;padding:0 22px;border-radius:25px;border:none;background:#EDE7DD;color:#1A1816;font:500 15px 'Instrument Sans',sans-serif;cursor:pointer;">Notify me</button>
        </form>
        <div class="hf-done" style="font-family:'Newsreader',serif;font-size:24px;">Thank you. You'll hear once.</div>
        <div style="font-family:'IBM Plex Mono',monospace;font-size:11px;letter-spacing:0.05em;color:#A39C91;">NO TRACKING · UNSUBSCRIBE ANY TIME</div>
      </div>
    </section>
  </main>

  <footer style="max-width:1040px;margin:0 auto;padding:28px 24px 48px;border-top:1px solid #C9C2B6;display:flex;justify-content:space-between;gap:16px;flex-wrap:wrap;font-size:14px;line-height:1.5;color:#6C675F;">
    <div style="max-width:520px;">Designed and built by <a href="/about/">Aaron</a>. A sibling to <a href="/tidyapps/">Still Dark</a>, a prayer journal. Holdfast is not a medical service.</div>
    <div style="font-family:'Newsreader',serif;font-style:italic;font-size:16px;">Hold fast to what is good.</div>
  </footer>
</div>
