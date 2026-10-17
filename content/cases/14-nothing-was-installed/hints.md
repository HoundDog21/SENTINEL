# Case 14: Hints

Read one hint at a time, and only after you've really tried that step.

---

### Step 1: Survey

<details><summary>Hint 1</summary>

```sh
jq -r '[.Event.System.EventRecordID, .Event.System.EventID, .Event.EventData.UtcTime, .Event.EventData.Image] | @tsv' data/case14-sysmon.jsonl
```
Count from the first record ID to the last. How many should there be?
</details>

### Step 2: Process tree

<details><summary>Hint 1</summary>

The outer `cmd.exe` has no arguments, which looks like an open Command Prompt window. The inner one is `cmd /c …`, which runs one command and exits. What does that pattern suggest about how the command was entered?
</details>

### Step 3: The tool

<details><summary>Hint 1</summary>

`desktopimgdownldr.exe` is part of Windows' **Personalization** features. Its real job is fetching lock-screen and desktop images for managed devices. Check its `Company` and `OriginalFileName`, then search LOLBAS for its name.
</details>

<details><summary>Hint 2</summary>

Look at the end of the URL. Lock-screen images are usually `.jpg` or `.png`. What's this one? And what kind of site is `a.uguu.se`? Answer from public information, and label it as outside knowledge in your report.
</details>

### Step 4: The file event

<details><summary>Hint 1</summary>

`svchost.exe` hosts Windows services. Which Windows service downloads files in the background for other programs, and keeps going even when they exit?
</details>

<details><summary>Hint 2</summary>

`CreationUtcTime` equals `UtcTime` here. Compare that with a case where they differ. What does it say about whether this is a brand-new file?
</details>

### Step 5: Linking file and command

<details><summary>Hint 1</summary>

Make two lists. Observed: path, extension, timing, user folder. Not observed: a network connection, the download job, the file's contents or hash. Which of these does a report need before it can say "this file *is* the one from that URL"?
</details>

### Step 6: Gaps

<details><summary>Hint 1</summary>

One missing record falls between the two process creations, the other between the second process creation and the file write. Does this export have any Event ID 3 at all?
</details>

### Step 7: The client's claim

<details><summary>Hint 1</summary>

Where did the file land, in a system folder or the user's own profile? Does downloading a file need admin rights? Does *running* one? Think about what an attacker needs next.
</details>

### Step 8: Assess

<details><summary>Hint 1</summary>

A `.7z` file doesn't run by itself. Is there any event showing it being opened or extracted? Keep "downloaded" and "executed" separate in your verdict.
</details>
