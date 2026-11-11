# evals/ — is the reviewer actually good?

## Why it exists

You cannot improve an agent you can't measure. Change the prompt, swap the
model, tweak a tool description — did it get better or worse? Without
evals you're guessing. This folder is the measuring stick.

## fixtures.py — ground truth

Three diffs with KNOWN answers:

- **`sql_injection`** — an f-string SQL query. A real reviewer must flag it.
- **`hardcoded_secret`** — API key + DB password in source. Must flag.
- **`clean_code`** — two fine utility functions. Must flag NOTHING
  (tests precision: an agent that invents issues fails here).

Each fixture declares `expect`: keywords a correct finding should mention,
and min/max finding counts.

## run_evals.py — the harness

For each fixture: run the real `review_pr()` → `score()` checks whether
the findings' explanations mention expected keywords and the count is in
range → prints pass/fail + cost per fixture + a final "X/3 passed."

## How to use it

```bash
python -m evals.run_evals
```

Run it after every prompt or model change. It's the agent equivalent of a
test suite — it doesn't prove the agent is good, but it catches regressions
you'd never notice by eyeballing one review.

## Honest limitation

Keyword matching is crude — a correct finding phrased differently could
miss. The README notes the upgrade: swap `score()` for LLM-as-judge (a
second model grades the findings). Start simple, upgrade when the simple
version lies to you.
