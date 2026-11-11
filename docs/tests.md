# tests/ — the offline test suite

## Why it exists

Production code ships with tests. These three tests cover the pure logic —
no API calls, no keys needed. `pytest tests/` runs them in seconds.

## What's covered

- **`test_split_diff_multiple_files`** — feeds a two-file unified diff to
  `split_diff()` and asserts it splits into the right `{filename: hunk}`
  map. This is the function the whole context-management strategy depends
  on; if it breaks, the agent sees garbage.
- **`test_verify_signature`** — computes a real HMAC signature and checks
  `verify_signature()` accepts it, rejects a forged signature, and rejects
  a missing one. Webhook security is the kind of thing you really don't
  want to discover is broken in production.
- **`test_cost_stats`** — verifies the `RunStats` cost math: 1M input
  tokens + 100k output tokens at Sonnet pricing = $4.50. If someone
  changes the pricing constants, this test says so.

## What's deliberately not tested

Anything calling the Anthropic or GitHub APIs — those need keys and network
and belong in evals/integration tests, not unit tests. The eval harness
(`evals/run_evals.py`) is the behavioral test for the agent itself.
