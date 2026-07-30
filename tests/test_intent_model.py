from __future__ import annotations

from careerproof.intent_model import LocalIntentModel


def test_local_model_recognizes_skill_question():
    result = LocalIntentModel().predict("What technical skills show up most often in remote jobs?")
    assert result.label == "skill_frequency"
    assert result.confidence > 0.20


def test_local_model_runs_without_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    model = LocalIntentModel()
    assert model.predict("How many postings are there?").label == "count"
