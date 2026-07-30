from __future__ import annotations


def test_application_builds_without_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    from careerproof.ui import create_app

    app = create_app()
    assert app is not None
