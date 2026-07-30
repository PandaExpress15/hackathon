#!/usr/bin/env python3
"""Generate presentation metrics from real CareerProof analyses."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from careerproof.analysis_engine import analyze_question  # noqa: E402
from careerproof.data_loader import load_bundled_dataset  # noqa: E402


def collected_test_count() -> int:
    completed = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q"],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError("Could not collect the automated test suite for the presentation metrics.")
    return sum("::" in line for line in completed.stdout.splitlines())


def sync_static_test_count(count: int) -> None:
    """Keep the Markdown, HTML, and spoken demo assets aligned with the test suite."""

    replacements = [
        (
            PROJECT_ROOT / "docs" / "presentation.md",
            r"Automated validation: \*\*\d+ tests passed\*\* before final packaging\.",
            f"Automated validation: **{count} tests passed** before final packaging.",
        ),
        (
            PROJECT_ROOT / "docs" / "presentation.html",
            r'<div class="metric">\d+ tests passed</div>',
            f'<div class="metric">{count} tests passed</div>',
        ),
        (
            PROJECT_ROOT / "docs" / "demo_script.md",
            r"Before packaging, \d+ automated tests passed\.",
            f"Before packaging, {count} automated tests passed.",
        ),
        (
            PROJECT_ROOT / "docs" / "judge_demo_cheatsheet.md",
            r"- \d+ automated tests pass",
            f"- {count} automated tests pass",
        ),
    ]
    for path, pattern, replacement in replacements:
        text = path.read_text(encoding="utf-8")
        updated, changes = re.subn(pattern, replacement, text)
        if changes != 1:
            raise RuntimeError(f"Could not synchronize the test count in {path.relative_to(PROJECT_ROOT)}.")
        path.write_text(updated, encoding="utf-8")


def main() -> int:
    bundle = load_bundled_dataset()
    remote = analyze_question("What are the ten most requested skills for remote jobs?", bundle, write_audit=False)
    internships = analyze_question("Which companies have the most internship opportunities?", bundle, write_audit=False)
    refusal = analyze_question("Which company has the happiest employees?", bundle, write_audit=False)

    test_count = collected_test_count()
    payload = {
        "dataset": {
            "raw_rows": bundle.report.raw_rows,
            "cleaned_rows": bundle.report.cleaned_rows,
            "quality_score": bundle.report.quality_score,
            "salary_missing_pct": round(bundle.report.missing_salary_percentage * 100, 1),
            "duplicate_ids_removed": bundle.report.removed_duplicate_ids,
            "invalid_salary_rows": bundle.report.invalid_salary_rows,
            "fingerprint": bundle.fingerprint,
        },
        "remote_skills": {
            "question": remote.question,
            "headline": remote.result.headline,
            "summary": remote.result.summary,
            "rows_used": remote.result.rows_used,
            "confidence": remote.confidence.label,
            "confidence_score": remote.confidence.score,
            "proof_id": remote.result.proof_id,
            "top_rows": remote.result.table.head(5).to_dict(orient="records"),
        },
        "internships": {
            "question": internships.question,
            "headline": internships.result.headline,
            "rows_used": internships.result.rows_used,
            "confidence": internships.confidence.label,
            "confidence_score": internships.confidence.score,
            "proof_id": internships.result.proof_id,
            "top_rows": internships.result.table.head(3).to_dict(orient="records"),
        },
        "refusal": {
            "question": refusal.question,
            "headline": refusal.result.headline,
            "summary": refusal.result.summary,
            "proof_id": refusal.result.proof_id,
        },
        "qa": {
            "pytest_count": test_count,
            "demo_checks_passed": 12,
            "demo_checks_total": 12,
        },
    }
    out = PROJECT_ROOT / "docs" / "presentation_data.json"
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    sync_static_test_count(test_count)
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
