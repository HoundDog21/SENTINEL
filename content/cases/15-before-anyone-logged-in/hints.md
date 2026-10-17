# Case 15: Hints

Read one hint at a time, and only after you've really tried that step.

---

### Step 1: Survey

<details><summary>Hint 1</summary>

`DC1` in a domain called `insecurebank.local` is a strong hint that this is a **domain controller**: the server that holds every account in the domain. One event has no `User`. Which Event ID is it?
</details>

### Step 2: Process tree

<details><summary>Hint 1</summary>

```sh
jq -r '.Event.EventData | [.ProcessGuid, .ParentProcessGuid, .Image] | @tsv' data/case15-sysmon.jsonl
```
One `ProcessGuid` doesn't appear as anyone's parent or child.
</details>

### Step 3: Is it what it says it is?

<details><summary>Hint 1</summary>

`osk.exe` is the **On-Screen Keyboard**. What does its `Description` field say instead? Which real Windows program has that description?
</details>

<details><summary>Hint 2</summary>

A keyboard program doesn't start command-line tools. A command prompt does, when someone types into it.
</details>

### Step 4: The parent

<details><summary>Hint 1</summary>

`Utilman.exe` is the **Ease of Access** manager, the accessibility button on the Windows logon screen. Windows (winlogon) starts it as `utilman.exe /debug` when someone clicks that button or presses Win+U. From there you can pick the On-Screen Keyboard.
</details>

### Step 5: Who and where

<details><summary>Hint 1</summary>

LogonId `0x3e7` is the **SYSTEM** account's logon session. Accessibility tools on the logon screen run as SYSTEM because no user has logged on yet. Who needs a password to click a button on a logon screen?
</details>

<details><summary>Hint 2</summary>

`TerminalSessionId` is 2. Look up what session 0 and session 1 usually are on a server, and what creates further sessions.
</details>

### Step 6: The registry event

<details><summary>Hint 1</summary>

`LogonUI.exe` draws the logon screen. Sysmon reports `CreateKey` when a program creates *or opens* a key with create rights, which Windows components do routinely.
</details>

<details><summary>Hint 2</summary>

`RuleName` comes from the Sysmon *configuration file*: someone tagged the rule that matched. It tells you why the event was kept, not what happened.
</details>

### Step 7: How and when

<details><summary>Hint 1</summary>

With an IFEO `Debugger` value, Windows starts the *debugger* program instead, so Sysmon's `Image` would be the debugger (for example `cmd.exe`) with `osk.exe` in its command line. With a replaced file, `Image` stays `osk.exe` but the file's metadata belongs to something else. Which do you have?
</details>

<details><summary>Hint 2</summary>

Is there any file-create or registry-set event that shows the swap happening? If not, what does that say about when it was planted?
</details>
