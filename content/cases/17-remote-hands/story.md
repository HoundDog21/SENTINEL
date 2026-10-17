**From:** Priya Nandakumar, SOC Team Lead · Ironlantern Security  
**To:** Cody  
**Sent:** 21:15  
**Subject:** Ostrander & Lowe: WMI on a paralegal's PC

Cody,

**Ostrander & Lowe** are a law firm. Their agent fired at **20:32 UTC** on `IEWIN7`, a paralegal's workstation: the WMI provider host started a command shell.

Their sysadmin, Graham, works three days a week and isn't in today. The office manager forwarded his standing note about alerts like this:

> "The asset-inventory tool polls every machine over WMI each evening to collect hardware and software lists. It sometimes trips the agent. Safe to ignore."

So there's a known, legitimate tool that uses WMI on these machines in the evening. That's a real alternative, and I want you to test it, not wave it away. Inventory tools *ask WMI questions*. Ask yourself whether that's what these events show.

The paralegal left at 17:30, according to the office manager. That's a claim too.

This is an intermediate case: seven events, and two of the network ones are easy to misread. Read `Initiated` before you read anything else on them.

— Priya
