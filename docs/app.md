# app.py — the webhook service

## Why it exists

The agent needs a trigger. This FastAPI app is the door: GitHub POSTs PR
events to `/webhook`, and this file decides what happens next.

## The endpoints

- **`POST /webhook`** — the real entry point. Order matters:
  1. Read the raw body (needed for signature check — must verify the exact
     bytes, not parsed JSON).
  2. `verify_signature()` — reject anything not from GitHub with 403.
  3. Filter: only `pull_request` events, only `opened`/`synchronize`/
     `reopened` actions. (`synchronize` = new commits pushed to an open PR.)
  4. Kick off `process_pr` in a **background thread** and return 202
     immediately. GitHub retries webhooks that don't answer fast — never
     do slow agent work inside the request.
- **`POST /review`** — manual trigger `{owner, repo, number}`. This is the
  demo path: works on any public PR with no webhook setup.
- **`GET /traces`** — last 20 runs with cost/token stats.
- **`GET /health`** — liveness check, also reports whether DRY_RUN is on.

## process_pr — the pipeline

1. `already_reviewed(sha)` — **idempotency.** Webhooks are at-least-once
   delivery; the same event can arrive twice. Each unique commit SHA gets
   reviewed exactly once.
2. `get_pr_diff()` → `review_pr()` → findings.
3. If `DRY_RUN`: return findings, post nothing. **Human-in-the-loop** —
   run the agent for weeks, inspect drafts, flip the switch when you trust
   it. Every responsible agent rollout looks like this.
4. If live: `_format_body()` + `_format_comments()` (only bug/security go
   inline) → `post_review()`.

## Why DRY_RUN exists

An agent that can post to your repos is a liability until proven. DRY_RUN
lets you accumulate evidence: "it reviewed 20 PRs and only flagged real
issues" → then you trust it with write access.
