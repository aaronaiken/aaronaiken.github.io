---
layout: post
title: "Cloudbase Limited Beta"
date: 2026-10-16T16:47:56.644237+00:00
categories: [apps]
tags: [cloudbase, beta]
base: KMDT
author: aaron
cosmic_id: Endpaper-Ψ-0016
written_in: Endpaper
---

![A silhouetted commercial airplane on a tarmac at sunset with a small aircraft and figure standing nearby.](https://cargo.aaronaiken.me/blog-img/2924d8f856e4468a980c7064fe4e3a3a.jpg)

*pretty big class rating jump*

For almost all of my professional working life, which is only 19 years at this point, I have always worked to _do things better_. I am constantly looking at how things are done, what processes are or are not in place, and then I get to work on implementing solutions (after designing them, of course). By the time I hit my 10 year mark I learned about ITIL through my employer and went through all the training to get up to what was then called _Expert_ and achieved the Managing Across the Lifecycle (MALC) certificate. I had the papers, and thankfully something of a solid career behind them to give them actual meaning and weight. While not all of ITIL is clear or even applicable in all situations, I do find that most of what I learned is helpful in _a lot_ of situations.[^1]
As usual, I digress.

Part of what has happened over the past 19 years is me figuring out exactly how I work, how I think work works best, and over time building systems and tools to help me keep track of things that needed doing. This all culminated in a private application I made for myself that I called _Cockpit_.

My Cockpit, and the _Command Deck_ within, helped me track projects, record time, mileage, meetings, notes, people, clients, tickets (incoming requests), and so on. I built a Spotify player for it. I even built a publishing tool that I can use to publish status updates to my website (my fun and Twitter '07 vibed [status page](https://aaronaiken.me/status.html)). I made a private video-call platform attached to it called [_Formation_](https://cloudbase.day/formation) and I used this to have meetings with clients and other people that I work with. I made my Cockpit to be where I started each day, worked each day, and then logged off knowing that everything was where I needed it to be.

And it was great. All was well and good. Until on a Formation call one of the participants asked: "how can I get my own Cockpit?"

That's all I needed to hear. And so I spent the next several months porting my built-for-one-person app into infrastructure that would support users and teams. I also built it from the ground up to support the very thing I enjoyed so much about building my own cockpit in the first place: it is built to be customized. My cockpit did this by its own nature, it was only me using it. When building for other people I had to make sure the architecture was such that I could build custom features for one account that would not have any impact on another unrelated account.

All of this is what came to be [Cloudbase](https://cloudbase.day).
![Advertisement with dark blue text reading "The cockpit for a company of one" and Cloudbase logo on light background.](https://cargo.aaronaiken.me/blog-img/234eda08a7184fb9bf9938f7ef843d1f.jpg)
I have taken my Cockpit, which only had one seat, and rebuilt it from the ground up so now it can have many seats. The beta has 25 of them (not counting mine), and 5 beta testers are already in, so 20 are open. Cloudbase is running in something of a private beta. _Limited_ beta may be a more accurate term for it since it isn't strictly invite only. [You do have to ask for access and I'll send you a magic link to get your beta account created.](https://cloudbase.day/signup)

**Who it's for.** If you run your own work, alone or with a small team, it's for you. A consultant, a tutor, a coach, a pastor, someone with a side business and a crew. Even those like me, salaried with plenty of projects on the side (I run my salaried work from here alongside my other projects and use [Modes](https://cloudbase.day/modes) to determine what I see when). If you've ever stitched together a task app, a spreadsheet for hours, a notebook for mileage and something else for meetings, Cloudbase puts all of that in one place. You don't need to be technical. My current beta testers mostly aren't.

**Why only 25.** Because I'm one person, and I want to answer every note myself. When something breaks, it lands in my queue, not a support team's. A small room is how I keep that promise.

**What it costs.** Nothing during the beta. If you join now, your base price locks at $19 a month for life when billing starts (the standard will be $24). You'll know the price well before you ever pay. If you leave, your workspace goes dormant, not deleted.

**What to expect.** Rough edges, honestly. I run my entire professional life out of Cloudbase now, and so it is something that I work on and maintain and update pretty frequently. You can take a look at the change log and release notes [here](https://cloudbase.day/shipped). Beta feedback is acted on almost immediately, and I'll check in with you a few times in the first month, one question each time. I am really hoping to fill up the beta sooner than later so I can iron out all of the various nuances and bugs that others will find.

And so, that's my pitch :-) If you'd like to take a look at what I made to improve how work is done, please do take a look at what I built in [Cloudbase](https://cloudbase.day). And if you know someone it's for, I'd be grateful if you sent this their way.

Cheers,
~ Aaron

[^1]: All of this relates because in Cloudbase I built what I call [Ground Control](https://cloudbase.day/ground-control) which is primarily for _receiving_ requests from customers (i.e. a Request for Service "portal"). Those requests come in via [tickets](https://cloudbase.day/tickets) and then can take the form of whatever they need: help with a question, a report, an application enhancement, a bugfix, and so on. And if a code change is needed they move into the [release management process](https://cloudbase.day/for/it-shops) via a tracked Change. From there the actual code work begins and the change is boarded onto a Flight (a release). And so on and so forth. The app also handles customer communication automatically at points and by hand (i.e. not automated messages), all of it is tracked and everyone can see what is where. Just scratching the surface here, but the plumbing is immense. **BUT** Cloudbase is not just for IT people or app devs. Actually, my current group of beta testers are _not_ in a technical field. That said, I think a ticket tracking system is something that almost everyone who works could benefit from, but that's a post for another time.
