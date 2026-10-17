# Case 16: Hints

Read one hint at a time, and only after you've really tried that step.

---

### Step 1: Survey

<details><summary>Hint 1</summary>

The **Key Distribution Center** (KDC) logs 4768 and 4771, and it runs on domain controllers. So whatever this server's name suggests, it's acting as a DC.
</details>

### Step 2: The log clear

<details><summary>Hint 1</summary>

1102 keeps its details under `UserData.LogFileCleared`, not `EventData`:
```sh
jq '.Event.UserData' data/case16-security.jsonl | head
```
</details>

<details><summary>Hint 2</summary>

Clearing removes everything *before* the clear. Anything logged *after* it is still there. Which side of the 1102 is the rest of this export on?
</details>

### Step 3: Tabulate

<details><summary>Hint 1</summary>

```sh
jq -r 'select(.Event.System.EventID!=1102) | [.Event.System.EventRecordID, .Event.System.EventID, .Event.System.TimeCreated_attributes.SystemTime, .Event.EventData.TargetUserName, .Event.EventData.TargetSid, .Event.EventData.Status, .Event.EventData.IpAddress, .Event.EventData.IpPort] | @tsv' data/case16-security.jsonl
```
</details>

### Step 4: Decode

<details><summary>Hint 1</summary>

`0x6` = KDC_ERR_C_PRINCIPAL_UNKNOWN. `0x18` = KDC_ERR_PREAUTH_FAILED. `0x0` = success. `S-1-0-0` is the NULL SID, which the KDC uses when it can't find the account.
</details>

<details><summary>Hint 2</summary>

Group 1: "no such account". Group 2: "account exists, wrong password". Group 3: "account exists, right password". If you were an attacker, which group would you care about most?
</details>

### Step 5: Pattern

<details><summary>Hint 1</summary>

Count the attempts per account, and work out the time from first to last. One try per account across many accounts is a different attack from many tries against one account. Look up both.
</details>

<details><summary>Hint 2</summary>

Windows clients normally ask for a TGT with `TicketOptions 0x40810010` (forwardable, renewable, canonicalize, renewable-ok). These ask for `0x10`. That fits a tool talking to Kerberos directly, but it's a lead, not proof.
</details>

### Step 6: Successes

<details><summary>Hint 1</summary>

Look at how `IpAddress` is written in the last event, and at its source port compared with all the others.
</details>

### Step 7: Names

<details><summary>Hint 1</summary>

Read the `TargetUserName` of every event in group 2 out loud. Does one sound like something an admin would create on purpose? Its `TargetSid` tells you it exists. Does anything tell you when it was created?
</details>

### Step 8: One actor or two?

<details><summary>Hint 1</summary>

1102 records the account and logon session. 4768/4771 record a source IP. Is there any field the two kinds of event share? What would you need (for example a 4624 for logon `0x3a17a`) to connect them?
</details>
