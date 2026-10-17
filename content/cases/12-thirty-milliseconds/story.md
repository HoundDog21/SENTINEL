**From:** Dee, Senior Analyst · Ironlantern Security  
**To:** Cody  
**Sent:** 00:40  
**Subject:** Brightwater: blink-and-you-miss-it task

Hey Cody,

Priya says you're ready for one on your own, so here's a short one.

**Brightwater Housing Trust** forwards their Security logs to their own SIEM, and we get whatever trips a rule. At **00:02 UTC** something created a scheduled task on `WIN-77LTAPHIQ1R` and deleted it again almost straight away. Two events. That's the whole export.

I rang their on-call, Fiona. Her words:

> "That'll be the patch tool. It drops a temporary task, runs it, cleans up. It does that hundreds of times a week. The admin account is the one the tool uses, so that fits too."

Could be. Patch tools really do work like that, and so do a few attacker tools. So "it creates temporary tasks" doesn't settle anything by itself. What did *this* task run? Fiona didn't say what time their patch window is, and I didn't ask, so don't assume one.

Two events doesn't mean two minutes. The task XML is the evidence here. Read all of it.

Send me your report when you're done. If you think it's the patch tool, say why. If you don't, say why not.

— Dee
