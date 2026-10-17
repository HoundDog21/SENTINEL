# Case 01: Hints

Read one hint at a time, and only after you've really tried that step.

---

### Step 1: Survey

<details><summary>Hint 1</summary>

`duckdb -c "select Event.System.EventID, count(*) from read_json_auto('data/case01.jsonl') group by 1"`. For the time range, use `min()` and `max()` of `Event.EventData.UtcTime`.
</details>

<details><summary>Hint 2</summary>

Look at the `EventRecordID` values in order. Are they consecutive? Gaps mean events exist on the host that aren't in your export.
</details>

### Step 3: Process tree

<details><summary>Hint 1</summary>

```sh
jq -r 'select(.Event.System.EventID==1) | .Event.EventData | [.ParentProcessGuid, .ProcessGuid, .Image] | @tsv' data/case01.jsonl
```
</details>

<details><summary>Hint 2</summary>

Several processes share the same parent. One process in the data has a parent from a *completely different* part of the tree. What kind of software is it, and is it part of the activity or a reaction to it?
</details>

### Step 4: Files

<details><summary>Hint 1</summary>

The `ProcessGuid` on an Event ID 11 tells you which process wrote the file. Match it against your tree.
</details>

<details><summary>Hint 2</summary>

`CreationUtcTime` is the file's creation *timestamp* as recorded by the file system, which can be inherited, preserved or set by the writer. `UtcTime` is when Sysmon saw the event. A big gap is worth noting, but don't overclaim why it exists.
</details>

### Step 5: Command lines

<details><summary>Hint 1</summary>

One utility is normally used to store credentials in Windows Credential Manager. Read its `/generic:` target name carefully. Which Windows feature does that name belong to?
</details>

<details><summary>Hint 2</summary>

Search for `Microsoft_Windows_Shell_ZipFolder`. What does Windows' built-in ZIP support do with a credential stored under that name?
</details>

### Step 6: The alert

<details><summary>Hint 1</summary>

Compare `Image` with `OriginalFileName` and `Description` for every process. Which one doesn't match?
</details>

### Step 7: Timeline

<details><summary>Hint 1</summary>

Sort by `UtcTime`, then by `EventRecordID`. One event swaps places. Records are numbered when they're *written* to the log, and that isn't always the moment the activity happened.
</details>
