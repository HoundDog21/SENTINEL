# Case 01: First Watch

**Difficulty:** Beginner · **Severity:** High · **Data:** Sysmon (Event IDs 1 and 11) + Program Compatibility Assistant (Event ID 17) · **Time budget:** 1–2 hours

## The alert

> **Client:** Halberd & Vale (architecture firm, managed endpoints)
>
> **2019-07-29 21:11 UTC**: The endpoint security agent on the front-desk PC `MSEDGEWIN10` raised:
> **"Suspicious Script Host Execution: wscript.exe spawned by rundll32.exe"**
>
> The client's IT contact thinks the agent is overreacting to someone paying invoices. You've been handed two log exports from the host.

Your job: work out what actually happened, how confident you are, and what should happen next.

## Evidence

| File | Notes |
|---|---|
| `data/case01-sysmon.evtx` | Sysmon log export (SHA-256 `3a343508…3c3550`) |
| `data/case01-sysmon.jsonl` | Same events converted with `chainsaw dump --jsonl`, one event per line |
| `data/case01-pca.evtx` | Program Compatibility Assistant log export from the same host (SHA-256 `435da66e…2fcc92`) |
| `data/case01-pca.jsonl` | Same events, converted |

The two files come from **different logs**. Each log numbers its own records, so record IDs from one file can't be compared with the other. The exports are **not guaranteed to be complete**. Keep that in mind when you say what *didn't* happen.

## What you'll practice

- Reading Sysmon **Event ID 1** (process creation) and **Event ID 11** (file creation)
- Following `ProcessGuid` → `ParentProcessGuid` to build a process tree
- Telling normal Windows plumbing apart from the attacker's actions
- Using a second log source to corroborate, and telling evidence apart from noise
- Writing down what you *can't* conclude

## Guided steps

Do these in order. Write findings in `worksheet.md` as you go, with the `EventRecordID` for each one.

1. **Survey.** How many events are in each file? Which Event IDs and channels? What time range does each file cover? Which host(s) and user(s)?
   Tools: `duckdb` counts (see `docs/toolkit.md`), `jq`.
2. **Read the alerting event in full.** Find the process the alert names and go through *every* field. Compare `Image` with the path in `CommandLine`. Look up any field you don't recognize (`IntegrityLevel`, `LogonId`, `CurrentDirectory`, `Hashes`…).
3. **Build the process tree.** List each process's `ProcessGuid`, `ParentProcessGuid` and `Image`. Build it in the **Process tree** widget. Add a not-in-evidence node for any parent that has no process-create event.
4. **Follow the file.** For the Event ID 11: which process wrote which file, and where? Compare `UtcTime` with `CreationUtcTime`. Do they agree? What could explain a difference?
5. **Read every command line slowly.** What is each one doing? Look up anything you don't know: what a `.cpl` file is, `Control_RunDLL`, `shell32.dll,#44`, `/e:JScript.Encode` (try the LOLBAS project: lolbas-project.github.io).
6. **Corroborate.** Which events in the second log relate to this activity, and which don't? Don't explain away an event you can't tie to the chain, and don't pull one into it without evidence.
7. **Timeline.** Put both logs in one time order. Look at the Sysmon record IDs. Are they consecutive?
8. **Assess.** Malicious, benign or undetermined? Map *observed* behavior to ATT&CK techniques. List what's unknown.
9. **Report.** Fill in `report.md`.

Only when your report is finished, submit it and compare with the answer key. Stuck on a step? Open **Hints** and read **one** hint at a time.

## Ground rules

- Every claim needs an `EventRecordID` behind it (say which log it's from).
- Write "observed" facts separately from what you *think* they mean.
- The alert is a lead, not proof. Confirm it from the raw events.
