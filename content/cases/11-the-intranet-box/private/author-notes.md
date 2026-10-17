# Author notes: 11-the-intranet-box

Private to the case author. The app never shows this file. It lists mechanical facts about the data to help you write the brief, hints and answer key. It is **not** an analysis: decide yourself what matters.

Generated 2026-10-17T00:16:50Z by `tools/case.py survey`.

## Sources

| Case file | From | Format | Events | SHA-256 |
|---|---|---|---|---|
| `data/case11-sysmon.jsonl` | LM_typical_IIS_webshell_sysmon_1_10_traces.evtx | EVTX (chainsaw dump) | 4 | `6f1cb3c43538…` |

## Counts

| Channel | Event ID | Label | Count |
|---|---|---|---|
| Microsoft-Windows-Sysmon/Operational | 1 | Process create | 3 |
| Microsoft-Windows-Sysmon/Operational | 10 | Process access | 1 |

- **Events:** 4
- **Hosts:** `IEWIN7` (4)
- **Users:** `IIS APPPOOL\DefaultAppPool` (3)

## Time and record IDs per channel

| Channel | First (UTC) | Last (UTC) | Record IDs | Missing |
|---|---|---|---|---|
| Microsoft-Windows-Sysmon/Operational | 2019-05-24 01:33:53.112 | 2019-05-24 01:33:53.162 | 1044–1047 | none |

Record order vs time order: 0 place(s) where a later event has a lower record ID within its channel.

## Process-create style events (time order)

| Time | Ref | Image | ProcessGuid | ParentProcessGuid | Parent image | Command line |
|---|---|---|---|---|---|---|
| 2019-05-24 01:33:53.112 | rec 1044 | `C:\Windows\System32\cmd.exe` | `365ABB72-4A01-5CE7-0000-0010EE9DAC00` | `365ABB72-49D6-5CE7-0000-001020A7A700` (no process-create event) | `C:\Windows\System32\inetsrv\w3wp.exe` | `"c:\windows\system32\cmd.exe" /c net user` |
| 2019-05-24 01:33:53.152 | rec 1046 | `C:\Windows\System32\net.exe` | `365ABB72-4A01-5CE7-0000-00102DA1AC00` | `365ABB72-4A01-5CE7-0000-0010EE9DAC00` | `C:\Windows\System32\cmd.exe` | `net  user` |
| 2019-05-24 01:33:53.162 | rec 1047 | `C:\Windows\System32\net1.exe` | `365ABB72-4A01-5CE7-0000-0010B6A2AC00` | `365ABB72-4A01-5CE7-0000-00102DA1AC00` | `C:\Windows\System32\net.exe` | `C:\Windows\system32\net1  user` |
