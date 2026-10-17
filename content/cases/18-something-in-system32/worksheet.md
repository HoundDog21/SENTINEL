# Worksheet: <case name>

**Analyst:**  **Started (UTC):**  **Data sources:**

## 1. Brief: what was I told?

-

## 2. Data overview

- Time range covered (UTC):
- Hosts:
- Users:
- Event types / counts:
- Known gaps (missing sources, time ranges, fields):

## 3. Evidence log

Record each item **as you find it**. "Ref" = something that locates the raw event (file + EventRecordID, or line number).

| # | Time (UTC) | Host | Ref | Observation (fact only) | Why it matters |
|---|---|---|---|---|---|
| 1 | | | | | |

## 4. Process chain

Use ProcessGuid. Write `[unknown]` if a parent isn't in the data. Don't guess.

```text
[unknown parent]
└── explorer.exe (guid …)  — ref
    └── …
```

## 5. Hypotheses

| Hypothesis | Supporting evidence (#) | Contradicting evidence (#) | Confidence (Low/Med/High) | What would confirm/refute it? |
|---|---|---|---|---|
| | | | | |

## 6. Questions

- **Initial access:** how did it start?
- **Execution:** what ran, and what launched it?
- **Persistence:** anything set up to survive a reboot?
- **Command & control / exfil:** outbound network or DNS activity?
- **Scope:** which hosts, accounts, files and indicators are *demonstrably* affected?
- **ATT&CK mapping** (only for behavior you observed):
- **Verdict:** true positive / benign / undetermined, and why:

## 7. Unknowns and limits

What can't these logs tell me?

-

## 8. Lessons

What did I learn, what slowed me down, and what should go on the tool wishlist?

-
