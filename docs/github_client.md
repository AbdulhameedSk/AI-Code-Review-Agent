# github_client.py — talking to GitHub

## Why it exists

All GitHub API interaction in one place: fetching PR data, posting reviews,
and verifying that incoming webhooks are really from GitHub.

## How each piece works

- **`_headers()`** — every request sends `Authorization: Bearer <token>`
  plus GitHub's API version header. The token comes from env, never code.

- **`verify_signature(body, signature)`** — GitHub signs every webhook
  payload with HMAC-SHA256 using your `WEBHOOK_SECRET`. We recompute the
  signature over the raw request body and compare with
  `hmac.compare_digest` (constant-time — prevents timing attacks). Without
  this, anyone on the internet could POST fake PR events and make your
  agent spend money reviewing nothing.

- **`get_pr_diff()`** — the trick here is the `Accept` header:
  `application/vnd.github.v3.diff` makes the PR endpoint return the raw
  unified diff text instead of JSON metadata.

- **`get_pr_files()`** — returns per-file info (filename, status, patch).
  Used by the manual `/review` endpoint to show what was reviewed.

- **`post_review()`** — creates a PR review: a `body` (summary + findings
  list) plus optional inline `comments` (`{path, line, body}`). Returns the
  review's URL.

## Why these choices

- Token in env var → secrets never hit git.
- HMAC before any work → cheap rejection of forged requests.
- Constant-time compare → standard for signature checks; `==` leaks timing.
