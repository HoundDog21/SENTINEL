# Case 01: Answer key (SPOILERS)

> Don't open this until your `report.md` is finished.

**Source:** EVTX-ATTACK-SAMPLES (sbousseaden), `Execution/sysmon_1_11_rundll32_cpl_ostap.evtx` and `Execution/Exec_via_cpl_Application_Experience_EventID_17_ControlPanelApplet.evtx`. The researcher recorded them on a Microsoft test VM (`MSEDGEWIN10`, user `IEUser`) while running a sample, so there's no real victim. Treat it as real for the exercise.

## Survey

- **Sysmon:** 5 events: 4 × Event ID 1, 1 × Event ID 11. Records 4860–4865 with **4862 missing**, so the export is partial.
- **Program Compatibility Assistant (PCA):** 4 × Event ID 17, records 1–4, spread from **2019-07-18 to 2019-08-23**. That's a much wider window than the Sysmon export.
- Host `MSEDGEWIN10`, user `MSEDGEWIN10\IEUser`, LogonId `0x4131b5`, Medium integrity, session 1 on every process.
- The Sysmon activity runs **21:11:11.127 → 21:11:19.010 UTC** on 2019-07-29, about 8 seconds.

## Process tree

```text
explorer.exe   guid …6056…C9EF4100, PID 4600   [no process-create event; it shows up as the writer in rec 4860]
└── control.exe "…\Downloads\Invoice@0582.cpl",                                      rec 4861
    └── rundll32.exe (System32) Shell32.dll,Control_RunDLL "…\Invoice@0582.cpl",     rec 4863
        └── rundll32.exe (SysWOW64) "…\SysWOW64\shell32.dll",#44 "…\Invoice@0582.cpl",  rec 4864
            └── wscript.exe (SysWOW64) /e:JScript.Encode /nologo …\AppData\Local\Temp\info.txt   rec 4865
```

`explorer.exe` has no Event ID 1 in the export, so it belongs in the tree as a not-in-evidence node. Its `ProcessGuid` does appear in the file-create event (rec 4860), which ties the file write and the launch to the same Explorer process. Either way of showing that is correct, as long as you don't invent a process-create event for it.

## The file event

| Rec | UtcTime | Process | TargetFilename | CreationUtcTime |
|---|---|---|---|---|
| 4860 | 21:11:11.127 | `explorer.exe` (…C9EF4100) | `C:\Users\IEUser\Downloads\Invoice@0582.cpl` | **21:09:48.910** (about 82 s earlier) |

Explorer wrote the file, not a browser or mail client. That fits a user copying or extracting it in Explorer, such as dragging it out of an archive, but the logs don't prove that. The earlier `CreationUtcTime` shows the timestamp came from somewhere else. It doesn't say where.

## What happened (interpretation)

1. A file named `Invoice@0582.cpl` landed in Downloads (rec 4860). A `.cpl` is a **Control Panel item: a DLL** with a Control Panel entry point. It runs code when opened. The "invoice" name and the `@` are social engineering.
2. Six seconds later Explorer started `control.exe` with the `.cpl` as its argument (rec 4861). That's what happens when you **double-click** a `.cpl`. It strongly suggests the user opened it, though "double-click" is an inference. **T1204.002** (User Execution: Malicious File).
3. `control.exe` handed it to `rundll32.exe Shell32.dll,Control_RunDLL` (rec 4863). Because this `.cpl` is **32-bit**, Windows relaunched it in the 32-bit `SysWOW64\rundll32.exe` via `shell32.dll,#44` (rec 4864). **Both rundll32 launches are Windows' normal plumbing for a 32-bit Control Panel item**, not two attacker stages. The attacker's code ran *inside* the second rundll32. **T1218.002** (System Binary Proxy Execution: Control Panel).
4. That code started `wscript.exe /e:JScript.Encode /nologo …\Temp\info.txt` (rec 4865). `/e:JScript.Encode` forces the **encoded JScript** engine, so `info.txt` is an obfuscated script wearing a `.txt` extension. **T1059.007** (JavaScript), **T1027** (Obfuscated Files or Information).
5. **The path mismatch:** `CommandLine` says `C:\Windows\System32\wscript.exe` but `Image` is `C:\Windows\SysWOW64\wscript.exe`. A 32-bit process asked for System32 and Windows' **WOW64 file-system redirection** quietly gave it the 32-bit copy. It's not spoofing, and it confirms the launcher was 32-bit.
6. **PCA rec 2** (`ResolverName: ControlPanelApplet`, `ExePath: …\Invoice@0582.cpl`) at **21:11:17.282** lands between `control.exe` (17.256) and the first `rundll32` (17.445). An independent log corroborates that this `.cpl` was run as a Control Panel applet.
7. **PCA recs 1, 3 and 4** are `procexp64.exe` (Sysinternals Process Explorer) on the Desktop, with `WrpKeyMitigation`, on 07-18, 07-29 21:14:29 (three minutes after the chain) and 08-23. They're a legitimate admin tool and not part of the chain. The 21:14 run is close in time, but nothing in the data links it to the `.cpl`. "Unrelated or unexplained" is right. "Attacker tool" or "the user investigating" is a guess.

## Timeline (both logs, UTC, 2019-07-29)

| Time | Log / rec | Event |
|---|---|---|
| 21:09:48.910 | Sysmon 4860 (field) | `CreationUtcTime` of the `.cpl`. A timestamp, not an observed event |
| 21:11:11.127 | Sysmon 4860 | Explorer writes `Downloads\Invoice@0582.cpl` |
| 21:11:17.256 | Sysmon 4861 | `control.exe` opens the `.cpl` |
| 21:11:17.282 | PCA 2 | PCA: Control Panel applet `Invoice@0582.cpl` |
| 21:11:17.445 | Sysmon 4863 | `rundll32.exe` (64-bit) `Control_RunDLL` |
| 21:11:17.503 | Sysmon 4864 | `rundll32.exe` (32-bit) `shell32.dll,#44` |
| 21:11:19.010 | Sysmon 4865 | `wscript.exe /e:JScript.Encode …\Temp\info.txt` |
| 21:14:29.638 | PCA 3 | `procexp64.exe` on Desktop (not linked to the chain) |

Sysmon record 4862 is missing between `control.exe` and `rundll32`. Something was logged there that you can't see.

## Verdict

**True positive, high confidence.** A Control Panel file disguised as an invoice, opened from Downloads, that immediately runs an encoded script from `%TEMP%` has no plausible business explanation. Escalate. The client's "accounting software" theory doesn't match any event.

For context, the sample's author labeled it **Ostap**, a known JScript downloader family. You couldn't know that from these logs, and a report shouldn't name a malware family without evidence like a hash match or the script's contents.

## IOCs

- `C:\Users\IEUser\Downloads\Invoice@0582.cpl` (file name and path. The logs have no hash for it, so collect the file)
- `C:\Users\IEUser\AppData\Local\Temp\info.txt` (encoded JScript, origin unknown)
- Command-line pattern: `wscript.exe /e:JScript.Encode` with a non-`.jse` file, and `rundll32.exe … shell32.dll,#44` pointing at a `.cpl` in a user folder
- The `Hashes` on the four processes are **legitimate Windows binaries**. They aren't IOCs.

## What you can't conclude from this data

- How the `.cpl` reached the PC (email, browser, USB?), or why its creation time is 82 seconds before the write
- Who or what wrote `info.txt`: there's no file-create event for it (maybe in the missing record, maybe outside the export)
- What `info.txt` contains, and what `wscript.exe` did next: no network, child process or file events after 21:11:19
- What the missing Sysmon record 4862 was
- Whether the endpoint agent blocked anything or only alerted
- Whether other hosts or users received the same file

## Good next steps (for your recommendations)

- **Contain:** isolate `MSEDGEWIN10` until you know what the script did. Treat the user's credentials as exposed.
- **Preserve:** collect `Invoice@0582.cpl`, `info.txt`, the user's mail and browser history, and complete Sysmon and Security logs for the window, before anyone cleans up.
- **Scope:** hunt every client for `Invoice@*.cpl`, `wscript.exe /e:JScript.Encode`, and `SysWOW64\rundll32.exe … #44` with a user-folder `.cpl`. Ask whether the same "invoice" was emailed to other staff.
- **Detect and prevent:** block `.cpl` attachments and archives containing them at the mail gateway, and alert on script hosts spawned by `rundll32.exe`.

*Score yourself with the rubric panel above the answer key in SENTINEL.*
