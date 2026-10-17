**From:** Priya Nandakumar, SOC Team Lead · Ironlantern Security  
**To:** Cody  
**Sent:** 02:05  
**Subject:** Marrowfield Dental: alert on the intranet server

Cody,

New one for you. **Marrowfield Dental Group** runs a staff intranet portal (rotas, HR forms, that sort of thing) on a server called `IEWIN7`. At **01:33 UTC** their endpoint agent flagged the web server process starting a command shell.

Their IT manager, Owen, replied to the auto-ticket before I'd even picked it up:

> "That portal is internal only. Nobody outside the clinics can reach it. We've got a nightly maintenance job that runs around then, so it's probably that. Happy for you to close it if you agree."

I don't agree or disagree yet. That's your job. Owen hasn't told us what the maintenance job is supposed to run, and "internal only" is the kind of thing people believe right up until the firewall rules say otherwise. Treat both as claims.

It's a tiny export, four events. Read every field anyway. Small exports are where people get lazy.

What I need back:

1. What ran, what started it, and as whom, with record numbers.
2. Whether any of it looks like a maintenance job.
3. What you *can't* tell from a server's process log about a web request. Owen will ask.

— Priya
