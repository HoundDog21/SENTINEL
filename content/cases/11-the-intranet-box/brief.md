# Case 11: The Intranet Box

**Difficulty:** Beginner · **Severity:** High · **Data:** Sysmon (Event IDs 1 and 10) · **Time budget:** 30–45 minutes

## The alert

> **Client:** Marrowfield Dental Group (eleven clinics, small central IT team)
>
> **2019-05-24 01:33 UTC**: The endpoint security agent on `IEWIN7`, the server that hosts the staff intranet portal, raised:
> **"Web Server Process Spawned Command Shell: cmd.exe launched by w3wp.exe"**
>
> The client says the portal is internal-only and that a scheduled maintenance job probably tripped the alert. You've been handed one Sysmon export from the server.

Your job: work out what actually happened, how confident you are, and what should happen next.

## Evidence

| File | Notes |
|---|---|
| `data/case11-sysmon.evtx` | Sysmon log export (SHA-256 `6f1cb3c4…327c7b`) |
| `data/case11-sysmon.jsonl` | Same 4 events, one per line, in the format the app reads |

The export is short. It covers what the agent captured around the alert, not the server's whole day.

## What you'll practice

- Reading Sysmon **Event ID 1** (process creation) and **Event ID 10** (process access)
- Recognising the IIS worker process and the account it runs as
- Telling one attacker command apart from the helper processes Windows starts for it
- Reading a `CallTrace` without over-reading it
- Saying what a server-side log can and can't tell you about a web request

## Guided steps

Do these in order. Write findings in `worksheet.md` as you go, with the `EventRecordID` for each one.

1. **Survey.** How many events are there? Which Event IDs and channels? What time range? Which host(s) and user(s)? Are the record IDs consecutive?
2. **Read the parent.** The first process-create event names a parent. Read its `ParentImage` and `ParentCommandLine` in full. What is that program, what is an application pool, and who does it run as? Should it be starting command shells?
3. **Build the process tree.** List each process's `ProcessGuid`, `ParentProcessGuid` and `Image`, and build it in the **Process tree** widget. Add a not-in-evidence node for any parent that has no process-create event.
4. **Read every command line.** What does each one do? Why are there two different `net` programs? Which command did someone actually ask for, and which processes did Windows start on its own to carry it out?
5. **Read the process-access event.** Which process opened which, and when, compared with the process-create events? Look up what `GrantedAccess 0x1fffff` means. Read the `CallTrace` top to bottom: which runtime and which libraries appear? Is this a second action, or a side effect of something you've already seen?
6. **Context.** Look at `User`, `LogonId`, `TerminalSessionId`, `IntegrityLevel` and `CurrentDirectory` on every process. Is a person logged on at the console? How long does the whole chain take? What can and can't timing tell you?
7. **Assess.** Malicious, benign or undetermined? Does anything in the data fit the client's "maintenance job" theory? Map *observed* behavior to ATT&CK techniques. List what's unknown, especially about *how* the command reached the server.
8. **Report.** Fill in `report.md`.

Only when your report is finished, submit it and compare with the answer key. Stuck on a step? Open **Hints** and read **one** hint at a time.

## Ground rules

- Every claim needs an `EventRecordID` behind it.
- Write "observed" facts separately from what you *think* they mean.
- The alert is a lead, not proof. Confirm it from the raw events.
