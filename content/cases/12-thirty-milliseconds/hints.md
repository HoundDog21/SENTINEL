# Case 12: Hints

Read one hint at a time, and only after you've really tried that step.

---

### Step 1: Survey

<details><summary>Hint 1</summary>

`jq -c '.Event.System | {EventRecordID, EventID, t: .TimeCreated_attributes.SystemTime}' data/case12-security.jsonl`. Subtract the two times. The case title is a clue.
</details>

### Step 2: Who did it

<details><summary>Hint 1</summary>

RID 500 is the **built-in Administrator** account, the one created when Windows or the domain was installed. Look at `SubjectDomainName` to see which one this is.
</details>

<details><summary>Hint 2</summary>

Security events are written by the Local Security Authority (`lsass.exe`), whatever caused them. The `ProcessID` in the System section is the *logger*, not the actor. The actor is in the `Subject…` fields.
</details>

### Step 3: The task definition

<details><summary>Hint 1</summary>

```sh
jq -r '.Event.EventData.TaskContent' data/case12-security.jsonl | head -50
```
</details>

<details><summary>Hint 2</summary>

`S-1-5-18` is the LocalSystem account. Look up `<Hidden>` in the Task Scheduler schema. Then look at the year in `<StartBoundary>` and compare it with the date of the events.
</details>

### Step 4: Compare the two events

<details><summary>Hint 1</summary>

A daily trigger fires once a day. This task existed for a few hundredths of a second. Look at `<AllowStartOnDemand>`. A task can also be started immediately with an API call or `schtasks /run`.
</details>

### Step 5: The output

<details><summary>Hint 1</summary>

Unescape it: `&gt;` is `>` and `&amp;` is `&`. So the arguments are `/C tasklist > %windir%\Temp\CYAlyNSS.tmp 2>&1`. What does `2>&1` add?
</details>

<details><summary>Hint 2</summary>

Compare the file name with the task name. If you were running a command on a machine you couldn't see, how would you get its output back?
</details>

### Step 6: What's missing

<details><summary>Hint 1</summary>

Think about what Windows can log between "task registered" and "task deleted": the task starting, a process being created, a file being written, privileges being used. Which of those are in the Security log, and which need other logs (Task Scheduler Operational, Sysmon)?
</details>

### Step 7: Assess

<details><summary>Hint 1</summary>

Write two columns: "fits a patch tool" and "doesn't fit a patch tool". Put every field you noted in one of them. Then search the web for the exact `StartBoundary` value, and treat what you find as context, not proof.
</details>
