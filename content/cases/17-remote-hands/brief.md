# Case 17: Remote Hands

**Difficulty:** Intermediate · **Severity:** High · **Data:** Sysmon (Event IDs 1 and 3) · **Time budget:** 1 hour

## The alert

> **Client:** Ostrander & Lowe (law firm, 60 staff, IT managed by a part-time sysadmin)
>
> **2019-04-30 20:32 UTC**: The endpoint security agent on the paralegal workstation `IEWIN7` raised:
> **"Command Shell Spawned by WMI Provider Host"**
>
> The client says their asset-inventory tool queries every PC over WMI each evening. You've been handed one Sysmon export from the workstation.

Your job: work out what actually happened, how confident you are, and what should happen next.

## Evidence

| File | Notes |
|---|---|
| `data/case17-sysmon.evtx` | Sysmon log export (SHA-256 `21b8852b…4ffe59`) |
| `data/case17-sysmon.jsonl` | Same 7 events, one per line, in the format the app reads |

## What you'll practice

- Reading Sysmon **Event ID 1** (process creation) and **Event ID 3** (network connection), including inbound connections
- Recognising remote execution through WMI
- Reading output redirection and administrative shares in a command line
- Telling a tool's own housekeeping apart from an operator's commands
- Decoding a timestamp hidden in a file name

## Guided steps

Do these in order. Write findings in `worksheet.md` as you go, with the `EventRecordID` for each one.

1. **Survey.** How many events, which Event IDs, which users? What time range? Sort the events by record ID and then by `UtcTime`. Where do the two orders disagree?
2. **Build the process tree.** Use `ProcessGuid` and `ParentProcessGuid`, with a not-in-evidence node for any parent with no process-create event. What is `WmiPrvSE.exe`, and what do `-secured -Embedding` tell you about why it's running?
3. **Read the command lines.** Take one `cmd.exe` command line apart: `/Q`, `/c`, `1>`, `2>&1`, and the path after `1>`. What is `ADMIN$`, which folder does it map to, and why would anyone write to it through `\\127.0.0.1` instead of a local path?
4. **Operator or tool?** Compare the three commands. Which look like a program setting itself up, and which looks like a person's question? What does the last command show the person who ran it?
5. **Read the network events.** For each one, read `Initiated` first. Which side is this host? Which address is remote, and on which ports? Which connection fits the output redirection, and which one shows someone arriving from outside? Compare their times with the process events.
6. **Decode the number.** The output file is named `__1556656369.7`. What kind of number is `1556656369`? Convert it, and compare the result with the earliest event in the export.
7. **Whose hands?** Look at `User`, `LogonId`, `TerminalSessionId` and `IntegrityLevel` on the processes. Was anyone sitting at this PC? What does running these commands remotely require, and what does that say about the account?
8. **Assess.** Does this look like an inventory tool? Malicious, benign or undetermined? Map *observed* behavior to ATT&CK techniques. List what's unknown.
9. **Report.** Fill in `report.md`.

Only when your report is finished, submit it and compare with the answer key. Stuck on a step? Open **Hints** and read **one** hint at a time.

## Ground rules

- Every claim needs an `EventRecordID` behind it.
- Write "observed" facts separately from what you *think* they mean.
- The alert is a lead, not proof. Confirm it from the raw events.
