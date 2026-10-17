# Case 12: Answer key (SPOILERS)

> Don't open this until your `report.md` is finished.

**Source:** EVTX-ATTACK-SAMPLES (sbousseaden), `temp_scheduled_task_4698_4699.evtx`. The researcher recorded it in a lab domain (`example.corp`) while running a remote-execution tool, so there's no real victim. Treat it as real for the exercise.

## Survey

- **Security:** 2 events: 1 × Event ID 4698 (rec 566836) and 1 × Event ID 4699 (rec 566840).
- Records 566837, 566838 and 566839 are **missing**. The host logged three Security events between the create and the delete that aren't in this export.
- Host `WIN-77LTAPHIQ1R.example.corp`. Times: **00:02:04.319945** and **00:02:04.351252** UTC on 2019-03-19, **about 31 ms apart**.

## Who did it

| Field | Value | Meaning |
|---|---|---|
| `SubjectUserName` / `SubjectDomainName` | `Administrator` / `EXAMPLE` | the domain's account, not a local one (a local account would show the computer name) |
| `SubjectUserSid` | `S-1-5-21-…-500` | RID **500**: the **built-in Administrator** of the `EXAMPLE` domain |
| `SubjectLogonId` | `0x17e2d2` | the same logon session for both events. A 4624 with this LogonId would show how and from where it logged on |
| System `Execution_attributes.ProcessID` | `452` | the process that **wrote** the event, which for the Security log is `lsass.exe`. It is **not** the process that created the task |

## The task (rec 566836, identical in rec 566840)

| Section | Content | Note |
|---|---|---|
| Name | `\CYAlyNSS` | random-looking 8 letters, in the root task folder |
| Trigger | `CalendarTrigger`, daily, `StartBoundary` **2015-07-15T20:35:13.2757294** | nearly four years before the events. A daily trigger is irrelevant to a task that lives for 31 ms |
| Principal | `UserId S-1-5-18` (**LocalSystem**), `RunLevel HighestAvailable` | the command would run as SYSTEM, more than Administrator |
| Settings | `Hidden true`, `AllowStartOnDemand true`, `ExecutionTimeLimit P3D`, `Priority 7` | hidden from the default Task Scheduler view, and can be started on demand |
| Action | `cmd.exe /C tasklist > %windir%\Temp\CYAlyNSS.tmp 2>&1` | lists running processes and writes the output, errors included, to a file named after the task |

## What happened (interpretation)

1. **Observed:** at 00:02:04.319945, `EXAMPLE\Administrator` registered a hidden task, `\CYAlyNSS`, that runs `tasklist` as SYSTEM (rec 566836). At 00:02:04.351252 the same logon session deleted it (rec 566840). The definition hadn't changed in between.
2. **The lifetime gives it away.** A task that exists for about 31 ms isn't there to run on a schedule, and it isn't **persistence**. It's a way to **run one command as SYSTEM** and tidy up. If it ran, it was started on demand (`AllowStartOnDemand`), by an API call or `schtasks /run`, in the gap. **T1053.005** (Scheduled Task) used for *execution*.
3. **The output file is the tell for remote use.** `> %windir%\Temp\CYAlyNSS.tmp 2>&1` saves the output to a file named after the task. That's what you do when you **can't see the screen**: someone runs the task from elsewhere, then reads the `.tmp` file back, for example over the `ADMIN$` share. This strongly suggests remote execution, but the export doesn't show where the logon came from.
4. **`tasklist` is reconnaissance:** what's running, including security tools. **T1057** (Process Discovery).
5. **The patch-tool theory, weighed fairly:**

   | Fits a patch tool | Doesn't fit a patch tool |
   |---|---|
   | A temporary task, created and deleted | It runs `tasklist`, which is reconnaissance and installs nothing |
   | An admin account | The *built-in* domain Administrator rather than a named service account |
   | | A random name, `Hidden`, and a start date four years in the past |
   | | Output redirected to a `.tmp` file for collection, not a log the tool keeps |

   On balance, this **doesn't look like patching**. It's still worth asking the client to check the patch tool's own records for 00:02 UTC, because that is a cheap way to rule it out for certain.
6. **Context, not proof:** this exact XML, with the `2015-07-15T20:35:13.2757294` start boundary, `Hidden`, `P3D`, priority 7 and `cmd.exe /C … > %windir%\Temp\<name>.tmp 2>&1`, is the hard-coded template of **Impacket's `atexec.py`**, a public remote-execution tool. A web search for the start boundary finds it. That's a strong lead, but other tools could copy the template, so a report should say "matches the public atexec template" rather than "the attacker used atexec".

## Timeline (UTC, 2019-03-19)

| Time | Rec | Event |
|---|---|---|
| 00:02:04.319945 | 566836 | 4698: `EXAMPLE\Administrator` (logon `0x17e2d2`) creates hidden task `\CYAlyNSS` → `cmd.exe /C tasklist > %windir%\Temp\CYAlyNSS.tmp 2>&1` as SYSTEM |
| — | 566837–566839 | **missing**: three Security events you can't see |
| 00:02:04.351252 | 566840 | 4699: the same session deletes `\CYAlyNSS` |

## Verdict

**Likely malicious (true positive), medium-high confidence.** The domain's built-in Administrator was used to run reconnaissance as SYSTEM through a hidden, self-deleting task that captured its output for collection. That's a remote-execution pattern, and it matches a public offensive tool's template. The patch-tool explanation doesn't fit what the task ran. Escalate, and treat the **domain Administrator credentials as compromised** until the client proves otherwise.

## IOCs

- Task name `\CYAlyNSS` (random, so useful only for this host)
- File `%windir%\Temp\CYAlyNSS.tmp` (output file. It may already be deleted)
- Pattern: a 4698 whose `TaskContent` has `StartBoundary 2015-07-15T20:35:13.2757294`, or an action `cmd.exe /C … > %windir%\Temp\*.tmp 2>&1`
- Account `EXAMPLE\Administrator` (RID 500), logon session `0x17e2d2`

## What you can't conclude from this data

- Whether the task actually ran, and what `tasklist` returned: no Task Scheduler Operational, process-creation or file events
- What the three missing records (566837–566839) were
- Where the `Administrator` logon came from (no 4624 for `0x17e2d2` in the export), or how the attacker got the password
- Whether the `.tmp` file was read back or deleted, and by whom
- What happened before or after this minute, on this host or others
- Whether the patch tool ran anything at that time (the client hasn't said)

## Good next steps (for your recommendations)

- **Investigate:** pull the full Security log around 00:02 UTC. Find the 4624 for LogonId `0x17e2d2` (logon type and source IP), the missing records, and any 5140/5145 share access to `ADMIN$` or `C$`. Pull Task Scheduler Operational (Event IDs 106, 200, 201) to see if the task ran.
- **Ask the client:** check the patch tool's job history for 00:02 UTC and confirm which account it really uses.
- **Contain:** reset the domain Administrator password, review everywhere it's used or stored, and isolate the source host once you know it.
- **Scope:** hunt every host for 4698 events with the 2015 `StartBoundary` or `%windir%\Temp\*.tmp` redirects, and for other logons by `Administrator`.
- **Detect:** alert on a 4698 followed by a 4699 for the same task within seconds, and on any use of the RID-500 account.

*Score yourself with the rubric panel above the answer key in SENTINEL.*
