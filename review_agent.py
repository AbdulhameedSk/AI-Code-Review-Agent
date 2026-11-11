"""
review_agent.py — the reviewer.

Two techniques that matter for real agents:

1. CONTEXT MANAGEMENT — a PR diff can be 10k lines. We never dump it into
   the prompt. Instead it's split into per-file hunks stored locally; the
   agent asks for the files it wants to see via tools. Big context windows
   don't remove the need for this — cost and attention both degrade.

2. FORCED STRUCTURED OUTPUT — instead of parsing prose, we define a
   `submit_review` tool whose schema IS the output format. The model must
   produce valid JSON findings or the loop keeps going. This is the
   standard trick behind "guaranteed JSON mode" in production agents.
"""
import re
import time

from core import run_agent
from trace import log_run

REVIEW_PROMPT = """You are Sentinel, a senior code reviewer. You are reviewing
a pull request diff. Rules:

- Use list_files to see what changed, then get_diff for the files that matter.
- Only report REAL problems: bugs, security issues, broken logic, missing
  error handling. No style nitpicks, no "consider adding comments".
- Every finding needs file, line (approximate new-side line number),
  severity (bug|security|warning), and a one-paragraph explanation.
- If the diff is clean, submit an empty findings list — do not invent issues.
- When done, you MUST call submit_review with your findings and a 1-2
  sentence summary. That tool call IS your output."""


def split_diff(diff: str) -> dict[str, str]:
    """Split a unified diff into {filename: hunk_text}."""
    parts = re.split(r"(?=^diff --git )", diff, flags=re.M)
    hunks = {}
    for p in parts:
        m = re.search(r"^\+\+\+ b/(.+)$", p, flags=re.M)
        if m:
            hunks[m.group(1)] = p.strip()
    return hunks


def review_pr(pr_label: str, sha: str, diff: str) -> dict:
    """Run the reviewer over a diff. Returns {findings, summary, stats,...}"""
    hunks = split_diff(diff)
    submitted = {}

    def list_files() -> str:
        return "\n".join(
            f"{name} ({h.count(chr(10))} diff lines)" for name, h in hunks.items()
        ) or "(empty diff)"

    def get_diff(filename: str) -> str:
        return hunks.get(filename, f"ERROR: no file {filename} in diff")[:8000]

    def submit_review(findings: list, summary: str) -> str:
        submitted["findings"] = findings
        submitted["summary"] = summary
        return "Review submitted."

    tools = [
        {"name": "list_files",
         "description": "List files changed in this PR.",
         "input_schema": {"type": "object", "properties": {}}},
        {"name": "get_diff",
         "description": "Get the diff hunk for one file.",
         "input_schema": {"type": "object", "properties": {
             "filename": {"type": "string"}}, "required": ["filename"]}},
        {"name": "submit_review",
         "description": "Submit the final review. findings: [{file, line, severity, explanation}]. Call exactly once, at the end.",
         "input_schema": {"type": "object", "properties": {
             "findings": {"type": "array", "items": {"type": "object",
                 "properties": {
                     "file": {"type": "string"},
                     "line": {"type": "integer"},
                     "severity": {"type": "string",
                                  "enum": ["bug", "security", "warning"]},
                     "explanation": {"type": "string"}},
                 "required": ["file", "line", "severity", "explanation"]}},
             "summary": {"type": "string"}},
             "required": ["findings", "summary"]}},
    ]

    dispatch_table = {"list_files": list_files, "get_diff": get_diff,
                      "submit_review": submit_review}

    def dispatch(name, inputs):
        return dispatch_table[name](**inputs)

    start = time.time()
    _, stats, tool_log = run_agent(
        REVIEW_PROMPT, tools, dispatch,
        f"Review PR {pr_label}. Start by listing the changed files.",
        max_steps=20,
    )
    run_id = log_run(pr_label, sha,
                     "done" if submitted else "no_review",
                     len(submitted.get("findings", [])),
                     stats, time.time() - start, tool_log)
    return {**submitted, "run_id": run_id, "stats": stats}
