# Case 13: Just One Command

**Difficulty:** Beginner · **Severity:** High · **Data:** Sysmon (Event IDs 1 and 3) · **Time budget:** 30–45 minutes

## The alert

> **Client:** Northgate Veterinary Partners (four animal hospitals, IT outsourced to a one-person shop)
>
> **2019-05-12 18:35 UTC**: The endpoint security agent on the reception PC `IEWIN7` raised:
> **"Suspicious Network Activity by Signed Windows Binary: regsvr32.exe"**
>
> The user says she was following an online guide to fix a printer problem and only ran one command. You've been handed one Sysmon export from the PC.

Your job: work out what actually happened, how confident you are, and what should happen next.

## Evidence

| File | Notes |
|---|---|
| `data/case13-sysmon.evtx` | Sysmon log export (SHA-256 `d6978888…956442`) |
| `data/case13-sysmon.jsonl` | Same 3 events, one per line, in the format the app reads |

**Safety:** the evidence contains a URL. Don't open it from your own machine. If a URL needs checking, that happens in a sandbox, by someone who's been asked to.

## What you'll practice

- Reading Sysmon **Event ID 1** (process creation) and **Event ID 3** (network connection)
- Taking a command line apart switch by switch
- Linking a network connection to a process by `ProcessGuid`
- Noticing when timestamps disagree, and deciding what to trust
- Saying what a user's story does and doesn't match

## Guided steps

Do these in order. Write findings in `worksheet.md` as you go, with the `EventRecordID` for each one.

1. **Survey.** How many events, which Event IDs, which host and user? What time range? Sort the events by record ID, then by `UtcTime`. Is the order the same?
2. **Take the command line apart.** Read `regsvr32.exe`'s `CommandLine` one switch at a time: `/u`, `/s`, `/i:…` and the DLL at the end. What is `regsvr32` normally for? What is `scrobj.dll`? What is the `/i:` value here, and what kind of thing is usually given to `/i:`? (Try the LOLBAS project: lolbas-project.github.io.)
3. **Build the process tree.** List `ProcessGuid`, `ParentProcessGuid` and `Image` for each process and build it in the **Process tree** widget. Add a not-in-evidence node for any parent with no process-create event. Compare the two `cmd.exe` command lines.
4. **Read the network connection.** Which process made it? Match it by `ProcessGuid`, not just by name. Where did it connect, on which port and protocol? Does that agree with the URL in the command line? What does the log *not* tell you about the destination?
5. **Check the clock.** Compare the network event's `UtcTime` with the `UtcTime` of the process that made it. Is the order possible? What do you trust when two timestamps disagree, and how should that change the way you write your timeline?
6. **Who ran it?** Look at the parent of `regsvr32.exe`, `TerminalSessionId`, `IntegrityLevel`, `LogonId` and `CurrentDirectory`. Does the data fit "I typed one command into a prompt"? What did that one command cause?
7. **Assess.** Malicious, benign or undetermined? Map *observed* behavior to ATT&CK techniques. List what's unknown, especially about what was downloaded and what ran afterwards.
8. **Report.** Fill in `report.md`.

Only when your report is finished, submit it and compare with the answer key. Stuck on a step? Open **Hints** and read **one** hint at a time.

## Ground rules

- Every claim needs an `EventRecordID` behind it.
- Write "observed" facts separately from what you *think* they mean.
- The alert is a lead, not proof. Confirm it from the raw events.
