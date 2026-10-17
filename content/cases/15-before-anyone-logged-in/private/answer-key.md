# Case 15: Answer key (SPOILERS)

> Don't open this until your `report.md` is finished.

**Source:** EVTX-ATTACK-SAMPLES (sbousseaden), `persistence_accessibility_features_osk_sysmon1.evtx`. A researcher recorded it in a lab domain (`insecurebank.local`, Windows Server 2012 R2) while demonstrating the technique, so there's no real victim. Treat it as real for the exercise.

## Survey

- **Sysmon:** 3 events: 1 × Event ID 12 (rec 18916), 2 × Event ID 1 (recs 18917, 18918). Consecutive, no gaps.
- Host **`DC1.insecurebank.local`**, a **domain controller** by its name.
- Time: **16:08:30.515 → 16:08:40.350 UTC** on 2019-05-16, about 10 seconds.
- Both processes run as `NT AUTHORITY\SYSTEM`, LogonId `0x3e7`, **System** integrity, **TerminalSessionId 2**. The registry event has no `User`.

## Process tree

```text
Utilman.exe /debug   guid …8B00…43C20A00, PID 1112   [no process-create event]
└── osk.exe  "C:\Windows\System32\osk.exe"   PID 1720, rec 18917   ← Description: "Windows Command Processor"
    └── whoami.exe  whoami                   PID 3764, rec 18918

LogonUI.exe   guid …8AFE…35B90A00, PID 1684   [no process-create event]
└── [registry] CreateKey HKLM\SOFTWARE\Policies\Microsoft\Windows NT\Terminal Services   rec 18916
```

`LogonUI.exe` isn't part of the parent-child chain. It's related by time and context only.

## The osk.exe event (rec 18917)

| Field | Value | What's wrong |
|---|---|---|
| `Image` | `C:\Windows\System32\osk.exe` | the On-Screen Keyboard's path and name |
| `Description` | **`Windows Command Processor`** | that's **cmd.exe**'s description, not "Accessibility On-Screen Keyboard" |
| `FileVersion` | `6.3.9600.17415 (winblue_r4…)` | a Server 2012 R2 build string that fits a system binary. It doesn't distinguish the two files by itself |
| Child | `whoami.exe` 5.5 s later (rec 18918) | a keyboard doesn't start command-line tools. A command prompt does, when someone types |

**The file at `osk.exe` is a copy of `cmd.exe`.** The `Hashes` for "osk.exe" would match `cmd.exe` from a clean 2012 R2 host. That's worth checking, and here the hash *is* a useful IOC: an `osk.exe` with cmd's hash.

## What happened (interpretation)

1. **Planted earlier, not in this export:** someone with admin rights replaced `C:\Windows\System32\osk.exe` with `cmd.exe`. That needs taking ownership of a protected system file, so the attacker already had administrative control of `DC1` at some earlier time. **T1546.008** (Event Triggered Execution: Accessibility Features). It's persistence: a door left open for later.
2. **Logon screen up:** at 16:08:30, `LogonUI.exe`, the process that draws the logon screen, created or opened the Terminal Services policy key (rec 18916). This is routine for LogonUI. It shows that a logon screen was being prepared. The `RuleName` "T1076 Remote Desktop Protocol" is a **tag from the Sysmon config's author**, not a detection. It suggests, and doesn't prove, that the session was a Remote Desktop one.
3. **Backdoor used:** about 4 s later, `Utilman.exe /debug`, the **Ease of Access** manager that winlogon starts from the logon screen, launched "osk.exe", which was really `cmd.exe` (rec 18917). It ran as **SYSTEM** (`0x3e7`, System integrity) in **session 2**.
4. **Someone typed `whoami`** 5.5 s later (rec 18918), checking what account they had. **T1033** (System Owner/User Discovery). The answer would have been `nt authority\system`.
5. **Bernadette's claim, tested:** "Nobody was logged on" is **probably true, and that's the point**. This backdoor works *from the logon screen, before anyone authenticates*. No password is needed. No user logon happened, and Session 2 plus LogonUI fits someone sitting at a logon screen in a second session, most often a Remote Desktop connection. So it's **not** a false positive. It's an unauthenticated SYSTEM shell on a domain controller.
6. **Why it's Critical:** SYSTEM on a domain controller means control of Active Directory: every account, every password hash, every group policy in the domain.

## Replaced file or IFEO debugger?

| | Replaced file (this case) | IFEO `Debugger` value |
|---|---|---|
| Sysmon `Image` | `…\osk.exe` | the debugger, e.g. `…\cmd.exe` |
| `CommandLine` | `"C:\Windows\System32\osk.exe"` | e.g. `cmd.exe C:\Windows\System32\osk.exe` |
| Metadata | belongs to the *other* program (`Windows Command Processor`) | matches the debugger's real name |
| Where to look | file hash of `System32\osk.exe` | `HKLM\…\Image File Execution Options\osk.exe\Debugger` |

The data fits a **replaced file**.

## Timeline (UTC, 2019-05-16)

| Time | Rec | Event |
|---|---|---|
| earlier, unknown | — | `osk.exe` replaced with `cmd.exe` (not in this export) |
| 16:08:30.515 | 18916 | `LogonUI.exe` CreateKey `HKLM\SOFTWARE\Policies\Microsoft\Windows NT\Terminal Services` |
| 16:08:34.853 | 18917 | `Utilman.exe /debug` → "osk.exe" (cmd.exe) as SYSTEM, session 2 |
| 16:08:40.350 | 18918 | `whoami` from the SYSTEM shell |

## Verdict

**True positive, Critical, high confidence.** A backdoored accessibility tool gave an unauthenticated SYSTEM command prompt on the domain controller's logon screen, and someone used it. Assume **domain compromise**: the attacker had admin rights on `DC1` before this, and has SYSTEM-level access whenever they reach a logon screen. Escalate to incident response immediately.

## IOCs

- `C:\Windows\System32\osk.exe` with `Description: Windows Command Processor`, SHA256 `6F88FB88FFB0F1D5465C2826E5B4F523598B1B8378377C8378FFEBC171BAD18B` (check it against a clean `cmd.exe` and `osk.exe` from the same build)
- Behavior: `Utilman.exe` → `osk.exe` → any command-line tool, and accessibility binaries (`sethc`, `utilman`, `osk`, `magnify`, `narrator`, `displayswitch`, `atbroker`) whose metadata doesn't match their names
- The `whoami.exe` hash is a legitimate Windows binary. It isn't an IOC.

## What you can't conclude from this data

- When, how and by whom `osk.exe` was replaced, or which account had admin rights at that time
- Whether session 2 was a Remote Desktop connection, and if so from which IP address (needs Security 4624/4625/4778 or TerminalServices logs)
- What was typed after `whoami`: no events after 16:08:40
- Whether other accessibility binaries, or other DCs, are backdoored too
- How the attacker first gained admin access to the domain

## Good next steps (for your recommendations)

- **Escalate:** treat this as an active domain compromise and bring in incident response.
- **Contain:** restrict network access to `DC1`, especially RDP, to known admin hosts. Don't reboot or "fix" the file before preserving it.
- **Preserve:** collect `System32\osk.exe` and the other accessibility binaries with hashes and timestamps, full Sysmon/Security/TerminalServices logs, and a memory image if feasible.
- **Investigate:** find the RDP connection behind session 2 (TerminalServices-RemoteConnectionManager 1149, LocalSessionManager 21/22/25, Security 4778/4779). Find when `osk.exe` changed (file timestamps, USN journal, Volume Shadow Copies).
- **Scope:** check every DC and server for altered accessibility binaries and IFEO `Debugger` values. Plan for domain-wide credential resets, including `krbtgt` (twice).
- **Prevent:** require Network Level Authentication for RDP, so nobody reaches a logon screen without credentials, and monitor System32 accessibility binaries for changes.

*Score yourself with the rubric panel above the answer key in SENTINEL.*
