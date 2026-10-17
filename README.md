# SENTINEL

Hands-on DFIR labs. Investigate real recorded attack telemetry, write an incident report, then check it against an answer key.

You play **Cody**, a new night-shift analyst at **Ironlantern Security**, a fictional managed detection and response company. Each case is a chapter in a story campaign. The app shows you the evidence and stores your work. You do the investigating.

## Quick start

```sh
./sentinel
```

Or double-click **Sentinel.command** in Finder. It opens http://127.0.0.1:8765 in your browser. Stop it with Ctrl+C.

New to the console? Press **Tutorial** on the HQ screen for a guided tour on harmless practice data.

Requires `python3.12` (Homebrew). Optional: `chainsaw`, for converting `.evtx` files.

## Commands

```sh
./sentinel                     # start the app
./sentinel case new|check|publish|list …    # build and publish cases
./sentinel test                # run the test suite (--fast skips the browser tests)
```

## What's where

```text
Sentinel/
├── sentinel, Sentinel.command   launchers
├── app/                         the program
│   ├── server.py                local web server and JSON API (standard library only)
│   ├── eventids.json            event labels and field types: edit this to support a new log source
│   └── static/                  the web console (HTML, JS, CSS)
├── content/                     everything authored: no code
│   ├── campaign.json            chapters, ranks and XP thresholds
│   ├── cases/                   one folder per case
│   ├── tutorial/practice/       the tutorial's practice case
│   ├── templates/               blank worksheet and report
│   └── archive/                 retired cases
├── docs/                        guides, the learning plan and your notes
├── tests/                       test suite
└── tools/                       case pipeline and git hook
```

## Docs

| Guide | What's in it |
|---|---|
| [Playing SENTINEL](docs/playing.md) | The campaign, the tutorial, working a case, customizing the console |
| [Adding a case](docs/adding-cases.md) | The case pipeline, accepted log formats, and what's in a case folder |
| [Tests](tests/README.md) | What the test suite checks, and how new cases are covered automatically |
| [Learning plan](docs/plan.md) | The roadmap: phases, datasets and the tool wishlist |
| [Toolkit](docs/toolkit.md) | Command-line tools: chainsaw, Hayabusa, DuckDB, jq |
| [Your notes](docs/notes/) | Your own concept notes |
