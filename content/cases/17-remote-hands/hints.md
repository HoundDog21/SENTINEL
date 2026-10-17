# Case 17: Hints

Read one hint at a time, and only after you've really tried that step.

---

### Step 1: Survey

<details><summary>Hint 1</summary>

```sh
jq -r '[.Event.System.EventRecordID, .Event.System.EventID, .Event.EventData.UtcTime, .Event.EventData.Image, .Event.EventData.User] | @tsv' data/case17-sysmon.jsonl
```
</details>

### Step 2: Process tree

<details><summary>Hint 1</summary>

`WmiPrvSE.exe` is the **WMI Provider Host**. It runs WMI work on behalf of callers, local or remote. `-Embedding` means COM started it to serve a request. When a WMI caller uses the `Win32_Process.Create` method, the new process becomes a child of `WmiPrvSE.exe`.
</details>

<details><summary>Hint 2</summary>

All three `cmd.exe` have the same `ParentProcessGuid`. The `whoami.exe` has a different parent.
</details>

### Step 3: Command lines

<details><summary>Hint 1</summary>

`/Q` turns echo off and `/c` runs one command and exits. `1> file 2>&1` sends normal output and errors to the file. `ADMIN$` is a hidden admin share that maps to `C:\Windows`.
</details>

<details><summary>Hint 2</summary>

A process started through WMI has no console you can read remotely. So how would a remote caller see the output? Something that can read `\\IEWIN7\ADMIN$` from elsewhere can collect it.
</details>

### Step 4: Operator or tool?

<details><summary>Hint 1</summary>

A remote "shell" needs to know the current directory to show a prompt. Which commands would a tool run first, automatically, to find that out?
</details>

### Step 5: Network events

<details><summary>Hint 1</summary>

For an *inbound* connection (`Initiated: false`), Sysmon puts this host's address and listening port in `Source…` and the remote party in `Destination…`. Don't let the field names fool you.
</details>

<details><summary>Hint 2</summary>

Port 445 is SMB, used for file shares. Records 9830 and 9831 are two halves of one loopback connection. Check whether its `UtcTime` can really be before the first process it would serve.
</details>

### Step 6: The number

<details><summary>Hint 1</summary>

Ten digits starting with 15… is a Unix epoch time: seconds since 1970-01-01 UTC. Try `date -u -r 1556656369` on a Mac, or `date -u -d @1556656369` on Linux.
</details>

### Step 7: Whose hands

<details><summary>Hint 1</summary>

Session 0 with High integrity and a fresh `LogonId` isn't someone at the desktop. Creating processes over remote WMI needs administrator rights on the target. Whose credentials does that mean someone has?
</details>

### Step 8: Assess

<details><summary>Hint 1</summary>

An inventory tool *reads* WMI classes (hardware, software). Does it need to start `cmd.exe`, write output into `C:\Windows` and ask `whoami /all`?
</details>
