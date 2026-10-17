# Test fixtures

Tiny, harmless sample inputs for `tests/test_pipeline.py`, one per format `tools/case.py` accepts.

| File | Format | What it exercises |
|---|---|---|
| `chainsaw.jsonl` | chainsaw JSONL | Passthrough (two events from the tutorial data) |
| `otrf.json` | OTRF / nxlog flat JSON | No record IDs; `TimeCreated` in local time (UTC-16:00, like the real OTRF sample); envelope vs event-data fields |
| `winlogbeat.json` | Winlogbeat JSON array | `winlog.event_data`, `@timestamp` |
| `events.xml` | Windows event XML | Bare `<Event>` elements, `EventData` and `UserData` |
| `doctype.xml` | XML with an entity declaration | Must be refused |
| `unknown.json` | Not an event | Must be refused |

ZIP inputs are built at test time from these files.
