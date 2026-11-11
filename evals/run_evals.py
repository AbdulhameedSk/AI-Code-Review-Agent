"""
evals/run_evals.py — the eval harness.

    python -m evals.run_evals

Ship agents without evals and you're flying blind: every prompt tweak or
model swap could silently regress review quality. This runs the reviewer
against fixture diffs with KNOWN issues and scores:

  hit  = found a finding whose explanation mentions an expected keyword
  fp   = flagged something in a fixture that should be clean
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import review_agent
from evals.fixtures import FIXTURES


def score(fixture: dict, findings: list) -> dict:
    text = " ".join(f["explanation"].lower() for f in findings)
    exp = fixture["expect"]
    hit = any(k in text for k in exp["keywords"]) if exp["keywords"] else True
    too_many = len(findings) > exp.get("max_findings", 99)
    too_few = len(findings) < exp.get("min_findings", 0)
    return {"hit": hit and not too_many and not too_few,
            "n_findings": len(findings)}


def main():
    results = []
    for fx in FIXTURES:
        print(f"--- {fx['name']} ---")
        out = review_agent.review_pr(f"eval:{fx['name']}", f"eval-{fx['name']}",
                                     fx["diff"])
        findings = out.get("findings", [])
        s = score(fx, findings)
        results.append(s["hit"])
        print(f"  findings={s['n_findings']} hit={s['hit']} "
              f"cost=${out['stats'].cost_usd:.4f}")
        for f in findings:
            print(f"    [{f['severity']}] {f['file']}:{f['line']} "
                  f"{f['explanation'][:80]}")

    passed = sum(results)
    print(f"\nEval: {passed}/{len(results)} fixtures passed")


if __name__ == "__main__":
    main()
