# Author notes: 16-a-clean-slate

Private to the case author. The app never shows this file. It lists mechanical facts about the data to help you write the brief, hints and answer key. It is **not** an analysis: decide yourself what matters.

Generated 2026-10-17T00:56:57Z by `tools/case.py survey`.

## Sources

| Case file | From | Format | Events | SHA-256 |
|---|---|---|---|---|
| `data/case16-security.jsonl` | kerberos_pwd_spray_4771.evtx | EVTX (chainsaw dump) | 12 | `4a0a1c7132e2…` |

## Counts

| Channel | Event ID | Label | Count |
|---|---|---|---|
| Security | 1102 | Audit log cleared | 1 |
| Security | 4768 | Kerberos TGT requested | 9 |
| Security | 4771 | Kerberos pre-auth failed | 2 |

- **Events:** 12
- **Hosts:** `01566s-win16-ir.threebeesco.com` (12)
- **Users:** `normal` (2), `a-jbrown` (1), `HD01` (1), `admin` (1), `svc-02` (1), `HD02` (1), `svc-01` (1), `bob` (1), `admin02` (1), `Administrator` (1), `backdoor` (1)

## Time and record IDs per channel

| Channel | First (UTC) | Last (UTC) | Record IDs | Missing |
|---|---|---|---|---|
| Security | 2020-07-22 20:29:27.321769 | 2020-07-22 20:29:36.437702 | 887106–887117 | none |

Record order vs time order: 0 place(s) where a later event has a lower record ID within its channel.
