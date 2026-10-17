# Case 15: Before Anyone Logged In

**Difficulty:** Beginner+ · **Severity:** Critical · **Data:** Sysmon (Event IDs 1 and 12) · **Time budget:** 45 minutes

## The alert

> **Client:** Halloran Community Credit Union (regional credit union, small in-house IT team)
>
> **2019-05-16 16:08 UTC**: The endpoint security agent on `DC1.insecurebank.local` raised:
> **"Discovery Command Run as SYSTEM: whoami.exe"**
>
> The client says nobody was logged on to the domain controller at the time, so it must be a false positive. You've been handed one Sysmon export from the server.

Your job: work out what actually happened, how confident you are, and what should happen next.

## Evidence

| File | Notes |
|---|---|
| `data/case15-sysmon.evtx` | Sysmon log export (SHA-256 `9a99994b…f6ea2925`) |
| `data/case15-sysmon.jsonl` | Same 3 events, one per line, in the format the app reads |

## What you'll practice

- Reading Sysmon **Event ID 1** (process creation) and **Event ID 12** (registry key created or deleted)
- Checking whether a program is what its file name says it is
- Knowing which Windows processes run on the logon screen, and as whom
- Treating a log's `RuleName` as a label someone wrote, not as evidence
- Telling *when a backdoor was used* apart from *when it was planted*

## Guided steps

Do these in order. Write findings in `worksheet.md` as you go, with the `EventRecordID` for each one.

1. **Survey.** How many events, which Event IDs, which host? What role does that host's name suggest? What time range, which users, which sessions?
2. **Build the process tree.** Use `ProcessGuid` and `ParentProcessGuid`, and add a not-in-evidence node for any parent with no process-create event. Which process in the data doesn't belong to the tree?
3. **Is it what it says it is?** Read the `osk.exe` process-create event in full. What is `osk.exe` meant to be? Now read its `Description` and `FileVersion`, and compare them with the `whoami.exe` event and with what you'd expect. What does `whoami.exe` being its child tell you?
4. **Read the parent.** What is `Utilman.exe`, when does Windows start it, with `/debug`, and as which user? Is `Utilman.exe` → `osk.exe` normal by itself?
5. **Who and where.** `User`, `LogonId`, `IntegrityLevel` and `TerminalSessionId` on both processes. What is LogonId `0x3e7`? What does the client's "nobody was logged on" claim get right, and why doesn't it make this a false positive?
6. **The registry event.** Which process, which key, which `EventType`? What is `LogonUI.exe`? Read the `RuleName` and ask who wrote that text. What does this event suggest, and what does it *not* prove?
7. **How was it done, and when?** Two well-known ways to make an accessibility tool open something else are replacing the file and setting an *Image File Execution Options* `Debugger` value. Which one fits the `Image` and `Description` you see? Was the backdoor *planted* during this export, or only *used*?
8. **Assess.** Malicious, benign or undetermined? Map *observed* behavior to ATT&CK techniques. What does SYSTEM on this particular host mean for the client? List what's unknown.
9. **Report.** Fill in `report.md`.

Only when your report is finished, submit it and compare with the answer key. Stuck on a step? Open **Hints** and read **one** hint at a time.

## Ground rules

- Every claim needs an `EventRecordID` behind it.
- Write "observed" facts separately from what you *think* they mean.
- The alert is a lead, not proof. Confirm it from the raw events.
