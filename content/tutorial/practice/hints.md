# Tutorial: Hints

In real cases every hint you open costs points. Practice hints are free, so open them to see how it works.

---

### Step 1: Survey

<details><summary>Hint 1</summary>

The Event ID chips above the events table count each type for you. Click one to show only that type.
</details>

### Step 3: Process tree

<details><summary>Hint 1</summary>

Open the process-create event (Event ID 1) for the process you care about. Its `ParentProcessGuid` is the `ProcessGuid` of whatever started it. Search for that value.
</details>

<details><summary>Hint 2</summary>

If a parent's `ProcessGuid` never shows up as its own Event ID 1, it isn't in your evidence. Add it as a not-in-evidence node instead of leaving it out.
</details>
