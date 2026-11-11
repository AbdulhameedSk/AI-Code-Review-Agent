"""
trace.py — observability: every agent run, logged.

When an agent does something weird in prod, "the model decided to" is not a
debugging strategy. You need: what tools did it call, with what inputs, what
came back, how many tokens, what did it cost, how long did it take.
"""
import json
import os
import sqlite3
import time

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "traces.db")


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pr TEXT, sha TEXT, status TEXT,
            findings INTEGER, cost_usd REAL,
            input_tokens INTEGER, output_tokens INTEGER,
            latency_s REAL, tool_log TEXT, created_at REAL
        )
    """)
    return conn


def already_reviewed(sha: str) -> bool:
    """Idempotency: has this exact commit been reviewed?"""
    with _conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM runs WHERE sha=? AND status='done' LIMIT 1", (sha,)
        ).fetchone()
    return row is not None


def log_run(pr: str, sha: str, status: str, findings: int,
            stats, latency_s: float, tool_log: list) -> int:
    with _conn() as conn:
        cur = conn.execute(
            "INSERT INTO runs (pr, sha, status, findings, cost_usd, "
            "input_tokens, output_tokens, latency_s, tool_log, created_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            (pr, sha, status, findings, stats.cost_usd,
             stats.input_tokens, stats.output_tokens,
             latency_s, json.dumps(tool_log), time.time()),
        )
        return cur.lastrowid


def recent_runs(limit: int = 10) -> list[dict]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT id, pr, sha, status, findings, cost_usd, latency_s, "
            "created_at FROM runs ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    cols = ["id", "pr", "sha", "status", "findings", "cost_usd",
            "latency_s", "created_at"]
    return [dict(zip(cols, r)) for r in rows]
