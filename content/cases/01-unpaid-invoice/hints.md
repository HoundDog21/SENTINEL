# Case 01: Hints

Read one hint at a time, and only after you've really tried that step.

---

### Step 1: Survey

<details><summary>Hint 1</summary>

`duckdb -c "select Event.System.Channel, Event.System.EventID, count(*) from read_json_auto('data/*.jsonl') group by all"`. For time ranges, use `min()` and `max()` of `Event.System.TimeCreated_attributes.SystemTime` per file.
</details>

<details><summary>Hint 2</summary>

Look at the Sysmon `EventRecordID` values in order. Are they consecutive? A missing number means the host logged an event that isn't in your export.
</details>

### Step 2: The alerting event

<details><summary>Hint 1</summary>

The `CommandLine` is what the parent *asked for*. The `Image` is the file that actually ran. On 64-bit Windows, what happens when a 32-bit program asks for something in `C:\Windows\System32`?
</details>

### Step 3: Process tree

<details><summary>Hint 1</summary>

```sh
jq -r 'select(.Event.System.EventID==1) | .Event.EventData | [.ParentProcessGuid, .ProcessGuid, .Image] | @tsv' data/case01-sysmon.jsonl
```
</details>

<details><summary>Hint 2</summary>

The top of the chain has no process-create event. But search for its `ProcessGuid`: it does appear in the data, doing something else.
</details>

### Step 4: The file

<details><summary>Hint 1</summary>

`CreationUtcTime` is the file's creation *timestamp* as recorded by the file system, which can be inherited, preserved or set by whoever wrote it. `UtcTime` is when Sysmon saw the write. A gap is worth noting, but don't overclaim why it exists.
</details>

### Step 5: Command lines

<details><summary>Hint 1</summary>

A `.cpl` file is a Control Panel item. What kind of file is it really, and what does Windows do when you double-click one?
</details>

<details><summary>Hint 2</summary>

There are two `rundll32.exe` processes, one in `System32` and one in `SysWOW64`. Look up what `shell32.dll,#44` does. Is the second one the attacker's choice, or Windows' own plumbing?
</details>

<details><summary>Hint 3</summary>

`/e:JScript.Encode` tells the script host which engine to use, whatever the file extension says. What does that mean for a file called `info.txt`?
</details>

### Step 6: Corroborate

<details><summary>Hint 1</summary>

Line up the second log's timestamps with the Sysmon timeline. One event lands within a fraction of a second of the chain. The others are days or minutes away. Read their `ExePath` before you decide what they are.
</details>
