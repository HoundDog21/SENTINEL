# Tutorial: A Quiet Morning

**Difficulty:** Practice · **Severity:** Low · **Data:** Sysmon (Event IDs 1, 5, 11, 13) and one Security 4624 · **Time budget:** 15 minutes

## The alert

> **Client:** Ironlantern training lab (internal)
>
> **2026-10-12 09:04 UTC**: A practice rule on the training PC `TRAIN-PC01` raised:
> **"Training alert: text file written to Documents"**
>
> This is a drill. Nothing bad happened on this machine. The point is to learn the console on data that's easy to read.

Your job: confirm what the user did, write it up, and submit a practice report.

## Evidence

| File | Notes |
|---|---|
| `data/tutorial.jsonl` | Six events from the training PC, in the same format as real cases |

This practice workspace is separate from your real cases. Nothing you do here changes your XP, rank or case files.

## Guided steps

1. **Survey** the events: how many are there, what Event IDs, which host and user, what time range?
2. **Find the process** that wrote the file named in the alert, and add it to your evidence with a note.
3. **Build the process tree** for that process from `ProcessGuid` and `ParentProcessGuid`.
4. **Write and submit** a short practice report, then compare it with the practice answer key.

## What you'll practice

- Moving around the console: every widget, the layout controls and settings
- Adding evidence, building a process tree, flagging an IOC, posting in the war room
- Submitting a report and scoring it against a rubric
