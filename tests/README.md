# SENTINEL tests

```sh
./sentinel test                     # everything, about a minute
./sentinel test --fast              # no browser tests, about a second
./sentinel test --case 02-echoes    # just one case (what `case publish` runs, with --strict)
./sentinel test --install-hook      # run the fast tests before every git commit
```

Every test runs on a **throwaway copy of the project** with its own server on a free port. Your real cases, progress, XP and layout are never touched.

## New cases are covered automatically

You don't write tests for a new case. Every folder in `content/cases/`, plus the tutorial, goes through all of these:

| Test | What it catches |
|---|---|
| `case check` is clean | Missing files, leftover TODOs, broken rubric/debrief JSON, events that won't load, Event IDs with no label in `app/eventids.json` |
| Data loads | Unreadable lines, events with no timestamp, duplicate keys |
| Answer key cites real records | `rec 4961` when the data has no such record (a gap the key calls missing is fine) |
| `file:line` references exist | Citations of a file or line that isn't in `data/` |
| Brief lists every data file | A `data/*.jsonl` the learner is never told about |
| Brief hashes match | A wrong `SHA-256 \`…\`` in the Evidence table |
| Brief's **Data:** field matches | Event IDs named that aren't in the data, or (when published) Event IDs in the data that aren't named |
| Hints fit the playbook | `### Step 12` when there are 9 steps, unbalanced `<details>`, a hint with no `<summary>` |
| Rubric and debrief fit | Points not totalling 100 (when published), a grade with no debrief text, duplicate items |
| API playthrough | Answer key, rubric or debrief served before submit; `submitted` forced through a state update; wrong score or grade; the debrief text not matching the grade; reset not hiding the key again |
| Browser playthrough | The case doesn't open, the briefing doesn't show, an event won't render (or shows `null`/`undefined`), evidence/tree/IOC/war room/hints/playbook don't work, the tree picks a parent on its own, the report doesn't save or `+ Evidence` inserts nothing, submit and scoring fail, any JavaScript error |

**Drafts:** a case that isn't in the campaign yet may still have TODOs, but everything else must already pass. `./sentinel case publish` runs `./sentinel test --case <id> --strict`, which holds the case to the full standard, and refuses to publish if anything fails.

## The rest of the suite

| File | Covers |
|---|---|
| `test_cases.py` | The per-case tests above, plus campaign structure (chapters numbered 1…N, no case twice, playable chapters first) and ranks |
| `test_pipeline.py` | Every input format `tools/case.py` accepts, using the samples in `fixtures/`; the local-time-to-UTC fix; refusals (unknown JSON, XML entities, unsupported files); ZIPs read safely; `new → check → publish` with every guard; `add-data` and `survey` |
| `test_server.py` | Static files and path traversal; the event catalog; cross-origin writes refused; only `worksheet.md`/`report.md` writable; chapter locking and XP; the tutorial never touching real cases, XP or its own template |
| `browser/test_play_cases.py` | The browser playthrough for every case, and the HQ screen |
| `browser/test_tutorial.py` | The guided tour end to end, around 90 checks: every step and practice task, Back/Skip/resume/replay, and your prefs, XP and case files left alone |

Set `SENTINEL_SHOTS=/some/folder` to save screenshots from the tutorial test.

## Browser tests need Playwright

They live in the project's `.venv`, which is gitignored. `./sentinel test` uses it automatically. To set it up again:

```sh
python3.12 -m venv .venv && .venv/bin/pip install playwright==1.64.0 && .venv/bin/playwright install chromium-headless-shell
```

Without it, browser tests are skipped, not failed.
