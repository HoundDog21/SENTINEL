# Case 16: Answer key (SPOILERS)

> Don't open this until your `report.md` is finished.

**Source:** EVTX-ATTACK-SAMPLES (sbousseaden), `kerberos_pwd_spray_4771.evtx`. It was recorded in a lab domain (`threebeesco.com`) while running a Kerberos password spray, so there's no real victim. Treat it as real for the exercise.

## Survey

- **Security:** 12 events: 1 × 1102, 9 × 4768, 2 × 4771. Records **887106–887117**, consecutive, no gaps.
- Host `01566s-win16-ir.threebeesco.com`. It logs 4768/4771, so it's running the **KDC**: it's a **domain controller**.
- **20:29:27.321769**: the log clear (rec 887106).
- **20:29:36.414827 → 20:29:36.437702**: eleven Kerberos events in **about 23 milliseconds**, all from **172.16.66.1**.

## The log clear (rec 887106)

| Field | Value |
|---|---|
| `SubjectUserName` / `SubjectDomainName` | `a-jbrown` / `3B` |
| `SubjectUserSid` | `S-1-5-21-308926384-506822093-3341789130-1106` |
| `SubjectLogonId` | `0x3a17a` |

- **Observed:** `3B\a-jbrown` cleared the Security log at 20:29:27. Everything before that moment is gone from this log. Forwarded copies (SIEM) may still have it.
- **The clear is *before* the Kerberos activity**, so it did not hide it. If whoever cleared the log intended to cover something up, it was what came *before* 20:29:27, not the spray.
- 1102 records **no source IP or workstation**. Nothing in the export links logon `0x3a17a` to 172.16.66.1.
- **T1070.001** (Indicator Removal: Clear Windows Event Logs) *if* it was malicious. The data can't decide that. Callum's explanation (maintenance) is a claim that needs checking, not something the logs disprove.

## The Kerberos events

| Rec | Time (.s) | ID | Account | TargetSid | Status | Meaning | Src port |
|---|---|---|---|---|---|---|---|
| 887107 | 36.414827 | 4768 | `HD01` | `S-1-0-0` | `0x6` | no such account | 55961 |
| 887108 | 36.414856 | 4768 | `admin` | `S-1-0-0` | `0x6` | no such account | 55958 |
| 887109 | 36.414929 | 4768 | `svc-02` | `S-1-0-0` | `0x6` | no such account | 55963 |
| 887110 | 36.414967 | 4768 | `HD02` | `S-1-0-0` | `0x6` | no such account | 55962 |
| 887111 | 36.414984 | 4768 | `svc-01` | `S-1-0-0` | `0x6` | no such account | 55960 |
| 887112 | 36.415050 | 4768 | `bob` | `S-1-0-0` | `0x6` | no such account | 55957 |
| 887113 | 36.415371 | 4768 | `admin02` | `S-1-0-0` | `0x6` | no such account | 55966 |
| 887114 | 36.425365 | 4771 | `Administrator` | `…-500` | `0x18` | **exists, wrong password** | 55967 |
| 887115 | 36.425838 | 4771 | `backdoor` | `…-107103` | `0x18` | **exists, wrong password** | 55968 |
| 887116 | 36.434698 | 4768 | `normal` | `…-109603` | `0x0` | **exists, right password: TGT issued** (AES256, `0x12`) | 55969 |
| 887117 | 36.437702 | 4768 | `normal` | `…-109603` | `0x0` | TGT issued again | **52559**, from `::ffff:172.16.66.1` |

All requests use `TicketOptions 0x10`.

## What happened (interpretation)

1. **Password spraying.** One source tried **ten different account names, one attempt each, in about 23 ms**, with out-of-order source ports in a tight range (55957–55969). That's a tool sending requests in parallel, not a person. One try per account, likely with a single common password, is **password spraying**: it avoids account lockouts. **T1110.003** (Brute Force: Password Spraying).
2. **Account discovery as a side effect.** The KDC answers differently for accounts that don't exist (`0x6`, NULL SID) and accounts that do (`0x18` or success). From this alone the attacker learned that `HD01`, `admin`, `svc-01/02`, `HD02`, `bob` and `admin02` **don't exist**, and that `Administrator`, `backdoor` and `normal` **do**.
3. **`normal` is compromised.** The KDC issued a TGT for `normal` to 172.16.66.1 (rec 887116), so the password guessed was correct. **T1078.002** (Valid Accounts: Domain Accounts). The second TGT 3 ms later (rec 887117) uses the IPv6-mapped form `::ffff:172.16.66.1` and a source port from a **different range** (52559). That suggests a second request made a different way, perhaps the credential being used straight away by another tool or library. It's the same address, but the logs don't say what the second client was.
4. **`TicketOptions 0x10`.** Ordinary Windows clients ask for `0x40810010`. A bare `0x10` fits a tool building Kerberos requests itself. That's supporting context, not proof.
5. **An account called `backdoor`** exists (RID 107103, rec 887115). The name alone is reason to review it now: who created it, when, which groups it's in. The export can't say whether it's malicious or a badly named test account, and nothing here shows when it was created. The attacker had it on their list, but so did the wordlist that included `bob` and `admin`.
6. **Port gaps (observation):** source ports 55959, 55964 and 55965 fall inside the range but have no event here. They might be connections that weren't Kerberos requests, requests to another DC, or nothing. Note them without explaining them.
7. **One actor or two?** The 1102 (account `a-jbrown`, logon `0x3a17a`) and the spray (IP 172.16.66.1) share **no field**. They're 9 seconds apart on the same DC, which is suspicious timing, but **not a link**. You'd need the 4624 for logon `0x3a17a` (its source IP) to connect them. Keep them as two findings: one **confirmed malicious** (the spray and the compromised `normal` account), one **unexplained and needing verification** (the log clear).

## Timeline (UTC, 2020-07-22)

| Time | Rec | Event |
|---|---|---|
| 20:29:27.321769 | 887106 | `3B\a-jbrown` (logon `0x3a17a`) clears the Security log |
| 20:29:36.414827–.415371 | 887107–887113 | 7 unknown account names from 172.16.66.1 (`0x6`) |
| 20:29:36.425365–.425838 | 887114–887115 | `Administrator`, `backdoor`: wrong password (`0x18`) |
| 20:29:36.434698 | 887116 | `normal`: TGT issued |
| 20:29:36.437702 | 887117 | `normal`: TGT issued again (`::ffff:` form, port 52559) |

## Verdict

**True positive, high confidence: a password spray from 172.16.66.1 succeeded against the domain account `normal`.** The log clear is a **separate, unresolved finding**. It may be the maintenance Callum describes, but clearing a DC's Security log nine seconds before an attack can't be closed on a verbal explanation. Escalate both, and prioritise `normal`.

## IOCs

- Source IP `172.16.66.1` (internal: identify the machine)
- Compromised account `THREEBEESCO\normal` (SID `…-109603`)
- Account to review: `backdoor` (SID `…-107103`)
- Account to verify: `3B\a-jbrown` (SID `…-1106`), logon `0x3a17a`
- Pattern: many 4768 `0x6`/4771 `0x18` from one IP within seconds, and TGT requests with `TicketOptions 0x10`

## What you can't conclude from this data

- Which machine or person is behind 172.16.66.1, and how they got onto the network
- What password was sprayed, and whether other DCs saw more attempts
- What `normal` was used for after getting a TGT (no 4769 service tickets or 4624 logons in the export)
- Why `a-jbrown` cleared the log, from where, and what was in it
- Who created `backdoor`, and when
- What, if anything, the port gaps represent

## Good next steps (for your recommendations)

- **Contain now:** reset `normal`'s password and revoke its sessions. Find and isolate the machine at 172.16.66.1 (DHCP, switch or EDR data).
- **Investigate `normal`:** pull 4769 (service tickets) and 4624 (logons) for `normal` after 20:29:36 on every DC. That shows what the attacker reached with it.
- **Verify the clear:** ask Jamie directly when and from where he cleared it, and check the 4624 for logon `0x3a17a`. Recover the pre-clear events from the SIEM if it was forwarding them.
- **Review `backdoor`:** creation time (4720 in the SIEM, or `whenCreated` in AD), group memberships, last logon. Disable it if nobody can account for it.
- **Harden:** enforce a strong password policy and lockout thresholds, alert on bursts of 4768 `0x6` and 4771 `0x18` from one source, and alert on every 1102.

*Score yourself with the rubric panel above the answer key in SENTINEL.*
