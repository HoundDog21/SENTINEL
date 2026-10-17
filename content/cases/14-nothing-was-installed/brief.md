# Case 14: Nothing Was Installed

**Difficulty:** Beginner+ · **Severity:** Medium · **Data:** Sysmon (Event IDs 1 and 11) · **Time budget:** 45 minutes

## The alert

> **Client:** Kestrel Print & Signage (print shop, twenty staff, locked-down workstations)
>
> **2020-07-03 08:47 UTC**: The endpoint security agent on the design workstation `MSEDGEWIN10` raised:
> **"Windows Utility Run With Remote URL Argument"**
>
> The client says the user has no admin rights, so nothing could have been installed. You've been handed one Sysmon export from the workstation.

Your job: work out what actually happened, how confident you are, and what should happen next.

## Evidence

| File | Notes |
|---|---|
| `data/case14-sysmon.evtx` | Sysmon log export (SHA-256 `f63ea099…6e861af`) |
| `data/case14-sysmon.jsonl` | Same 3 events, one per line, in the format the app reads |

The export is **not guaranteed to be complete**. Check the record IDs before you say what didn't happen. Don't open the URL in the evidence.

## What you'll practice

- Reading Sysmon **Event ID 1** (process creation) and **Event ID 11** (file creation)
- Researching an unfamiliar Windows binary before you judge it
- Linking a file to the command that caused it when a *different* process wrote it
- Separating "downloaded" from "installed" from "executed"
- Using record-ID gaps and missing event types to bound your conclusions

## Guided steps

Do these in order. Write findings in `worksheet.md` as you go, with the `EventRecordID` for each one.

1. **Survey.** How many events, which Event IDs, which host and user? What time range? Are the record IDs consecutive? Which event has no `User`?
2. **Build the process tree.** Build it in the **Process tree** widget from `ProcessGuid` and `ParentProcessGuid`, with a not-in-evidence node for any parent with no process-create event. Why are there two `cmd.exe`s, and what do their command lines tell you about how this started?
3. **Research the tool.** What is the second program normally for? Where does it live, who signs it (`Company`, `OriginalFileName`), and what are its switches meant to do? Look it up (try LOLBAS). What is the URL pointing at, judging *only* by its text?
4. **Read the file event.** Which process wrote the file, and where? Which file extension does it have? Compare `UtcTime` with `CreationUtcTime`. Why might a process other than the one you ran have written it? What usually runs inside that kind of process?
5. **Link the file to the command.** List every piece of evidence that ties this file to the command line, and say which links are observed and which are inferred. What would make the link certain?
6. **Mind the gaps.** Which record IDs are missing, and where do they fall? Which event types would you expect for a download that aren't here at all? Is there a hash for the downloaded file?
7. **Test the client's claim.** "No admin rights, so nothing was installed." Which parts are supported by the data (look at `IntegrityLevel` and the file path)? Which parts miss the point?
8. **Assess.** Malicious, benign or undetermined? Map *observed* behavior to ATT&CK techniques. List what's unknown.
9. **Report.** Fill in `report.md`.

Only when your report is finished, submit it and compare with the answer key. Stuck on a step? Open **Hints** and read **one** hint at a time.

## Ground rules

- Every claim needs an `EventRecordID` behind it.
- Write "observed" facts separately from what you *think* they mean.
- The alert is a lead, not proof. Confirm it from the raw events.
