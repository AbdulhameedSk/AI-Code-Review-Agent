# trace.py — observability

## Why it exists

When an agent does something weird, "the model decided to" is not a
debugging strategy. You need an audit trail: which tools were called, with
what inputs, what came back, how many tokens, what it cost, how long it
took. That's this file.

## What it stores

One SQLite table, `runs` — one row per agent run:

| Column | Meaning |
| ------ | ------- |
| `pr` | which PR (e.g. `owner/repo#123`) |
| `sha` | the head commit reviewed — the dedupe key |
| `status` | `done` / `no_review` |
| `findings` | how many findings it produced |
| `cost_usd` | what the run cost |
| `input_tokens` / `output_tokens` | token totals |
| `latency_s` | wall-clock seconds |
| `tool_log` | full JSON of every tool call + result |
| `created_at` | timestamp |

## The functions

- **`already_reviewed(sha)`** — idempotency check. `app.py` calls this
  before spending a cent; a SHA that already has a `done` row is skipped.
- **`log_run(...)`** — called by `review_agent.review_pr()` after every
  run. Returns the row id.
- **`recent_runs(limit)`** — powers `GET /traces`.

## Why SQLite

Zero-config, file-based, perfect for a single-service agent. The README
notes the upgrade path: on multi-instance deploys you swap the driver for
Postgres — the SQL stays the same.
