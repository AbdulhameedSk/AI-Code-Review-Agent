"""
app.py — the webhook service.

    uvicorn app:app --port 8000

Endpoints:
  POST /webhook   — GitHub pull_request events (HMAC-verified)
  POST /review    — manual trigger: {owner, repo, number} (great for demos)
  GET  /traces    — recent runs with cost/token stats
  GET  /health

Two production behaviors:
- DEDUPE: if we've already reviewed this head SHA, skip it. Webhooks are
  delivered at-least-once; idempotency is your job.
- DRY_RUN: with DRY_RUN=true, findings are logged but never posted to
  GitHub — human-in-the-loop until you trust it.
"""
import os
import json
import threading

from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

import github_client as gh
import review_agent
from trace import already_reviewed, recent_runs

load_dotenv()
app = FastAPI(title="Sentinel — AI code review agent")
DRY_RUN = os.getenv("DRY_RUN", "true").lower() == "true"


class ReviewRequest(BaseModel):
    owner: str
    repo: str
    number: int


def _format_body(findings: list, summary: str) -> str:
    lines = [f"### Sentinel review\n\n{summary}\n"]
    for f in findings:
        lines.append(
            f"- **{f['severity'].upper()}** `{f['file']}:{f['line']}` — "
            f"{f['explanation']}")
    return "\n".join(lines)


def _format_comments(findings: list) -> list[dict]:
    """Findings -> GitHub inline review comments (bugs/security only)."""
    return [
        {"path": f["file"], "line": f["line"], "body":
         f"**{f['severity'].upper()}**: {f['explanation']}"}
        for f in findings if f["severity"] in ("bug", "security")
    ]


def process_pr(owner: str, repo: str, number: int, sha: str) -> dict:
    label = f"{owner}/{repo}#{number}"
    if already_reviewed(sha):
        return {"status": "skipped", "reason": "already reviewed this SHA"}

    diff = gh.get_pr_diff(owner, repo, number)
    result = review_agent.review_pr(label, sha, diff)
    findings = result.get("findings", [])

    if DRY_RUN:
        return {"status": "dry_run", "findings": findings,
                "summary": result.get("summary"),
                "cost_usd": result["stats"].cost_usd}

    url = gh.post_review(owner, repo, number,
                         _format_body(findings, result.get("summary", "")),
                         _format_comments(findings))
    return {"status": "posted", "url": url,
            "cost_usd": result["stats"].cost_usd}


@app.post("/webhook")
async def webhook(request: Request):
    body = await request.body()
    if not gh.verify_signature(body, request.headers.get("x-hub-signature-256")):
        raise HTTPException(403, "bad signature")

    event = request.headers.get("x-github-event")
    if event != "pull_request":
        return {"status": "ignored", "event": event}

    payload = await request.json()
    if payload.get("action") not in ("opened", "synchronize", "reopened"):
        return {"status": "ignored", "action": payload.get("action")}

    pr = payload["pull_request"]
    args = (payload["repository"]["owner"]["login"],
            payload["repository"]["name"],
            pr["number"], pr["head"]["sha"])
    threading.Thread(target=process_pr, args=args, daemon=True).start()
    return {"status": "queued", "pr": pr["number"], "dry_run": DRY_RUN}


@app.post("/review")
def review_manual(req: ReviewRequest):
    files = gh.get_pr_files(req.owner, req.repo, req.number)
    sha = "manual"  # manual runs skip dedupe via non-SHA label
    diff = gh.get_pr_diff(req.owner, req.repo, req.number)
    result = review_agent.review_pr(f"{req.owner}/{req.repo}#{req.number}",
                                    sha, diff)
    return {"findings": result.get("findings", []),
            "summary": result.get("summary"),
            "cost_usd": result["stats"].cost_usd,
            "files": [f["filename"] for f in files]}


@app.get("/traces")
def traces():
    return recent_runs(20)


@app.get("/health")
def health():
    return {"status": "ok", "dry_run": DRY_RUN}
