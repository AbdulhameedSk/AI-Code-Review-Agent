"""
github_client.py — talking to GitHub like a real integration.

Three production details that matter:

1. HMAC signature verification — anyone can POST to your webhook endpoint;
   only GitHub knows the secret. Verify before doing any work.
2. Token auth via header — a PAT or GitHub App token.
3. Diff handling — the PR diff is pulled via the media-type trick
   (Accept: application/vnd.github.v3.diff).
"""
import hashlib
import hmac
import os

import httpx

API = "https://api.github.com"


def _headers(accept: str = "application/vnd.github+json") -> dict:
    return {
        "Authorization": f"Bearer {os.getenv('GITHUB_TOKEN')}",
        "Accept": accept,
        "X-GitHub-Api-Version": "2022-11-28",
    }


def verify_signature(body: bytes, signature: str | None) -> bool:
    """Constant-time HMAC check of GitHub's X-Hub-Signature-256."""
    secret = os.getenv("WEBHOOK_SECRET")
    if not secret or not signature:
        return False
    expected = "sha256=" + hmac.new(
        secret.encode(), body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def get_pr_diff(owner: str, repo: str, number: int) -> str:
    resp = httpx.get(
        f"{API}/repos/{owner}/{repo}/pulls/{number}",
        headers=_headers("application/vnd.github.v3.diff"),
        timeout=20,
    )
    resp.raise_for_status()
    return resp.text


def get_pr_files(owner: str, repo: str, number: int) -> list[dict]:
    resp = httpx.get(
        f"{API}/repos/{owner}/{repo}/pulls/{number}/files",
        headers=_headers(), timeout=20,
    )
    resp.raise_for_status()
    return [
        {"filename": f["filename"], "status": f["status"],
         "patch": f.get("patch", "")}
        for f in resp.json()
    ]


def post_review(owner: str, repo: str, number: int,
                body: str, comments: list[dict]) -> str:
    """Post a PR review with inline comments.

    comments: [{path, line, body}] — line is the diff-position line number.
    """
    payload = {"event": "COMMENT", "body": body}
    if comments:
        payload["comments"] = comments
    resp = httpx.post(
        f"{API}/repos/{owner}/{repo}/pulls/{number}/reviews",
        headers=_headers(), json=payload, timeout=20,
    )
    resp.raise_for_status()
    return resp.json()["html_url"]
