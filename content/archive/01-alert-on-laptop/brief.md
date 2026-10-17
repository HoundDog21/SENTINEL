# Case 01: First Watch

**Difficulty:** Beginner · **Severity:** High · **Data:** Sysmon (Event IDs 1 and 11 only) · **Time budget:** 1–2 hours

## The alert

> **Client:** Halberd & Vale (architecture firm, managed endpoints)
>
> **2021-10-21 16:27 UTC**: The endpoint security agent on staff laptop `LAPTOP-JU4M3I0E` raised:
> **"Malicious Behavior Detection Alert: Execution via Renamed Signed Binary Proxy"**
>
> The client's IT contact believes it's a false positive. You've been handed the Sysmon events that were exported from the host around the time of the alert.

Your job: work out what actually happened, how confident you are, and what should happen next.

## Evidence

| File | Notes |
|---|---|
| `data/case01.evtx` | Original Windows event log (SHA-256 `4d995c2a…6cd894`) |
| `data/case01.jsonl` | Same events converted with `chainsaw dump --jsonl`, one event per line |

The export is **partial**: it doesn't contain every event the host logged in that window. Keep that in mind when you say what *didn't* happen.

## What you'll practice

- Reading Sysmon **Event ID 1** (process creation) and **Event ID 11** (file creation)
- Following `ProcessGuid` → `ParentProcessGuid` to build a process tree
- Comparing what a file is *called* with what it *is*
- Telling an alert apart from evidence
- Writing down what you *can't* conclude

## Guided steps

Do these in order. Write findings in `worksheet.md` as you go, with the `EventRecordID` for each one.

1. **Survey.** How many events are there? Which Event IDs? What time range? Which host(s) and user(s)?
   Tools: `duckdb` counts (see `docs/toolkit.md`), `jq`.
2. **Read one event in full.** Pick the first Event ID 1 and go through *every* field. Look up any you don't recognize (`IntegrityLevel`, `LogonId`, `OriginalFileName`, `Hashes`…), and note what each one tells you.
3. **Build the process tree.** List each process's `ProcessGuid`, `ParentProcessGuid` and `Image`. Build it in the **Process tree** widget (or draw it in the worksheet). Add a not-in-evidence node for any parent that isn't in the data.
4. **Follow the files.** For every Event ID 11, which process wrote which file, and where? Compare `UtcTime` with `CreationUtcTime`. Do they agree? What could explain a difference?
5. **Read every command line slowly.** What is each one doing? Look up any program you don't know (try the LOLBAS project: lolbas-project.github.io).
6. **Explain the alert.** Which event(s) most likely triggered "Renamed Signed Binary Proxy", and why does the name fit?
7. **Timeline.** Put events in time order. Does that match the order of `EventRecordID`? If not, why might that be?
8. **Assess.** Malicious, benign or undetermined? Map *observed* behavior to ATT&CK techniques. List what's unknown.
9. **Report.** Fill in `report.md`.

Only when your report is finished, open `private/answer-key.md` and compare. Stuck on a step? Open `hints.md` and read **one** hint at a time.

## Ground rules

- Every claim needs an `EventRecordID` behind it.
- Write "observed" facts separately from what you *think* they mean.
- The alert is a lead, not proof. Confirm it from the raw events.
