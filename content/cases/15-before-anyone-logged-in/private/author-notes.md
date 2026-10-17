# Author notes: 15-before-anyone-logged-in

Private to the case author. The app never shows this file. It lists mechanical facts about the data to help you write the brief, hints and answer key. It is **not** an analysis: decide yourself what matters.

Generated 2026-10-17T00:16:50Z by `tools/case.py survey`.

## Sources

| Case file | From | Format | Events | SHA-256 |
|---|---|---|---|---|
| `data/case15-sysmon.jsonl` | persistence_accessibility_features_osk_sysmon1.evtx | EVTX (chainsaw dump) | 3 | `9a99994be7f6…` |

## Counts

| Channel | Event ID | Label | Count |
|---|---|---|---|
| Microsoft-Windows-Sysmon/Operational | 1 | Process create | 2 |
| Microsoft-Windows-Sysmon/Operational | 12 | Registry key create/delete | 1 |

- **Events:** 3
- **Hosts:** `DC1.insecurebank.local` (3)
- **Users:** `NT AUTHORITY\SYSTEM` (2)

## Time and record IDs per channel

| Channel | First (UTC) | Last (UTC) | Record IDs | Missing |
|---|---|---|---|---|
| Microsoft-Windows-Sysmon/Operational | 2019-05-16 16:08:30.515 | 2019-05-16 16:08:40.350 | 18916–18918 | none |

Record order vs time order: 0 place(s) where a later event has a lower record ID within its channel.

## Process-create style events (time order)

| Time | Ref | Image | ProcessGuid | ParentProcessGuid | Parent image | Command line |
|---|---|---|---|---|---|---|
| 2019-05-16 16:08:34.853 | rec 18917 | `C:\Windows\System32\osk.exe` | `DFAE8213-8B02-5CDD-0000-00109BCA0A00` | `DFAE8213-8B00-5CDD-0000-001043C20A00` (no process-create event) | `C:\Windows\System32\Utilman.exe` | `"C:\Windows\System32\osk.exe"  ` |
| 2019-05-16 16:08:40.350 | rec 18918 | `C:\Windows\System32\whoami.exe` | `DFAE8213-8B08-5CDD-0000-001011CE0A00` | `DFAE8213-8B02-5CDD-0000-00109BCA0A00` | `C:\Windows\System32\osk.exe` | `whoami` |
