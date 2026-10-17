# Case 12: Thirty Milliseconds

**Difficulty:** Beginner · **Severity:** Medium · **Data:** Security (Event IDs 4698 and 4699) · **Time budget:** 30 minutes

## The alert

> **Client:** Brightwater Housing Trust (social housing provider, about 300 staff)
>
> **2019-03-19 00:02 UTC**: The client's SIEM raised on `WIN-77LTAPHIQ1R.example.corp`:
> **"Scheduled Task Created and Deleted Within One Second"**
>
> The client's IT team says their patch-deployment tool creates short-lived tasks all the time. You've been handed the two Security log events behind the alert.

Your job: work out what actually happened, how confident you are, and what should happen next.

## Evidence

| File | Notes |
|---|---|
| `data/case12-security.evtx` | Security log export (SHA-256 `a7decf0f…a6bf8b70`) |
| `data/case12-security.jsonl` | Same 2 events, one per line, in the format the app reads |

The SIEM forwarded only the events that matched its rule. It is **not** the full Security log for that minute.

## What you'll practice

- Reading Security **Event ID 4698** (scheduled task created) and **Event ID 4699** (scheduled task deleted)
- Reading a task's XML definition: triggers, principal, settings and actions
- Telling the account that *did* something apart from the process that *logged* it
- Using record-ID gaps to say what's missing
- Weighing an admin-tool explanation against the evidence, fairly

## Guided steps

Do these in order. Write findings in `worksheet.md` as you go, with the `EventRecordID` for each one.

1. **Survey.** How many events, which Event IDs, which host? What time does each one have, and how far apart are they? Look at the record IDs. Are they consecutive?
2. **Who did it?** Read the `Subject…` fields. Which account, which domain, which logon session? Look up what a SID ending in `-500` means. Then look at `Execution_attributes.ProcessID` in the System section and find out which process writes Security events. Is it the process that created the task?
3. **Read the task definition.** `TaskContent` is XML. Go through it section by section: when is it set to run (`Triggers`), as whom and with what rights (`Principals`), how is it configured (`Settings`), and what does it run (`Actions`)? Note anything unusual, including dates.
4. **Compare the two events.** What's the same and what's different? How long did the task exist? With that lifetime, could it ever have run on its own schedule? How else could it have run?
5. **Follow the output.** Read the action's arguments slowly, including the `&gt;` and `&amp;` escapes. What command runs, and where does its output go? Why would someone want the output in a file with that name?
6. **What's missing.** Three record IDs fall between the two events. What kinds of events could be there? Which other logs would show whether the task actually ran and what it did?
7. **Assess.** Does this look like the client's patch tool? List what supports that theory and what doesn't. Malicious, benign or undetermined? Map *observed* behavior to ATT&CK techniques. List what's unknown.
8. **Report.** Fill in `report.md`.

Only when your report is finished, submit it and compare with the answer key. Stuck on a step? Open **Hints** and read **one** hint at a time.

## Ground rules

- Every claim needs an `EventRecordID` behind it.
- Write "observed" facts separately from what you *think* they mean.
- The alert is a lead, not proof. Confirm it from the raw events.
