---
layout: kitchentable
title: Kitchen Table · What we decided
permalink: /tools/kitchen-table/
description: An iPhone app for writing down what we decided at home, so we stop deciding it twice. Two lines to capture, shared between two iCloud accounts, settled things in order, never by date, and a separate money plan you take one step at a time. A Tidy app.
image:
  path: /assets/img/kitchentable/og.png
  width: 1200
  height: 630
theme_color: "#FAF5EC"
author: aaron
---

<meta name="theme-color" content="#FAF5EC" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#1B1714" media="(prefers-color-scheme: dark)">
<style>
@import url('https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,300..600;1,6..72,300..500&family=IBM+Plex+Mono:wght@400;500;600&display=swap');
:root { --kt-icon-bg:#FAF5EC; --kt-icon-rule:#38302A; --kt-icon-accent:#A85331; --kt-icon-edge:rgba(56,48,42,0.08); --kt-bg:#FAF5EC; --kt-raise:#FFFDF7; --kt-sunk:#F2EBDF; --kt-rule:#E1D8C9; --kt-ink:#38302A; --kt-body:#4A4138; --kt-meta:#655A4E; --kt-rust:#A85331; --kt-rust-tint:#FDF0E4; --kt-rust-line:#E9DACA; --kt-sage:#4A7256; --kt-inv-bg:#38302A; --kt-inv-ink:#FAF5EC; --kt-inv-meta:#C3B8A9; --kt-inv-field:#2C2621; --kt-shadow:rgba(56,48,42,0.16); color-scheme: light; }
@media (prefers-color-scheme: dark) { :root:not([data-kt-theme="light"]) { --kt-icon-bg:#1C1815; --kt-icon-rule:#F1E9DC; --kt-icon-accent:#D9784F; --kt-icon-edge:rgba(241,233,220,0.08); --kt-bg:#1B1714; --kt-raise:#25201C; --kt-sunk:#15120F; --kt-rule:#3A332C; --kt-ink:#F1EADF; --kt-body:#D2C8BA; --kt-meta:#A89B8C; --kt-rust:#E39068; --kt-rust-tint:#3A251B; --kt-rust-line:#5A3A2B; --kt-sage:#8DB89A; --kt-inv-bg:#2A241F; --kt-inv-ink:#F1EADF; --kt-inv-meta:#A89B8C; --kt-inv-field:#1B1714; --kt-shadow:rgba(0,0,0,0.5); color-scheme: dark; } }
:root[data-kt-theme="dark"] { --kt-icon-bg:#1C1815; --kt-icon-rule:#F1E9DC; --kt-icon-accent:#D9784F; --kt-icon-edge:rgba(241,233,220,0.08); --kt-bg:#1B1714; --kt-raise:#25201C; --kt-sunk:#15120F; --kt-rule:#3A332C; --kt-ink:#F1EADF; --kt-body:#D2C8BA; --kt-meta:#A89B8C; --kt-rust:#E39068; --kt-rust-tint:#3A251B; --kt-rust-line:#5A3A2B; --kt-sage:#8DB89A; --kt-inv-bg:#2A241F; --kt-inv-ink:#F1EADF; --kt-inv-meta:#A89B8C; --kt-inv-field:#1B1714; --kt-shadow:rgba(0,0,0,0.5); color-scheme: dark; }
html { scroll-behavior: smooth; }
body { margin: 0; padding: 0; max-width: none; display: block; background: var(--kt-bg); -webkit-font-smoothing: antialiased; }
.kt-page a { color: var(--kt-ink); text-underline-offset: 3px; }
.kt-page a:hover { color: var(--kt-rust); }
.kt-page input::placeholder { color: var(--kt-inv-meta); }

[data-tidy-notify].is-done .kt-form { display: none; }
[data-tidy-notify].is-done .kt-done { display: block !important; }
</style>

<div class="kt-page" style="background: var(--kt-bg); color: var(--kt-ink); font-family: Newsreader, Georgia, serif; min-height: 100vh;">

  <div style="max-width: 1040px; margin: 0 auto; padding: 22px 24px 0; display: flex; justify-content: space-between; align-items: center; font-family: 'IBM Plex Mono', monospace; font-size: 11px; letter-spacing: 0.08em; color: var(--kt-meta);">
    <a href="/tools/" style="color: var(--kt-meta); text-decoration: none;">‹ WORKBENCH</a>
    <div>A TIDY APP</div>
  </div>

  <header style="max-width: 1040px; margin: 0 auto; padding: 64px 24px 40px; display: flex; flex-direction: column; align-items: center; text-align: center; gap: 18px;">
    <div role="img" aria-label="Kitchen Table app icon" style="width: 88px; height: 88px; border-radius: 20px; background: var(--kt-icon-bg); box-shadow: 0 10px 24px var(--kt-shadow), 0 0 0 1px var(--kt-icon-edge); display: grid; place-items: center;">
      <div style="width: 53px; display: flex; flex-direction: column; gap: 7.3px;">
        <div style="height: 3.4px; background: var(--kt-icon-rule);"></div>
        <div style="height: 3.4px; background: var(--kt-icon-rule);"></div>
        <div style="height: 3.4px; width: 62%; background: var(--kt-icon-accent);"></div>
        <div style="height: 3.4px; background: var(--kt-icon-rule);"></div>
      </div>
    </div>
    <h1 style="margin: 6px 0 0; font-weight: 400; font-size: clamp(48px, 8vw, 76px); line-height: 1; letter-spacing: -0.015em;">Kitchen Table</h1>
    <div style="font-family: 'IBM Plex Mono', monospace; font-size: 11px; letter-spacing: 0.14em; color: var(--kt-meta);">IPHONE · FOR TWO · DECISIONS AND MONEY · NO DEADLINES</div>
    <p style="margin: 4px 0 0; font-size: clamp(22px, 3vw, 28px); line-height: 1.3; max-width: 540px; text-wrap: pretty;">What we decided, written down, so we stop deciding it twice.</p>
    <div style="display: flex; gap: 10px; flex-wrap: wrap; justify-content: center; margin-top: 8px;">
      <a href="#notify" style="height: 46px; padding: 0 22px; border-radius: 2px; background: var(--kt-rust); color: var(--kt-bg); text-decoration: none; display: flex; align-items: center; font-family: 'IBM Plex Mono', monospace; font-size: 12px; font-weight: 600; letter-spacing: 0.12em;">BETA SOON · GET A NOTE →</a>
      <a href="#how" style="height: 46px; padding: 0 22px; border-radius: 2px; border: 1px solid var(--kt-ink); color: var(--kt-ink); text-decoration: none; display: flex; align-items: center; box-sizing: border-box; font-family: 'IBM Plex Mono', monospace; font-size: 12px; letter-spacing: 0.12em;">HOW IT WORKS</a>
    </div>
    <div style="font-family: 'IBM Plex Mono', monospace; font-size: 11px; letter-spacing: 0.08em; color: var(--kt-meta);">PUBLIC TESTFLIGHT COMING SOON · iOS 18+</div>
    <div style="width: min(340px, 82vw); aspect-ratio: 402 / 874; margin-top: 28px; filter: drop-shadow(0 12px 24px var(--kt-shadow));">
      <img src="/assets/img/kitchentable/landing/phone-list.png" alt="Kitchen Table list: still deciding on top, settled below" style="width:100%;height:100%;display:block;border-radius:44px;">
    </div>
    <div style="font-size: 16px; font-style: italic; color: var(--kt-meta); max-width: 380px; line-height: 1.5;">One list. What we haven't settled sits on top.</div>
  </header>

  <main style="max-width: 1040px; margin: 0 auto; padding: 0 24px; display: flex; flex-direction: column;">

    <section style="padding: 72px 0; border-top: 1px solid var(--kt-rule); display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 300px), 1fr)); gap: 40px; align-items: start;">
      <div style="display: flex; flex-direction: column; gap: 16px;">
        <div style="font-family: 'IBM Plex Mono', monospace; font-size: 11px; letter-spacing: 0.14em; color: var(--kt-meta);">WHY IT EXISTS</div>
        <h2 style="margin: 0; font-weight: 400; font-size: clamp(32px, 4.4vw, 44px); line-height: 1.08; letter-spacing: -0.01em; text-wrap: pretty;">We'd already decided. <span style="font-style: italic;">Then we forgot.</span></h2>
      </div>
      <div style="display: flex; flex-direction: column; gap: 14px; font-size: 19px; line-height: 1.6; color: var(--kt-body); text-wrap: pretty;">
        <p style="margin: 0;">Most of what gets decided at home gets decided out loud: at the counter, in the driveway, halfway through dinner. Then it evaporates. A few weeks later we're having the same conversation, a little less sure what we said the first time.</p>
        <p style="margin: 0;">That's always frustrated me. Kitchen Table is where those three sentences go before they're gone. The new mattress, the back tree, the couches. Not the purchase, just what we agreed.</p>
      </div>
    </section>

    <section id="how" style="padding: 72px 0; border-top: 1px solid var(--kt-rule); display: flex; flex-direction: column; gap: 32px;">
      <div style="display: flex; flex-direction: column; gap: 14px; max-width: 640px;">
        <div style="font-family: 'IBM Plex Mono', monospace; font-size: 11px; letter-spacing: 0.14em; color: var(--kt-meta);">HOW IT WORKS</div>
        <h2 style="margin: 0; font-weight: 400; font-size: clamp(32px, 4.4vw, 44px); line-height: 1.08; letter-spacing: -0.01em;">Write it down. <span style="font-style: italic;">Find it later.</span></h2>
      </div>
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 230px), 1fr)); gap: 0 28px;">
        <div style="border-top: 1px solid var(--kt-ink); padding-top: 16px; padding-bottom: 20px; display: flex; flex-direction: column; gap: 10px;">
          <div style="font-family: 'IBM Plex Mono', monospace; font-size: 13px; font-weight: 500; color: var(--kt-meta);">01</div>
          <div style="font-size: 25px; line-height: 1.15;">Two lines, then save.</div>
          <div style="font-size: 17px; line-height: 1.55; color: var(--kt-body);">A title and what we decided. About fifteen seconds. Cost, who, why and photos can come later.</div>
        </div>
        <div style="border-top: 1px solid var(--kt-ink); padding-top: 16px; padding-bottom: 20px; display: flex; flex-direction: column; gap: 10px;">
          <div style="font-family: 'IBM Plex Mono', monospace; font-size: 13px; font-weight: 500; color: var(--kt-rust);">02</div>
          <div style="font-size: 25px; line-height: 1.15;">Unsettled stays on top.</div>
          <div style="font-size: 17px; line-height: 1.55; color: var(--kt-body);">The things we're still deciding are the ones we forget fastest, so they're the first thing you see.</div>
        </div>
        <div style="border-top: 1px solid var(--kt-ink); padding-top: 16px; padding-bottom: 20px; display: flex; flex-direction: column; gap: 10px;">
          <div style="font-family: 'IBM Plex Mono', monospace; font-size: 13px; font-weight: 500; color: var(--kt-sage);">03</div>
          <div style="font-size: 25px; line-height: 1.15;">Shared between you.</div>
          <div style="font-size: 17px; line-height: 1.55; color: var(--kt-body);">Either of you can add or change anything, from your own phone. Search finds what we said about the couch in a few letters.</div>
        </div>
      </div>
    </section>

    <section style="padding: 72px 0; border-top: 1px solid var(--kt-rule); display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 320px), 1fr)); gap: 48px; align-items: center;">
      <div style="display: flex; flex-direction: column; gap: 16px;">
        <div style="font-family: 'IBM Plex Mono', monospace; font-size: 11px; letter-spacing: 0.14em; color: var(--kt-meta);">THE FIFTEEN SECONDS</div>
        <h2 style="margin: 0; font-weight: 400; font-size: clamp(32px, 4.4vw, 44px); line-height: 1.08; letter-spacing: -0.01em;">Nothing stands <span style="font-style: italic;">between you and save.</span></h2>
        <p style="margin: 0; font-size: 19px; line-height: 1.6; color: var(--kt-body); text-wrap: pretty;">The keyboard is up when it opens. Write the title, write what we decided, tap save. If there's more worth keeping, tap to add it. Nothing is required past the first two lines.</p>
        <div style="display: flex; flex-wrap: wrap; gap: 8px; margin-top: 4px;">
          <div style="font-family: 'IBM Plex Mono', monospace; font-size: 11px; letter-spacing: 0.1em; padding: 7px 11px; border-radius: 2px; border: 1px solid var(--kt-rule); color: var(--kt-meta);">+ WHY</div>
          <div style="font-family: 'IBM Plex Mono', monospace; font-size: 11px; letter-spacing: 0.1em; padding: 7px 11px; border-radius: 2px; border: 1px solid var(--kt-rust); color: var(--kt-rust); background: var(--kt-rust-tint);">+ COST</div>
          <div style="font-family: 'IBM Plex Mono', monospace; font-size: 11px; letter-spacing: 0.1em; padding: 7px 11px; border-radius: 2px; border: 1px solid var(--kt-rule); color: var(--kt-meta);">+ WHO</div>
          <div style="font-family: 'IBM Plex Mono', monospace; font-size: 11px; letter-spacing: 0.1em; padding: 7px 11px; border-radius: 2px; border: 1px solid var(--kt-rule); color: var(--kt-meta);">+ PHOTO</div>
        </div>
      </div>
      <div style="display: flex; justify-content: center;">
        <div style="width: min(300px, 78vw); aspect-ratio: 402 / 874; filter: drop-shadow(0 12px 24px var(--kt-shadow));">
          <img src="/assets/img/kitchentable/landing/phone-capture.png" alt="New decision: title, a line, optional fields" style="width:100%;height:100%;display:block;border-radius:44px;">
        </div>
      </div>
    </section>

    <section style="padding: 72px 0; border-top: 1px solid var(--kt-rule); display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 320px), 1fr)); gap: 48px; align-items: center;">
      <div style="display: flex; justify-content: center;">
        <div style="width: min(300px, 78vw); aspect-ratio: 402 / 874; filter: drop-shadow(0 12px 24px var(--kt-shadow));">
          <img src="/assets/img/kitchentable/landing/phone-order.png" alt="Settled decisions in order, 01 02 03" style="width:100%;height:100%;display:block;border-radius:44px;">
        </div>
      </div>
      <div style="display: flex; flex-direction: column; gap: 16px;">
        <div style="font-family: 'IBM Plex Mono', monospace; font-size: 11px; letter-spacing: 0.14em; color: var(--kt-meta);">ORDER, NOT DATES</div>
        <h2 style="margin: 0; font-weight: 400; font-size: clamp(32px, 4.4vw, 44px); line-height: 1.08; letter-spacing: -0.01em;">What comes next, <span style="font-style: italic;">not when.</span></h2>
        <p style="margin: 0; font-size: 19px; line-height: 1.6; color: var(--kt-body); text-wrap: pretty;">Dates slip. A list built on deadlines turns into a list of things you're late on, and that's the last thing a house needs.</p>
        <p style="margin: 0; font-size: 19px; line-height: 1.6; color: var(--kt-body); text-wrap: pretty;">Settled decisions just hold their place in line. Drag one, or nudge it up or down, as life rearranges itself. Add a date if it helps; nothing depends on it.</p>
        <div style="display: flex; flex-direction: column; margin-top: 6px; border-bottom: 1px solid var(--kt-rule);">
          <div style="display: grid; grid-template-columns: 34px 1fr auto; gap: 8px; align-items: baseline; padding: 12px 0; border-top: 1px solid var(--kt-rule);">
            <div style="font-family: 'IBM Plex Mono', monospace; font-size: 13px; font-weight: 500; color: var(--kt-meta);">01</div>
            <div style="font-size: 20px;">The mattress</div>
            <div style="font-family: 'IBM Plex Mono', monospace; font-size: 10.5px; letter-spacing: 0.1em; color: var(--kt-meta);">DECIDED</div>
          </div>
          <div style="display: grid; grid-template-columns: 34px 1fr auto; gap: 8px; align-items: baseline; padding: 12px 0; border-top: 1px solid var(--kt-rule);">
            <div style="font-family: 'IBM Plex Mono', monospace; font-size: 13px; font-weight: 500; color: var(--kt-meta);">02</div>
            <div style="font-size: 20px;">Kitchen faucet</div>
            <div style="font-family: 'IBM Plex Mono', monospace; font-size: 10.5px; letter-spacing: 0.1em; color: var(--kt-meta);">DECIDED</div>
          </div>
          <div style="display: grid; grid-template-columns: 34px 1fr auto; gap: 8px; align-items: baseline; padding: 12px 0; border-top: 1px solid var(--kt-rule);">
            <div style="font-family: 'IBM Plex Mono', monospace; font-size: 13px; font-weight: 500; color: var(--kt-meta);">03</div>
            <div style="font-size: 20px;">Storm door</div>
            <div style="font-family: 'IBM Plex Mono', monospace; font-size: 10.5px; letter-spacing: 0.1em; color: var(--kt-meta);">DECIDED</div>
          </div>
        </div>
        <p style="margin: 0; font-size: 17px; line-height: 1.55; color: var(--kt-meta); font-style: italic; text-wrap: pretty;">Mark something Done and it moves to a dated shelf at the bottom. Everything behind it moves up a number.</p>
      </div>
    </section>

    <section style="padding: 72px 0; border-top: 1px solid var(--kt-rule); display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 320px), 1fr)); gap: 48px; align-items: center;">
      <div style="display: flex; flex-direction: column; gap: 16px;">
        <div style="font-family: 'IBM Plex Mono', monospace; font-size: 11px; letter-spacing: 0.14em; color: var(--kt-meta);">MONTHS LATER</div>
        <h2 style="margin: 0; font-weight: 400; font-size: clamp(32px, 4.4vw, 44px); line-height: 1.08; letter-spacing: -0.01em;">Did it <span style="font-style: italic;">hold up?</span></h2>
        <p style="margin: 0; font-size: 19px; line-height: 1.6; color: var(--kt-body); text-wrap: pretty;">Eight months after something's decided or done, Kitchen Table brings it back once and asks. Write a line and it joins the record, so next time we know whether we got it right.</p>
        <p style="margin: 0; font-size: 19px; line-height: 1.6; color: var(--kt-body); text-wrap: pretty;">Wave it off and it's gone for good. No ratings, no scores, no asking twice.</p>
      </div>
      <div style="display: flex; justify-content: center;">
        <div style="width: min(380px, 100%); background: var(--kt-raise); border: 1px solid var(--kt-rust-line); border-radius: 3px; padding: 22px 22px 20px; box-sizing: border-box; box-shadow: 0 12px 30px var(--kt-shadow);">
          <div style="font-family: 'IBM Plex Mono', monospace; font-size: 10.5px; letter-spacing: 0.16em; color: var(--kt-rust);">EIGHT MONTHS ON</div>
          <div style="font-size: 24px; line-height: 1.25; margin: 10px 0 4px;">The mattress</div>
          <div style="font-size: 17px; line-height: 1.5; color: var(--kt-body);">Did it hold up? One line is plenty.</div>
          <div style="font-size: 19px; font-style: italic; color: var(--kt-ink); padding: 14px 0 9px; margin-top: 6px; border-bottom: 1px solid var(--kt-rule);">Firm was right. One step firmer next time.</div>
          <div style="display: flex; gap: 10px; margin-top: 16px; align-items: center;">
            <div style="font-family: 'IBM Plex Mono', monospace; font-size: 11px; font-weight: 600; letter-spacing: 0.12em; padding: 9px 16px; border-radius: 2px; background: var(--kt-rust); color: var(--kt-bg);">APPEND IT</div>
            <div style="font-family: 'IBM Plex Mono', monospace; font-size: 11px; letter-spacing: 0.12em; padding: 9px 12px; color: var(--kt-meta);">NEVER MIND</div>
          </div>
        </div>
      </div>
    </section>

    <section style="padding: 72px 0; border-top: 1px solid var(--kt-rule); display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 320px), 1fr)); gap: 48px; align-items: center;">
      <div style="display: flex; flex-direction: column; gap: 16px;">
        <div style="font-family: 'IBM Plex Mono', monospace; font-size: 11px; letter-spacing: 0.14em; color: var(--kt-meta);">MONEY, IN ITS OWN PLACE</div>
        <h2 style="margin: 0; font-weight: 400; font-size: clamp(32px, 4.4vw, 44px); line-height: 1.08; letter-spacing: -0.01em; text-wrap: pretty;">A money plan is a sequence. <span style="font-style: italic;">One step at a time.</span></h2>
        <p style="margin: 0; font-size: 19px; line-height: 1.6; color: var(--kt-body); text-wrap: pretty;">After a money meeting you don't have a list of decisions. You have an order: this first, then that. Money gets its own tab, kept apart from everything else.</p>
        <p style="margin: 0; font-size: 19px; line-height: 1.6; color: var(--kt-body); text-wrap: pretty;">One step is Now. The rest wait their turn. Finish one and the next moves up. Some steps never finish, like retirement, so once they start they stay on for good.</p>
        <p style="margin: 0; font-size: 17px; line-height: 1.55; color: var(--kt-meta); font-style: italic; text-wrap: pretty;">No bank links, no balances, no budgets. A target is a note you type, if you want one.</p>
      </div>
      <div style="display: flex; justify-content: center;">
        <div style="width: min(380px, 100%); background: var(--kt-raise); border: 1px solid var(--kt-rule); border-radius: 3px; box-sizing: border-box; box-shadow: 0 12px 30px var(--kt-shadow); padding: 20px 0 18px; display: flex; flex-direction: column;">
          <div style="display: flex; justify-content: space-between; align-items: baseline; padding: 0 20px 14px;">
            <div style="font-size: 24px; line-height: 1.15;">Our money plan</div>
            <div style="font-family: 'IBM Plex Mono', monospace; font-size: 10.5px; letter-spacing: 0.12em; color: var(--kt-ink); border-bottom: 1.5px solid var(--kt-rust); padding-bottom: 3px;">MONEY</div>
          </div>
          <div style="font-family: 'IBM Plex Mono', monospace; font-size: 10px; letter-spacing: 0.16em; color: var(--kt-rust); padding: 0 20px 6px;">NOW</div>
          <div style="padding: 12px 20px 14px; background: var(--kt-rust-tint); box-shadow: inset 3px 0 0 var(--kt-rust); border-top: 1px solid var(--kt-rule); display: flex; flex-direction: column; gap: 10px;">
            <div style="display: flex; gap: 10px; align-items: baseline;">
              <div style="font-family: 'IBM Plex Mono', monospace; font-size: 12px; font-weight: 500; color: var(--kt-rust);">01</div>
              <div style="font-size: 23px; line-height: 1.15;">Debt free</div>
            </div>
            <div style="height: 3px; background: var(--kt-rule);"><div style="height: 3px; width: 62%; background: var(--kt-rust);"></div></div>
            <div style="align-self: flex-start; font-family: 'IBM Plex Mono', monospace; font-size: 10.5px; font-weight: 600; letter-spacing: 0.12em; padding: 7px 12px; border-radius: 2px; border: 1px solid var(--kt-rust); color: var(--kt-rust);">WE DID IT</div>
          </div>
          <div style="font-family: 'IBM Plex Mono', monospace; font-size: 10px; letter-spacing: 0.16em; color: var(--kt-meta); padding: 16px 20px 4px;">THEN</div>
          <div style="display: grid; grid-template-columns: 30px 1fr auto; gap: 6px; align-items: baseline; padding: 10px 20px; border-top: 1px solid var(--kt-rule);">
            <div style="font-family: 'IBM Plex Mono', monospace; font-size: 12px; font-weight: 500; color: var(--kt-meta);">02</div>
            <div style="font-size: 18.5px;">401k and Roth</div>
            <div style="font-family: 'IBM Plex Mono', monospace; font-size: 10px; letter-spacing: 0.1em; color: var(--kt-sage);">∞ FOREVER</div>
          </div>
          <div style="display: grid; grid-template-columns: 30px 1fr auto; gap: 6px; align-items: baseline; padding: 10px 20px; border-top: 1px solid var(--kt-rule);">
            <div style="font-family: 'IBM Plex Mono', monospace; font-size: 12px; font-weight: 500; color: var(--kt-meta);">03</div>
            <div style="font-size: 18.5px;">Three months in savings</div>
            <div></div>
          </div>
          <div style="display: grid; grid-template-columns: 30px 1fr auto; gap: 6px; align-items: baseline; padding: 10px 20px; border-top: 1px solid var(--kt-rule); border-bottom: 1px solid var(--kt-rule);">
            <div style="font-family: 'IBM Plex Mono', monospace; font-size: 12px; font-weight: 500; color: var(--kt-meta);">04</div>
            <div style="font-size: 18.5px;">New car fund</div>
            <div></div>
          </div>
          <div style="display: flex; justify-content: space-between; gap: 10px; padding: 14px 20px 0; font-family: 'IBM Plex Mono', monospace; font-size: 10px; letter-spacing: 0.08em;">
            <div style="color: var(--kt-meta);">LAST MONEY MEETING · OCT 18</div>
            <div style="color: var(--kt-rust);">WE MET AGAIN</div>
          </div>
        </div>
      </div>
    </section>
    <section style="padding: 0 0 72px; display: flex; flex-wrap: wrap; justify-content: center; gap: 40px;">
      <div style="display: flex; flex-direction: column; align-items: center; gap: 12px;">
        <div style="width: min(280px, 78vw); aspect-ratio: 402 / 874; filter: drop-shadow(0 12px 24px var(--kt-shadow));">
          <img src="/assets/img/kitchentable/landing/phone-money-plan.png" alt="Our money plan: one step Now, the rest in order" style="width:100%;height:100%;display:block;border-radius:40px;">
        </div>
        <div style="font-size: 16px; font-style: italic; color: var(--kt-meta);">The plan, in order.</div>
      </div>
      <div style="display: flex; flex-direction: column; align-items: center; gap: 12px;">
        <div style="width: min(280px, 78vw); aspect-ratio: 402 / 874; filter: drop-shadow(0 12px 24px var(--kt-shadow));">
          <img src="/assets/img/kitchentable/landing/phone-money-always.png" alt="Always on and behind us: forever steps and finished ones" style="width:100%;height:100%;display:block;border-radius:40px;">
        </div>
        <div style="font-size: 16px; font-style: italic; color: var(--kt-meta);">What's always on, and what's behind us.</div>
      </div>
    </section>


    <section style="padding: 72px 0; border-top: 1px solid var(--kt-rule); display: flex; flex-direction: column; gap: 32px;">
      <div style="display: flex; flex-direction: column; gap: 14px; max-width: 640px;">
        <div style="font-family: 'IBM Plex Mono', monospace; font-size: 11px; letter-spacing: 0.14em; color: var(--kt-meta);">ON PURPOSE</div>
        <h2 style="margin: 0; font-weight: 400; font-size: clamp(32px, 4.4vw, 44px); line-height: 1.08; letter-spacing: -0.01em;">What it <span style="font-style: italic;">leaves out.</span></h2>
        <p style="margin: 0; font-size: 19px; line-height: 1.6; color: var(--kt-body); text-wrap: pretty;">It's a record of the conversation, not a system for running a house. Everything here was left out deliberately.</p>
      </div>
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 230px), 1fr)); gap: 0 28px;">
        <div style="border-top: 1px solid var(--kt-rule); padding: 14px 0 18px; display: flex; flex-direction: column; gap: 4px;"><div style="font-size: 20px;">No budgets or totals.</div><div style="font-size: 16.5px; line-height: 1.5; color: var(--kt-body);">Costs and money targets are notes you type, not a ledger.</div></div>
        <div style="border-top: 1px solid var(--kt-rule); padding: 14px 0 18px; display: flex; flex-direction: column; gap: 4px;"><div style="font-size: 20px;">No categories.</div><div style="font-size: 16.5px; line-height: 1.5; color: var(--kt-body);">One list and a search box. Nothing to file.</div></div>
        <div style="border-top: 1px solid var(--kt-rule); padding: 14px 0 18px; display: flex; flex-direction: column; gap: 4px;"><div style="font-size: 20px;">No due dates.</div><div style="font-size: 16.5px; line-height: 1.5; color: var(--kt-body);">Nothing turns red. Nothing is overdue.</div></div>
        <div style="border-top: 1px solid var(--kt-rule); padding: 14px 0 18px; display: flex; flex-direction: column; gap: 4px;"><div style="font-size: 20px;">No accounts.</div><div style="font-size: 16.5px; line-height: 1.5; color: var(--kt-body);">No sign-up, no ads, no tracking. Your iCloud is the account.</div></div>
      </div>
    </section>

    <section style="padding: 72px 0; border-top: 1px solid var(--kt-rule);">
      <div style="display: flex; flex-direction: column; gap: 16px; max-width: 680px;">
        <div style="font-family: 'IBM Plex Mono', monospace; font-size: 11px; letter-spacing: 0.14em; color: var(--kt-meta);">FOR TWO</div>
        <h2 style="margin: 0; font-weight: 400; font-size: clamp(32px, 4.4vw, 44px); line-height: 1.08; letter-spacing: -0.01em;">Either of you <span style="font-style: italic;">can write it down.</span></h2>
        <p style="margin: 0; font-size: 19px; line-height: 1.6; color: var(--kt-body); text-wrap: pretty;">Send an invite from the list and it becomes one shared list, edited from two phones and two iCloud accounts. Whoever is holding a phone when the conversation ends writes it down, and the other sees it.</p>
      </div>
    </section>

    <section style="padding: 72px 0; border-top: 1px solid var(--kt-rule);">
      <div style="display: flex; flex-direction: column; gap: 16px; max-width: 680px;">
        <div style="font-family: 'IBM Plex Mono', monospace; font-size: 11px; letter-spacing: 0.14em; color: var(--kt-meta);">YOUR DATA</div>
        <h2 style="margin: 0; font-weight: 400; font-size: clamp(32px, 4.4vw, 44px); line-height: 1.08; letter-spacing: -0.01em;">It lives <span style="font-style: italic;">in your iCloud.</span></h2>
        <p style="margin: 0; font-size: 19px; line-height: 1.6; color: var(--kt-body); text-wrap: pretty;">There's no server of mine in the middle. Only the people you invite can see it.</p>
        <p style="margin: 0; font-size: 19px; line-height: 1.6; color: var(--kt-body); text-wrap: pretty;">Keep a copy whenever you like: every decision, photos included, as one file in Files. Restoring only adds what's missing, so it's safe to run twice.</p>
      </div>
    </section>

    <section id="notify" data-tidy-notify="" data-app="kitchentable" data-endpoint="https://email.aaronaiken.me/subscribe" style="margin: 24px 0 72px; background: var(--kt-inv-bg); color: var(--kt-inv-ink); border-radius: 3px; padding: clamp(28px, 5vw, 56px); display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 300px), 1fr)); gap: 32px; align-items: end;">
      <div style="display: flex; flex-direction: column; gap: 14px;">
        <div style="font-family: 'IBM Plex Mono', monospace; font-size: 11px; letter-spacing: 0.14em; color: var(--kt-inv-meta);">COMING SOON</div>
        <h2 style="margin: 0; font-weight: 400; font-size: clamp(30px, 4vw, 40px); line-height: 1.1;">Hear when the beta opens.</h2>
        <p style="margin: 0; font-size: 18px; line-height: 1.55; color: var(--kt-inv-meta);">A public beta on TestFlight is days away. Leave an address and you'll get a note when it opens, and one more at launch.</p>
      </div>
      <div style="display: flex; flex-direction: column; gap: 10px;">
        <form class="kt-form" style="display: flex; gap: 8px; flex-wrap: wrap;">
          <input type="email" name="email" required="" autocomplete="email" placeholder="you@example.com" aria-label="Email address" style="flex: 1 1 220px; min-width: 0; height: 50px; padding: 0 16px; border-radius: 2px; border: 1px solid var(--kt-inv-meta); background: var(--kt-inv-field); color: var(--kt-inv-ink); font: 17px Newsreader, Georgia, serif; outline: none; box-sizing: border-box;">
          <button type="submit" style="height: 50px; padding: 0 20px; border-radius: 2px; border: none; background: var(--kt-inv-ink); color: var(--kt-inv-bg); font-family: 'IBM Plex Mono', monospace; font-size: 12px; font-weight: 600; letter-spacing: 0.12em; cursor: pointer;">NOTIFY ME</button>
        </form>
        <div class="kt-done" style="display: none; font-size: 24px;">Written down. You'll hear once.</div>
        <div style="font-family: 'IBM Plex Mono', monospace; font-size: 11px; letter-spacing: 0.08em; color: var(--kt-inv-meta);">TWO NOTES, TOPS · NO TRACKING · LEAVE ANY TIME</div>
      </div>
    </section>
  </main>

  <footer style="max-width: 1040px; margin: 0 auto; padding: 28px 24px 48px; border-top: 1px solid var(--kt-rule); display: flex; justify-content: space-between; gap: 16px; flex-wrap: wrap; font-size: 16px; line-height: 1.5; color: var(--kt-meta);">
    <div style="max-width: 540px;">Designed and built by <a href="/about/">Aaron</a> at a kitchen table in Harrisburg. One of the <a href="/tidyapps/">Tidy apps</a>.</div>
    <div style="display: flex; flex-direction: column; gap: 6px; align-items: flex-end;">
      <div style="font-style: italic; font-size: 17px;">Write it down once.</div>
      <div style="display: flex; gap: 18px; font-family: 'IBM Plex Mono', monospace; font-size: 11px; letter-spacing: 0.1em;">
        <a href="/tools/kitchen-table/support/">SUPPORT</a>
        <a href="/tools/kitchen-table/privacy/">PRIVACY</a>
      </div>
    </div>
  </footer>
</div>
