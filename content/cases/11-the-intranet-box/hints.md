# Case 11: Hints

Read one hint at a time, and only after you've really tried that step.

---

### Step 1: Survey

<details><summary>Hint 1</summary>

`jq -c '.Event.System | {EventRecordID, EventID, Computer}' data/case11-sysmon.jsonl` lists the records. Then compare the first and last `UtcTime`. How long is the whole export, in milliseconds?
</details>

<details><summary>Hint 2</summary>

One event has no `User` field at all. Look at which Event ID it is before you count users.
</details>

### Step 2: The parent

<details><summary>Hint 1</summary>

`w3wp.exe` is the IIS worker process. Each IIS *application pool* gets its own worker, and `-ap "…"` in its command line names the pool. Compare that name with the `User` on the child process.
</details>

<details><summary>Hint 2</summary>

`-v "v2.0"` and `webengine4.dll` tell you this pool runs ASP.NET code. Ask yourself: when would a web page ever need to start `cmd.exe`?
</details>

### Step 3: Process tree

<details><summary>Hint 1</summary>

```sh
jq -r 'select(.Event.System.EventID==1) | .Event.EventData | [.ParentProcessGuid, .ProcessGuid, .Image] | @tsv' data/case11-sysmon.jsonl
```
</details>

<details><summary>Hint 2</summary>

The top of the chain has no process-create event. Search for its `ProcessGuid`. It shows up in another event as the *source* of something.
</details>

### Step 4: Command lines

<details><summary>Hint 1</summary>

`cmd /c` runs one command and exits. What does `net user` print when you run it with no other arguments?
</details>

<details><summary>Hint 2</summary>

On older Windows, `net.exe` hands many subcommands to `net1.exe`. Look at the parent of `net1.exe` and at how close together the two start.
</details>

### Step 5: Process access

<details><summary>Hint 1</summary>

Compare the `UtcTime` of the process-access event with the `UtcTime` of the first process-create event. Then compare its `TargetProcessGUID` with that process's `ProcessGuid`.
</details>

<details><summary>Hint 2</summary>

When a program calls `CreateProcess`, Windows hands it a handle to the new process with full rights. `0x1fffff` is `PROCESS_ALL_ACCESS`. Is that suspicious for a parent and its brand-new child?
</details>

<details><summary>Hint 3</summary>

In a .NET program, code that was compiled on the fly (JIT) doesn't belong to any DLL on disk, so it shows up as `UNKNOWN(…)` in a call trace. Look at the named modules around those frames: `mscorwks.dll`, `System.ni.dll`, `System.Web.ni.dll`.
</details>

### Step 6: Context

<details><summary>Hint 1</summary>

`TerminalSessionId` 0 is the services session. Compare the `LogonId` across all three processes. Would a person typing at the server's keyboard look like this?
</details>

<details><summary>Hint 2</summary>

Speed alone doesn't tell you whether a human or a script sent the command. A person typing into a web form gets the same `cmd /c` wrapper and the same few milliseconds. What would you need to see to tell the two apart?
</details>

### Step 7: Assess

<details><summary>Hint 1</summary>

Two common ways web-server code ends up running a command: a file the attacker planted in the site (a web shell), or a bug in the real application that passes input to the shell (command injection). Which of those does the data actually let you tell apart?
</details>
