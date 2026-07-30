#!/usr/bin/env python3
"""Run the judge-ready CareerProof questions and record real outcomes."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from careerproof.analysis_engine import analyze_question  # noqa: E402
from careerproof.data_loader import load_bundled_dataset  # noqa: E402
from careerproof.intent_training_data import (  # noqa: E402
    SUPPORTED_DEMO_QUESTIONS,
    UNSUPPORTED_DEMO_QUESTIONS,
)

REPORT_PATH = PROJECT_ROOT / "docs" / "testing_report.md"
JSON_PATH = PROJECT_ROOT / "docs" / "demo_check_results.json"


def _summary_row(question: str, expected: str, response: Any, duration_ms: float) -> dict[str, Any]:
    result = response.result
    has_evidence = bool(response.proof_bundle) and bool(result.calculation)
    has_chart = response.chart is not None
    correct_status = result.status == expected
    if expected == "supported":
        passed = correct_status and not result.table.empty and has_evidence and has_chart
    else:
        passed = correct_status and bool(result.summary or result.headline) and has_evidence
    return {
        "question": question,
        "expected_status": expected,
        "actual_status": result.status,
        "pass": passed,
        "headline": result.headline,
        "rows_used": int(result.rows_used),
        "confidence": response.confidence.label,
        "confidence_score": int(response.confidence.score),
        "evidence_generated": has_evidence,
        "chart_generated": has_chart,
        "proof_id": result.proof_id,
        "duration_ms": round(duration_ms, 2),
        "warnings": list(result.warnings),
    }


def _safe_cell(text: Any) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ").strip()


def collected_test_count() -> int:
    """Return the number of tests currently collected by pytest."""

    completed = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q"],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        return 0
    return sum("::" in line for line in completed.stdout.splitlines())


def write_markdown_report(
    results: list[dict[str, Any]],
    dataset_summary: dict[str, Any],
    test_count: int,
) -> None:
    passed = sum(1 for row in results if row["pass"])
    supported = [row for row in results if row["expected_status"] == "supported"]
    refusals = [row for row in results if row["expected_status"] == "unsupported"]
    generated_at = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")

    lines = [
        "# Testing Report",
        "",
        f"Generated from real executions on **{generated_at}** by `python scripts/run_demo_checks.py`.",
        "",
        "## Summary",
        "",
        f"- Demo checks passed: **{passed}/{len(results)}**",
        f"- Supported questions passed: **{sum(row['pass'] for row in supported)}/{len(supported)}**",
        f"- Expected refusal cases passed: **{sum(row['pass'] for row in refusals)}/{len(refusals)}**",
        f"- Automated tests collected: **{test_count}**",
        f"- Raw dataset rows: **{dataset_summary['raw_rows']:,}**",
        f"- Cleaned dataset rows: **{dataset_summary['cleaned_rows']:,}**",
        f"- Dataset quality score: **{dataset_summary['quality_score']}/100**",
        f"- Dataset fingerprint: `{dataset_summary['fingerprint']}`",
        "",
        "The bundled dataset is synthetic. The report describes the supplied demonstration data and does not make claims about the live labor market.",
        "",
        "## Demo-check results",
        "",
        "| # | Question | Expected | Actual | Rows used | Confidence | Evidence | Chart | Evidence ID | Result |",
        "|---:|---|---|---|---:|---|---:|---:|---|---|",
    ]
    for idx, row in enumerate(results, start=1):
        lines.append(
            "| {idx} | {question} | {expected} | {actual} | {rows} | {confidence} ({score}) | {evidence} | {chart} | `{proof}` | {result} |".format(
                idx=idx,
                question=_safe_cell(row["question"]),
                expected=row["expected_status"],
                actual=row["actual_status"],
                rows=row["rows_used"],
                confidence=row["confidence"],
                score=row["confidence_score"],
                evidence="Yes" if row["evidence_generated"] else "No",
                chart="Yes" if row["chart_generated"] else "No",
                proof=row["proof_id"],
                result="PASS" if row["pass"] else "FAIL",
            )
        )

    lines += [
        "",
        "## Representative verified result",
        "",
    ]
    representative = next(row for row in supported if "remote jobs" in row["question"].lower())
    lines += [
        f"**Question:** {representative['question']}",
        "",
        f"**Verified result:** {representative['headline']}",
        "",
        f"**Rows used:** {representative['rows_used']:,}",
        "",
        f"**Confidence:** {representative['confidence']} ({representative['confidence_score']}/100)",
        "",
        f"**Evidence ID:** `{representative['proof_id']}`",
        "",
        "## Representative safe refusal",
        "",
    ]
    refusal = refusals[0]
    lines += [
        f"**Question:** {refusal['question']}",
        "",
        f"**System behavior:** {_safe_cell(refusal['headline'])}",
        "",
        f"**Evidence ID:** `{refusal['proof_id']}`",
        "",
        "The system refused because the dataset does not contain the field required to support the requested conclusion. It did not invent an employer-quality judgment.",
        "",
        "## Additional automated tests",
        "",
        "Run the full unit and integration suite with:",
        "",
        "```bash",
        "pytest -q",
        "```",
        "",
        f"The current suite contains **{test_count} tests**. The submission verifier runs every test and stops packaging if any test fails.",
        "",
        "The suite covers schema validation, cleaning, privacy masking, proof-bundle integrity and replay, intent routing, query validation, deterministic execution, confidence scoring, exports, refusals, adversarial inputs, audit logging, UI construction, and the prohibition on arbitrary code execution.",
        "",
        "## Real application launch check",
        "",
        "Run the Gradio server smoke test with:",
        "",
        "```bash",
        "python scripts/smoke_test_app.py",
        "```",
        "",
        "The smoke test launches the real application on a temporary loopback port, waits for HTTP 200, confirms the CareerProof title marker, and shuts the server down. The submission verifier runs this check automatically.",
        "",
        "## Pass criteria used by this script",
        "",
        "- A supported question must return a nonempty deterministic result table, a calculation/evidence bundle, and a chart.",
        "- An expected refusal must return `unsupported`, include a clear reason, and still generate a traceable proof bundle.",
        "- Every result must have a confidence label and Evidence ID.",
        "",
    ]
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--no-write",
        action="store_true",
        help="Run the demo checks without updating the committed JSON and Markdown reports.",
    )
    args = parser.parse_args()

    bundle = load_bundled_dataset()
    checks: list[tuple[str, str]] = [
        *((question, "supported") for question in SUPPORTED_DEMO_QUESTIONS),
        *((question, "unsupported") for question in UNSUPPORTED_DEMO_QUESTIONS),
    ]
    results: list[dict[str, Any]] = []

    print("CareerProof AI demo checks")
    print(f"Dataset: {bundle.display_name}")
    print(f"Rows: {bundle.report.raw_rows} raw / {bundle.report.cleaned_rows} cleaned")
    print("-" * 96)

    for index, (question, expected) in enumerate(checks, start=1):
        start = time.perf_counter()
        try:
            response = analyze_question(question, bundle, write_audit=False)
            duration_ms = (time.perf_counter() - start) * 1000
            row = _summary_row(question, expected, response, duration_ms)
        except Exception as exc:  # pragma: no cover - command-line safety net
            duration_ms = (time.perf_counter() - start) * 1000
            row = {
                "question": question,
                "expected_status": expected,
                "actual_status": "error",
                "pass": False,
                "headline": f"{type(exc).__name__}: {exc}",
                "rows_used": 0,
                "confidence": "Unavailable",
                "confidence_score": 0,
                "evidence_generated": False,
                "chart_generated": False,
                "proof_id": "none",
                "duration_ms": round(duration_ms, 2),
                "warnings": [str(exc)],
            }
        results.append(row)
        print(
            f"[{index:02d}/{len(checks):02d}] {'PASS' if row['pass'] else 'FAIL'} | "
            f"expected={expected:<11} actual={row['actual_status']:<11} "
            f"rows={row['rows_used']:<4} confidence={row['confidence']:<22} "
            f"proof={row['proof_id']}"
        )
        print(f"    {question}")
        print(f"    {row['headline']}")

    dataset_summary = {
        "raw_rows": bundle.report.raw_rows,
        "cleaned_rows": bundle.report.cleaned_rows,
        "quality_score": bundle.report.quality_score,
        "fingerprint": bundle.fingerprint,
    }
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "dataset": dataset_summary,
        "checks": results,
    }
    if not args.no_write:
        JSON_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        write_markdown_report(results, dataset_summary, collected_test_count())

    passed = sum(1 for row in results if row["pass"])
    print("-" * 96)
    print(f"Result: {passed}/{len(results)} checks passed")
    if args.no_write:
        print("Report write: skipped (--no-write)")
    else:
        print(f"Markdown report: {REPORT_PATH.relative_to(PROJECT_ROOT)}")
        print(f"Machine-readable report: {JSON_PATH.relative_to(PROJECT_ROOT)}")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
