# Case 13: Hints

Read one hint at a time, and only after you've really tried that step.

---

### Step 1: Survey

<details><summary>Hint 1</summary>

```sh
jq -r '[.Event.System.EventRecordID, .Event.System.EventID, .Event.EventData.UtcTime] | @tsv' data/case13-sysmon.jsonl
```
Now sort that list by the third column.
</details>

### Step 2: The command line

<details><summary>Hint 1</summary>

`regsvr32` registers and unregisters COM DLLs. `/s` means silent (no message box). `/u` means unregister. `/i:` passes a string to the DLL's `DllInstall` function. What does `scrobj.dll` do with that string?
</details>

<details><summary>Hint 2</summary>

`scrobj.dll` is the Windows Script Component runtime. Given a URL, it fetches a *scriptlet* (an XML file holding script code, often `.sct`) and runs the script inside it. The URL here is a raw paste.
</details>

### Step 3: Process tree

<details><summary>Hint 1</summary>

The top `cmd.exe` has no process-create event. Its PID and GUID are in `regsvr32.exe`'s `Parent…` fields. Neither `cmd.exe` has any arguments. What does a `cmd.exe` with no arguments usually mean?
</details>

### Step 4: Network connection

<details><summary>Hint 1</summary>

Compare the network event's `ProcessGuid` with each process-create event's `ProcessGuid`.
</details>

<details><summary>Hint 2</summary>

`DestinationHostname` is empty, and there's no DNS event. An IP address alone doesn't prove which website it was. Many sites share IPs behind content-delivery networks. What would you need to say "this connection was to pastebin.com"?
</details>

### Step 5: The clock

<details><summary>Hint 1</summary>

A process can't connect to anything before it exists. Sysmon collects network connections from a different source than process creation, and they can be stamped or delivered out of step. Look at the System `TimeCreated` of each event too.
</details>

<details><summary>Hint 2</summary>

When timestamps from different event types disagree by under a second, the `ProcessGuid` link is stronger evidence than the clock. Write the timeline in the order that is *possible*, and note the discrepancy rather than hiding it.
</details>

### Step 6: Who ran it

<details><summary>Hint 1</summary>

Session 1 is an interactive desktop session. A `cmd.exe` parent with no arguments, in the user's home directory, fits a person typing or pasting into a Command Prompt window.
</details>

### Step 7: Assess

<details><summary>Hint 1</summary>

Does a printer driver get "re-registered" from a paste site? And whose code made the second `cmd.exe`: Jo's, or the code at the URL?
</details>
