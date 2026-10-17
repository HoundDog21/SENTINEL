# Case 18: Something in System32

**Difficulty:** Intermediate · **Severity:** High · **Data:** Sysmon (Event IDs 1, 7, 10, 11) · **Time budget:** 1 hour

## The alert

> **Client:** TODO: client name (and what kind of business)
>
> **2019-08-30 12:54 UTC**: TODO: which product raised what alert, on which host.
> **"TODO: alert name"**
>
> TODO: what the client believes, and what you've been handed.

Your job: work out what actually happened, how confident you are, and what should happen next.

## Evidence

| File | Notes |
|---|---|
| `data/case18-sysmon.evtx` | Original EVTX (chainsaw dump) file (SHA-256 `d1bf591c…6f96b4`) |
| `data/case18-sysmon.jsonl` | Same 6 events, one per line, in the format the app reads |

## What you'll practice

- TODO

## Guided steps

Do these in order. Write findings in `worksheet.md` as you go, with a reference for each one.

1. **Survey.** How many events are there? Which Event IDs and channels? What time range? Which host(s) and user(s)?
2. TODO: next step
3. **Assess.** Malicious, benign or undetermined? Map *observed* behavior to ATT&CK techniques. List what's unknown.
4. **Report.** Fill in `report.md`.

Only when your report is finished, submit it and compare with the answer key. Stuck on a step? Open **Hints** and read **one** hint at a time.

## Ground rules

- Every claim needs an event reference behind it.
- Write "observed" facts separately from what you *think* they mean.
- The alert is a lead, not proof. Confirm it from the raw events.
