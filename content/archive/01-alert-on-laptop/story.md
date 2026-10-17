**From:** Priya Nandakumar, SOC Team Lead · Ironlantern Security  
**To:** Cody  
**Sent:** 21:04 (your first night shift)  
**Subject:** Welcome aboard, and your first ticket

Cody,

Welcome to Ironlantern. HR tells me you survived onboarding, which puts you ahead of the coffee machine.

Quick orientation: we're a managed detection & response shop. About forty clients pay us to watch their endpoints around the clock, and when their security agent raises its hand, we're the ones who decide whether it's nothing or the start of a very bad week.

New hires normally shadow for two weeks. Tonight isn't normal. Dee, our senior analyst, is stuck on a call with another client. A ticket just came in from **Halberd & Vale**, a small architecture firm and one of our oldest clients. Their endpoint agent fired an alert at **16:27 UTC** on a staff laptop, `LAPTOP-JU4M3I0E`.

Their IT contact, Tomás, sent over a Sysmon export and this note:

> "Honestly probably a false positive. I asked around and nobody remembers doing anything unusual on that machine. Can you confirm before our morning meeting so I can close it out?"

It's a small export, only eight events. Don't let that fool you.

House rules, and I mean all three:

1. **Every claim gets a record number.** If you can't point to an event, it's not a finding.
2. **What the client tells you is a claim, not evidence.** Tomás is a nice guy. He's also not looking at the logs.
3. **"I don't know" is a legitimate answer.** Making things up is not.

Write your report like I'm going to forward it to Tomás's boss, because I am.

Ping the war room if you get stuck. Hints are there for a reason, but every one you open shows up in your review.

— Priya

*P.S. Your 90-day probation review starts tonight. No pressure.*
