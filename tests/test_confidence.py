from __future__ import annotations

from careerproof.analysis_engine import analyze_question


def test_supported_answer_has_data_based_confidence(bundle):
    response = analyze_question("Which cities have the most entry-level job postings?", bundle, write_audit=False)
    assert response.confidence.label in {"High confidence", "Medium confidence", "Low confidence"}
    assert response.confidence.score > 0
    assert set(response.confidence.breakdown) == {"evidence", "completeness", "intent", "quality"}


def test_unsupported_answer_is_insufficient_confidence(bundle):
    response = analyze_question("Which company has the happiest employees?", bundle, write_audit=False)
    assert response.confidence.label == "Insufficient evidence"
    assert response.confidence.score == 0
