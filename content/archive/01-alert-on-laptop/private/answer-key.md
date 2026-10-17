# Case 01: Answer key (SPOILERS)

> Don't open this until your `report.md` is finished.

**Source:** EVTX-ATTACK-SAMPLES (sbousseaden), `Execution/sysmon_zipexec.evtx`. The researcher recorded it in a lab while demonstrating a technique ("testme.js"), so it's not a real victim. Treat it as real for the exercise.

## Survey

- 8 events: 5 × Event ID 1, 3 × Event ID 11
- Host `LAPTOP-JU4M3I0E`, user `LAPTOP-JU4M3I0E\bouss`, LogonId `0x779c2`, Medium integrity, session 1
- 2021-10-21 16:27:02.278 → 16:27:12.925 UTC (about 11 seconds)
- EventRecordIDs 10920364–10920383 with gaps (365–366, 368, 371–377, 380, 382). The export is partial.

## Process tree

```text
[unknown] cmd.exe  (ParentProcessGuid …85C9-6170-…-001008E62B6B, PID 24148; not in data)
└── cscript.exe //e:jscript testme.js          guid …94D6…0514967B   rec 10920364
    ├── cmdkey.exe /generic:Microsoft_Windows_Shell_ZipFolder:filename=…\Temp\lync.zip /pass:tWIMmIF /user:""   rec 10920367
    ├── i.exe  (…\Temp\Temp3_lync.zip\i.exe; OriginalFileName Cmd.Exe)                                  rec 10920379
    └── cmdkey.exe /delete Microsoft_Windows_Shell_ZipFolder:filename=…\Temp\lync.zip                   rec 10920381

[separate tree] elastic-endpoint.exe run → elastic-endpoint.exe popup "Malicious Behavior Detection Alert" …   rec 10920383
```

## File events (all written by cscript.exe, guid …0514967B)

| Rec | UtcTime | TargetFilename | CreationUtcTime |
|---|---|---|---|
| 10920369 | 16:27:03.397 | `C:\Users\bouss\AppData\Local\Temp\lync.zip` | **2021-10-21 12:05:31.740** (≈4h20m earlier) |
| 10920370 | 16:27:12.522 | `…\Temp\Temp3_lync.zip` (extraction folder) | 16:27:12.521 |
| 10920378 | 16:27:12.549 | `…\Temp\Temp3_lync.zip\i.exe` | 16:27:12.548 |

The earlier `CreationUtcTime` on lync.zip shows the timestamp was carried over from somewhere (copied or extracted from a source that kept it, or set explicitly). It does **not** tell you where the ZIP came from.

## What happened (interpretation)

1. A JScript file `testme.js` on the user's Desktop was run with `cscript.exe` from a `cmd.exe` prompt. **T1059.007** (JavaScript).
2. The script stored a password (`tWIMmIF`) in Credential Manager under `Microsoft_Windows_Shell_ZipFolder:filename=<zip path>`. Windows' built-in ZIP handler checks this credential, so a **password-protected ZIP can be extracted silently** without prompting the user. Password-protected archives are a common way to slip past email and AV scanning. Related: **T1027** (obfuscated files) / archive evasion.
3. The script wrote `lync.zip` to `%TEMP%`, and the Shell ZIP handler (running inside cscript's process) extracted it to `Temp3_lync.zip\`, dropping `i.exe`.
4. `i.exe` was run. Its PE metadata says it is **`cmd.exe`** (`OriginalFileName: Cmd.Exe`, Description "Windows Command Processor"), so it's a **renamed signed Microsoft binary**. **T1036.003** (Masquerading: Rename System Utilities). This is what the alert detected.
5. The script then **deleted the credential** to clean up. **T1070** (Indicator Removal).
6. `elastic-endpoint.exe … popup` is the security product's **user notification**, which is a *reaction* to the activity, not part of it. Its UtcTime (16:27:12.873) is *earlier* than the cmdkey /delete (16:27:12.925), but it has a *higher* EventRecordID (10920383 vs 10920381). Record order follows when events were written to the log, not when they happened. Always sort by time.

## Verdict

**True positive for malicious-technique execution, high confidence.** The scripted silent extraction of a password-protected archive, followed by running a renamed system binary from %TEMP% and then cleanup, has no plausible benign explanation. (Real-world context: it's a lab test. In a real environment you'd confirm with the user and team.)

## IOCs

- `C:\Users\bouss\Desktop\testme.js`
- `C:\Users\bouss\AppData\Local\Temp\lync.zip`, ZIP password `tWIMmIF`
- `C:\Users\bouss\AppData\Local\Temp\Temp3_lync.zip\i.exe`, SHA256 `FF79D3C4A0B7EB191783C323AB8363EBD1FD10BE58D8BCC96B07067743CA81D5` (a legitimate cmd.exe hash, so it's useful for spotting renamed copies but **not** as a "bad hash" blocklist entry)
- Command-line pattern: `cmdkey /generic:Microsoft_Windows_Shell_ZipFolder:` (good for hunting)

## What you can't conclude from this data

- How `testme.js` reached the Desktop (no email, browser or download events)
- Where `lync.zip`'s content came from, or why its creation time is 12:05
- What `i.exe` actually *did*: there are no child processes, network events or command arguments in the export. It may have been blocked by the endpoint agent, or the events may simply be missing from the partial export (recall the record-ID gaps).
- Who launched the parent `cmd.exe` (not in data)
- Whether the endpoint agent blocked or only alerted
- Whether other hosts were affected

## Good next steps (for your recommendations)

- Preserve: acquire `testme.js`, `lync.zip`, `Temp3_lync.zip\` and the full Sysmon/Security logs for the window, *before* cleanup
- Scope: hunt fleet-wide for `Microsoft_Windows_Shell_ZipFolder` in cmdkey command lines, `i.exe` / `OriginalFileName=Cmd.Exe` with a non-cmd.exe image name, and `testme.js`
- Contain: isolate the host if `i.exe` ran successfully or the origin is unknown. Reset user credentials if the source was phishing.
- Detect: alert on `Image` ≠ `OriginalFileName` for system binaries, and on cmdkey with the ZipFolder target

*Score yourself with the rubric panel above the answer key in SENTINEL.*
