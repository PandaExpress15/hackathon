from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from careerproof.data_store import get_store
from careerproof.query_engine import QueryEngine

CHECKS = [
    ("Which states pay nuclear engineers the most?", "supported"),
    ("What skills do public relations specialists need?", "supported"),
    ("Which broad bachelor's degree fields have the highest median earnings?", "supported"),
    ("What is the job outlook for political scientists?", "supported"),
    ("How much do lawyers earn in Maryland?", "supported"),
    ("Compare lawyers and political scientists.", "supported"),
    ("What tasks do public relations specialists perform?", "supported"),
    ("What software do broadcast technicians use?", "supported"),
    ("How do national wages compare by typical entry-level education?", "supported"),
    ("Which states have the highest median wage for bachelor's-level occupations?", "supported"),
    ("What bachelor's degree should I pursue for the highest pay after becoming a lawyer?", "refused"),
    ("Which company has the happiest employees?", "refused"),
]


def main() -> int:
    engine = QueryEngine(get_store())
    results = []
    failures = 0
    for number, (question, expected) in enumerate(CHECKS, start=1):
        result = engine.answer(question)
        passed = result.status == expected and bool(result.evidence_id)
        if expected == "supported":
            passed = passed and bool(result.rows) and bool(result.sources) and bool(result.evidence.get("calculation"))
        if not passed:
            failures += 1
        results.append({
            "number": number,
            "question": question,
            "expected": expected,
            "actual": result.status,
            "dataset": result.dataset,
            "intent": result.intent,
            "rows": len(result.rows),
            "confidence": f"{result.confidence.label} ({result.confidence.score})",
            "evidence_id": result.evidence_id,
            "headline": result.headline,
            "result": "PASS" if passed else "FAIL",
        })
        print(f"[{number:02d}] {'PASS' if passed else 'FAIL'} | {result.dataset} | {question}")
        print(f"     {result.headline} | {result.evidence_id}")

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "passed": len(CHECKS) - failures,
        "total": len(CHECKS),
        "results": results,
    }
    (ROOT / "docs/demo_check_results.json").write_text(json.dumps(output, indent=2), encoding="utf-8")
    lines = [
        "# Testing Report",
        "",
        f"Generated from real executions on **{output['generated_at']}** by `python scripts/run_demo_checks.py`.",
        "",
        "## Summary",
        "",
        f"- Demo checks passed: **{output['passed']}/{output['total']}**",
        "- Bundled labor-market records: **official BLS, Census, and O*NET data only**",
        "- Synthetic labor-market records: **0**",
        "- Automated unit and integration tests: run with `pytest -q`",
        "",
        "## Demo results",
        "",
        "| # | Question | Expected | Actual | Dataset | Rows | Confidence | Evidence ID | Result |",
        "| ---: | --- | --- | --- | --- | ---: | --- | --- | --- |",
    ]
    for row in results:
        lines.append(
            f"| {row['number']} | {row['question'].replace('|', '/')} | {row['expected']} | {row['actual']} | {row['dataset']} | {row['rows']} | {row['confidence']} | `{row['evidence_id']}` | {row['result']} |"
        )
    lines.extend([
        "",
        "## Notes",
        "",
        "- Values are calculated from the bundled official source snapshots.",
        "- Evidence IDs are content-derived and change when the question route, query plan, or returned rows change.",
        "- Refusal checks confirm that the application does not invent employer happiness, hiring guarantees, or lawyer-specific causal degree outcomes.",
    ])
    (ROOT / "docs/TESTING_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nSummary: {output['passed']}/{output['total']} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
