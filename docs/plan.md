# SENTINEL — Lean Plan

**Goal:** Get hands-on DFIR experience by working real investigations. Build tooling only when an investigation shows a real need for it.

**Rule of thumb:** About 80% of the time goes to investigating, writing up and building lab data. About 20% goes to code.

## How this repo is organized

```text
Sentinel/
├── app/                    the lab GUI (server, event catalog, web console)
├── content/
│   ├── campaign.json       chapters and ranks
│   ├── cases/NN-name/      brief, story, hints, data/, worksheet, report, private/ (answer key)
│   ├── tutorial/           the guided tutorial's practice case
│   ├── templates/          worksheet.md and report.md, copied into each case
│   └── archive/            retired cases
├── docs/
│   ├── plan.md             this file
│   ├── toolkit.md          command-line tool cheat sheet
│   └── notes/              your own concept notes (Sysmon IDs, ATT&CK, etc.)
├── tests/                  test suite (./sentinel test)
└── tools/                  case pipeline (./sentinel case …)
```

## Phase 0: Toolkit setup (one evening)

On macOS, install these:

- `brew install jq python@3.12`
- **Hayabusa** and **Chainsaw**: download the macOS ARM release binaries from GitHub. Both hunt and build timelines from EVTX files using Sigma rules.
- **DuckDB** (`brew install duckdb`): runs SQL directly on JSON or CSV files with no setup, which makes it a good scratch "database".
- A notes app or just VS Code Markdown.

**Done when:** you can run `hayabusa dfir-timeline` on a sample EVTX and open the output. *(Done 2026-10-16. See `docs/toolkit.md`.)*

## Phase 1: Learn to read the telemetry (about 1 week)

Write a short note of your own in `docs/notes/` for each topic:

- Sysmon Event IDs 1 (process create), 3 (network), 7 (image load), 11 (file create), 13 (registry set), 22 (DNS)
- `ProcessGuid` vs `ProcessId`, and why the GUID is the one to follow
- Parent/child chains: which ones are normal (`explorer.exe → chrome.exe`) and which aren't (`winword.exe → powershell.exe`)
- Windows Security 4624/4625/4688; logon types
- UTC and time zones, and how to work out when something happened from several sources
- MITRE ATT&CK: tactics vs techniques, and how to map observed behavior to a technique without overclaiming

**Done when:** you can read a raw Sysmon Event ID 1 record and explain every field that matters.

## Phase 2: Guided cases on public data (2–4 weeks)

Work 3 cases using real recorded attack data. For each one: write `brief.md`, investigate using `worksheet.md`, write `report.md`, *then* compare against the dataset's documentation or published write-ups (this is the "answer key").

Suggested sources:

1. **EVTX-ATTACK-SAMPLES** (sbousseaden): small, single-technique EVTX files. Start here.
2. **OTRF Security Datasets**: recorded ATT&CK simulations with documentation.
3. **Splunk `attack_data`** or **Boss of the SOC v1–v3**: larger, multi-stage cases with noise.

Investigate with jq, DuckDB, Hayabusa and Chainsaw. Each time something is painful, add a line to the "Tool wishlist" below.

**Done when:** three finished reports. Each one has a timeline, an execution chain backed by event references, scope, confidence, and what you *couldn't* conclude.

## Phase 3: Build a lab and generate your own data (1–2 weeks)

This is where most of the hands-on learning happens.

- **UTM** (free) + **Windows 11 ARM** VM. Install Sysmon (`Sysmon64a.exe` is the ARM64 build) with the SwiftOnSecurity or Olaf Hartong config.
- Take a VM snapshot before every run.
- Run **Atomic Red Team** tests one at a time. Before each run, predict which events it should create, then check what actually showed up.
- Build "The Archived Shortcut" yourself: a ZIP containing a `.lnk` that launches a *benign* PowerShell chain (writes a file, sets a Run key, makes a DNS lookup to a domain you control or a sinkhole). Use the VM normally for 30+ minutes around it so the logs contain realistic noise.
- Export the logs (EVTX → JSON via Hayabusa/Chainsaw or `Get-WinEvent | ConvertTo-Json`).

Safety: no real malware, keep the VM network isolated or host-only for anything beyond benign tests, and never run this on a work machine.

**Done when:** you have a dataset you created, plus an answer key written from what you *did*, checked against what the logs *show* (these won't fully match, and the gaps are worth studying).

## Phase 4: Turn your data into training cases (ongoing)

For each lab dataset, write `brief.md`, put the answers in `private/`, then work the case cold a week later (or give it to a friend).

Optional small tool: `tools/grade.py` compares your worksheet's answers (event refs, IOCs, affected hosts/users) with `private/answers.yaml` and prints what you got, what you missed, and what you claimed without evidence.

## Phase 5: Detection engineering (ongoing)

- Write a Sigma rule for each behavior you investigated.
- Test it with Chainsaw/Hayabusa against your attack dataset (true positive) **and** a clean, noise-only dataset (false positives).
- Record the assumptions and blind spots of each rule.

## Tooling: only build what the wishlist justifies

Likely candidates, all in plain Python and run from the CLI:

- `tools/load.py`: normalize Sysmon JSON → JSONL/DuckDB table with consistent UTC timestamps
- `tools/tree.py`: print a process tree from `ProcessGuid`/`ParentProcessGuid`, marking missing parents as `[unknown parent]`
- `tools/timeline.py`: merge bookmarked event IDs from a worksheet into a Markdown timeline

**Lab GUI (added 2026-10-16):** `./sentinel` (or double-click `Sentinel.command`) opens a local app in the browser for working cases: brief, step checklist, layered hints, event table with search and Event ID filters, process tree, raw event detail, bookmarks with notes, in-app worksheet/report editors, and a Submit button that unlocks the answer key. It uses only Python's standard library and plain JS, reads the case folders in `content/cases/`, and binds to localhost only. New features go in only when a case shows they're needed. Tool wishlist items can become GUI features.

**Case pipeline (added 2026-10-16):** `./sentinel case new|check|publish` turns raw logs into a playable chapter without code changes. Event labels live in `app/eventids.json`. See `docs/adding-cases.md`.

## Tool wishlist

_Add to this list during investigations: "I kept wishing I could…"_

-
