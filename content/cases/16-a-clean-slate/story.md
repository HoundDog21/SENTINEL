**From:** Dee, Senior Analyst · Ironlantern Security  
**To:** Cody  
**Sent:** 21:05  
**Subject:** Three Bees: log cleared on a server

Cody,

**Three Bees & Co.** have a SIEM rule for cleared Security logs, and it fired at **20:29 UTC** on `01566s-win16-ir`. Their IT lead, Callum, answered within minutes:

> "That's Jamie (a-jbrown is his admin account). He was doing evening maintenance and the Security log on that box was huge, so he cleared it. I've told him to archive it first next time. Nothing to worry about."

That might be exactly what happened. Admins clear logs more often than they should. But I asked their SIEM for the next few seconds of the same log as well, because a log clear is only interesting for what's around it.

Callum's message is a claim about the 1102 only. He hasn't looked at the other eleven events, so he hasn't said anything about them, and I haven't either.

This is a step up from the process trees. There's no tree to build here, just a lot of small events that only mean something together. Make a table.

— Dee
