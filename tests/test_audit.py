from __future__ import annotations

from pathlib import Path

from careerproof.audit import log_analysis_event, read_audit_log
from careerproof.analysis_engine import analyze_question


def test_audit_log_masks_question_contacts(bundle, tmp_path: Path):
    response = analyze_question("How many jobs? Contact me at jordan.lee@example.com or (206) 555-0123", bundle, write_audit=False)
    path = tmp_path / "audit.jsonl"
    log_analysis_event(
        question=response.question,
        plan=response.plan,
        prediction=response.prediction,
        result=response.result,
        confidence=response.confidence,
        dataset_fingerprint=bundle.fingerprint,
        execution_time_ms=12.3,
        path=path,
    )
    text = path.read_text()
    assert "jordan.lee@example.com" not in text
    assert "(206) 555-0123" not in text
    frame = read_audit_log(path)
    assert len(frame) == 1
