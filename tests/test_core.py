"""Offline unit tests — no API key needed."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from review_agent import split_diff
from github_client import verify_signature
import hmac, hashlib


def test_split_diff_multiple_files():
    diff = (
        "diff --git a/a.py b/a.py\n--- a/a.py\n+++ b/a.py\n@@ +x\n"
        "diff --git a/b.py b/b.py\n--- a/b.py\n+++ b/b.py\n@@ +y\n"
    )
    hunks = split_diff(diff)
    assert set(hunks) == {"a.py", "b.py"}
    assert "+x" in hunks["a.py"] and "+y" in hunks["b.py"]


def test_verify_signature(monkeypatch):
    monkeypatch.setenv("WEBHOOK_SECRET", "s3cret")
    body = b'{"hello":"world"}'
    sig = "sha256=" + hmac.new(b"s3cret", body, hashlib.sha256).hexdigest()
    assert verify_signature(body, sig)
    assert not verify_signature(body, "sha256=deadbeef")
    assert not verify_signature(body, None)


def test_cost_stats():
    from core import RunStats
    s = RunStats()
    s.input_tokens, s.output_tokens = 1_000_000, 100_000
    assert abs(s.cost_usd - (3.0 + 1.5)) < 1e-9
