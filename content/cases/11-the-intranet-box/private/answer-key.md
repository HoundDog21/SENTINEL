# Case 11: Answer key (SPOILERS)

> Don't open this until your `report.md` is finished.

**Source:** EVTX-ATTACK-SAMPLES (sbousseaden), `LM_typical_IIS_webshell_sysmon_1_10_traces.evtx`. A researcher recorded it on a Microsoft Windows 7 test VM (`IEWIN7`) while running a command through a web shell, so there's no real victim. Treat it as real for the exercise.

## Survey

- **Sysmon:** 4 events: 3 × Event ID 1, 1 × Event ID 10. Records **1044–1047**, consecutive, no gaps.
- Host `IEWIN7`. Every process runs as `IIS APPPOOL\DefaultAppPool`, LogonId `0x9cf992`, `TerminalSessionId` 0, High integrity, `CurrentDirectory` `c:\windows\system32\inetsrv\`. The Event ID 10 has no `User` field.
- Time (by `UtcTime`): **01:33:53.112 → 01:33:53.162 UTC** on 2019-05-24, **50 milliseconds** in total.
- The export is consecutive, but it's only 50 ms long. It says nothing about what happened before record 1044 or after record 1047.

## Process tree

```text
w3wp.exe  -ap "DefaultAppPool" -v "v2.0"   guid …49D6…20A7A700, PID 2580   [no process-create event; it is the source in rec 1045]
└── cmd.exe "c:\windows\system32\cmd.exe" /c net user        PID 2404, rec 1044
    └── net.exe  net  user                                  PID 788,  rec 1046
        └── net1.exe C:\Windows\system32\net1  user         PID 712,  rec 1047
```

`w3wp.exe` belongs in the tree as a not-in-evidence node. Its `ProcessGuid` appears as `SourceProcessGUID` in rec 1045, so it is in the data, just not as a process-create event.

## The process-access event

| Rec | UtcTime | Source → Target | GrantedAccess | CallTrace (summary) |
|---|---|---|---|---|
| 1045 | 01:33:53.112 | `w3wp.exe` (2580) → `cmd.exe` (2404) | `0x1fffff` | `ntdll` → `kernel32` → `mscorwks.dll` (CLR 2.0) → `UNKNOWN` → `System.ni.dll` → `UNKNOWN` → several `System.Web.ni.dll` frames |

- **Observed:** same `UtcTime` as rec 1044, and the target GUID is the `cmd.exe` created in rec 1044. `0x1fffff` is `PROCESS_ALL_ACCESS`.
- **Interpretation:** this is the full-rights handle a parent gets back from `CreateProcess` for its own new child. It's a side effect of the launch in rec 1044, **not** a separate action like injection or credential theft (the target is `cmd.exe`, not `lsass.exe`).
- **CallTrace:** the call came up through the ASP.NET request pipeline (`System.Web`) into the .NET runtime (`mscorwks.dll`) and `System.dll` (where `System.Diagnostics.Process` lives) before reaching `kernel32`. The `UNKNOWN(…)` frames are **JIT-compiled .NET code**, which has no module on disk. They're normal here and are not evidence of injected shellcode. What this does show is that the command was started by **code running inside the web application**, during a web request.

## What happened (interpretation)

1. The IIS worker process for **DefaultAppPool**, an ASP.NET 2.0 application pool, started `cmd.exe /c net user` (rec 1044, with rec 1045 as the handle it got back). A web application starting a command shell is abnormal. Ordinary pages don't do it, and the client named no page or job that should.
2. `cmd /c net user` lists the **local user accounts**. That's reconnaissance: the person behind it wants to know which accounts exist. **T1087.001** (Account Discovery: Local Account). Running it through the shell is **T1059.003** (Windows Command Shell).
3. `net.exe` (rec 1046) started `net1.exe` (rec 1047) 10 ms later. That's how `net.exe` works on this version of Windows, and it's **one command**, not two.
4. Everything ran as `IIS APPPOOL\DefaultAppPool` in session 0 with the IIS directory as its working directory. No person was logged on at the console. The command arrived through the web server.
5. **How it reached the web server is not in the data.** Two common explanations fit equally well:
   - a **web shell**: a script file planted in the site that runs whatever command it's sent (**T1505.003**), or
   - **command injection** in the real application: a page that passes user input to a shell (**T1190**).
   The process log can't tell these apart. The dataset's author labels it a web shell, but you couldn't know that from the four events. A report should say "consistent with a web shell or command injection" and name what would decide it.
6. **Timing:** the chain took 50 ms. That doesn't show automation. A person typing into a web shell form gets the same `cmd /c` wrapper and the same speed.

## Timeline (UTC, 2019-05-24)

| Time | Rec | Event |
|---|---|---|
| 01:33:53.112 | 1044 | `w3wp.exe` (DefaultAppPool) starts `cmd.exe /c net user` |
| 01:33:53.112 | 1045 | `w3wp.exe` holds a full-access handle to the new `cmd.exe` (CallTrace through System.Web) |
| 01:33:53.152 | 1046 | `cmd.exe` starts `net  user` |
| 01:33:53.162 | 1047 | `net.exe` starts `net1  user` |

## Verdict

**True positive, high confidence** that code running inside the intranet web application executed an operating-system command to enumerate local accounts. Nothing in the data looks like a maintenance job: a job would normally run from Task Scheduler or a service, not from the IIS worker in the middle of a web request, and it wouldn't list user accounts. Escalate as a **likely web server compromise**. The entry point (web shell or vulnerable page) is undetermined.

## IOCs

- Behavior: `w3wp.exe` (DefaultAppPool) → `cmd.exe /c net user` on `IEWIN7` at 01:33:53 UTC
- Account: `IIS APPPOOL\DefaultAppPool`, LogonId `0x9cf992`, the identity the attacker's commands run as
- The `Hashes` on `cmd.exe`, `net.exe` and `net1.exe` are **legitimate Windows binaries**. They aren't IOCs.
- There's **no** file name, URL or IP address in this data. Don't invent one.

## What you can't conclude from this data

- Which URL or file handled the request, and whether a web shell exists at all (no file events, no IIS logs)
- Who sent the request and from where: no source IP, so "internal only" is neither confirmed nor ruled out
- What `net user` returned, or whether the attacker saw the output
- How the attacker got code onto, or a vulnerability into, the site, and when
- What happened before record 1044 or after record 1047: other commands, network connections, files written
- Whether the maintenance job Owen mentioned exists or ran that night

## Good next steps (for your recommendations)

- **Contain:** take the portal off the network, or at least block inbound web traffic to it, until the entry point is found.
- **Preserve:** collect IIS logs (`C:\inetpub\logs\LogFiles`) around 01:33:53 UTC, the whole web root with file timestamps, the full Sysmon and Security logs, and if possible a memory image of `w3wp.exe`.
- **Investigate:** look in the web root for recently created or modified `.aspx`, `.ashx`, `.asmx` or `.asp` files. Match the IIS log request at 01:33:53 to a page. Check the firewall or NAT rules to test the "internal only" claim.
- **Scope:** hunt for any other children of `w3wp.exe` on this server and on the client's other IIS hosts. Review which local accounts exist and reset any that the app pool could reach.
- **Detect:** alert on `w3wp.exe` starting `cmd.exe`, `powershell.exe`, `net.exe`, `whoami.exe` and similar.

*Score yourself with the rubric panel above the answer key in SENTINEL.*
