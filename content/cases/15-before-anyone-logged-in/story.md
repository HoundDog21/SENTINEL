**From:** Priya Nandakumar, SOC Team Lead · Ironlantern Security  
**To:** Cody  
**Sent:** 16:30  
**Subject:** Halloran CCU: whoami on the DC

Cody,

This one's on a **domain controller**, so it jumps the queue.

**Halloran Community Credit Union** got an alert at **16:08 UTC** on `DC1`: `whoami.exe` running as SYSTEM. Their sysadmin, Bernadette, is confident:

> "Nobody was logged on to DC1. I checked the session list straight after the alert and there's no one there. Admins only touch the DCs through the management tools anyway. Must be some agent or update process. False positive, I'd say."

Two claims there: nobody was logged on, and therefore it's a false positive. The first one might be true. Whether the second follows from it is what I want you to work out.

`whoami` on its own is boring. What I care about is *what ran it*. Read the parent's event like you've never seen the file name before.

Three events. On a DC. Take it seriously, and send me something I can put in front of their head of IT.

— Priya
