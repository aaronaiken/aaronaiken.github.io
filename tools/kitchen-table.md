---
layout: kitchentable
title: Kitchen Table · What we decided, and why
permalink: /tools/kitchen-table/
description: A household decision log for iPhone. Write down what the two of you decided, and why, in about fifteen seconds. Pending decisions stay on top, and a money plan keeps one thing at a time. Lives in your own iCloud. Paid once.
image:
  path: /assets/img/kitchentable/og.png
  width: 1200
  height: 630
theme_color: "#FAF5EC"
author: aaron
---

{% comment %}
SCREENSHOTS TO DROP IN (from the Simulator, sample data only — never the real household or money plan).
Save to /assets/img/kitchentable/landing/ with these names, then swap each
`.kt-shot` placeholder div for the <img> in the comment right above it:
  phone-list.png      the list, pending on top          (hero)
  phone-capture.png   capture, mid-typing, keyboard up
  phone-detail.png    a decision's detail
  phone-followup.png  the "did it hold up?" card
  phone-done.png      the Done shelf, open
  phone-money.png     Money: "Our money plan" with Now / Then / Always on
Shots are 1320×2868 (iPhone 17 Pro Max); the placeholders use that ratio.
{% endcomment %}

<style>
@import url('https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,300..600;1,6..72,300..500&family=IBM+Plex+Mono:wght@400;500&display=swap');
html { scroll-behavior: smooth; }
/* The global stylesheet pins body to max-width:960px with side padding (and flex),
   which left-anchors the page. Reset to a full-bleed block for this page only so the
   1040px content columns center normally. */
body { margin: 0; padding: 0; max-width: none; display: block;
       background: #FAF5EC; -webkit-font-smoothing: antialiased; }
.kt-page a { color: #A85331; text-decoration: underline; text-underline-offset: 3px; }
.kt-page a:hover { color: #38302A; }
.kt-page input::placeholder { color: #B8ADA0; }
.kt-shot { aspect-ratio: 1320/2868; width: 100%; box-sizing: border-box; border: 1.5px dashed #DBD2C3; border-radius: 28px;
           background: #FFFDF7; display: flex; align-items: center; justify-content: center; text-align: center; padding: 16px;
           font-family: 'IBM Plex Mono', monospace; font-size: 11px; letter-spacing: 0.08em; color: #B8ADA0; }
.kt-img { aspect-ratio: 1320/2868; width: 100%; filter: drop-shadow(0 12px 24px rgba(56,48,42,0.16)); }
.kt-done { display: none; }
[data-tidy-notify].is-done .kt-form { display: none; }
[data-tidy-notify].is-done .kt-done { display: block; }
</style>

<div class="kt-page" style="background:#FAF5EC;color:#38302A;font-family:'Newsreader',serif;min-height:100vh;">
  <div style="max-width:1040px;margin:0 auto;padding:22px 24px 0;display:flex;justify-content:space-between;align-items:center;font-family:'IBM Plex Mono',monospace;font-size:11px;letter-spacing:0.05em;color:#655A4E;">
    <a href="/tools/" style="color:#655A4E;text-decoration:none;">‹ WORKBENCH</a>
    <div>A TIDY APP</div>
  </div>

  <header style="max-width:1040px;margin:0 auto;padding:64px 24px 40px;display:flex;flex-direction:column;align-items:center;text-align:center;gap:18px;">
    <img src="/assets/img/kitchentable/landing/app-icon.png" alt="Kitchen Table app icon" style="width:88px;height:88px;border-radius:20px;box-shadow:0 10px 24px rgba(56,48,42,0.18);">
    <h1 style="margin:6px 0 0;font-family:'Newsreader',serif;font-weight:400;font-size:clamp(48px,8vw,76px);line-height:1;letter-spacing:-0.015em;">Kitchen Table</h1>
    <div style="font-family:'IBM Plex Mono',monospace;font-size:11px;letter-spacing:0.08em;color:#655A4E;">IPHONE · FOR TWO · PAID ONCE</div>
    <p style="margin:4px 0 0;font-size:clamp(22px,3vw,28px);line-height:1.3;max-width:540px;text-wrap:pretty;">What we decided, and why. A record of your household's decisions, so nobody has to remember.</p>
    <div style="display:flex;gap:10px;flex-wrap:wrap;justify-content:center;margin-top:8px;font-family:'IBM Plex Mono',monospace;">
      <a href="#notify" style="height:46px;padding:0 22px;border-radius:23px;background:#38302A;color:#FAF5EC;text-decoration:none;display:flex;align-items:center;font-size:13px;letter-spacing:0.06em;">GET NOTIFIED</a>
      <a href="#how" style="height:46px;padding:0 22px;border-radius:23px;border:1.5px solid #38302A;color:#38302A;text-decoration:none;display:flex;align-items:center;font-size:13px;letter-spacing:0.06em;box-sizing:border-box;">SEE HOW IT WORKS</a>
    </div>
    <div style="font-family:'IBM Plex Mono',monospace;font-size:11px;letter-spacing:0.05em;color:#655A4E;">PRIVATE BETA · iOS 18+ · $2.99 AT LAUNCH</div>
    <div style="width:min(340px,82vw);margin-top:28px;">
      <!-- <img src="/assets/img/kitchentable/landing/phone-list.png" alt="The list: pending decisions on top, numbered in the order you'll tackle them" class="kt-img"> -->
      <div class="kt-shot">SCREENSHOT · THE LIST, PENDING ON TOP</div>
    </div>
    <div style="font-size:16px;font-style:italic;color:#5E5448;max-width:360px;line-height:1.5;">The ones you'd forget first are the ones you see first.</div>
  </header>

  <main style="max-width:1040px;margin:0 auto;padding:0 24px;display:flex;flex-direction:column;">

    <section style="padding:72px 0;border-top:1px solid #DBD2C3;display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,300px),1fr));gap:40px;align-items:start;">
      <div style="display:flex;flex-direction:column;gap:16px;">
        <div style="font-family:'IBM Plex Mono',monospace;font-size:11px;letter-spacing:0.08em;color:#655A4E;">WHY IT EXISTS</div>
        <h2 style="margin:0;font-weight:400;font-size:clamp(32px,4.4vw,44px);line-height:1.08;letter-spacing:-0.01em;text-wrap:pretty;">You talked it through. <span style="font-style:italic;">Then it evaporated.</span></h2>
      </div>
      <div style="display:flex;flex-direction:column;gap:14px;font-size:19px;line-height:1.6;color:#41382F;text-wrap:pretty;">
        <p style="margin:0;">The new mattress. Taking the back tree down. Replacing the couches. You sit at the kitchen table, talk it through, and land somewhere.</p>
        <p style="margin:0;">Three weeks later, neither of you can remember what you said, or why.</p>
        <p style="margin:0;">I made Kitchen Table for our own house, to catch the outcome before it's gone. It's a shared notebook for the two of you, nothing more.</p>
      </div>
    </section>

    <section id="how" style="padding:72px 0;border-top:1px solid #DBD2C3;display:flex;flex-direction:column;gap:32px;">
      <div style="display:flex;flex-direction:column;gap:14px;max-width:640px;">
        <div style="font-family:'IBM Plex Mono',monospace;font-size:11px;letter-spacing:0.08em;color:#655A4E;">HOW IT WORKS</div>
        <h2 style="margin:0;font-weight:400;font-size:clamp(32px,4.4vw,44px);line-height:1.08;letter-spacing:-0.01em;">Fifteen seconds to write it down. <span style="font-style:italic;">Then it keeps.</span></h2>
      </div>
      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,230px),1fr));gap:14px;">
        <div style="background:#FFFDF7;border:1px solid #E4DCCE;border-radius:18px;padding:22px;display:flex;flex-direction:column;gap:10px;">
          <div style="font-family:'IBM Plex Mono',monospace;font-size:11px;color:#A85331;">01</div>
          <div style="font-size:24px;line-height:1.15;">Write it down.</div>
          <div style="font-size:17px;line-height:1.55;color:#564C42;">A title and a few lines. Cost, vendor, a date or a photo can come later. Nothing ever stops you from saving.</div>
        </div>
        <div style="background:#FFFDF7;border:1px solid #E4DCCE;border-radius:18px;padding:22px;display:flex;flex-direction:column;gap:10px;">
          <div style="font-family:'IBM Plex Mono',monospace;font-size:11px;color:#A85331;">02</div>
          <div style="font-size:24px;line-height:1.15;">Pending stays on top.</div>
          <div style="font-size:17px;line-height:1.55;color:#564C42;">What you haven't decided yet sits first, numbered in the order you'll tackle it. Nudge anything up or down.</div>
        </div>
        <div style="background:#FFFDF7;border:1px solid #E4DCCE;border-radius:18px;padding:22px;display:flex;flex-direction:column;gap:10px;">
          <div style="font-family:'IBM Plex Mono',monospace;font-size:11px;color:#A85331;">03</div>
          <div style="font-size:24px;line-height:1.15;">Did it hold up?</div>
          <div style="font-size:17px;line-height:1.55;color:#564C42;">Months later it asks once how it went. One line is plenty. No ratings, no scores. Dismiss it and it never comes back.</div>
        </div>
      </div>
      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,220px),1fr));gap:24px;justify-items:center;padding-top:12px;">
        <figure style="margin:0;display:flex;flex-direction:column;gap:10px;align-items:center;width:100%;max-width:280px;">
          <!-- <img src="/assets/img/kitchentable/landing/phone-capture.png" alt="Capturing a decision: a title, a few lines, optional extras" class="kt-img"> -->
          <div class="kt-shot">SCREENSHOT · CAPTURE</div>
          <figcaption style="font-family:'IBM Plex Mono',monospace;font-size:11px;letter-spacing:0.05em;color:#655A4E;">A TITLE AND A FEW LINES</figcaption>
        </figure>
        <figure style="margin:0;display:flex;flex-direction:column;gap:10px;align-items:center;width:100%;max-width:280px;">
          <!-- <img src="/assets/img/kitchentable/landing/phone-detail.png" alt="A decision's detail, with the reasoning kept alongside it" class="kt-img"> -->
          <div class="kt-shot">SCREENSHOT · DETAIL</div>
          <figcaption style="font-family:'IBM Plex Mono',monospace;font-size:11px;letter-spacing:0.05em;color:#655A4E;">THE REASONING STAYS WITH IT</figcaption>
        </figure>
        <figure style="margin:0;display:flex;flex-direction:column;gap:10px;align-items:center;width:100%;max-width:280px;">
          <!-- <img src="/assets/img/kitchentable/landing/phone-followup.png" alt="The follow-up card asking whether a decision held up" class="kt-img"> -->
          <div class="kt-shot">SCREENSHOT · FOLLOW-UP CARD</div>
          <figcaption style="font-family:'IBM Plex Mono',monospace;font-size:11px;letter-spacing:0.05em;color:#655A4E;">MONTHS LATER, ONCE</figcaption>
        </figure>
      </div>
    </section>

    <section style="padding:72px 0;border-top:1px solid #DBD2C3;display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,320px),1fr));gap:48px;align-items:center;">
      <div style="display:flex;flex-direction:column;gap:16px;">
        <div style="font-family:'IBM Plex Mono',monospace;font-size:11px;letter-spacing:0.08em;color:#4A7256;">THE DONE SHELF</div>
        <h2 style="margin:0;font-weight:400;font-size:clamp(32px,4.4vw,44px);line-height:1.08;letter-spacing:-0.01em;">See what you've gotten done <span style="font-style:italic;">together.</span></h2>
        <p style="margin:0;font-size:19px;line-height:1.6;color:#41382F;text-wrap:pretty;">Finished something? It leaves the list for a dated Done shelf at the bottom, newest first. The list renumbers, so #2 becomes #1.</p>
        <p style="margin:0;font-size:19px;line-height:1.6;color:#41382F;text-wrap:pretty;">Search finds any decision by any word in it, including the ones on the shelf.</p>
      </div>
      <div style="display:flex;justify-content:center;">
        <div style="width:min(300px,100%);">
          <!-- <img src="/assets/img/kitchentable/landing/phone-done.png" alt="The Done shelf: finished decisions, dated" class="kt-img"> -->
          <div class="kt-shot">SCREENSHOT · DONE SHELF</div>
        </div>
      </div>
    </section>

    <section style="padding:72px 0;border-top:1px solid #DBD2C3;display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,320px),1fr));gap:48px;align-items:center;">
      <div style="display:flex;justify-content:center;">
        <div style="width:min(300px,100%);">
          <!-- <img src="/assets/img/kitchentable/landing/phone-money.png" alt="Our money plan: one step Now, the rest waiting in order" class="kt-img"> -->
          <div class="kt-shot">SCREENSHOT · OUR MONEY PLAN</div>
        </div>
      </div>
      <div style="display:flex;flex-direction:column;gap:16px;">
        <div style="font-family:'IBM Plex Mono',monospace;font-size:11px;letter-spacing:0.08em;color:#A85331;">MONEY</div>
        <h2 style="margin:0;font-weight:400;font-size:clamp(32px,4.4vw,44px);line-height:1.08;letter-spacing:-0.01em;">Our money plan. <span style="font-style:italic;">One thing at a time, in this order.</span></h2>
        <p style="margin:0;font-size:19px;line-height:1.6;color:#41382F;text-wrap:pretty;">Some plans aren't a list of decisions. They're a sequence: pay this off, then build that. Money is its own area, kept apart from your decisions.</p>
        <p style="margin:0;font-size:19px;line-height:1.6;color:#41382F;text-wrap:pretty;">One step is <strong style="font-weight:500;">Now</strong>. The rest wait their turn. When you finish it, the next one moves up. Some steps never end, like saving for retirement. Start those and they stay <strong style="font-weight:500;">Always on</strong>.</p>
        <p style="margin:0;font-size:19px;line-height:1.6;color:#41382F;text-wrap:pretty;">A target and "where we are" are just notes in your own words. No bank linking, no balances, no charts, no due dates, no reminders.</p>
      </div>
    </section>

    <section style="padding:72px 0;border-top:1px solid #DBD2C3;display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,300px),1fr));gap:40px;align-items:start;">
      <div style="display:flex;flex-direction:column;gap:16px;">
        <div style="font-family:'IBM Plex Mono',monospace;font-size:11px;letter-spacing:0.08em;color:#655A4E;">FOR TWO</div>
        <h2 style="margin:0;font-weight:400;font-size:clamp(32px,4.4vw,44px);line-height:1.08;letter-spacing:-0.01em;">Share it with <span style="font-style:italic;">your person.</span></h2>
        <p style="margin:0;font-size:19px;line-height:1.6;color:#41382F;text-wrap:pretty;">Tap Share and send the invite. You both keep the same record, decisions and money plan, and either of you can add to it.</p>
      </div>
      <div style="display:flex;flex-direction:column;gap:16px;">
        <div style="font-family:'IBM Plex Mono',monospace;font-size:11px;letter-spacing:0.08em;color:#655A4E;">PRIVATE</div>
        <h2 style="margin:0;font-weight:400;font-size:clamp(32px,4.4vw,44px);line-height:1.08;letter-spacing:-0.01em;">It lives in <span style="font-style:italic;">your own iCloud.</span></h2>
        <p style="margin:0;font-size:19px;line-height:1.6;color:#41382F;text-wrap:pretty;">Only the people you invite can see it. I can't. No accounts, no ads, no tracking. Keep a copy as a file any time, and restore from it safely.</p>
      </div>
    </section>

    <section style="padding:72px 0;border-top:1px solid #DBD2C3;"><div style="display:flex;flex-direction:column;gap:16px;max-width:680px;">
      <div style="font-family:'IBM Plex Mono',monospace;font-size:11px;letter-spacing:0.08em;color:#655A4E;">PRICE</div>
      <h2 style="margin:0;font-weight:400;font-size:clamp(32px,4.4vw,44px);line-height:1.08;letter-spacing:-0.01em;">$2.99, <span style="font-style:italic;">once.</span></h2>
      <p style="margin:0;font-size:19px;line-height:1.6;color:#41382F;text-wrap:pretty;">No subscription, no in-app purchases. If the person you share it with is in your Apple Family, Family Sharing covers them.</p>
      </div></section>

    <section id="notify" data-tidy-notify data-app="kitchentable" data-endpoint="https://email.aaronaiken.me/subscribe" style="margin:24px 0 72px;background:#38302A;color:#F1E9DC;border-radius:28px;padding:clamp(28px,5vw,56px);display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,300px),1fr));gap:32px;align-items:end;">
      <div style="display:flex;flex-direction:column;gap:14px;">
        <div style="font-family:'IBM Plex Mono',monospace;font-size:11px;letter-spacing:0.08em;color:#ADA090;">WHEN IT'S READY</div>
        <h2 style="margin:0;font-weight:400;font-size:clamp(30px,4vw,40px);line-height:1.1;">Hear when Kitchen Table launches.</h2>
        <p style="margin:0;font-size:18px;line-height:1.55;color:#C9BDAE;">One note at launch. That's it.</p>
      </div>
      <div style="display:flex;flex-direction:column;gap:10px;">
        <form class="kt-form" style="display:flex;gap:8px;flex-wrap:wrap;">
          <input type="email" name="email" required autocomplete="email" placeholder="you@example.com" aria-label="Email address" style="flex:1 1 220px;min-width:0;height:50px;padding:0 18px;border-radius:25px;border:1px solid #4A4037;background:#1C1815;color:#F1E9DC;font:16px 'Newsreader',serif;outline:none;">
          <button type="submit" style="height:50px;padding:0 22px;border-radius:25px;border:none;background:#D9784F;color:#1C1815;font:500 13px 'IBM Plex Mono',monospace;letter-spacing:0.06em;cursor:pointer;">NOTIFY ME</button>
        </form>
        <div class="kt-done" style="font-size:24px;">Thank you. You'll hear once.</div>
        <div style="font-family:'IBM Plex Mono',monospace;font-size:11px;letter-spacing:0.05em;color:#ADA090;">NO TRACKING · UNSUBSCRIBE ANY TIME</div>
      </div>
    </section>
  </main>

  <footer style="max-width:1040px;margin:0 auto;padding:28px 24px 48px;border-top:1px solid #DBD2C3;display:flex;justify-content:space-between;gap:16px;flex-wrap:wrap;font-size:16px;line-height:1.5;color:#655A4E;">
    <div style="max-width:520px;">Designed and built by <a href="/about/">Aaron</a>. A sibling to <a href="/tools/holdfast/">Holdfast</a> and <a href="/tools/still-dark/">Still Dark</a>.</div>
    <nav style="display:flex;flex-wrap:wrap;gap:20px;align-items:center;font-family:'IBM Plex Mono',monospace;font-size:12px;letter-spacing:0.05em;">
      <a href="/tools/kitchen-table/privacy/">PRIVACY</a>
      <a href="/tools/kitchen-table/support/">SUPPORT</a>
      <a href="https://cloudbase.day/notes/aaron/kitchen_table" target="_blank" rel="noopener noreferrer">RELEASE NOTES</a>
    </nav>
    <div style="font-style:italic;font-size:17px;">Decided at the kitchen table.</div>
  </footer>
</div>
