# Sentinel — how every file works

Plain-English docs for each source file. Read them in this order — each
builds on the last.

| Doc | File | What you'll understand after reading |
| --- | ---- | ------------------------------------ |
| 1. [The agent loop](core.md) | `core.py` | The engine every agent shares: LLM + while loop + tools, plus cost tracking |
| 2. [The reviewer](review_agent.md) | `review_agent.py` | How a PR diff becomes structured findings — diff chunking + forced JSON output |
| 3. [The GitHub client](github_client.md) | `github_client.py` | How we talk to GitHub safely: diffs, posting reviews, verifying webhooks |
| 4. [The webhook service](app.md) | `app.py` | How GitHub events trigger reviews — HMAC, dedupe, DRY_RUN, background work |
| 5. [The trace store](trace.md) | `trace.py` | Observability: logging every run's tools, tokens, cost to SQLite |
| 6. [Evals](evals.md) | `evals/` | How we measure whether the reviewer is actually good |
| 7. [Tests](tests.md) | `tests/` | The offline test suite |

## The one-paragraph mental model

GitHub sends a webhook when a PR opens → `app.py` verifies it's really
GitHub and hasn't been reviewed already → `review_agent.py` runs the agent
loop (`core.py`) where Claude pulls diff hunks via tools → Claude submits
findings as JSON through a forced tool call → `app.py` either posts the
review to GitHub or logs a draft → `trace.py` records everything.
