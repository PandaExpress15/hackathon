from __future__ import annotations

import pytest

from careerproof.analysis_engine import analyze_question
from careerproof.intent_training_data import SUPPORTED_DEMO_QUESTIONS


@pytest.mark.parametrize("question", SUPPORTED_DEMO_QUESTIONS)
def test_every_demo_question_returns_verified_evidence(bundle, question):
    response = analyze_question(question, bundle, write_audit=False)
    assert response.result.status == "supported", response.result.summary
    assert not response.result.table.empty
    assert response.result.rows_used > 0
    assert response.result.proof_id.startswith("CP-")
    assert response.chart is not None
    assert response.confidence.score > 0
