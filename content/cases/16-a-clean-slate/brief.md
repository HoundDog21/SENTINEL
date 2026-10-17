# Case 16: A Clean Slate

**Difficulty:** Intermediate · **Severity:** High · **Data:** Security (Event IDs 1102, 4768 and 4771) · **Time budget:** 1 hour

## The alert

> **Client:** Three Bees & Co. (specialty food distributor, two warehouses, one domain)
>
> **2020-07-22 20:29 UTC**: The client's SIEM raised on `01566s-win16-ir.threebeesco.com`:
> **"Security Audit Log Cleared"**
>
> The client says one of their admins cleared the log during evening maintenance. You've been handed the Security events from that server for the following few seconds.

Your job: work out what actually happened, how confident you are, and what should happen next.

## Evidence

| File | Notes |
|---|---|
| `data/case16-security.evtx` | Security log export (SHA-256 `4a0a1c71…9ae11d`) |
| `data/case16-security.jsonl` | Same 12 events, one per line, in the format the app reads |

The alert was about one event. The export has twelve. Read all of them.

## What you'll practice

- Reading Security **Event ID 1102** (audit log cleared)
- Reading Kerberos authentication events: **Event ID 4768** (TGT requested) and **Event ID 4771** (pre-authentication failed)
- Decoding Kerberos status codes, and what a NULL SID means
- Recognising an authentication pattern from many small events
- Keeping two possibly unrelated activities apart until the evidence joins them

## Guided steps

Do these in order. Write findings in `worksheet.md` as you go, with the `EventRecordID` for each one.

1. **Survey.** How many events of each ID? What time range? Are the record IDs consecutive? Which kind of server logs Event IDs 4768 and 4771, and what does that tell you about this host?
2. **Read the log clear.** Who cleared it (account, domain, SID, logon session) and when? What does clearing the log remove, and what can it *not* remove? Note where the 1102 sits in the export relative to everything else.
3. **Tabulate the Kerberos events.** For each one, write down `TargetUserName`, `TargetSid`, `Status`, `PreAuthType`, `IpAddress`, `IpPort` and time. Sort by time, then by port.
4. **Decode the results.** Look up Kerberos status codes `0x6`, `0x18` and `0x0`, and the SID `S-1-0-0`. Sort every account name into one of three groups. What does each group tell an attacker?
5. **Find the pattern.** How many accounts, how many attempts per account, from how many sources, over how long? Could a person type this? Compare `TicketOptions` with what a normal Windows client sends. Name the pattern.
6. **Read the successes.** Which account succeeded, and in which records? Compare those two events field by field. What's different, and what might that mean?
7. **Names worth a second look.** Among the accounts that *exist* in the domain, does any name stand out? What can and can't the data tell you about it?
8. **One actor or two?** Is the person who cleared the log the same as whoever is behind the Kerberos traffic? List what links them, what doesn't, and what's missing to decide.
9. **Assess.** Map *observed* behavior to ATT&CK techniques. Which accounts need action now? List what's unknown.
10. **Report.** Fill in `report.md`.

Only when your report is finished, submit it and compare with the answer key. Stuck on a step? Open **Hints** and read **one** hint at a time.

## Ground rules

- Every claim needs an `EventRecordID` behind it.
- Write "observed" facts separately from what you *think* they mean.
- The alert is a lead, not proof. Confirm it from the raw events.
