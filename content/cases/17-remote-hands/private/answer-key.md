# Case 17: Answer key (SPOILERS)

> Don't open this until your `report.md` is finished.

**Source:** EVTX-ATTACK-SAMPLES (sbousseaden), `LM_wmiexec_impacket_sysmon_whoami.evtx`. A researcher recorded it on a Microsoft Windows 7 test VM (`IEWIN7`) while running Impacket's `wmiexec.py` against it from another lab machine, so there's no real victim. Treat it as real for the exercise.

## Survey

- **Sysmon:** 7 events: 4 × Event ID 1, 3 × Event ID 3. Records **9825–9831**, consecutive, no gaps.
- Host `IEWIN7` (10.0.2.18). Processes run as `IEWIN7\IEUser`. Network events are owned by `System` (PID 4) as `NT AUTHORITY\SYSTEM`.
- `UtcTime` range: **20:32:49.659 → 20:32:51.356** on 2019-04-30.
- **Order mismatch:** recs 9830/9831 come *after* rec 9829 by record ID, but their `UtcTime` (51.144) is *before* recs 9826–9829.

## Process tree

```text
WmiPrvSE.exe -secured -Embedding   guid …B0C0…17C31C00, PID 836   [no process-create event]
├── cmd.exe /Q /c cd \ 1> \\127.0.0.1\ADMIN$\__1556656369.7 2>&1          PID 3840, rec 9826
├── cmd.exe /Q /c cd  1> \\127.0.0.1\ADMIN$\__1556656369.7 2>&1           PID 2504, rec 9827
└── cmd.exe /Q /c whoami /all 1> \\127.0.0.1\ADMIN$\__1556656369.7 2>&1   PID 2828, rec 9828
    └── whoami.exe  whoami /all                                             PID 3328, rec 9829
```

## Network events

| Rec | UtcTime | Initiated | This host | Remote | Meaning |
|---|---|---|---|---|---|
| 9825 | 20:32:49.659 | **false** (inbound) | 10.0.2.18:**445** | **10.0.2.19**:45616 | another machine opened an **SMB** connection *to* IEWIN7 |
| 9830 | 20:32:51.144 | true | 127.0.0.1:49162 → 127.0.0.1:445 | itself | **loopback SMB**, the client side |
| 9831 | 20:32:51.144 | false | 127.0.0.1:445 ← 127.0.0.1:49162 | itself | the same loopback connection, server side |

For inbound rec 9825, Sysmon's `Source…` fields are **this host**. The remote party is in `Destination…`. Read `Initiated` first.

## What happened (interpretation)

1. **Someone arrived from 10.0.2.19** at 20:32:49 over SMB (rec 9825). That fits a remote tool connecting to read and write the admin share.
2. **Remote process creation through WMI.** Three `cmd.exe` processes were started by `WmiPrvSE.exe -secured -Embedding` (recs 9826–9828). That's what happens when a caller uses WMI's `Win32_Process.Create`. **T1047** (Windows Management Instrumentation).
3. **Output collected through the admin share.** Each command writes its output and errors (`1> … 2>&1`) to `\\127.0.0.1\ADMIN$\__1556656369.7`, which is `C:\Windows\__1556656369.7`. A process started through WMI has no console the caller can see, so the tool saves output to a file **the remote side can read over SMB**. The loopback SMB connection (recs 9830/9831) is the local half of that redirection. **T1021.002** (SMB/Windows Admin Shares) is the transport for the output.
4. **Tool housekeeping, then an operator command.** `cd \` and then `cd` (recs 9826, 9827) set and read the current directory, which is what a semi-interactive remote shell does on start-up to draw its prompt. `whoami /all` (recs 9828, 9829) is the **first real question**: which user, groups and privileges do I have? **T1033** (System Owner/User Discovery). Running it via `cmd` is **T1059.003**.
5. **The file name is a timestamp.** `1556656369` is Unix epoch time for **2019-04-30 20:32:49 UTC**, the same second as the inbound SMB connection in rec 9825. So the tool named its output file from its own clock when it started. Using a Unix epoch (with a fractional suffix) is typical of tooling written in Python, like Impacket's `wmiexec.py`, whose output files follow exactly this `__<epoch>` pattern. That's context, not proof of which tool it was.
6. **Whose hands:** `IEWIN7\IEUser`, **session 0**, **High** integrity, a new `LogonId 0x1d313d`. Nobody was at the desktop. These are **network logons** using IEUser's credentials. Remote WMI process creation needs **local administrator** rights, so whoever is at 10.0.2.19 has **IEUser's password or hash, and IEUser is an admin on this PC**. **T1078** (Valid Accounts).
7. **The clock:** the loopback connection (51.144) is stamped 24 ms before the first `cmd.exe` it serves (51.168). As with other Sysmon network events, its timestamp isn't exact to the millisecond. Record order puts it after the processes, and it's best read as part of the output writes, not a cause of them.
8. **The inventory theory, tested:** inventory tools **read** WMI classes. They don't need to start `cmd.exe`, write files into `C:\Windows` or ask `whoami /all`. Nothing here is an inventory query. The tool's existence is real, but it doesn't explain these events.
9. **Remote port 45616** is below Windows' default ephemeral range (49152+). It fits a Linux client. That's a weak hint, worth noting, not concluding.

## Timeline (UTC, 2019-04-30)

| Time | Rec | Event |
|---|---|---|
| 20:32:49 | — | `1556656369`: the tool's start time, encoded in the output file name |
| 20:32:49.659 | 9825 | inbound SMB from 10.0.2.19:45616 → IEWIN7:445 |
| 20:32:51.144 (approx., see above) | 9830, 9831 | loopback SMB 127.0.0.1:49162 ↔ 445 |
| 20:32:51.168 | 9826 | WmiPrvSE → `cmd /Q /c cd \ 1> \\127.0.0.1\ADMIN$\__1556656369.7 2>&1` |
| 20:32:51.246 | 9827 | WmiPrvSE → `cmd /Q /c cd …` |
| 20:32:51.324 | 9828 | WmiPrvSE → `cmd /Q /c whoami /all …` |
| 20:32:51.356 | 9829 | `whoami /all` |

## Verdict

**True positive, high confidence: remote command execution over WMI from 10.0.2.19 using IEUser's administrator credentials.** This is **lateral movement** into the paralegal's PC. The source machine and the IEUser credentials are compromised. Escalate.

## IOCs

- Source IP `10.0.2.19` (internal: identify it)
- File `C:\Windows\__1556656369.7` (output file; may have been deleted)
- Account `IEWIN7\IEUser`, network logon `0x1d313d`
- Pattern: `WmiPrvSE.exe` → `cmd.exe /Q /c … 1> \\127.0.0.1\ADMIN$\__<10-digit number>… 2>&1`
- The `Hashes` on `cmd.exe` and `whoami.exe` are **legitimate Windows binaries**. They aren't IOCs.

## What you can't conclude from this data

- Who or what is at 10.0.2.19, and how they got IEUser's credentials (password or hash)
- The DCOM/RPC connection that carried the WMI call (only the SMB side is in the export)
- What `whoami /all` returned, and whether anything was run after 20:32:51
- Whether the output file was read back and deleted
- Whether IEUser's credentials work on other machines (a shared local admin password?)
- Which tool was used, for certain

## Good next steps (for your recommendations)

- **Contain:** isolate `IEWIN7` and the machine at **10.0.2.19**. Reset IEUser's password, and any other local admin account that shares it.
- **Investigate:** Security log 4624 (logon type 3) for `0x1d313d` and its authentication package (NTLM could mean pass-the-hash), WMI-Activity Operational, the rest of the Sysmon log after 20:32:51, and whether `C:\Windows\__1556656369.7` still exists.
- **Scope:** hunt every host for `WmiPrvSE.exe` → `cmd.exe` with `\\127.0.0.1\ADMIN$\__` and for inbound SMB/RPC from 10.0.2.19. Ask Graham whether the inventory tool runs from 10.0.2.19, and if so check that server first.
- **Harden:** unique local admin passwords per machine (e.g. LAPS), restrict remote WMI and SMB to admin hosts with the host firewall, and alert on `WmiPrvSE.exe` spawning shells.

*Score yourself with the rubric panel above the answer key in SENTINEL.*
