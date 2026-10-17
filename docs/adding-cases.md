# Adding a case

Cases are data, not code. The pipeline in `tools/case.py` builds one from raw logs:

```sh
./sentinel case new 02-echoes-in-the-scheduler --title "Echoes in the Scheduler" \
    --severity High --difficulty "Beginner+" --data ~/dfir-data/sample.evtx ~/dfir-data/otrf.zip
./sentinel case check 02-echoes-in-the-scheduler      # lists every TODO and problem
./sentinel case publish 02-echoes-in-the-scheduler --chapter 2
./sentinel case publish 12-thirty-milliseconds --library --teaser "A housing charity's SIEM caught…"   # or a standalone case
./sentinel case list                                  # all cases and their status
```

1. **`new`** converts each input into the JSONL format the app reads. Accepted inputs: `.evtx` (via chainsaw), chainsaw JSONL, OTRF Security-Datasets or nxlog flat JSON, Winlogbeat JSON, Windows event XML, or a `.zip` of any of these. It checks that every event loads, keeps the originals, and writes skeleton files full of `TODO`s. It also writes `private/author-notes.md`, a private list of data facts for the author: counts, time ranges, record-ID gaps, and a process-create table. The app never shows that file.
2. **Write the case:** fill in every `TODO` in `brief.md` (its `## Guided steps` list becomes the Playbook), `story.md`, `hints.md` (one `<details>` block per hint), `private/answer-key.md`, `private/rubric.json` and `private/debrief.json`.
3. **`check`** lists anything missing or broken: leftover `TODO`s, a rubric that doesn't total 100, debrief grades with no text, events that won't load, and Event IDs with no label.
4. **`publish`** refuses until `check` is clean. Then it either:
   - points a chapter in `content/campaign.json` at the case (`--chapter N`). Pass `--title`, `--teaser` and `--difficulty` to add a new chapter, and `--replace` to swap the case an existing chapter plays; or
   - adds it to the **Case library** in `content/library.json` (`--library --teaser "…"`): standalone cases, never locked, that earn XP like chapters. The teaser is one or two sentences on the situation. It must not name the technique, and `publish` refuses one that names a file such as an `.exe` or `.dll`.

   A case is a chapter or a library case, never both.

`new` names the converted files after the case and the log (`case12-security.jsonl`), not after the input file, because public dataset names often give the technique away. The original name is kept in `private/case.json`. Pass `--keep-names` to keep the input names instead.

`add-data` adds more files to a case, and `survey` regenerates the author notes.

**Tests.** `./sentinel test` runs the whole suite. Every case is tested automatically, so a new case needs no test code of its own. `publish` runs the case's tests and refuses on any failure. See [tests/README.md](../tests/README.md).

**New log sources need no code.** Event labels, which fields count as which IOC type, and which fields fill the table columns all live in `app/eventids.json`. If `check` reports a missing label, add it there.

**Datasets without record IDs**, like OTRF, are cited by `file:line`, and the app shows that wherever it would show a record number. Flat JSON that stamps `TimeCreated` in local time is converted to UTC. The offset is learned from Sysmon `UtcTime` fields, or you can set it with `--tz-offset`.

## What's in a case folder

```text
content/cases/NN-name/
├── brief.md              the alert, evidence table and "## Guided steps" (becomes the Playbook)
├── story.md              Priya's briefing message (story only: it never adds evidence)
├── hints.md              one <details> block per hint, under "### Step N" headings
├── worksheet.md          the learner's notes (starts as a copy of content/templates/worksheet.md)
├── report.md             the learner's report (starts as a copy of content/templates/report.md)
├── data/
│   ├── *.jsonl           events, one per line, in the format the app reads
│   ├── *.evtx            original logs (gitignored)
│   └── source/           other original inputs kept by the pipeline (gitignored)
└── private/              locked until the report is submitted
    ├── answer-key.md
    ├── rubric.json       {"hint_penalty", "grades", "items": [{"points", "text"}]}
    ├── debrief.json      {"common", "by_grade": {"S": …}, "next"}
    ├── author-notes.md   data facts for the author (never shown in the app)
    └── case.json         where each data file came from
```

While someone plays, the app also writes `state.json`, `activity.json`, `bookmarks.json`, `iocs.json` and `tree.json` here.

Retired cases go in `content/archive/`, where the app doesn't load them.
