# Toolkit cheat sheet

Installed 2026-10-16 on macOS (Apple Silicon).

| Tool | Version | Where | What it's for |
|---|---|---|---|
| jq | system | `/usr/bin/jq` | Slice and filter JSON events |
| DuckDB | 1.5.6 | Homebrew | SQL directly on JSON/CSV files |
| Python | 3.12 | Homebrew (`python3.12`) | Helper scripts in `tools/` |
| Hayabusa | 4.2.0 | `~/dfir-tools/hayabusa` (wrapper at `/opt/homebrew/bin/hayabusa`) | Sigma-based detection timeline from EVTX |
| Chainsaw | 2.17.1 | Homebrew; rules/mappings in `~/dfir-tools/chainsaw-repo` | Hunt EVTX with Sigma; dump EVTX → JSON |

Datasets: `~/dfir-data/` (kept outside this repo).

## Everyday commands

```sh
# 1. Convert EVTX → JSONL so you can read every raw event
chainsaw dump FILE.evtx --jsonl -o events.jsonl -q

# 2. What's in here? Count by Event ID
duckdb -c "select Event.System.EventID eid, count(*) n
           from read_json_auto('events.jsonl') group by 1 order by 2 desc"

# 3. Read one event in full (here: the first Sysmon Event ID 1)
jq -c 'select(.Event.System.EventID==1)' events.jsonl | head -1 | jq .

# 4. Process creations as a table, in time order
duckdb -c "select Event.System.TimeCreated_attributes.SystemTime t,
                  Event.EventData.ParentImage parent,
                  Event.EventData.Image image,
                  Event.EventData.CommandLine cmd
           from read_json_auto('events.jsonl')
           where Event.System.EventID = 1 order by t"

# 5. Detection timeline (Sigma rules)
hayabusa dfir-timeline -f FILE.evtx -o timeline.csv -w -C -q -U

# 6. Chainsaw hunt with Sigma
chainsaw hunt FILE.evtx -s ~/dfir-tools/hayabusa/rules/sigma \
  --mapping ~/dfir-tools/chainsaw-repo/mappings/sigma-event-logs-all.yml \
  -r ~/dfir-tools/chainsaw-repo/rules -q
```

## Habits

- Detection rules (Hayabusa/Chainsaw) are **leads, not conclusions**. Always confirm by reading the raw event (step 3).
- Record the `RecordID` (`Event.System.EventRecordID`) of every event you cite. That's your evidence ref.
- Timestamps in `SystemTime` / `UtcTime` are UTC.
- Update rules occasionally: `hayabusa update-rules`.
