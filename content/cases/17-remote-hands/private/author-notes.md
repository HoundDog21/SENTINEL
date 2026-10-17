# Author notes: 17-remote-hands

Private to the case author. The app never shows this file. It lists mechanical facts about the data to help you write the brief, hints and answer key. It is **not** an analysis: decide yourself what matters.

Generated 2026-10-17T00:16:50Z by `tools/case.py survey`.

## Sources

| Case file | From | Format | Events | SHA-256 |
|---|---|---|---|---|
| `data/case17-sysmon.jsonl` | LM_wmiexec_impacket_sysmon_whoami.evtx | EVTX (chainsaw dump) | 7 | `21b8852b2b38…` |

## Counts

| Channel | Event ID | Label | Count |
|---|---|---|---|
| Microsoft-Windows-Sysmon/Operational | 1 | Process create | 4 |
| Microsoft-Windows-Sysmon/Operational | 3 | Network connection | 3 |

- **Events:** 7
- **Hosts:** `IEWIN7` (7)
- **Users:** `IEWIN7\IEUser` (4), `NT AUTHORITY\SYSTEM` (3)

## Time and record IDs per channel

| Channel | First (UTC) | Last (UTC) | Record IDs | Missing |
|---|---|---|---|---|
| Microsoft-Windows-Sysmon/Operational | 2019-04-30 20:32:49.659 | 2019-04-30 20:32:51.356 | 9825–9831 | none |

Record order vs time order: 1 place(s) where a later event has a lower record ID within its channel.

## Process-create style events (time order)

| Time | Ref | Image | ProcessGuid | ParentProcessGuid | Parent image | Command line |
|---|---|---|---|---|---|---|
| 2019-04-30 20:32:51.168 | rec 9826 | `C:\Windows\System32\cmd.exe` | `365ABB72-B0F3-5CC8-0000-00105F321D00` | `365ABB72-B0C0-5CC8-0000-001017C31C00` (no process-create event) | `C:\Windows\System32\wbem\WmiPrvSE.exe` | `cmd.exe /Q /c cd \ 1> \\127.0.0.1\ADMIN$\__1556656369.7 2>&1` |
| 2019-04-30 20:32:51.246 | rec 9827 | `C:\Windows\System32\cmd.exe` | `365ABB72-B0F3-5CC8-0000-0010B1361D00` | `365ABB72-B0C0-5CC8-0000-001017C31C00` (no process-create event) | `C:\Windows\System32\wbem\WmiPrvSE.exe` | `cmd.exe /Q /c cd  1> \\127.0.0.1\ADMIN$\__1556656369.7 2>&1` |
| 2019-04-30 20:32:51.324 | rec 9828 | `C:\Windows\System32\cmd.exe` | `365ABB72-B0F3-5CC8-0000-0010C43A1D00` | `365ABB72-B0C0-5CC8-0000-001017C31C00` (no process-create event) | `C:\Windows\System32\wbem\WmiPrvSE.exe` | `cmd.exe /Q /c whoami /all 1> \\127.0.0.1\ADMIN$\__1556656369.7 2>&1` |
| 2019-04-30 20:32:51.356 | rec 9829 | `C:\Windows\System32\whoami.exe` | `365ABB72-B0F3-5CC8-0000-0010373E1D00` | `365ABB72-B0F3-5CC8-0000-0010C43A1D00` | `C:\Windows\System32\cmd.exe` | `whoami  /all ` |
