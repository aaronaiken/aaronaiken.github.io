---
layout: stilldark
title: Still Dark · A prayer journal
permalink: /tools/still-dark/
description: A prayer journal for Mac and iPhone. One page, one caret, nothing in the margins. Encrypted end to end and synced only between your own devices — no account, no server anyone can read. Paid once.
image:
  path: /assets/img/stilldark/og.png
  width: 1200
  height: 630
theme_color: "#0D0B0A"
author: aaron
---

<style>
@import url('https://fonts.googleapis.com/css2?family=EB+Garamond:ital,wght@0,400;0,500;1,400&family=IBM+Plex+Sans:wght@300;400&family=IBM+Plex+Mono:wght@400&display=swap');
html { scroll-behavior: smooth; }
/* The global stylesheet pins body to max-width:960px with side padding (and flex),
   which left-anchors the page. Reset to full-bleed for this page only; the page's own
   flex column centers each 1080px section. */
body { margin: 0; padding: 0; max-width: none; display: block;
       background: #0D0B0A; -webkit-font-smoothing: antialiased; }
.sd-page a { color: #C79F6E; text-decoration: none; }
.sd-page a:hover { color: #E2BB8C; }
.sd-page input::placeholder { color: #8A7258; }
@keyframes sd-blink { 0%, 46% { opacity: 1 } 50%, 96% { opacity: 0 } 100% { opacity: 1 } }
@media (prefers-reduced-motion: reduce) {
  .sd-page [style*="sd-blink"] { animation: none !important; opacity: 1 !important; }
}
.sd-done { display: none; }
[data-tidy-notify].is-done .sd-form { display: none; }
[data-tidy-notify].is-done .sd-done { display: block; }
</style>

<div class="sd-page" style="background:#0d0b0a;color:#bda186;font-family:'IBM Plex Sans',system-ui,sans-serif;font-weight:300;display:flex;flex-direction:column;align-items:center;padding:0 24px;">

  <nav style="width:100%;max-width:1080px;display:flex;justify-content:space-between;align-items:center;padding:22px 0;font-family:'IBM Plex Mono',monospace;font-size:11px;letter-spacing:0.16em;text-transform:uppercase;">
    <a href="/tools/" style="color:#9a8168;">← Workbench</a>
    <span style="color:#9a8168;">A Tidy app</span>
  </nav>

  <header style="background:#0d0b0a;width:100%;max-width:1080px;display:flex;flex-direction:column;align-items:center;text-align:center;gap:22px;padding:56px 0 40px;">
    <img src="/assets/img/stilldark/landing/app-icon.png" alt="Still Dark app icon" style="width:88px;height:88px;border-radius:20px;box-shadow:0 16px 32px -14px #000,inset 0 1px 0 rgba(199,159,110,0.11);">
    <h1 style="font-family:'EB Garamond',serif;font-weight:400;font-size:clamp(52px,8vw,84px);line-height:1;color:#d9b483;margin:0;">Still Dark</h1>
    <div style="font-family:'IBM Plex Mono',monospace;font-size:11px;letter-spacing:0.18em;text-transform:uppercase;color:#9a8168;">Prayer journal · Mac &amp; iPhone · Paid once</div>
    <p style="margin:0;max-width:30ch;font-family:'EB Garamond',serif;font-weight:400;font-size:clamp(22px,2.6vw,27px);line-height:1.45;color:#c79f6e;text-wrap:balance;">A prayer journal that waits in the dark. One page, one caret, nothing in the margins.</p>
    <div style="display:flex;flex-wrap:wrap;justify-content:center;gap:12px;margin-top:6px;">
      <a href="https://testflight.apple.com/join/CPjjmV97" target="_blank" rel="noopener noreferrer" style="display:flex;align-items:center;height:44px;padding:0 22px;border-radius:22px;background:#c79f6e;color:#12100e;font-size:14px;font-weight:400;">Join the beta →</a>
      <a href="#page" style="display:flex;align-items:center;height:44px;padding:0 22px;border-radius:22px;border:1px solid #4a3b2d;color:#c79f6e;font-size:14px;font-weight:400;">See the page</a>
    </div>
    <div style="font-family:'IBM Plex Mono',monospace;font-size:11px;letter-spacing:0.16em;text-transform:uppercase;color:#9a8168;">Now in open beta · Mac &amp; iPhone · Paid once at launch</div>
  </header>

  <section id="page" style="background:#0d0b0a;width:100%;max-width:1080px;display:flex;flex-direction:column;align-items:center;gap:18px;padding-bottom:96px;">
    <div style="width:100%;border-radius:12px;border:1px solid #2a221c;background:#12100e;overflow:hidden;box-shadow:0 60px 120px -60px #000,0 0 0 1px #0a0908;">
      <div style="height:28px;display:flex;align-items:center;gap:8px;padding:0 12px;background:#110f0d;border-bottom:1px solid #1d1814;">
        <div style="width:11px;height:11px;border-radius:6px;background:#2a221c;"></div>
        <div style="width:11px;height:11px;border-radius:6px;background:#2a221c;"></div>
        <div style="width:11px;height:11px;border-radius:6px;background:#2a221c;"></div>
      </div>
      <div style="container-type:size;aspect-ratio:16/10;width:100%;position:relative;display:flex;justify-content:center;">
        <div style="width:48cqw;font-weight:300;font-size:1.62cqw;line-height:2.05;color:#bda186;display:flex;flex-direction:column;position:absolute;top:50cqh;transform:translateY(-100%);">
          <div style="opacity:0.28;">It is still dark and the house is quiet. I woke before the alarm</div>
          <div style="opacity:0.38;">again and I am not sure whether that is a gift or just the age I</div>
          <div style="opacity:0.5;">am. Either way I am up, so: here.</div>
          <div style="opacity:0.5;">&nbsp;</div>
          <div style="opacity:0.72;">For my father, who goes in on Tuesday. I have been carrying it</div>
          <div style="opacity:0.86;">around all week like something in a coat pocket and I keep</div>
          <div style="display:flex;align-items:baseline;color:#d9b483;">
            <span>putting my hand in to check it is still</span>
            <span style="display:inline-block;width:0.16cqw;height:2.1cqw;background:#e2bb8c;margin-left:0.25cqw;transform:translateY(0.35cqw);animation:sd-blink 1.2s step-end infinite;box-shadow:0 0 2cqw 0.35cqw rgba(226,187,140,0.16);"></span>
          </div>
        </div>
        <div style="position:absolute;left:0;right:0;top:0;height:22cqh;background:linear-gradient(#12100e,rgba(18,16,14,0));"></div>
      </div>
    </div>
    <p style="margin:0;font-size:14px;color:#9a8168;text-align:center;">The whole app. The line you're writing never moves.</p>
  </section>

  <section style="background:#0d0b0a;width:100%;max-width:1080px;display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:40px 72px;padding:72px 0;border-top:1px solid #221c17;">
    <div style="display:flex;flex-direction:column;gap:16px;">
      <div style="font-family:'IBM Plex Mono',monospace;font-size:11px;letter-spacing:0.16em;text-transform:uppercase;color:#9a8168;">Why it exists</div>
      <h2 style="font-family:'EB Garamond',serif;font-weight:400;font-size:clamp(34px,4vw,44px);line-height:1.12;color:#d9b483;margin:0;">A room, <em style="font-style:italic;color:#c79f6e;">not a routine.</em></h2>
    </div>
    <div style="display:flex;flex-direction:column;gap:18px;font-size:16px;line-height:1.8;color:#ab9075;text-wrap:pretty;padding-top:30px;">
      <p style="margin:0;">Most journaling apps want to be opened every day. They count streaks, send reminders, and show you a grid of the days you missed. For prayer, that's exactly backwards.</p>
      <p style="margin:0;">Still Dark is one page and a blinking caret. You write, and at midnight the day seals and joins the record — read-only, because a prayer was prayed by who you were that morning.</p>
      <p style="margin:0;">Everything else was left out on purpose.</p>
    </div>
  </section>

  <section style="background:#0d0b0a;width:100%;max-width:1080px;display:flex;flex-direction:column;gap:36px;padding:72px 0;border-top:1px solid #221c17;">
    <div style="display:flex;flex-direction:column;gap:16px;">
      <div style="font-family:'IBM Plex Mono',monospace;font-size:11px;letter-spacing:0.16em;text-transform:uppercase;color:#9a8168;">How it's made</div>
      <h2 style="font-family:'EB Garamond',serif;font-weight:400;font-size:clamp(34px,4vw,44px);line-height:1.12;color:#d9b483;margin:0;">Built from <em style="font-style:italic;color:#c79f6e;">one verse.</em></h2>
      <p style="margin:0;max-width:60ch;font-family:'EB Garamond',serif;font-style:italic;font-size:20px;line-height:1.6;color:#ab9075;">“Very early in the morning, while it was still dark, Jesus got up, left the house and went off to a solitary place, where he prayed.” <span style="font-style:normal;color:#9a8168;">— Mark 1:35</span></p>
    </div>
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:14px;">
      <div style="background:#14110f;border:1px solid #221c17;border-radius:10px;padding:24px;display:flex;flex-direction:column;gap:12px;">
        <div style="font-family:'IBM Plex Mono',monospace;font-size:11px;color:#9a8168;">01</div>
        <div style="font-family:'EB Garamond',serif;font-size:23px;line-height:1.25;color:#d9b483;">While it was still dark</div>
        <div style="font-size:14px;line-height:1.7;color:#a68d73;text-wrap:pretty;">Warm amber on a brown-black, tuned for 5am and a dilated eye. The dimmest thing on your screen.</div>
      </div>
      <div style="background:#14110f;border:1px solid #221c17;border-radius:10px;padding:24px;display:flex;flex-direction:column;gap:12px;">
        <div style="font-family:'IBM Plex Mono',monospace;font-size:11px;color:#9a8168;">02</div>
        <div style="font-family:'EB Garamond',serif;font-size:23px;line-height:1.25;color:#d9b483;">Got up, left the house</div>
        <div style="font-size:14px;line-height:1.7;color:#a68d73;text-wrap:pretty;">No notifications, no widgets, no menu bar. You go to it. It never comes to you.</div>
      </div>
      <div style="background:#14110f;border:1px solid #221c17;border-radius:10px;padding:24px;display:flex;flex-direction:column;gap:12px;">
        <div style="font-family:'IBM Plex Mono',monospace;font-size:11px;color:#9a8168;">03</div>
        <div style="font-family:'EB Garamond',serif;font-size:23px;line-height:1.25;color:#d9b483;">A solitary place</div>
        <div style="font-size:14px;line-height:1.7;color:#a68d73;text-wrap:pretty;">No account, no sharing, no one else. Encrypted end to end between your own devices.</div>
      </div>
      <div style="background:#14110f;border:1px solid #221c17;border-radius:10px;padding:24px;display:flex;flex-direction:column;gap:12px;">
        <div style="font-family:'IBM Plex Mono',monospace;font-size:11px;color:#9a8168;">04</div>
        <div style="font-family:'EB Garamond',serif;font-size:23px;line-height:1.25;color:#d9b483;">There he prayed</div>
        <div style="font-size:14px;line-height:1.7;color:#a68d73;text-wrap:pretty;">One page. What you've prayed recedes above the line; what you're praying is the brightest thing in the room.</div>
      </div>
    </div>
  </section>

  <section style="background:#0d0b0a;width:100%;max-width:1080px;display:flex;flex-direction:column;gap:36px;padding:72px 0;border-top:1px solid #221c17;">
    <div style="display:flex;flex-direction:column;gap:16px;">
      <div style="font-family:'IBM Plex Mono',monospace;font-size:11px;letter-spacing:0.16em;text-transform:uppercase;color:#9a8168;">macOS</div>
      <h2 style="font-family:'EB Garamond',serif;font-weight:400;font-size:clamp(34px,4vw,44px);line-height:1.12;color:#d9b483;margin:0;">On the Mac, <em style="font-style:italic;color:#c79f6e;">the only lit thing.</em></h2>
      <p style="margin:0;max-width:58ch;font-size:16px;line-height:1.8;color:#ab9075;text-wrap:pretty;">Full screen by default and keyboard first. ⌘N for a new page, ⌘L to look back, Esc to return. There is no toolbar to learn because there is no toolbar.</p>
    </div>
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:24px;">
      <div style="display:flex;flex-direction:column;gap:12px;">
        <div style="border-radius:10px;border:1px solid #2a221c;background:#12100e;overflow:hidden;box-shadow:0 30px 60px -30px #000;">
          <div style="height:20px;display:flex;align-items:center;gap:6px;padding:0 9px;background:#110f0d;border-bottom:1px solid #1d1814;">
            <div style="width:8px;height:8px;border-radius:4px;background:#2a221c;"></div>
            <div style="width:8px;height:8px;border-radius:4px;background:#2a221c;"></div>
            <div style="width:8px;height:8px;border-radius:4px;background:#2a221c;"></div>
          </div>
          <div style="container-type:size;aspect-ratio:16/10;width:100%;display:flex;justify-content:center;">
            <div style="width:60cqw;padding-top:16cqh;display:flex;flex-direction:column;gap:4.2cqh;">
              <div style="font-family:'EB Garamond',serif;font-size:3.4cqw;color:#9a8168;letter-spacing:0.02em;">Thursday, 12 September</div>
              <div style="width:0.3cqw;height:5cqw;background:#c79f6e;animation:sd-blink 1.2s step-end infinite;box-shadow:0 0 3cqw 0.5cqw rgba(199,159,110,0.12);"></div>
            </div>
          </div>
        </div>
        <div style="display:flex;flex-direction:column;gap:4px;">
          <div style="font-family:'IBM Plex Mono',monospace;font-size:11px;letter-spacing:0.14em;text-transform:uppercase;color:#9a8168;">The page</div>
          <div style="font-size:14px;line-height:1.6;color:#a68d73;">Where it always opens. The date is the only chrome.</div>
        </div>
      </div>
      <div style="display:flex;flex-direction:column;gap:12px;">
        <div style="border-radius:10px;border:1px solid #2a221c;background:#12100e;overflow:hidden;box-shadow:0 30px 60px -30px #000;">
          <div style="height:20px;display:flex;align-items:center;gap:6px;padding:0 9px;background:#110f0d;border-bottom:1px solid #1d1814;">
            <div style="width:8px;height:8px;border-radius:4px;background:#2a221c;"></div>
            <div style="width:8px;height:8px;border-radius:4px;background:#2a221c;"></div>
            <div style="width:8px;height:8px;border-radius:4px;background:#2a221c;"></div>
          </div>
          <div style="container-type:size;aspect-ratio:16/10;width:100%;display:flex;justify-content:center;">
            <div style="width:64cqw;padding-top:10cqh;display:flex;flex-direction:column;gap:5cqh;">
              <div style="display:flex;flex-direction:column;gap:1cqh;">
                <div style="font-family:'EB Garamond',serif;font-size:3.1cqw;color:#d9b483;">Yesterday</div>
                <div style="font-size:2.5cqw;color:#b39a80;">For my father, who goes in on Tuesday.</div>
              </div>
              <div style="display:flex;flex-direction:column;gap:1cqh;">
                <div style="font-family:'EB Garamond',serif;font-size:3.1cqw;color:#a8875f;">Tuesday, 10 September</div>
                <div style="font-size:2.5cqw;color:#ab9177;">I have nothing to say and I am saying it anyway.</div>
              </div>
              <div style="display:flex;flex-direction:column;gap:1cqh;">
                <div style="font-family:'EB Garamond',serif;font-size:3.1cqw;color:#a8875f;">Sunday, 8 September</div>
                <div style="font-size:2.5cqw;color:#a4896f;">Thank you for the rain, which I did not ask for.</div>
              </div>
              <div style="display:flex;flex-direction:column;gap:1cqh;">
                <div style="font-family:'EB Garamond',serif;font-size:3.1cqw;color:#97794f;">Saturday, 7 September</div>
                <div style="font-size:2.5cqw;color:#9d8268;">Keep me from making this about being seen.</div>
              </div>
            </div>
          </div>
        </div>
        <div style="display:flex;flex-direction:column;gap:4px;">
          <div style="font-family:'IBM Plex Mono',monospace;font-size:11px;letter-spacing:0.14em;text-transform:uppercase;color:#9a8168;">Looking back</div>
          <div style="font-size:14px;line-height:1.6;color:#a68d73;">One line per day, dimming as you go back. No calendar, ever.</div>
        </div>
      </div>
    </div>
  </section>

  <section style="background:#0d0b0a;width:100%;max-width:1080px;display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:40px 64px;align-items:center;padding:72px 0;border-top:1px solid #221c17;">
    <div style="display:flex;flex-direction:column;gap:16px;">
      <div style="font-family:'IBM Plex Mono',monospace;font-size:11px;letter-spacing:0.16em;text-transform:uppercase;color:#9a8168;">Sealed</div>
      <h2 style="font-family:'EB Garamond',serif;font-weight:400;font-size:clamp(34px,4vw,44px);line-height:1.12;color:#d9b483;margin:0;">At midnight, <em style="font-style:italic;color:#c79f6e;">the day closes.</em></h2>
      <p style="margin:0;font-size:16px;line-height:1.8;color:#ab9075;text-wrap:pretty;">Everything prayed that day reads as one page, in order. It can't be edited — the record stays honest.</p>
      <p style="margin:0;font-size:16px;line-height:1.8;color:#ab9075;text-wrap:pretty;">Nothing announces it. No lock icon, no banner. The text is one step dimmer and the caret is gone.</p>
    </div>
    <div style="border-radius:10px;border:1px solid #2a221c;background:#12100e;overflow:hidden;box-shadow:0 40px 80px -40px #000;">
      <div style="height:20px;display:flex;align-items:center;gap:6px;padding:0 9px;background:#110f0d;border-bottom:1px solid #1d1814;">
        <div style="width:8px;height:8px;border-radius:4px;background:#2a221c;"></div>
        <div style="width:8px;height:8px;border-radius:4px;background:#2a221c;"></div>
        <div style="width:8px;height:8px;border-radius:4px;background:#2a221c;"></div>
      </div>
      <div style="container-type:size;aspect-ratio:16/10;width:100%;position:relative;display:flex;justify-content:center;">
        <div style="width:64cqw;padding-top:9cqh;display:flex;flex-direction:column;gap:5cqh;font-size:2.4cqw;line-height:1.95;color:#ab9075;">
          <div style="font-family:'EB Garamond',serif;font-size:3.8cqw;line-height:1.2;color:#d9b483;">Wednesday, 11 September</div>
          <div style="display:flex;flex-direction:column;gap:1cqh;">
            <div style="font-family:'EB Garamond',serif;font-size:2.3cqw;color:#9a8168;">5:12</div>
            <div>It is still dark and the house is quiet. I woke before the alarm again.</div>
          </div>
          <div style="display:flex;flex-direction:column;gap:1cqh;">
            <div style="font-family:'EB Garamond',serif;font-size:2.3cqw;color:#9a8168;">12:40</div>
            <div>I was patient once today and it cost me something. I would like that to count.</div>
          </div>
          <div style="display:flex;flex-direction:column;gap:1cqh;">
            <div style="font-family:'EB Garamond',serif;font-size:2.3cqw;color:#9a8168;">21:55</div>
            <div>For my father, who goes in on Tuesday.</div>
          </div>
        </div>
        <div style="position:absolute;left:0;right:0;bottom:0;height:20cqh;background:linear-gradient(rgba(18,16,14,0),#12100e);"></div>
      </div>
    </div>
  </section>

  <section style="background:#0d0b0a;width:100%;max-width:1080px;display:flex;flex-direction:column;gap:40px;padding:72px 0;border-top:1px solid #221c17;">
    <div style="display:flex;flex-direction:column;gap:16px;">
      <div style="font-family:'IBM Plex Mono',monospace;font-size:11px;letter-spacing:0.16em;text-transform:uppercase;color:#9a8168;">iPhone</div>
      <h2 style="font-family:'EB Garamond',serif;font-weight:400;font-size:clamp(34px,4vw,44px);line-height:1.12;color:#d9b483;margin:0;">The same room, <em style="font-style:italic;color:#c79f6e;">smaller.</em></h2>
      <p style="margin:0;max-width:58ch;font-size:16px;line-height:1.8;color:#ab9075;text-wrap:pretty;">Same page, same caret, same dark, carried in your pocket. The archive is home; pull in from the edge for a fresh page, and swipe back to put it away. It syncs from the Mac over your own iCloud.</p>
    </div>
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:28px 20px;">

      <div style="display:flex;flex-direction:column;align-items:center;gap:14px;">
        <div style="container-type:size;width:100%;max-width:240px;aspect-ratio:9/19.5;border-radius:36px;border:1px solid #2a221c;background:#12100e;position:relative;overflow:hidden;box-shadow:0 0 0 5px #080706,0 40px 70px -30px #000;">
          <div style="position:absolute;top:2.2cqh;left:50%;transform:translateX(-50%);width:30cqw;height:3.6cqh;border-radius:2cqh;background:#050404;"></div>
          <div style="position:absolute;top:2.6cqh;left:9cqw;font-size:5.2cqw;font-weight:400;color:#9a8168;">5:12</div>
          <div style="position:absolute;top:20cqh;left:10cqw;right:10cqw;display:flex;flex-direction:column;gap:3cqh;">
            <div style="font-family:'EB Garamond',serif;font-size:7cqw;color:#9a8168;">Thursday, 12 September</div>
            <div style="width:0.8cqw;height:8cqw;background:#c79f6e;animation:sd-blink 1.2s step-end infinite;box-shadow:0 0 6cqw 1cqw rgba(199,159,110,0.12);"></div>
          </div>
        </div>
        <div style="font-family:'IBM Plex Mono',monospace;font-size:11px;letter-spacing:0.14em;text-transform:uppercase;color:#9a8168;">The page</div>
      </div>

      <div style="display:flex;flex-direction:column;align-items:center;gap:14px;">
        <div style="container-type:size;width:100%;max-width:240px;aspect-ratio:9/19.5;border-radius:36px;border:1px solid #2a221c;background:#12100e;position:relative;overflow:hidden;box-shadow:0 0 0 5px #080706,0 40px 70px -30px #000;">
          <div style="position:absolute;top:2.2cqh;left:50%;transform:translateX(-50%);width:30cqw;height:3.6cqh;border-radius:2cqh;background:#050404;"></div>
          <div style="position:absolute;top:2.6cqh;left:9cqw;font-size:5.2cqw;font-weight:400;color:#9a8168;z-index:1;">5:14</div>
          <div style="position:absolute;left:10cqw;right:10cqw;top:50cqh;transform:translateY(-100%);font-size:5.6cqw;line-height:1.95;color:#bda186;display:flex;flex-direction:column;">
            <div style="opacity:0.28;">It is still dark and the</div>
            <div style="opacity:0.38;">house is quiet. I woke</div>
            <div style="opacity:0.5;">before the alarm again.</div>
            <div style="opacity:0.5;">&nbsp;</div>
            <div style="opacity:0.72;">For my father, who goes</div>
            <div style="opacity:0.86;">in on Tuesday. I keep</div>
            <div style="display:flex;align-items:baseline;color:#d9b483;">
              <span>checking it is still</span>
              <span style="display:inline-block;width:0.7cqw;height:6.6cqw;background:#e2bb8c;margin-left:1cqw;transform:translateY(1.1cqw);animation:sd-blink 1.2s step-end infinite;"></span>
            </div>
          </div>
          <div style="position:absolute;left:0;right:0;top:0;height:24cqh;background:linear-gradient(#12100e 30%,rgba(18,16,14,0));"></div>
        </div>
        <div style="font-family:'IBM Plex Mono',monospace;font-size:11px;letter-spacing:0.14em;text-transform:uppercase;color:#9a8168;">Mid-prayer</div>
      </div>

      <div style="display:flex;flex-direction:column;align-items:center;gap:14px;">
        <div style="container-type:size;width:100%;max-width:240px;aspect-ratio:9/19.5;border-radius:36px;border:1px solid #2a221c;background:#12100e;position:relative;overflow:hidden;box-shadow:0 0 0 5px #080706,0 40px 70px -30px #000;">
          <div style="position:absolute;top:2.2cqh;left:50%;transform:translateX(-50%);width:30cqw;height:3.6cqh;border-radius:2cqh;background:#050404;"></div>
          <div style="position:absolute;top:2.6cqh;left:9cqw;font-size:5.2cqw;font-weight:400;color:#9a8168;">5:20</div>
          <div style="position:absolute;top:13cqh;left:10cqw;right:10cqw;display:flex;flex-direction:column;gap:3.4cqh;">
            <div style="display:flex;flex-direction:column;gap:0.6cqh;">
              <div style="font-family:'EB Garamond',serif;font-size:7cqw;color:#d9b483;">Yesterday</div>
              <div style="font-size:5cqw;line-height:1.5;color:#b39a80;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">For my father, who goes in on Tuesday.</div>
            </div>
            <div style="display:flex;flex-direction:column;gap:0.6cqh;">
              <div style="font-family:'EB Garamond',serif;font-size:7cqw;color:#a8875f;">Tuesday, 10 September</div>
              <div style="font-size:5cqw;line-height:1.5;color:#ab9177;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">I have nothing to say and I am saying it anyway.</div>
            </div>
            <div style="display:flex;flex-direction:column;gap:0.6cqh;">
              <div style="font-family:'EB Garamond',serif;font-size:7cqw;color:#a8875f;">Sunday, 8 September</div>
              <div style="font-size:5cqw;line-height:1.5;color:#a4896f;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">Thank you for the rain, which I did not ask for.</div>
            </div>
            <div style="display:flex;flex-direction:column;gap:0.6cqh;">
              <div style="font-family:'EB Garamond',serif;font-size:7cqw;color:#97794f;">Saturday, 7 September</div>
              <div style="font-size:5cqw;line-height:1.5;color:#9d8268;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">Keep me from making this about being seen.</div>
            </div>
            <div style="display:flex;flex-direction:column;gap:0.6cqh;">
              <div style="font-family:'EB Garamond',serif;font-size:7cqw;color:#9b7f52;">Monday, 2 September</div>
              <div style="font-size:5cqw;line-height:1.5;color:#967c5c;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">She called. Twenty minutes and none of it easy.</div>
            </div>
          </div>
        </div>
        <div style="font-family:'IBM Plex Mono',monospace;font-size:11px;letter-spacing:0.14em;text-transform:uppercase;color:#9a8168;">Looking back</div>
      </div>

      <div style="display:flex;flex-direction:column;align-items:center;gap:14px;">
        <div style="container-type:size;width:100%;max-width:240px;aspect-ratio:9/19.5;border-radius:36px;border:1px solid #2a221c;background:#100e0d;position:relative;overflow:hidden;display:flex;align-items:center;justify-content:center;box-shadow:0 0 0 5px #080706,0 40px 70px -30px #000;">
          <div style="position:absolute;top:2.2cqh;left:50%;transform:translateX(-50%);width:30cqw;height:3.6cqh;border-radius:2cqh;background:#050404;"></div>
          <div style="width:6cqw;height:6cqw;border-radius:50%;background:#3a2e22;box-shadow:0 0 16cqw 4cqw rgba(199,159,110,0.05);"></div>
        </div>
        <div style="font-family:'IBM Plex Mono',monospace;font-size:11px;letter-spacing:0.14em;text-transform:uppercase;color:#9a8168;">The door</div>
      </div>

    </div>
  </section>

  <section style="background:#0d0b0a;width:100%;max-width:1080px;display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:32px 72px;padding:72px 0;border-top:1px solid #221c17;">
    <div style="display:flex;flex-direction:column;gap:16px;">
      <div style="font-family:'IBM Plex Mono',monospace;font-size:11px;letter-spacing:0.16em;text-transform:uppercase;color:#9a8168;">Left out</div>
      <h2 style="font-family:'EB Garamond',serif;font-weight:400;font-size:clamp(34px,4vw,44px);line-height:1.12;color:#d9b483;margin:0;">What it <em style="font-style:italic;color:#c79f6e;">won't do.</em></h2>
      <p style="margin:0;font-size:16px;line-height:1.8;color:#ab9075;text-wrap:pretty;">Every one of these was considered and refused. Leaving things out is the feature.</p>
    </div>
    <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:0 24px;align-content:start;">
      <div style="font-family:'EB Garamond',serif;font-size:20px;color:#a68d73;padding:12px 0;border-bottom:1px solid #221c17;">Streaks</div>
      <div style="font-family:'EB Garamond',serif;font-size:20px;color:#a68d73;padding:12px 0;border-bottom:1px solid #221c17;">Reminders</div>
      <div style="font-family:'EB Garamond',serif;font-size:20px;color:#a68d73;padding:12px 0;border-bottom:1px solid #221c17;">Calendar grids</div>
      <div style="font-family:'EB Garamond',serif;font-size:20px;color:#a68d73;padding:12px 0;border-bottom:1px solid #221c17;">Word counts</div>
      <div style="font-family:'EB Garamond',serif;font-size:20px;color:#a68d73;padding:12px 0;border-bottom:1px solid #221c17;">Tags &amp; folders</div>
      <div style="font-family:'EB Garamond',serif;font-size:20px;color:#a68d73;padding:12px 0;border-bottom:1px solid #221c17;">Sharing</div>
      <div style="font-family:'EB Garamond',serif;font-size:20px;color:#a68d73;padding:12px 0;border-bottom:1px solid #221c17;">Verse of the day</div>
      <div style="font-family:'EB Garamond',serif;font-size:20px;color:#a68d73;padding:12px 0;border-bottom:1px solid #221c17;">Editing yesterday</div>
      <div style="font-family:'EB Garamond',serif;font-size:20px;color:#a68d73;padding:12px 0;border-bottom:1px solid #221c17;">Analytics</div>
      <div style="font-family:'EB Garamond',serif;font-size:20px;color:#a68d73;padding:12px 0;border-bottom:1px solid #221c17;">Widgets</div>
      <div style="font-family:'EB Garamond',serif;font-size:20px;color:#a68d73;padding:12px 0;border-bottom:1px solid #221c17;">Accounts</div>
      <div style="font-family:'EB Garamond',serif;font-size:20px;color:#a68d73;padding:12px 0;border-bottom:1px solid #221c17;">Subscriptions</div>
    </div>
  </section>

  <section style="background:#0d0b0a;width:100%;max-width:1080px;display:flex;flex-direction:column;gap:16px;padding:72px 0;border-top:1px solid #221c17;">
    <div style="font-family:'IBM Plex Mono',monospace;font-size:11px;letter-spacing:0.16em;text-transform:uppercase;color:#9a8168;">Private</div>
    <h2 style="font-family:'EB Garamond',serif;font-weight:400;font-size:clamp(34px,4vw,44px);line-height:1.12;color:#d9b483;margin:0;">It stays <em style="font-style:italic;color:#c79f6e;">between you.</em></h2>
    <p style="margin:0;max-width:60ch;font-size:16px;line-height:1.8;color:#ab9075;text-wrap:pretty;">Prayers are encrypted end to end and sync only between your own devices, with keys in your iCloud Keychain. No account, no server anyone can read, no settings to get wrong. An optional lock covers the page whenever you step away.</p>
  </section>

  <section id="notify" style="background:#0d0b0a;width:100%;max-width:1080px;padding:24px 0 72px;">
    <div data-tidy-notify data-app="stilldark" data-endpoint="https://email.aaronaiken.me/subscribe" style="background:#17130f;border:1px solid #2a221c;border-radius:16px;padding:clamp(28px,5vw,56px);display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:28px 48px;align-items:center;">
      <div style="display:flex;flex-direction:column;gap:12px;">
        <div style="font-family:'IBM Plex Mono',monospace;font-size:11px;letter-spacing:0.16em;text-transform:uppercase;color:#9a8168;">Open beta</div>
        <div style="font-family:'EB Garamond',serif;font-size:clamp(30px,3.6vw,40px);line-height:1.15;color:#d9b483;">Try it now on TestFlight.</div>
        <div style="font-size:15px;color:#ab9075;">Free while it's in beta, on Mac &amp; iPhone. You'll need Apple's TestFlight app, then tap through.</div>
        <a href="https://testflight.apple.com/join/CPjjmV97" target="_blank" rel="noopener noreferrer" style="align-self:flex-start;margin-top:6px;display:flex;align-items:center;height:46px;padding:0 22px;border-radius:23px;background:#c79f6e;color:#12100e;font-family:'IBM Plex Sans',sans-serif;font-size:14px;font-weight:400;text-decoration:none;">Join the beta →</a>
      </div>
      <div style="display:flex;flex-direction:column;gap:12px;">
        <div style="font-family:'IBM Plex Mono',monospace;font-size:11px;letter-spacing:0.16em;text-transform:uppercase;color:#9a8168;">Or wait for launch</div>
        <form class="sd-form" style="display:flex;flex-wrap:wrap;gap:10px;">
          <input type="email" name="email" required autocomplete="email" placeholder="you@example.com" aria-label="Email address" style="flex:1 1 200px;min-width:0;height:46px;padding:0 18px;border-radius:23px;border:1px solid #3a2e22;background:#0f0d0b;color:#d9b483;font-family:'IBM Plex Sans',sans-serif;font-weight:300;font-size:15px;outline:none;">
          <button type="submit" style="height:46px;padding:0 22px;border-radius:23px;border:none;background:#c79f6e;color:#12100e;font-family:'IBM Plex Sans',sans-serif;font-size:14px;font-weight:400;cursor:pointer;">Notify me</button>
        </form>
        <div class="sd-done" style="font-family:'EB Garamond',serif;font-size:22px;color:#d9b483;">Thank you. You'll hear once.</div>
        <div style="font-family:'IBM Plex Mono',monospace;font-size:10px;letter-spacing:0.14em;text-transform:uppercase;color:#9a8168;">No tracking · unsubscribe any time</div>
      </div>
    </div>
  </section>

  <footer style="background:#0d0b0a;width:100%;max-width:1080px;display:flex;flex-wrap:wrap;justify-content:space-between;gap:16px;padding:28px 0 44px;border-top:1px solid #221c17;font-size:13px;line-height:1.6;color:#9a8168;">
    <div style="max-width:48ch;">Designed and built by <a href="/about/">Aaron</a>. A sibling to <a href="/tools/holdfast/">Holdfast</a>, an app for keeping hold of one thing.</div>
    <nav style="display:flex;flex-wrap:wrap;gap:20px;align-items:center;">
      <a href="/tools/still-dark/privacy/">Privacy</a>
      <a href="/tools/still-dark/support/">Support</a>
      <a href="https://cloudbase.day/notes/still_dark" target="_blank" rel="noopener noreferrer">Release notes</a>
    </nav>
    <div style="font-family:'EB Garamond',serif;font-style:italic;font-size:16px;color:#a68d73;">Very early in the morning.</div>
  </footer>

</div>
