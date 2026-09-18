---
layout: cloudbase
title: Cloudbase — practice management for the person who does all the jobs
permalink: /tools/cloudbase/
description: Cloudbase runs a one-person practice — the work, the record, and the money in one place, and nothing in it scores you. A live, multi-tenant SaaS, built and run by one person.
image:
  path: /assets/img/cloudbase/og.png
  width: 1200
  height: 630
theme_color: "#11203b"
author: aaron
---

{% raw %}
<div style="background: var(--surface-sunk); color: var(--ink); font-family: var(--prose); min-height: 100vh; padding: 34px 28px 0;">
<div style="max-width: 960px; margin: 0 auto;">

  <nav style="font-family: 'Share Tech Mono', monospace; font-size: 12.8px; letter-spacing: .05em; line-height: 54px; display: flex; flex-wrap: wrap; gap: 8px; color: var(--ink-quiet);">
    <a href="/" style="color: var(--ink-quiet);">Home</a><span style="opacity:.4">|</span>
    <a href="/about/" style="color: var(--ink-quiet);">About</a><span style="opacity:.4">|</span>
    <a href="/blog/" style="color: var(--ink-quiet);">Blog</a><span style="opacity:.4">|</span>
    <a href="/work/" style="color: var(--ink-quiet);">Work</a><span style="opacity:.4">|</span>
    <a href="/tools/" style="color: var(--accent); text-decoration: underline;">Workbench</a><span style="opacity:.4">|</span>
    <a href="/selling" style="color: var(--ink-quiet);">Hire</a><span style="opacity:.4">|</span>
    <a href="/contact/" style="color: var(--ink-quiet);">Contact</a>
  </nav>
  <div style="display: flex; align-items: center; gap: 8px; font-family: var(--mono); font-size: 10.4px; letter-spacing: .18em; text-transform: uppercase; margin-bottom: 34px;">
    <span style="color: var(--accent);">The Workbench</span>
    <span style="opacity:.3">·</span>
    <span style="opacity:.45">Cloudbase</span>
  </div>

  <header style="border-bottom: 2px solid var(--line); padding-bottom: 34px; margin-bottom: 34px;">
    <div style="display: flex; align-items: center; gap: 10px; font-family: var(--mono); font-size: 10px; letter-spacing: .18em; text-transform: uppercase; color: var(--ok); margin-bottom: 18px;">
      <span style="width: 6px; height: 6px; border-radius: 50%; background: var(--ok); display: inline-block;"></span>
      Live at cloudbase.day
      <span style="color: var(--ink-faint); letter-spacing: .14em;">· in daily use since august 2026</span>
    </div>
    <h1 style="font-family: var(--serif); font-weight: 600; font-size: 54px; line-height: 1.04; letter-spacing: -0.02em; margin: 0; text-wrap: pretty; max-width: 20ch;">Practice management for the person who does all the jobs.</h1>
    <p style="font-family: var(--prose); font-size: 20px; line-height: 1.7; color: var(--ink-body); max-width: 62ch; margin: 20px 0 0;">Cloudbase runs a one-person practice — the work, the record, and the money — without ever once telling you how you did. I built it because every tool I paid for assumed I was a team of twelve, and then billed me per seat for the eleven I don't have.</p>
    <p style="font-family: var(--prose); font-size: 17px; line-height: 1.8; color: var(--ink-quiet); max-width: 62ch; margin: 14px 0 0;">It's the biggest thing I've ever built, it's in production, and it's what I open first every morning.</p>
    <div style="display: flex; flex-wrap: wrap; gap: 10px; margin-top: 26px;">
      <a href="https://cloudbase.day" style="font-family: var(--mono); font-size: 12px; letter-spacing: .12em; text-transform: uppercase; padding: 11px 20px; border-radius: 3px; background: var(--accent); border: 1px solid var(--accent); color: #fff;">Visit cloudbase.day →</a>
      <a href="#walkthrough" style="font-family: var(--mono); font-size: 12px; letter-spacing: .12em; text-transform: uppercase; padding: 11px 20px; border-radius: 3px; background: var(--surface); border: 1px solid var(--line); color: var(--ink-quiet);">Walk the screens</a>
    </div>
    <div style="display: flex; flex-wrap: wrap; gap: 26px; margin-top: 28px; font-family: var(--mono); font-size: 10px; letter-spacing: .14em; text-transform: uppercase; color: var(--ink-quiet);">
      <span>Flask · Postgres · Fly.io</span>
      <span>600+ tests, green</span>
      <span>Multi-tenant from day one</span>
      <span>Built and run by one person</span>
    </div>
  </header>

  <section style="margin-bottom: 46px;">
    <div style="font-family: var(--mono); font-size: 11px; letter-spacing: .16em; text-transform: uppercase; color: var(--ink-quiet); margin-bottom: 16px;">Why this exists</div>
    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 30px;">
      <div>
        <p style="font-family: var(--prose); font-size: 17px; line-height: 1.8; color: var(--ink-body); margin: 0 0 16px;">For years I ran my own work out of a private Flask app I called the Cockpit. It knew my projects, my hours, my mileage, and the twelve small requests that arrive in a week. It was ugly in places and it was <em>mine</em>, and it beat every subscription I'd tried.</p>
        <p style="font-family: var(--prose); font-size: 17px; line-height: 1.8; color: var(--ink-body); margin: 0;">Then other people started asking for it. Cloudbase is that app rebuilt properly — multi-tenant, productized, and rewritten from the assumption that the person using it is the whole company.</p>
      </div>
      <div>
        <p style="font-family: var(--prose); font-size: 17px; line-height: 1.8; color: var(--ink-body); margin: 0 0 16px;">Here's what running a small practice actually costs: not the hours, the <em>switching</em>. A request in email, a note in one app, the hours in a spreadsheet, the miles on a receipt in the truck. By Friday you can't say what an hour of your week earned, and you'd rather not find out.</p>
        <p style="font-family: var(--prose); font-size: 17px; line-height: 1.8; color: var(--ink-body); margin: 0;">So one place holds all of it, and none of it scores you. There are no streaks in here, no productivity number, no capacity bar. Twelve people want something and four of them are waiting on you — that's a sentence, not a dashboard.</p>
      </div>
    </div>
  </section>

  <section id="walkthrough" style="margin-bottom: 46px; padding-top: 30px; border-top: 2px solid var(--line);">
    <div style="display: flex; align-items: flex-end; justify-content: space-between; gap: 24px; flex-wrap: wrap; margin-bottom: 8px;">
      <div>
        <div style="font-family: var(--mono); font-size: 11px; letter-spacing: .16em; text-transform: uppercase; color: var(--ink-quiet); margin-bottom: 10px;">The walkthrough</div>
        <h2 style="font-family: var(--serif); font-weight: 600; font-size: 36px; line-height: 1.1; letter-spacing: -0.015em; margin: 0;">Two screens, and the whole argument.</h2>
      </div>
      <div style="display: flex; gap: 6px;">
        <button type="button" data-tab="cockpit" style="font-family: var(--mono); font-size: 11px; letter-spacing: .12em; text-transform: uppercase; padding: 9px 14px; border-radius: 3px; cursor: pointer; background: var(--accent-wash); border: 1px solid var(--accent); color: var(--accent);">The Cockpit</button>
        <button type="button" data-tab="today" style="font-family: var(--mono); font-size: 11px; letter-spacing: .12em; text-transform: uppercase; padding: 9px 14px; border-radius: 3px; cursor: pointer; background: var(--surface); border: 1px solid var(--line); color: var(--ink-quiet);">Planning today</button>
      </div>
    </div>
    <p style="font-family: var(--prose); font-size: 16px; line-height: 1.7; color: var(--ink-quiet); max-width: 76ch; margin: 0 0 20px;">Real screens, real numbers, live controls — tick a task and watch what it does. The notes underneath are mine: six things on these two screens that no other tool I've paid for would do.</p>

    <div data-fit="1" style="position: relative; container-type: inline-size; width: 1200px; max-width: calc(100vw - 56px); margin-left: 50%; translate: -50% 0; aspect-ratio: 1200 / 720; overflow: hidden;">
    <div data-frame="1" style="position: relative; border: 1px solid var(--line-strong); border-radius: 6px; overflow: hidden; background: var(--surface-sunk); height: 720px; width: 1200px; transform-origin: top left; transform: scale(var(--s, tan(atan2(min(100cqw, 1200px), 1200px))));">
      <div style="display: grid; grid-template-columns: 224px 1fr; height: 100%;">

        <aside style="background: var(--surface); border-right: 1px solid var(--line); display: flex; flex-direction: column; height: 100%; overflow: hidden;">
          <div style="display: flex; align-items: center; gap: 9px; font-family: var(--serif); font-weight: 600; font-size: 16px; color: var(--ink); padding: 18px 16px 12px; flex: none;">
            <span style="width: 22px; height: 22px; border-radius: 5px; background: var(--accent); position: relative; flex: none; overflow: hidden; display: inline-block;">
              <span style="position: absolute; background: #fff; border-radius: 3px; width: 9px; height: 6px; left: 8px; top: 7px;"></span>
              <span style="position: absolute; background: #fff; border-radius: 3px; width: 15px; height: 7px; left: 4px; top: 11px;"></span>
            </span>
            <span style="flex: 1 1 auto; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">Aiken Studio</span>
            <span style="color: var(--ink-faint); font-size: 12px; flex: none; font-family: var(--mono);">⇕</span>
          </div>
          <div style="flex: 1; overflow-y: auto; padding: 4px 16px 12px;">
            <div style="margin-bottom: 18px;">
              <div style="display: flex; align-items: center; justify-content: space-between; padding: 4px 2px; margin: 0 0 6px; font-family: var(--mono); font-size: 11px; text-transform: uppercase; letter-spacing: .14em; color: var(--ink-quiet);">The work<span style="width: 8px; height: 8px; border-right: 1.5px solid currentColor; border-bottom: 1.5px solid currentColor; transform: rotate(45deg); opacity: .7;"></span></div>
              <a href="#" data-tab="cockpit" data-navlink="cockpit" style="display: flex; align-items: center; justify-content: space-between; gap: 8px; padding: 7px 10px; border-radius: 4px; background: var(--accent); color: #fff; font-size: 14px; margin-bottom: 2px; cursor: pointer;">Cockpit</a>
              <a href="#" data-tab="today" data-navlink="today" style="display: flex; align-items: center; justify-content: space-between; gap: 8px; padding: 7px 10px; border-radius: 4px; color: var(--ink-body); font-size: 14px; margin-bottom: 2px; cursor: pointer;">Today<span style="display: flex; align-items: center; gap: 8px;"><span style="font-family: var(--fig); font-size: 11px; color: var(--ink-quiet);">4</span><span style="display: inline-flex; align-items: center; justify-content: center; width: 18px; height: 18px; border-radius: 50%; background: var(--accent); color: #fff; font-family: var(--mono); font-size: 10px; flex: none;">1</span></span></a>
              <a href="#" style="display: flex; align-items: center; justify-content: space-between; gap: 8px; padding: 7px 10px; border-radius: 4px; color: var(--ink-body); font-size: 14px; margin-bottom: 2px;">Inbox<span style="font-family: var(--fig); font-size: 11px; color: var(--ink-quiet);">2</span></a>
              <a href="#" style="display: block; padding: 7px 10px; border-radius: 4px; color: var(--ink-body); font-size: 14px; margin-bottom: 2px;">Projects</a>
              <a href="#" style="display: block; padding: 7px 10px; border-radius: 4px; color: var(--ink-body); font-size: 14px; margin-bottom: 2px;">Tickets</a>
              <a href="#" style="display: block; padding: 7px 10px 7px 22px; border-radius: 4px; color: var(--ink-body); font-size: 14px; margin-bottom: 2px;">The Hangar</a>
              <a href="#" style="display: block; padding: 7px 10px 7px 22px; border-radius: 4px; color: var(--ink-body); font-size: 14px; margin-bottom: 2px;">Flights</a>
              <a href="#" style="display: block; padding: 7px 10px; border-radius: 4px; color: var(--ink-body); font-size: 14px; margin-bottom: 2px;">The Logbook</a>
              <a href="#" style="display: block; padding: 7px 10px; border-radius: 4px; color: var(--ink-body); font-size: 14px; margin-bottom: 2px;">Meetings</a>
              <a href="#" style="display: block; padding: 7px 10px; border-radius: 4px; color: var(--ink-body); font-size: 14px; margin-bottom: 2px;">Files</a>
            </div>
            <div style="margin-bottom: 18px;">
              <div style="display: flex; align-items: center; justify-content: space-between; padding: 4px 2px; margin: 0 0 6px; font-family: var(--mono); font-size: 11px; text-transform: uppercase; letter-spacing: .14em; color: var(--ink-quiet);">The record<span style="width: 8px; height: 8px; border-right: 1.5px solid currentColor; border-bottom: 1.5px solid currentColor; transform: rotate(45deg); opacity: .7;"></span></div>
              <a href="#" style="display: flex; align-items: center; justify-content: space-between; gap: 8px; padding: 7px 10px; border-radius: 4px; color: var(--ink-body); font-size: 14px; margin-bottom: 2px;">Time<span style="font-family: var(--fig); font-size: 11px; color: var(--warn); letter-spacing: .02em;">1:12:04</span></a>
              <a href="#" style="display: block; padding: 7px 10px; border-radius: 4px; color: var(--ink-body); font-size: 14px; margin-bottom: 2px;">Mileage</a>
              <a href="#" style="display: block; padding: 7px 10px; border-radius: 4px; color: var(--ink-body); font-size: 14px; margin-bottom: 2px;">Reports</a>
            </div>
            <div style="margin-bottom: 18px;">
              <div style="display: flex; align-items: center; justify-content: space-between; padding: 4px 2px; margin: 0 0 6px; font-family: var(--mono); font-size: 11px; text-transform: uppercase; letter-spacing: .14em; color: var(--ink-quiet);">The money<span style="width: 8px; height: 8px; border-right: 1.5px solid currentColor; border-bottom: 1.5px solid currentColor; transform: rotate(45deg); opacity: .7;"></span></div>
              <a href="#" style="display: block; padding: 7px 10px; border-radius: 4px; color: var(--ink-body); font-size: 14px; margin-bottom: 2px;">Clients</a>
              <a href="#" style="display: block; padding: 7px 10px; border-radius: 4px; color: var(--ink-body); font-size: 14px; margin-bottom: 2px;">Estimates</a>
              <a href="#" style="display: block; padding: 7px 10px; border-radius: 4px; color: var(--ink-body); font-size: 14px; margin-bottom: 2px;">Contacts</a>
            </div>
            <div style="margin-bottom: 18px;">
              <div style="display: flex; align-items: center; justify-content: space-between; padding: 4px 2px; margin: 0; font-family: var(--mono); font-size: 11px; text-transform: uppercase; letter-spacing: .14em; color: var(--ink-quiet);">Mine<span style="width: 8px; height: 8px; border-right: 1.5px solid currentColor; border-bottom: 1.5px solid currentColor; transform: rotate(-45deg); opacity: .7;"></span></div>
            </div>
          </div>
          <div style="flex: none; border-top: 1px solid var(--line); padding: 8px 16px 10px;">
            <div style="padding: 4px 2px 8px; display: flex; align-items: center; gap: 8px;">
              <span style="flex: none; font-size: 13px; color: var(--ink-faint); font-family: var(--mono);">✎</span>
              <span style="flex: 1; min-width: 0; font-family: var(--prose); font-size: 14px; color: var(--ink-faint); font-style: italic;">a thought, before it goes…</span>
              <span style="flex: none; font-family: var(--mono); font-size: 10px; color: var(--ink-faint); border: 1px solid var(--line); border-radius: 3px; padding: 0 4px;">S</span>
            </div>
            <div style="display: flex; align-items: center; gap: 8px; padding: 8px 10px; border-radius: 4px;">
              <span style="width: 7px; height: 7px; border-radius: 50%; background: var(--warn); flex: none;"></span>
              <span style="font-size: 14px; color: var(--ink); flex: 1;">Work</span>
              <span style="font-family: var(--mono); font-size: 10px; letter-spacing: .12em; text-transform: uppercase; color: var(--ink-quiet);">Mode ▴</span>
            </div>
            <div style="display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-top: 4px;">
              <a href="#" style="font-family: var(--mono); font-size: 11px; letter-spacing: .1em; text-transform: uppercase; color: var(--ink-quiet); padding: 7px 10px;">Something's off?</a>
              <a href="#" style="font-size: 14px; color: var(--ink-body); padding: 7px 10px;">Settings</a>
            </div>
          </div>
          <div style="flex: none; background: var(--surface-quiet); border-top: 1px solid var(--line); padding: 12px 16px;">
            <div style="display: flex; align-items: center; gap: 9px; position: relative; margin-top: 3px;">
              <span style="flex: none; line-height: 0; position: relative;">
                <span style="display: inline-flex; align-items: center; justify-content: center; width: 40px; height: 40px; border-radius: 4px; background: #f0e6ef; color: #8b6b86; font-family: var(--mono); font-size: 14px;">♪</span>
              </span>
              <span style="min-width: 0; flex: 1;">
                <span style="display: block; font-family: var(--prose); font-size: 13px; color: var(--ink); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">we can't be friends</span>
                <span style="display: block; font-family: var(--prose); font-size: 11px; color: var(--ink-quiet); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">Ariana Grande · eternal sunshine</span>
              </span>
              <span style="display: flex; gap: 2px; align-items: flex-end; height: 14px; flex: none;">
                <i style="width: 3px; height: 50%; background: var(--ok); border-radius: 1px; animation: w 1s ease-in-out infinite; transform-origin: bottom; display: block;"></i>
                <i style="width: 3px; height: 100%; background: var(--ok); border-radius: 1px; animation: w 1s ease-in-out .15s infinite; transform-origin: bottom; display: block;"></i>
                <i style="width: 3px; height: 70%; background: var(--ok); border-radius: 1px; animation: w 1s ease-in-out .3s infinite; transform-origin: bottom; display: block;"></i>
              </span>
              <span style="display: inline-flex; align-items: center; justify-content: center; width: 18px; height: 18px; border-radius: 50%; background: var(--accent); color: #fff; font-family: var(--mono); font-size: 10px; flex: none;">7</span>
            </div>
            <div style="height: 2px; background: var(--line-quiet); border-radius: 1px; margin-top: 8px; overflow: hidden;">
              <span style="display: block; height: 100%; width: 41%; background: var(--accent);"></span>
            </div>
          </div>
        </aside>

        <main data-appmain style="overflow-y: auto; height: 100%;">

          <div data-screen="cockpit" style="padding: 28px 34px;">
            <div style="display: flex; flex-wrap: wrap; align-items: center; gap: 14px; background: #101828; color: #fff; border-radius: 8px; padding: 11px 16px; margin-bottom: 20px;">
              <div style="display: flex; align-items: center; gap: 11px; min-width: 0;">
                <span style="width: 8px; height: 8px; border-radius: 50%; background: #f5a623; animation: cbpulse 2s infinite;"></span>
                <span style="font-family: var(--mono); font-size: 10px; letter-spacing: .14em; text-transform: uppercase; opacity: .85;">Running</span>
                <span style="font-family: var(--mono); font-size: 20px; font-variant-numeric: tabular-nums;" data-clock="1">1:12:04</span>
                <span style="font-size: 14px;"><b style="font-weight: 600;">Brightside rebuild</b> — Write the invoice copy</span>
                <button type="button" style="border: 0; border-radius: 4px; padding: 6px 13px; font-family: var(--mono); font-size: 11px; letter-spacing: .08em; text-transform: uppercase; cursor: pointer; background: #fff; color: #101828;">Stop</button>
                <span style="display: inline-flex; align-items: center; justify-content: center; width: 18px; height: 18px; border-radius: 50%; background: #8fb0ff; color: #101828; font-family: var(--mono); font-size: 10px; flex: none;">2</span>
              </div>
            </div>

            <div style="display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 1px solid var(--line); padding-bottom: 22px; margin-bottom: 24px;">
              <div>
                <div style="font-family: var(--mono); font-size: 11px; text-transform: uppercase; letter-spacing: .14em; color: var(--ink-quiet); margin-bottom: 8px;">Wednesday, August 19 · <span style="color: var(--warn); font-style: italic; text-transform: none; letter-spacing: 0;">late summer</span></div>
                <h1 style="font-family: var(--serif); font-weight: 600; font-size: 30px; letter-spacing: -0.015em; margin: 0; color: var(--ink);">Morning, Aaron.</h1>
                <div style="color: var(--ink-quiet); font-size: 16px; margin-top: 4px; font-family: var(--prose);">Twelve people want something, four of them are waiting on you.<span style="display: inline-flex; align-items: center; justify-content: center; width: 18px; height: 18px; border-radius: 50%; background: var(--accent); color: #fff; font-family: var(--mono); font-size: 10px; vertical-align: middle; margin-left: 10px;">3</span></div>
              </div>
              <div style="display: flex; gap: 10px; flex: none;">
                <button type="button" style="font-family: var(--mono); font-size: 12px; text-transform: uppercase; letter-spacing: .12em; padding: 11px 20px; border-radius: 3px; background: var(--accent); border: 1px solid var(--accent); color: #fff; cursor: pointer;"><span style="font-family: var(--mono); font-size: 12px; margin-right: 3px;">✦</span> Quick add <span style="display: inline-block; font-family: var(--mono); font-size: 10px; border: 1px solid rgba(255,255,255,.45); border-radius: 3px; padding: 1px 5px; opacity: .85; margin-left: 6px;">A</span></button>
                <button type="button" style="font-family: var(--mono); font-size: 12px; text-transform: uppercase; letter-spacing: .12em; padding: 11px 20px; border-radius: 3px; background: var(--surface); border: 1px solid var(--line); color: var(--ink-quiet); cursor: pointer;"><span style="font-family: var(--mono); margin-right: 3px;">▶</span> Log time <span style="display: inline-block; font-family: var(--mono); font-size: 10px; border: 1px solid var(--line); border-radius: 3px; padding: 1px 5px; opacity: .7; margin-left: 6px;">⌃2</span></button>
              </div>
            </div>

            <div style="display: grid; grid-template-columns: 1fr 290px; gap: 22px; align-items: start;">
              <div>
                <div style="background: var(--surface); border: 1px solid var(--line); border-radius: 6px; padding: 20px 22px; margin-bottom: 18px;">
                  <div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 14px;">
                    <h2 style="font-family: var(--serif); font-weight: 600; font-size: 20px; margin: 0; letter-spacing: -0.015em;">Today</h2>
                    <span style="font-family: var(--mono); font-size: 11px; letter-spacing: .1em; text-transform: uppercase; color: var(--ink-quiet);"><a href="#" style="color: var(--accent);">Plan today</a> · 4 picked · 1 done<span style="display: inline-flex; align-items: center; justify-content: center; width: 18px; height: 18px; border-radius: 50%; background: var(--accent); color: #fff; font-family: var(--mono); font-size: 10px; vertical-align: middle; margin-left: 10px;">4</span></span>
                  </div>

                  <div data-taskrow="1" style="display: flex; justify-content: space-between; align-items: center; padding: 11px 0;">
                    <div style="display: flex; align-items: center; gap: 11px; min-width: 0;">
                      <button type="button" data-tick="1" style="width: 15px; height: 15px; border: 1.5px solid var(--line-strong); border-radius: 3px; flex: none; background: none; cursor: pointer; padding: 0; line-height: 12px; text-align: center; color: #fff; font-size: 10px; font-weight: 700;"></button>
                      <a href="#" data-title="1" style="color: var(--ink); font-family: var(--serif); font-weight: 600; font-size: 17px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; min-width: 0;">Write the invoice copy</a>
                      <span style="font-family: var(--mono); font-size: 9px; letter-spacing: .08em; text-transform: uppercase; color: var(--accent); border: 1px solid var(--accent); border-radius: 4px; padding: 2px 6px; margin-left: 6px; white-space: nowrap; flex: none;">today</span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 10px; flex: none;">
                      <span data-undo="1" style="display: none; align-items: center; gap: 8px;"><button type="button" data-undobtn="1" style="font-family: var(--mono); font-size: 10px; letter-spacing: .1em; text-transform: uppercase; color: var(--accent); background: none; border: 1px solid var(--accent-line); border-radius: 3px; padding: 4px 9px; cursor: pointer;">Undo</button></span>
                      <span data-ctrl="1" style="display: flex; align-items: center; gap: 10px;">
                        <span style="display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: #f5a623; animation: cbpulse 2s infinite;"></span>
                        <button type="button" style="display: inline-flex; align-items: center; justify-content: center; background: #101828; border: 1px solid #101828; border-radius: 4px; width: 24px; height: 24px; cursor: pointer; color: #fff; font-size: 9px; padding: 0;">■</button>
                        <a href="#" style="font-family: var(--mono); font-size: 10px; letter-spacing: .08em; text-transform: uppercase; color: var(--ink-quiet);">Brightside rebuild</a>
                        <button type="button" style="background: none; border: 0; cursor: pointer; font-size: 15px; line-height: 1; color: var(--warn); padding: 0;">★</button>
                      </span>
                    </div>
                  </div>

                  <div data-taskrow="2" style="display: flex; justify-content: space-between; align-items: center; padding: 11px 0; border-top: 1px solid var(--line-quiet);">
                    <div style="display: flex; align-items: center; gap: 11px; min-width: 0;">
                      <button type="button" data-tick="2" style="width: 15px; height: 15px; border: 1.5px solid var(--line-strong); border-radius: 3px; flex: none; background: none; cursor: pointer; padding: 0; line-height: 12px; text-align: center; color: #fff; font-size: 10px; font-weight: 700;"></button>
                      <a href="#" data-title="2" style="color: var(--ink); font-family: var(--serif); font-weight: 600; font-size: 17px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; min-width: 0;">Send Dana the revised estimate</a>
                      <span style="font-family: var(--mono); font-size: 9px; letter-spacing: .08em; text-transform: uppercase; color: var(--ink-quiet); border: 1px solid var(--line); border-radius: 4px; padding: 2px 6px; margin-left: 6px; white-space: nowrap; flex: none;">Aug 21</span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 10px; flex: none;">
                      <span data-undo="2" style="display: none; align-items: center; gap: 8px;"><button type="button" data-undobtn="2" style="font-family: var(--mono); font-size: 10px; letter-spacing: .1em; text-transform: uppercase; color: var(--accent); background: none; border: 1px solid var(--accent-line); border-radius: 3px; padding: 4px 9px; cursor: pointer;">Undo</button></span>
                      <span data-ctrl="2" style="display: flex; align-items: center; gap: 10px;">
                        <button type="button" style="display: inline-flex; align-items: center; justify-content: center; background: none; border: 1px solid var(--line); border-radius: 4px; width: 24px; height: 24px; cursor: pointer; color: var(--ink-quiet); font-size: 9px; padding: 0;">▶</button>
                        <a href="#" style="font-family: var(--mono); font-size: 10px; letter-spacing: .08em; text-transform: uppercase; color: var(--ink-quiet);">Vine Street clinic</a>
                        <button type="button" style="background: none; border: 0; cursor: pointer; font-size: 15px; line-height: 1; color: var(--warn); padding: 0;">★</button>
                      </span>
                    </div>
                  </div>

                  <div style="display: flex; justify-content: space-between; align-items: center; padding: 11px 0; border-top: 1px solid var(--line-quiet);">
                    <div style="display: flex; align-items: center; gap: 11px; min-width: 0;">
                      <span title="Waiting on the clinic" style="width: 15px; height: 15px; border: 1.5px dashed var(--line-strong); border-radius: 3px; flex: none; display: inline-flex; align-items: center; justify-content: center; color: var(--ink-quiet); font-size: 10px; font-family: var(--mono);">↻</span>
                      <a href="#" style="color: var(--ink-faint); font-family: var(--serif); font-weight: 600; font-size: 17px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; min-width: 0;">Book the follow-up walkthrough</a>
                      <span style="font-family: var(--mono); font-size: 9px; letter-spacing: .06em; text-transform: uppercase; color: var(--ink-quiet); background: var(--surface-quiet); border: 1px solid var(--line); border-radius: 3px; padding: 2px 6px; margin-left: 8px; white-space: nowrap; flex: none;">waiting on the clinic</span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 10px; flex: none;">
                      <a href="#" style="font-family: var(--mono); font-size: 10px; letter-spacing: .08em; text-transform: uppercase; color: var(--ink-quiet);">Vine Street clinic</a>
                      <button type="button" style="background: none; border: 0; cursor: pointer; font-size: 15px; line-height: 1; color: var(--warn); padding: 0;">★</button>
                    </div>
                  </div>

                  <div style="display: flex; justify-content: space-between; align-items: center; padding: 11px 0; border-top: 1px solid var(--line-quiet);">
                    <div style="display: flex; align-items: center; gap: 11px; min-width: 0;">
                      <a href="#" style="color: var(--ink); font-family: var(--serif); font-weight: 600; font-size: 17px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; min-width: 0;">Their card reader won't take taps</a>
                      <span style="font-family: var(--mono); font-size: 9px; letter-spacing: .06em; text-transform: uppercase; color: var(--warn); border: 1px solid var(--warn-line); border-radius: 3px; padding: 2px 6px; margin-left: 8px; white-space: nowrap; flex: none;">GC-114 · Dana R.</span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 10px; flex: none;">
                      <a href="#" style="font-family: var(--mono); font-size: 10px; letter-spacing: .08em; text-transform: uppercase; color: var(--ink-quiet);">Vine Street clinic</a>
                      <button type="button" style="background: none; border: 0; cursor: pointer; font-size: 15px; line-height: 1; color: var(--warn); padding: 0;">★</button>
                    </div>
                  </div>
                </div>

                <div style="background: var(--surface); border: 1px solid var(--line); border-radius: 6px; padding: 20px 22px; margin-bottom: 18px;">
                  <div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 14px;">
                    <h2 style="font-family: var(--serif); font-weight: 600; font-size: 20px; margin: 0; letter-spacing: -0.015em;">Projects</h2>
                    <a href="#" style="font-family: var(--mono); font-size: 11px; letter-spacing: .1em; text-transform: uppercase; color: var(--ink-quiet);">+ New project</a>
                  </div>
                  <div style="display: flex; justify-content: space-between; align-items: center; padding: 11px 0;">
                    <div style="display: flex; align-items: center; gap: 11px; min-width: 0;">
                      <span style="width: 10px; height: 10px; border-radius: 50%; flex: none; background: var(--ok);"></span>
                      <a href="#" style="font-size: 16px; color: var(--ink);">Brightside rebuild</a><span style="color: var(--ink-quiet); font-size: 13px; margin-left: 8px;">Brightside Dental</span>
                    </div>
                    <span style="font-family: var(--mono); font-size: 10px; letter-spacing: .08em; text-transform: uppercase; color: var(--ink-quiet);">5 open</span>
                  </div>
                  <div style="display: flex; justify-content: space-between; align-items: center; padding: 11px 0; border-top: 1px solid var(--line-quiet);">
                    <div style="display: flex; align-items: center; gap: 11px; min-width: 0;">
                      <span style="width: 10px; height: 10px; border-radius: 50%; flex: none; background: var(--warn);"></span>
                      <a href="#" style="font-size: 16px; color: var(--ink);">Vine Street clinic · intake forms</a><span style="color: var(--ink-quiet); font-size: 13px; margin-left: 8px;">Vine Street</span>
                    </div>
                    <span style="font-family: var(--mono); font-size: 10px; letter-spacing: .08em; text-transform: uppercase; color: var(--ink-quiet);">3 open</span>
                  </div>
                  <div style="display: flex; justify-content: space-between; align-items: center; padding: 11px 0; border-top: 1px solid var(--line-quiet);">
                    <div style="display: flex; align-items: center; gap: 11px; min-width: 0;">
                      <span style="width: 10px; height: 10px; border-radius: 50%; flex: none; background: var(--ink-faint);"></span>
                      <a href="#" style="font-size: 16px; color: var(--ink);">The reading list site</a><span style="color: var(--ink-quiet); font-size: 13px; margin-left: 8px;">Mine</span>
                    </div>
                    <span style="font-family: var(--mono); font-size: 10px; letter-spacing: .08em; text-transform: uppercase; color: var(--ink-quiet);">2 open · <span style="color: var(--ok);">invested</span></span>
                  </div>
                </div>

                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 18px;">
                  <div style="background: var(--surface); border: 1px solid var(--line); border-radius: 6px; padding: 20px 22px; margin: 0;">
                    <div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 14px;">
                      <h2 style="font-family: var(--serif); font-weight: 600; font-size: 16px; margin: 0;">Mileage · August</h2>
                      <a href="#" style="font-family: var(--mono); font-size: 11px; letter-spacing: .1em; text-transform: uppercase; color: var(--ink-quiet);">Log a trip</a>
                    </div>
                    <div style="font-family: var(--fig); font-size: 30px; color: var(--ink);">412</div>
                    <div style="color: var(--ink-faint); font-style: italic; font-size: 14px; margin-top: 6px;">miles · $280.16 claimable</div>
                  </div>
                  <div style="background: var(--surface); border: 1px solid var(--line); border-radius: 6px; padding: 20px 22px; margin: 0;">
                    <div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 14px;">
                      <h2 style="font-family: var(--serif); font-weight: 600; font-size: 16px; margin: 0;">Yours to move</h2>
                      <a href="#" style="font-family: var(--mono); font-size: 11px; letter-spacing: .1em; text-transform: uppercase; color: var(--ink-quiet);">All tickets</a>
                    </div>
                    <div style="display: flex; align-items: center; gap: 10px; padding: 9px 0;">
                      <span style="width: 7px; height: 7px; border-radius: 50%; background: var(--bad); flex: none;"></span>
                      <a href="#" style="flex: 1; font-size: 14px; color: var(--ink);">Card reader won't take taps</a>
                      <span style="font-family: var(--mono); font-size: 10px; color: var(--ink-quiet);">3 days</span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 10px; padding: 9px 0; border-top: 1px solid var(--line-quiet);">
                      <span style="width: 7px; height: 7px; border-radius: 50%; background: var(--accent); flex: none;"></span>
                      <a href="#" style="flex: 1; font-size: 14px; color: var(--ink);">Can we add a second front desk login?</a>
                      <span style="font-family: var(--mono); font-size: 10px; color: var(--ink-quiet);">1 day</span>
                    </div>
                  </div>
                </div>
              </div>

              <div>
                <div style="background: var(--surface); border: 1px solid var(--line); border-radius: 6px; padding: 16px 18px; margin-bottom: 18px;">
                  <span style="display: block; font-family: var(--mono); font-size: 11px; text-transform: uppercase; letter-spacing: .14em; color: var(--ink-quiet); margin-bottom: 10px;">Time today</span>
                  <div style="display: flex; align-items: baseline; gap: 10px; flex-wrap: wrap;">
                    <span style="font-family: var(--fig); font-size: 26px; letter-spacing: -.01em; color: var(--warn);">3h 41m</span>
                    <span style="font-family: var(--mono); font-size: 9px; letter-spacing: .12em; text-transform: uppercase; color: var(--warn);">a timer's running</span>
                    <a href="#" style="margin-left: auto; font-family: var(--mono); font-size: 10px; letter-spacing: .08em; text-transform: uppercase; color: var(--accent);">Time ›</a>
                  </div>
                </div>
                <div style="background: var(--surface); border: 1px solid var(--line); border-radius: 6px; padding: 16px 18px; margin-bottom: 18px;">
                  <span style="display: block; font-family: var(--mono); font-size: 11px; text-transform: uppercase; letter-spacing: .14em; color: var(--ink-quiet); margin-bottom: 10px;">Meetings</span>
                  <a href="#" style="display: flex; align-items: baseline; gap: 10px; padding: 9px 0;">
                    <span style="font-family: var(--mono); font-size: 10px; letter-spacing: .06em; text-transform: uppercase; color: var(--accent); white-space: nowrap; width: 52px; flex: none; display: flex; align-items: center; gap: 5px;"><span style="width: 6px; height: 6px; border-radius: 50%; background: var(--accent); flex: none;"></span>live</span>
                    <span style="min-width: 0; flex: 1;"><span style="display: block; font-family: var(--prose); font-size: 14px; color: var(--ink);">Brightside weekly</span><span style="display: block; font-family: var(--prose); font-size: 12px; color: var(--ink-quiet);">in Formation · Dana R.</span></span>
                  </a>
                  <a href="#" style="display: flex; align-items: baseline; gap: 10px; padding: 9px 0; border-top: 1px solid var(--line-quiet);">
                    <span style="font-family: var(--mono); font-size: 10px; letter-spacing: .06em; text-transform: uppercase; color: var(--ink-quiet); white-space: nowrap; width: 52px; flex: none;">2:30pm</span>
                    <span style="min-width: 0; flex: 1;"><span style="display: block; font-family: var(--prose); font-size: 14px; color: var(--ink);">Walkthrough — Vine Street</span><span style="display: block; font-family: var(--prose); font-size: 12px; color: var(--ink-quiet);">1200 Vine St · Marcus</span></span>
                  </a>
                </div>
                <div style="background: var(--surface); border: 1px solid var(--line); border-radius: 6px; padding: 16px 18px; margin-bottom: 18px;">
                  <span style="display: block; font-family: var(--mono); font-size: 11px; text-transform: uppercase; letter-spacing: .14em; color: var(--ink-quiet); margin-bottom: 10px;">Today's line</span>
                  <div style="font-family: var(--serif); font-size: 17px; color: var(--ink); line-height: 1.4;">"Do the work in front of you, and let it be enough."</div>
                  <div style="color: var(--ink-quiet); font-size: 13px; margin-top: 6px;">— a note I left myself</div>
                </div>
                <div style="background: var(--surface); border: 1px solid var(--line); border-radius: 6px; padding: 16px 18px; margin-bottom: 18px;">
                  <span style="display: block; font-family: var(--mono); font-size: 11px; text-transform: uppercase; letter-spacing: .14em; color: var(--ink-quiet); margin-bottom: 10px;">Need a hand?</span>
                  <a href="#" style="display: block; border: 1px solid var(--line); border-radius: 4px; padding: 10px 12px; font-size: 14px; color: var(--ink-body); margin-top: 8px;">Something's broken ›</a>
                  <a href="#" style="display: block; border: 1px solid var(--line); border-radius: 4px; padding: 10px 12px; font-size: 14px; color: var(--ink-body); margin-top: 8px;">I need something ›</a>
                </div>
              </div>
            </div>
          </div>

          <div data-screen="today" style="display: none; padding: 28px 34px;">
            <div style="max-width: 940px;">
              <div style="margin-bottom: 30px;">
                <div style="font-family: var(--mono); font-size: 11px; letter-spacing: .16em; text-transform: uppercase; color: var(--ink-quiet); margin-bottom: 10px;">Planning today · Wednesday, August 19</div>
                <h1 style="font-family: var(--serif); font-weight: 600; font-size: 30px; line-height: 1.12; color: var(--ink); margin: 0; letter-spacing: -0.015em;">23 things are open. Let's find today's four.</h1>
                <div style="font-family: var(--prose); font-size: 15px; color: var(--ink-quiet); margin-top: 8px;">23 open across everything · 5 waiting on somebody else, not shown.</div>
              </div>

              <section style="margin-bottom: 34px; background: var(--accent-wash); border: 1px solid var(--accent-line); border-radius: 10px; padding: 22px 24px;">
                <div style="font-family: var(--mono); font-size: 11px; letter-spacing: .14em; text-transform: uppercase; color: var(--accent); margin-bottom: 14px;">1 · What today already holds<span style="display: inline-flex; align-items: center; justify-content: center; width: 18px; height: 18px; border-radius: 50%; background: var(--accent); color: #fff; font-family: var(--mono); font-size: 10px; vertical-align: middle; margin-left: 10px;">5</span></div>
                <div style="display: flex; gap: 14px; flex-wrap: wrap;">
                  <a href="#" style="flex: 1 1 240px; min-width: 220px; display: flex; flex-direction: column; gap: 4px; padding: 14px 16px; background: var(--surface); border: 1px solid var(--line); border-radius: 8px;">
                    <span style="font-family: var(--serif); font-weight: 600; font-size: 15px; color: var(--ink);">9:00am · Brightside weekly</span>
                    <span style="font-family: var(--mono); font-size: 10px; letter-spacing: .06em; text-transform: uppercase; color: var(--ink-quiet);">in Formation · 30 minutes</span>
                  </a>
                  <a href="#" style="flex: 1 1 240px; min-width: 220px; display: flex; flex-direction: column; gap: 4px; padding: 14px 16px; background: var(--surface); border: 1px solid var(--line); border-radius: 8px;">
                    <span style="font-family: var(--serif); font-weight: 600; font-size: 15px; color: var(--ink);">2:30pm · Walkthrough, Vine Street</span>
                    <span style="font-family: var(--mono); font-size: 10px; letter-spacing: .06em; text-transform: uppercase; color: var(--ink-quiet);">1200 Vine St · 22 miles round trip</span>
                  </a>
                  <div style="flex: 1 1 240px; min-width: 220px; display: flex; flex-direction: column; gap: 4px; padding: 14px 16px; background: transparent; border: 1px dashed var(--line); border-radius: 8px;">
                    <span style="font-family: var(--serif); font-weight: 600; font-size: 15px; color: var(--ink);">School pickup at 3:15</span>
                    <span style="font-family: var(--mono); font-size: 10px; letter-spacing: .06em; text-transform: uppercase; color: var(--ink-quiet);">stated once, not a budget</span>
                  </div>
                </div>
                <div style="font-family: var(--prose); font-size: 13.5px; line-height: 1.6; color: var(--ink-quiet); font-style: italic; margin-top: 14px; max-width: 720px;">The constraints come first, and they're facts rather than a budget — nothing here subtracts hours from a capacity bar. You're a person, not a resource with a utilization.</div>
              </section>

              <section style="margin-bottom: 34px;">
                <div style="font-family: var(--mono); font-size: 11px; letter-spacing: .14em; text-transform: uppercase; color: var(--ink-quiet); margin-bottom: 14px;">2 · Yesterday's, if you still want them<span style="display: inline-flex; align-items: center; justify-content: center; width: 18px; height: 18px; border-radius: 50%; background: var(--accent); color: #fff; font-family: var(--mono); font-size: 10px; vertical-align: middle; margin-left: 10px;">6</span></div>
                <div style="border: 1px solid var(--line); border-radius: 9px; overflow: hidden; background: var(--surface);">
                  <div style="display: flex; align-items: center; gap: 16px; padding: 13px 16px;">
                    <div style="flex: 1; min-width: 0; display: flex; align-items: baseline; gap: 12px; flex-wrap: wrap;"><span style="font-family: var(--prose); font-size: 15px; color: var(--ink);">Photograph the finished cabinets</span><span style="font-family: var(--mono); font-size: 10px; letter-spacing: .06em; text-transform: uppercase; color: var(--ink-faint); white-space: nowrap;">Brightside rebuild</span></div>
                    <button type="button" style="flex: none; background: none; border: 1px solid var(--line); border-radius: 20px; padding: 5px 13px; font-family: var(--mono); font-size: 11px; letter-spacing: .04em; color: var(--ink-quiet); cursor: pointer; white-space: nowrap;">↻ Again</button>
                  </div>
                  <div style="display: flex; align-items: center; gap: 16px; padding: 13px 16px; border-top: 1px solid var(--line-quiet);">
                    <div style="flex: 1; min-width: 0; display: flex; align-items: baseline; gap: 12px; flex-wrap: wrap;"><span style="font-family: var(--prose); font-size: 15px; color: var(--ink);">Call the supplier back about the hinges</span><span style="font-family: var(--mono); font-size: 10px; letter-spacing: .06em; text-transform: uppercase; color: var(--ink-faint); white-space: nowrap;">Vine Street clinic</span></div>
                    <button type="button" style="flex: none; background: none; border: 1px solid var(--line); border-radius: 20px; padding: 5px 13px; font-family: var(--mono); font-size: 11px; letter-spacing: .04em; color: var(--ink-quiet); cursor: pointer; white-space: nowrap;">↻ Again</button>
                  </div>
                </div>
                <div style="font-family: var(--prose); font-size: 13.5px; line-height: 1.6; color: var(--ink-quiet); font-style: italic; margin-top: 14px; max-width: 720px;">Offered, never re-starred. They arrive unstarred, with no age and no colour — and if you ignore them three days running they simply stop being offered and go back to the pile.</div>
              </section>

              <section style="margin-bottom: 34px;">
                <div style="display: flex; align-items: baseline; justify-content: space-between; gap: 16px; flex-wrap: wrap; font-family: var(--mono); font-size: 11px; letter-spacing: .14em; text-transform: uppercase; color: var(--ink-quiet); margin-bottom: 14px;">
                  <span>3 · The pile · everything open, by client</span>
                  <span style="display: flex; gap: 4px;">
                    <a href="#" style="font-family: var(--mono); font-size: 10px; letter-spacing: .08em; text-transform: uppercase; color: var(--accent); padding: 4px 10px; border: 1px solid var(--accent); border-radius: 20px; background: var(--accent-wash);">By client</a>
                    <a href="#" style="font-family: var(--mono); font-size: 10px; letter-spacing: .08em; text-transform: uppercase; color: var(--ink-quiet); padding: 4px 10px; border: 1px solid var(--line); border-radius: 20px;">By project</a>
                    <a href="#" style="font-family: var(--mono); font-size: 10px; letter-spacing: .08em; text-transform: uppercase; color: var(--ink-quiet); padding: 4px 10px; border: 1px solid var(--line); border-radius: 20px;">Oldest first</a>
                  </span>
                </div>

                <div style="border: 1px solid var(--accent-line); border-radius: 9px; overflow: hidden; background: var(--surface); margin-bottom: 16px;">
                  <div style="display: flex; align-items: baseline; justify-content: space-between; gap: 12px; padding: 11px 16px; background: var(--accent-wash); border-bottom: 1px solid var(--accent-line);">
                    <span style="font-family: var(--mono); font-size: 11px; letter-spacing: .1em; text-transform: uppercase; color: var(--accent);">Caught, not filed · the Inbox</span>
                    <span style="font-family: var(--mono); font-size: 10px; letter-spacing: .06em; text-transform: uppercase; color: var(--ink-quiet);">2 unfiled</span>
                  </div>
                  <div style="display: flex; align-items: center; gap: 16px; padding: 13px 16px;">
                    <div style="flex: 1; min-width: 0;"><span style="font-family: var(--prose); font-size: 15px; color: var(--ink);">Ask Lindsay about the trailer weekend</span></div>
                    <span style="font-family: var(--mono); font-size: 11px; letter-spacing: .04em; color: var(--ink-quiet); border: 1px solid var(--line); border-radius: 20px; padding: 5px 13px;">Give it a project ▾</span>
                    <button type="button" style="flex: none; background: none; border: 1px solid var(--line); border-radius: 20px; padding: 5px 13px; font-family: var(--mono); font-size: 11px; color: var(--ink-quiet); cursor: pointer;">☆</button>
                  </div>
                  <div style="display: flex; align-items: center; gap: 16px; padding: 13px 16px; border-top: 1px solid var(--line-quiet);">
                    <div style="flex: 1; min-width: 0;"><span style="font-family: var(--prose); font-size: 15px; color: var(--ink);">Find out what the state form actually wants</span></div>
                    <span style="font-family: var(--mono); font-size: 11px; letter-spacing: .04em; color: var(--ink-quiet); border: 1px solid var(--line); border-radius: 20px; padding: 5px 13px;">Give it a project ▾</span>
                    <button type="button" style="flex: none; background: none; border: 1px solid var(--accent); border-radius: 20px; padding: 5px 13px; font-family: var(--mono); font-size: 11px; color: var(--accent); background: var(--accent-wash); cursor: pointer;">★ picked</button>
                  </div>
                  <div style="font-family: var(--prose); font-size: 13.5px; line-height: 1.6; color: var(--ink-quiet); font-style: italic; padding: 0 16px 14px; max-width: 720px;">Two moves, either order: star it for today, or give it a project. Starring doesn't file it.</div>
                </div>

                <div style="border: 1px solid var(--line); border-radius: 9px; overflow: hidden; background: var(--surface); margin-bottom: 16px;">
                  <div style="display: flex; align-items: baseline; justify-content: space-between; gap: 12px; padding: 11px 16px; background: var(--surface-quiet); border-bottom: 1px solid var(--line);">
                    <span style="font-family: var(--mono); font-size: 11px; letter-spacing: .1em; text-transform: uppercase; color: var(--ink-body);">Brightside Dental</span>
                    <span style="font-family: var(--mono); font-size: 10px; letter-spacing: .06em; text-transform: uppercase; color: var(--ink-quiet);">5 open · 1 waiting</span>
                  </div>
                  <div style="display: flex; align-items: center; gap: 16px; padding: 13px 16px; background: color-mix(in srgb, var(--accent) 6%, var(--surface));">
                    <div style="flex: 1; min-width: 0; display: flex; align-items: baseline; gap: 12px; flex-wrap: wrap;"><span style="font-family: var(--prose); font-size: 15px; color: var(--accent);">Write the invoice copy</span><span style="font-family: var(--mono); font-size: 10px; letter-spacing: .06em; text-transform: uppercase; color: var(--ink-faint); white-space: nowrap;">due today</span></div>
                    <button type="button" style="flex: none; border: 1px solid var(--accent); border-radius: 20px; padding: 5px 13px; font-family: var(--mono); font-size: 11px; color: var(--accent); background: var(--accent-wash); cursor: pointer;">★ picked</button>
                  </div>
                  <div style="display: flex; align-items: center; gap: 16px; padding: 13px 16px; border-top: 1px solid var(--line-quiet);">
                    <div style="flex: 1; min-width: 0; display: flex; align-items: baseline; gap: 12px; flex-wrap: wrap;"><span style="font-family: var(--prose); font-size: 15px; color: var(--ink);">Swap the two hero photos</span><span style="font-family: var(--mono); font-size: 10px; letter-spacing: .06em; text-transform: uppercase; color: var(--ink-faint); white-space: nowrap;">11 days</span></div>
                    <button type="button" style="flex: none; background: none; border: 1px solid var(--line); border-radius: 20px; padding: 5px 13px; font-family: var(--mono); font-size: 11px; color: var(--ink-quiet); cursor: pointer;">☆</button>
                  </div>
                  <div style="display: flex; align-items: center; gap: 16px; padding: 13px 16px; border-top: 1px solid var(--line-quiet); background: var(--surface-quiet);">
                    <div style="flex: 1; min-width: 0;"><span style="font-family: var(--mono); font-size: 11px; letter-spacing: .08em; text-transform: uppercase; color: var(--ink-faint); white-space: nowrap;">3 more · 1 waiting on Dana</span></div>
                    <span style="flex: none; color: var(--ink-faint); font-size: 13px;">↓</span>
                  </div>
                </div>

                <div style="border: 1px solid var(--line); border-radius: 9px; overflow: hidden; background: var(--surface); margin-bottom: 16px;">
                  <div style="display: flex; align-items: baseline; justify-content: space-between; gap: 12px; padding: 11px 16px; background: var(--surface-quiet); border-bottom: 1px solid var(--line);">
                    <span style="font-family: var(--mono); font-size: 11px; letter-spacing: .1em; text-transform: uppercase; color: var(--ink-body);">Vine Street clinic</span>
                    <span style="font-family: var(--mono); font-size: 10px; letter-spacing: .06em; text-transform: uppercase; color: var(--ink-quiet);">4 open · 2 waiting</span>
                  </div>
                  <div style="display: flex; align-items: center; gap: 16px; padding: 13px 16px;">
                    <div style="flex: 1; min-width: 0; display: flex; align-items: baseline; gap: 12px; flex-wrap: wrap;"><span style="font-family: var(--prose); font-size: 15px; color: var(--ink);">Send Dana the revised estimate</span><span style="font-family: var(--mono); font-size: 10px; letter-spacing: .06em; text-transform: uppercase; color: var(--ink-faint); white-space: nowrap;">2 days</span></div>
                    <button type="button" style="flex: none; border: 1px solid var(--accent); border-radius: 20px; padding: 5px 13px; font-family: var(--mono); font-size: 11px; color: var(--accent); background: var(--accent-wash); cursor: pointer;">★ picked</button>
                  </div>
                  <div style="display: flex; align-items: center; gap: 16px; padding: 13px 16px; border-top: 1px solid var(--line-quiet);">
                    <div style="flex: 1; min-width: 0; display: flex; align-items: baseline; gap: 12px; flex-wrap: wrap;"><span style="font-family: var(--prose); font-size: 15px; color: var(--ink);">Their card reader won't take taps</span><span style="font-family: var(--mono); font-size: 10px; letter-spacing: .06em; text-transform: uppercase; color: var(--ink-faint); white-space: nowrap;">GC-114 · 3 days</span></div>
                    <button type="button" style="flex: none; border: 1px solid var(--accent); border-radius: 20px; padding: 5px 13px; font-family: var(--mono); font-size: 11px; color: var(--accent); background: var(--accent-wash); cursor: pointer;">★ picked</button>
                  </div>
                </div>
              </section>

              <section style="margin-bottom: 34px; background: var(--accent-wash); border: 1px solid var(--accent-line); border-radius: 10px; padding: 22px 24px;">
                <div style="font-family: var(--mono); font-size: 11px; letter-spacing: .14em; text-transform: uppercase; color: var(--accent); margin-bottom: 14px;">4 · That's the day</div>
                <h2 style="font-family: var(--serif); font-weight: 600; font-size: 22px; line-height: 1.2; color: var(--ink); margin: 6px 0 14px; letter-spacing: -0.015em;">4 picked, 2 appointments, about 2 hours already gone.</h2>
                <div style="display: flex; align-items: center; justify-content: space-between; gap: 20px; flex-wrap: wrap;">
                  <span style="font-family: var(--prose); font-size: 13.5px; line-height: 1.6; color: var(--ink-quiet); font-style: italic; max-width: 520px;">Said once, in plain words, and then it gets out of the way. No warning, no capacity bar, and nothing stops you starring a fifth.</span>
                  <a href="#" style="font-family: var(--mono); font-size: 12px; letter-spacing: .12em; text-transform: uppercase; padding: 11px 20px; border-radius: 3px; background: var(--accent); border: 1px solid var(--accent); color: #fff;">✓ Start the day</a>
                </div>
              </section>

              <div style="font-family: var(--prose); font-size: 13px; line-height: 1.6; color: var(--ink-faint); border-top: 1px solid var(--line-quiet); padding-top: 16px; margin-top: 30px; max-width: 720px;">Order matters: the day first, then what carried over, then the pile. Showing the pile before the constraints is how every other tool produces an impossible day.</div>
            </div>
          </div>
        </main>
      </div>

    </div>
    </div>

    
      <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 22px 30px; margin-top: 24px; padding-top: 22px; border-top: 1px solid var(--line);">
        <div style="display: flex; gap: 12px; align-items: flex-start;">
          <span style="flex: none; display: flex; align-items: center; justify-content: center; width: 22px; height: 22px; border-radius: 50%; background: var(--accent); color: #fff; font-family: var(--mono); font-size: 11px;">1</span>
          <div>
            <div style="font-family: var(--mono); font-size: 10px; letter-spacing: .14em; text-transform: uppercase; color: var(--accent); margin-bottom: 5px;">Two numbers, total</div>
            <div style="font-family: var(--prose); font-size: 15px; line-height: 1.65; color: var(--ink-body);">The whole sidebar is allowed exactly two figures: how many things you picked for today, and a timer that is running. No unread badges, no counts that imply you are behind.</div>
          </div>
        </div>
        <div style="display: flex; gap: 12px; align-items: flex-start;">
          <span style="flex: none; display: flex; align-items: center; justify-content: center; width: 22px; height: 22px; border-radius: 50%; background: var(--accent); color: #fff; font-family: var(--mono); font-size: 11px;">2</span>
          <div>
            <div style="font-family: var(--mono); font-size: 10px; letter-spacing: .14em; text-transform: uppercase; color: var(--accent); margin-bottom: 5px;">The strip follows you</div>
            <div style="font-family: var(--prose); font-size: 15px; line-height: 1.65; color: var(--ink-body);">One timer per project, startable from any task row, pinned to every screen. Leave one running late and it offers to end it at the top of the hour instead of billing you nine hours.</div>
          </div>
        </div>
        <div style="display: flex; gap: 12px; align-items: flex-start;">
          <span style="flex: none; display: flex; align-items: center; justify-content: center; width: 22px; height: 22px; border-radius: 50%; background: var(--accent); color: #fff; font-family: var(--mono); font-size: 11px;">3</span>
          <div>
            <div style="font-family: var(--mono); font-size: 10px; letter-spacing: .14em; text-transform: uppercase; color: var(--accent); margin-bottom: 5px;">A sentence, not a stat</div>
            <div style="font-family: var(--prose); font-size: 15px; line-height: 1.65; color: var(--ink-body);">"Twelve people want something, four of them are waiting on you." Every other tool shows you 12 and a red badge.</div>
          </div>
        </div>
        <div style="display: flex; gap: 12px; align-items: flex-start;">
          <span style="flex: none; display: flex; align-items: center; justify-content: center; width: 22px; height: 22px; border-radius: 50%; background: var(--accent); color: #fff; font-family: var(--mono); font-size: 11px;">4</span>
          <div>
            <div style="font-family: var(--mono); font-size: 10px; letter-spacing: .14em; text-transform: uppercase; color: var(--accent); margin-bottom: 5px;">Nothing is instantly final</div>
            <div style="font-family: var(--prose); font-size: 15px; line-height: 1.65; color: var(--ink-body);">Tick a task above: it strikes through and hands you an Undo for about eight seconds before it settles. A mis-tick is never a loss.</div>
          </div>
        </div>
        <div style="display: flex; gap: 12px; align-items: flex-start;">
          <span style="flex: none; display: flex; align-items: center; justify-content: center; width: 22px; height: 22px; border-radius: 50%; background: var(--accent); color: #fff; font-family: var(--mono); font-size: 11px;">5</span>
          <div>
            <div style="font-family: var(--mono); font-size: 10px; letter-spacing: .14em; text-transform: uppercase; color: var(--accent); margin-bottom: 5px;">Constraints before the pile</div>
            <div style="font-family: var(--prose); font-size: 15px; line-height: 1.65; color: var(--ink-body);">On Planning today, what the day already holds comes first — meetings, drive time, school pickup. Showing the pile first is how every other planner produces an impossible day.</div>
          </div>
        </div>
        <div style="display: flex; gap: 12px; align-items: flex-start;">
          <span style="flex: none; display: flex; align-items: center; justify-content: center; width: 22px; height: 22px; border-radius: 50%; background: var(--accent); color: #fff; font-family: var(--mono); font-size: 11px;">6</span>
          <div>
            <div style="font-family: var(--mono); font-size: 10px; letter-spacing: .14em; text-transform: uppercase; color: var(--accent); margin-bottom: 5px;">Yesterday is an offer</div>
            <div style="font-family: var(--prose); font-size: 15px; line-height: 1.65; color: var(--ink-body);">Carry-over arrives unstarred, with no age and no colour, and nothing is ever labelled overdue. Ignore an offer three mornings running and it quietly goes back to the pile.</div>
          </div>
        </div>
        <div style="display: flex; gap: 12px; align-items: flex-start;">
          <span style="flex: none; display: flex; align-items: center; justify-content: center; width: 22px; height: 22px; border-radius: 50%; background: var(--accent); color: #fff; font-family: var(--mono); font-size: 11px;">7</span>
          <div>
            <div style="font-family: var(--mono); font-size: 10px; letter-spacing: .14em; text-transform: uppercase; color: var(--accent); margin-bottom: 5px;">Yes, that is a music player</div>
            <div style="font-family: var(--prose); font-size: 15px; line-height: 1.65; color: var(--ink-body);">Because I wanted one, and I am the whole product committee. It sits under the lenses, it is three lines tall, and it never once tells you how many minutes you listened. Nobody asked me for this — but when somebody does ask me for something, that is exactly how fast it gets built.</div>
          </div>
        </div>
      </div>
    


    <div style="display: flex; flex-wrap: wrap; gap: 26px; margin-top: 16px; font-family: var(--mono); font-size: 10px; letter-spacing: .14em; text-transform: uppercase; color: var(--ink-faint); white-space: nowrap;">
      <span>Live controls · tick a task, hit Undo</span>
      <span>Both screens · switch above, or click Today in the sidebar</span>
      <span>Demo data · a practice a lot like mine</span>
      <span>Night flight is a tweak away</span>
    </div>
  </section>

  <section style="margin-bottom: 46px; padding-top: 30px; border-top: 2px solid var(--line);">
    <div style="border-left: 2px solid var(--accent); padding-left: 24px;">
      <div style="font-family: var(--mono); font-size: 11px; letter-spacing: .16em; text-transform: uppercase; color: var(--accent); margin-bottom: 12px;">The best thing about it</div>
      <h2 style="font-family: var(--serif); font-weight: 600; font-size: 36px; line-height: 1.1; letter-spacing: -0.015em; margin: 0 0 18px; max-width: 26ch; text-wrap: pretty;">Ask me for something and the answer is almost always yes.</h2>
      <p style="font-family: var(--prose); font-size: 18px; line-height: 1.8; color: var(--ink-body); max-width: 66ch; margin: 0 0 16px;">That isn't a support promise — it's how the thing is built. I'm the only person who has to agree, there's no roadmap committee, and most of what people ask for is a config field I haven't written yet. So it gets written.</p>
      <p style="font-family: var(--prose); font-size: 17px; line-height: 1.8; color: var(--ink-quiet); max-width: 66ch; margin: 0 0 24px;">Every dead end in the app carries a line that says <em>tell me and I'll build it in</em>, and it goes straight to me. That's the whole support model, and it's why Cloudbase ends up looking like your practice instead of mine.</p>
    </div>
    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 18px; margin-top: 26px;">
      <div style="background: var(--surface); border: 1px solid var(--line); border-radius: 6px; padding: 20px 22px;">
        <div style="font-family: var(--mono); font-size: 10px; letter-spacing: .14em; text-transform: uppercase; color: var(--ink-quiet); margin-bottom: 8px;">Your words win</div>
        <div style="font-family: var(--prose); font-size: 16px; line-height: 1.7; color: var(--ink-body);">Clients, customers, students, families, parishioners — you name them once and every screen, button, report and email uses your word. Same for a project, and for a unit of work.</div>
      </div>
      <div style="background: var(--surface); border: 1px solid var(--line); border-radius: 6px; padding: 20px 22px;">
        <div style="font-family: var(--mono); font-size: 10px; letter-spacing: .14em; text-transform: uppercase; color: var(--ink-quiet); margin-bottom: 8px;">Your project screen</div>
        <div style="font-family: var(--prose); font-size: 16px; line-height: 1.7; color: var(--ink-body);">Pick the panels, the layout and your own custom fields in a split-screen builder that shows the real page as you set it up. A project page for a contractor and one for a tutor share no furniture.</div>
      </div>
      <div style="background: var(--surface); border: 1px solid var(--line); border-radius: 6px; padding: 20px 22px;">
        <div style="font-family: var(--mono); font-size: 10px; letter-spacing: .14em; text-transform: uppercase; color: var(--ink-quiet); margin-bottom: 8px;">Your pay model</div>
        <div style="font-family: var(--prose); font-size: 16px; line-height: 1.7; color: var(--ink-body);">Salary, hourly, fixed fee, a fully custom bonus schedule, or not billed at all. Unpaid work reads <b style="font-weight: 600;">INVESTED</b>, never $0.00 — because those aren't the same thing.</div>
      </div>
      <div style="background: var(--surface); border: 1px solid var(--line); border-radius: 6px; padding: 20px 22px;">
        <div style="font-family: var(--mono); font-size: 10px; letter-spacing: .14em; text-transform: uppercase; color: var(--ink-quiet); margin-bottom: 8px;">Your lens</div>
        <div style="font-family: var(--prose); font-size: 16px; line-height: 1.7; color: var(--ink-body);">A mode hides the instruments you're not using this afternoon and filters who you're working for. Hiding something never stops it recording, and never deletes anything.</div>
      </div>
    </div>
  </section>

  <section style="margin-bottom: 46px; padding-top: 30px; border-top: 2px solid var(--line);">
    <div style="font-family: var(--mono); font-size: 11px; letter-spacing: .16em; text-transform: uppercase; color: var(--ink-quiet); margin-bottom: 12px;">What's inside</div>
    <h2 style="font-family: var(--serif); font-weight: 600; font-size: 36px; line-height: 1.1; letter-spacing: -0.015em; margin: 0 0 8px;">Eleven instruments, one ship.</h2>
    <p style="font-family: var(--prose); font-size: 16px; line-height: 1.7; color: var(--ink-quiet); max-width: 76ch; margin: 0 0 24px;">Turn any of them off per project and the seam reads "soon", not "upgrade". Two of them cost twelve dollars extra; the rest come with it.</p>
    <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px;">
      <div style="background: var(--surface); border: 1px solid var(--line); border-radius: 6px; padding: 16px 18px;">
        <div style="font-family: var(--serif); font-weight: 600; font-size: 19px; margin-bottom: 6px;">Today</div>
        <div style="font-family: var(--prose); font-size: 15px; line-height: 1.6; color: var(--ink-quiet);">The planning session. Holds, then carry-over, then the pile, then the day in a sentence.</div>
      </div>
      <div style="background: var(--surface); border: 1px solid var(--line); border-radius: 6px; padding: 16px 18px;">
        <div style="font-family: var(--serif); font-weight: 600; font-size: 19px; margin-bottom: 6px;">Projects</div>
        <div style="font-family: var(--prose); font-size: 15px; line-height: 1.6; color: var(--ink-quiet);">Configurable pages with phases, sub-tasks, rhythms, notes and the people involved.</div>
      </div>
      <div style="background: var(--surface); border: 1px solid var(--line); border-radius: 6px; padding: 16px 18px;">
        <div style="font-family: var(--serif); font-weight: 600; font-size: 19px; margin-bottom: 6px;">Tickets</div>
        <div style="font-family: var(--prose); font-size: 15px; line-height: 1.6; color: var(--ink-quiet);">Requests sorted by whose move it is. The row you type is the row it becomes. Closing one says SORTED.</div>
      </div>
      <div style="background: var(--surface); border: 1px solid var(--line); border-radius: 6px; padding: 16px 18px;">
        <div style="font-family: var(--serif); font-weight: 600; font-size: 19px; margin-bottom: 6px;">Ground Control <span style="font-family: var(--mono); font-size: 9px; letter-spacing: .12em; color: var(--accent); border: 1px solid var(--accent-line); border-radius: 3px; padding: 2px 5px; vertical-align: middle;">+$12</span></div>
        <div style="font-family: var(--prose); font-size: 15px; line-height: 1.6; color: var(--ink-quiet);">The doors other people come in through: public intake, changes, releases, estimates they decide on without an account.</div>
      </div>
      <div style="background: var(--surface); border: 1px solid var(--line); border-radius: 6px; padding: 16px 18px;">
        <div style="font-family: var(--serif); font-weight: 600; font-size: 19px; margin-bottom: 6px;">Time</div>
        <div style="font-family: var(--prose); font-size: 15px; line-height: 1.6; color: var(--ink-quiet);">One timer per project, startable anywhere, add-after-the-fact, and the only chart in the app — twelve weeks of hours with no target line.</div>
      </div>
      <div style="background: var(--surface); border: 1px solid var(--line); border-radius: 6px; padding: 16px 18px;">
        <div style="font-family: var(--serif); font-weight: 600; font-size: 19px; margin-bottom: 6px;">Mileage</div>
        <div style="font-family: var(--prose); font-size: 15px; line-height: 1.6; color: var(--ink-quiet);">Two odometer readings and a route. Miles derived, the rate copied at log time, vehicles retired and never deleted.</div>
      </div>
      <div style="background: var(--surface); border: 1px solid var(--line); border-radius: 6px; padding: 16px 18px;">
        <div style="font-family: var(--serif); font-weight: 600; font-size: 19px; margin-bottom: 6px;">Meetings</div>
        <div style="font-family: var(--prose); font-size: 15px; line-height: 1.6; color: var(--ink-quiet);">A before, a during and an after. Move one instance without dragging the series; turn an action item into a task or a ticket.</div>
      </div>
      <div style="background: var(--surface); border: 1px solid var(--line); border-radius: 6px; padding: 16px 18px;">
        <div style="font-family: var(--serif); font-weight: 600; font-size: 19px; margin-bottom: 6px;">Formation <span style="font-family: var(--mono); font-size: 9px; letter-spacing: .12em; color: var(--accent); border: 1px solid var(--accent-line); border-radius: 3px; padding: 2px 5px; vertical-align: middle;">+$12</span></div>
        <div style="font-family: var(--prose); font-size: 15px; line-height: 1.6; color: var(--ink-quiet);">Video calls in the browser. No accounts, no install — guests join from a link, and the notes land in the meeting record.</div>
      </div>
      <div style="background: var(--surface); border: 1px solid var(--line); border-radius: 6px; padding: 16px 18px;">
        <div style="font-family: var(--serif); font-weight: 600; font-size: 19px; margin-bottom: 6px;">The Logbook</div>
        <div style="font-family: var(--prose); font-size: 15px; line-height: 1.6; color: var(--ink-quiet);">A writing room at a real reading size. Select a line and make something of it — a task, a ticket, a document — and the note stays whole.</div>
      </div>
      <div style="background: var(--surface); border: 1px solid var(--line); border-radius: 6px; padding: 16px 18px;">
        <div style="font-family: var(--serif); font-weight: 600; font-size: 19px; margin-bottom: 6px;">Files</div>
        <div style="font-family: var(--prose); font-size: 15px; line-height: 1.6; color: var(--ink-quiet);">No folder tree, ever. A file can't exist without a host, so ticking a task never loses its attachment. Paste is the primary path.</div>
      </div>
      <div style="background: var(--surface); border: 1px solid var(--line); border-radius: 6px; padding: 16px 18px;">
        <div style="font-family: var(--serif); font-weight: 600; font-size: 19px; margin-bottom: 6px;">Reports &amp; Views</div>
        <div style="font-family: var(--prose); font-size: 15px; line-height: 1.6; color: var(--ink-quiet);">Filters that read as sentences over your own fields. Add a schedule and the same saved view becomes a report that runs at 4am — silent when there's nothing.</div>
      </div>
      <div style="background: var(--surface-quiet); border: 1px dashed var(--line-strong); border-radius: 6px; padding: 16px 18px;">
        <div style="font-family: var(--serif); font-weight: 600; font-size: 19px; margin-bottom: 6px;">The one you need</div>
        <div style="font-family: var(--prose); font-size: 15px; line-height: 1.6; color: var(--ink-quiet);">Not here yet. Tell me and I'll build it in — that's the line at every dead end in the app, and it comes to me.</div>
      </div>
    </div>
  </section>

  <section class="cb-navy" style="background: var(--navy, #11203b); color: #fff; border-radius: 8px; padding: 44px 46px; margin-bottom: 46px;">
    <div style="font-family: var(--mono); font-size: 11px; letter-spacing: .16em; text-transform: uppercase; color: #8fb0ff; margin-bottom: 14px;">What it refuses to do</div>
    <h2 style="font-family: var(--serif); font-weight: 600; font-size: 36px; line-height: 1.1; letter-spacing: -0.015em; margin: 0 0 10px; color: #fff; max-width: 24ch;">Nothing in here scores you.</h2>
    <p style="font-family: var(--prose); font-size: 18px; line-height: 1.8; color: rgba(255,255,255,.82); max-width: 62ch; margin: 0 0 30px;">Most of this software's design work went into things it deliberately doesn't have. These are rules, not preferences — a screen that breaks one is a failed screen.</p>
    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 26px 40px;">
      <div>
        <div style="font-family: var(--mono); font-size: 10px; letter-spacing: .14em; text-transform: uppercase; color: #8fb0ff; margin-bottom: 6px;">No score, no streak</div>
        <div style="font-family: var(--prose); font-size: 16px; line-height: 1.7; color: rgba(255,255,255,.82);">No productivity number, no capacity bar, no goal, no word count while you write. One chart in the whole product, and a week off is pale, never red.</div>
      </div>
      <div>
        <div style="font-family: var(--mono); font-size: 10px; letter-spacing: .14em; text-transform: uppercase; color: #8fb0ff; margin-bottom: 6px;">No counts that imply debt</div>
        <div style="font-family: var(--prose); font-size: 16px; line-height: 1.7; color: rgba(255,255,255,.82);">No unread badges, no "7 unfiled", no inbox zero. Age is a plain fact in quiet ink — never bold, never red, and nothing is labelled overdue.</div>
      </div>
      <div>
        <div style="font-family: var(--mono); font-size: 10px; letter-spacing: .14em; text-transform: uppercase; color: #8fb0ff; margin-bottom: 6px;">Nothing is instantly final</div>
        <div style="font-family: var(--prose); font-size: 16px; line-height: 1.7; color: rgba(255,255,255,.82);">A tick holds for about eight seconds with an Undo before it settles. Offline keeps what you typed; a fault says "that's on me, not you" and hands you a ref code.</div>
      </div>
      <div>
        <div style="font-family: var(--mono); font-size: 10px; letter-spacing: .14em; text-transform: uppercase; color: #8fb0ff; margin-bottom: 6px;">Soft landings only</div>
        <div style="font-family: var(--prose); font-size: 16px; line-height: 1.7; color: rgba(255,255,255,.82);">No "upgrade now", no "you've reached your limit", no countdown. Stop paying and the workspace goes dormant, not deleted — everything exports, and the lamp's still where you left it.</div>
      </div>
    </div>
  </section>

  <section style="margin-bottom: 46px;">
    <div style="font-family: var(--mono); font-size: 11px; letter-spacing: .16em; text-transform: uppercase; color: var(--ink-quiet); margin-bottom: 12px;">How it's built</div>
    <div style="display: grid; grid-template-columns: 1.1fr 1fr; gap: 34px;">
      <div>
        <p style="font-family: var(--prose); font-size: 17px; line-height: 1.8; color: var(--ink-body); margin: 0 0 16px;">Flask with an app factory, SQLAlchemy 2.0, Alembic, Postgres on Neon, deployed to Fly.io with migrations on release. One shared core that ships single-tenant or multi-tenant, with per-request tenant binding as the enforced scoping layer — not a filter someone remembers to add.</p>
        <p style="font-family: var(--prose); font-size: 17px; line-height: 1.8; color: var(--ink-body); margin: 0;">No component library and no icon font: the interface is hairlines, four typefaces and Unicode glyphs set in mono. Server-rendered pages that swap only their main element, so the music never stops when you navigate. Past six hundred tests and still climbing.</p>
      </div>
      <div style="background: var(--surface); border: 1px solid var(--line); border-radius: 6px; padding: 20px 22px; align-self: start;">
        <div style="display: flex; justify-content: space-between; padding: 9px 0; font-size: 15px;"><span style="color: var(--ink-quiet);">Status</span><span style="font-family: var(--fig); color: var(--ok);">Live in production</span></div>
        <div style="display: flex; justify-content: space-between; padding: 9px 0; border-top: 1px solid var(--line-quiet); font-size: 15px;"><span style="color: var(--ink-quiet);">Home</span><span style="font-family: var(--fig);">cloudbase.day</span></div>
        <div style="display: flex; justify-content: space-between; padding: 9px 0; border-top: 1px solid var(--line-quiet); font-size: 15px;"><span style="color: var(--ink-quiet);">Tests</span><span style="font-family: var(--fig);">600+, green</span></div>
        <div style="display: flex; justify-content: space-between; padding: 9px 0; border-top: 1px solid var(--line-quiet); font-size: 15px;"><span style="color: var(--ink-quiet);">Team</span><span style="font-family: var(--fig);">1</span></div>
        <div style="display: flex; justify-content: space-between; padding: 9px 0; border-top: 1px solid var(--line-quiet); font-size: 15px;"><span style="color: var(--ink-quiet);">Dogfooded</span><span style="font-family: var(--fig);">every day</span></div>
      </div>
    </div>
  </section>

  <section style="border-top: 2px solid var(--line); padding-top: 34px; margin-bottom: 20px;">
    <h2 style="font-family: var(--serif); font-weight: 600; font-size: 36px; line-height: 1.1; letter-spacing: -0.015em; margin: 0 0 12px; max-width: 26ch; text-wrap: pretty;">If your practice is you, come look at it.</h2>
    <p style="font-family: var(--prose); font-size: 18px; line-height: 1.8; color: var(--ink-body); max-width: 62ch; margin: 0 0 24px;">Bring me the thing your current tool won't do. That's usually the shortest conversation we'll have, and I'd rather build it than talk you out of it.</p>
    <div style="display: flex; flex-wrap: wrap; gap: 10px;">
      <a href="https://cloudbase.day" style="font-family: var(--mono); font-size: 12px; letter-spacing: .12em; text-transform: uppercase; padding: 11px 20px; border-radius: 3px; background: var(--accent); border: 1px solid var(--accent); color: #fff;">Visit cloudbase.day →</a>
      <a href="/contact/" style="font-family: var(--mono); font-size: 12px; letter-spacing: .12em; text-transform: uppercase; padding: 11px 20px; border-radius: 3px; background: var(--surface); border: 1px solid var(--line); color: var(--ink-quiet);">⟩ Write to me</a>
      <a href="/tools/" style="font-family: var(--mono); font-size: 12px; letter-spacing: .12em; text-transform: uppercase; padding: 11px 20px; border-radius: 3px; background: var(--surface); border: 1px solid var(--line); color: var(--ink-quiet);">Back to the Workbench</a>
    </div>
  </section>

  <footer style="margin-top: 56px; padding-top: 24px; border-top: 1px solid var(--line); font-family: 'Share Tech Mono', monospace; font-size: 11.5px; letter-spacing: .06em; color: var(--ink-quiet);">
    <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px; margin-bottom: 20px;">
      <div>
        <p style="font-size: 9.3px; letter-spacing: .22em; text-transform: uppercase; color: var(--ink-faint); margin: 0 0 8px;">Navigate</p>
        <div style="display: flex; flex-direction: column; gap: 4px;">
          <a href="/" style="color: var(--ink-quiet);">Home</a><a href="/about/" style="color: var(--ink-quiet);">About</a><a href="/blog/" style="color: var(--ink-quiet);">Blog</a><a href="/work/" style="color: var(--ink-quiet);">Work</a><a href="/tools/" style="color: var(--ink-quiet);">Workbench</a><a href="/status.html" style="color: var(--ink-quiet);">Status</a><a href="/now/" style="color: var(--ink-quiet);">/now</a>
        </div>
      </div>
      <div>
        <p style="font-size: 9.3px; letter-spacing: .22em; text-transform: uppercase; color: var(--ink-faint); margin: 0 0 8px;">More</p>
        <div style="display: flex; flex-direction: column; gap: 4px;">
          <a href="/the-long-way" style="color: var(--ink-quiet);">The Long Way</a><a href="/splinched" style="color: var(--ink-quiet);">Splinched</a><a href="/selling" style="color: var(--ink-quiet);">Hire</a><a href="/colophon/" style="color: var(--ink-quiet);">Colophon</a><a href="/feed.xml" style="color: var(--ink-quiet);">Blog RSS</a>
        </div>
      </div>
      <div>
        <p style="font-size: 9.3px; letter-spacing: .22em; text-transform: uppercase; color: var(--ink-faint); margin: 0 0 8px;">Elsewhere</p>
        <div style="display: flex; flex-direction: column; gap: 4px;">
          <a href="/contact/" style="color: var(--ink-quiet);">Email</a>
        </div>
      </div>
    </div>
    <div style="text-align: center; padding: 14px 0; border-top: 1px solid var(--line); font-family: var(--prose); font-style: italic; font-size: 15px; letter-spacing: 0; color: var(--ink-quiet);">
      A letter, every two weeks — <a href="/the-long-way" style="color: var(--accent); border-bottom: 1px dotted var(--accent-line);">The Long Way →</a>
    </div>
    <div style="font-size: 10px; color: var(--ink-faint); padding-top: 14px; border-top: 1px solid var(--line); display: flex; align-items: center; flex-wrap: wrap; gap: 6px;">
      <span>Made by hand in Harrisburg, PA by <a href="/about/" style="color: var(--ink-faint);">Aaron Aiken</a></span>
      <span style="color: var(--line);">·</span>
      <a href="https://themarkup.org/blacklight?url=aaronaiken.me" style="color: var(--ink-faint);">not tracking you</a>
      <span style="color: var(--line);">·</span>
      <a href="/colophon/" style="color: var(--ink-faint);">colophon</a>
    </div>
    <div style="padding: 12px 0 34px; text-align: center; font-family: var(--prose); font-style: italic; font-size: 13px; color: var(--ink-faint); letter-spacing: 0;">Never tell me the odds.</div>
  </footer>

</div>
</div>
{% endraw %}
