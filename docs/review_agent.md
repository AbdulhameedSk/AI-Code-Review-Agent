# review_agent.py — turning a diff into structured findings

## Why it exists

This is the actual reviewer. Two design decisions make it
production-shaped rather than toy-shaped:

### 1. The diff never goes in the prompt

A PR diff can be thousands of lines. Dumping it into the task wastes tokens
and dilutes the model's attention. Instead:

- `split_diff()` regex-splits the unified diff on `diff --git` boundaries
  into `{filename: hunk_text}` — kept in a plain Python dict, not sent to
  the model.
- The agent gets `list_files` (cheap overview) and `get_diff(filename)`
  (fetch one hunk). It pulls only what it needs — like a human opening
  files in the Files Changed tab.

### 2. The output is a tool call, not prose

"Please output JSON" fails eventually — the model wraps it in prose or
breaks the schema. The reliable pattern: define a `submit_review` tool
whose `input_schema` IS the output format. The model can't finish without
calling it, so valid structured output is guaranteed by construction.

The schema requires per finding: `file`, `line`, `severity`
(bug/security/warning), `explanation`. Plus a `summary`.

`submit_review()` doesn't send anything anywhere — it just stashes the
payload in a `submitted` dict that `review_pr()` reads after the loop ends.

## The prompt (`REVIEW_PROMPT`)

Deliberately strict: "only real problems," "no style nitpicks," "empty
findings are fine." Agents invent issues when pressured — permission to
find nothing is how you keep precision high.

## The flow

`review_pr(pr_label, sha, diff)` → split diff → build tools + dispatch →
`run_agent()` → `log_run()` to the trace DB → return findings + stats.

If the loop ends without `submit_review` being called, status is
`"no_review"` in the trace — observable failure instead of silent weirdness.
