# Tutorial: Practice answer key

**This is ordinary user activity. Classification: Benign.**

## What happened

| Time (UTC) | Record | Event | What it shows |
|---|---|---|---|
| 08:59:58 | Security 41532 | 4624, LogonType 2 | `cody` logged on interactively at the keyboard (logon ID `0x3b2a1`) |
| 09:00:04 | Sysmon 3101 | 1, process create | `explorer.exe` (the desktop shell) started, parent `userinit.exe` |
| 09:02:41 | Sysmon 3102 | 1, process create | `notepad.exe` started, parent `explorer.exe`: the user opened Notepad |
| 09:04:15 | Sysmon 3103 | 13, registry value set | Notepad updated the Save dialog's recent-files list for `.txt` |
| 09:04:15 | Sysmon 3104 | 11, file create | Notepad wrote `C:\Users\cody\Documents\shopping-list.txt` |
| 09:05:02 | Sysmon 3105 | 5, process terminated | Notepad closed |

## Process tree

```text
userinit.exe [not in evidence]
└── explorer.exe (rec 3101)
    └── notepad.exe (rec 3102)
```

`notepad.exe`'s `ParentProcessGuid` (`…0AB1…` → `…0A14…`) matches `explorer.exe`'s `ProcessGuid`. `explorer.exe`'s parent, `userinit.exe`, has no process-create event in this data, so it's a not-in-evidence node.

## Things worth noticing even on boring data

- **Two logs, two record-ID sequences.** The Security event is record 41532 and the Sysmon events are 3101–3105. Record IDs are only comparable within one channel.
- **The logon ID ties the logs together.** The 4624's `TargetLogonId` (`0x3b2a1`) matches the `LogonId` on the Sysmon process events.
- **Benign is a finding.** A good report on harmless activity still cites the events, says what the logs can't show (what was typed into the file, for one), and recommends closing the alert or tuning the rule.

## IOCs

None. There's nothing malicious here. If you flagged `shopping-list.txt` while practicing, that's fine. In a real report, an IOC list for benign activity should be empty, or should say why each item is listed.
