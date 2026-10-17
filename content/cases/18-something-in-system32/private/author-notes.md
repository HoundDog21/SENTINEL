# Author notes: 18-something-in-system32

Private to the case author. The app never shows this file. It lists mechanical facts about the data to help you write the brief, hints and answer key. It is **not** an analysis: decide yourself what matters.

Generated 2026-10-17T00:16:50Z by `tools/case.py survey`.

## Sources

| Case file | From | Format | Events | SHA-256 |
|---|---|---|---|---|
| `data/case18-sysmon.jsonl` | sysmon_10_1_memdump_comsvcs_minidump.evtx | EVTX (chainsaw dump) | 6 | `d1bf591cabf7…` |

## Counts

| Channel | Event ID | Label | Count |
|---|---|---|---|
| Microsoft-Windows-Sysmon/Operational | 1 | Process create | 2 |
| Microsoft-Windows-Sysmon/Operational | 7 | Image loaded | 2 |
| Microsoft-Windows-Sysmon/Operational | 10 | Process access | 1 |
| Microsoft-Windows-Sysmon/Operational | 11 | File create | 1 |

- **Events:** 6
- **Hosts:** `MSEDGEWIN10` (6)
- **Users:** `MSEDGEWIN10\IEUser` (2)

## Time and record IDs per channel

| Channel | First (UTC) | Last (UTC) | Record IDs | Missing |
|---|---|---|---|---|
| Microsoft-Windows-Sysmon/Operational | 2019-08-30 12:54:07.823 | 2019-08-30 12:54:08.424 | 32151–32156 | none |

Record order vs time order: 0 place(s) where a later event has a lower record ID within its channel.

## Process-create style events (time order)

| Time | Ref | Image | ProcessGuid | ParentProcessGuid | Parent image | Command line |
|---|---|---|---|---|---|---|
| 2019-08-30 12:54:07.823 | rec 32151 | `C:\Windows\System32\cscript.exe` | `747F3D96-1C6F-5D69-0000-0010323C1F00` | `747F3D96-1B6C-5D69-0000-00106F060F00` (no process-create event) | `C:\Windows\System32\cmd.exe` | `cscript  c:\ProgramData\memdump.vbs notepad.exe` |
| 2019-08-30 12:54:08.331 | rec 32154 | `C:\Windows\System32\rundll32.exe` | `747F3D96-1C70-5D69-0000-0010C9661F00` | `747F3D96-1C70-5D69-0000-0010D4551F00` (no process-create event) | `C:\Windows\System32\wbem\WmiPrvSE.exe` | `rundll32 C:\windows\system32\comsvcs.dll, MiniDump 4868 C:\Windows\System32\notepad.bin full` |
