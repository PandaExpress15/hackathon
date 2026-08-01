from __future__ import annotations

from careerproof.config import ROOT


def test_blue_accents_and_existing_theme_are_present() -> None:
    css = (ROOT / "static/app.css").read_text(encoding="utf-8")
    assert "--blue-600:#2563eb" in css
    assert "--green-600:#0f9368" in css
    assert "--navy-950:#071a30" in css
    assert "--bg:#040812" in css
    assert "--violet" in css
    assert "prefers-reduced-motion" in css


def test_frontend_has_all_primary_workspaces() -> None:
    html = (ROOT / "templates/app.html").read_text(encoding="utf-8")
    for label in [
        "Career Universe", "Build My Path", "Compare Lab", "Skill Bridge", "Ask CareerProof",
        "Occupation Explorer", "Degree Pathways", "Question Library", "Data Catalog", "Trust Center",
    ]:
        assert label in html


def test_frontend_has_suit_bow_tie_identity_and_judge_mode() -> None:
    html = (ROOT / "templates/app.html").read_text(encoding="utf-8")
    assert "CareerProof suit and bow-tie emblem" in html
    assert "bow-tie" in html
    assert "Start guided judge presentation" in html
    assert "Plan your future" in html
    assert "Not for AI" in html
    assert "designed to endure AI change" in html
    assert "No career is permanently AI-proof" in html


def test_frontend_has_98_upgrade_controls() -> None:
    html = (ROOT / "templates/app.html").read_text(encoding="utf-8")
    js = (ROOT / "static/app.js").read_text(encoding="utf-8")
    for feature in [
        "Review CareerProof's interpretation",
        "Education is a hard limit",
        "Salary is a hard floor",
        "Location is required",
        "Resilience Model",
        "Data Quality",
        "Location Intelligence",
        "Saved Plans",
    ]:
        assert feature in html
    for feature in ["normalizePathPayload", "normalizeJudgePayload", "Challenge this recommendation", "comparisonTray"]:
        assert feature.lower() in js.lower()


def test_frontend_discloses_official_data_and_no_synthetic_records() -> None:
    html = (ROOT / "templates/app.html").read_text(encoding="utf-8")
    assert "No synthetic job records" in html
    assert "Official sources only" in html
    for source in ["BLS", "Census", "O*NET", "BEA", "NCES"]:
        assert source in html


def test_frontend_has_presentation_controls_and_readable_information_text() -> None:
    html = (ROOT / "templates/app.html").read_text(encoding="utf-8")
    css = (ROOT / "static/app.css").read_text(encoding="utf-8")
    js = (ROOT / "static/app.js").read_text(encoding="utf-8")
    for marker in [
        'id="judgeModeFull"', 'id="judgeModeQuick"', 'id="judgeAutoplay"',
        'id="judgeTimeline"', 'id="judgeOpenLive"', 'id="resetJudgeDemo"',
    ]:
        assert marker in html
    for marker in ["presenter_script", "renderJudgeTimeline", "openJudgeLiveFeature", "setJudgeAutoplay"]:
        assert marker in js
    assert "CareerProof 4.1 presentation and readability upgrade" in css
    assert "font-size:15.5px" in css
    assert "judge-presenter-script" in css


def test_deployment_files_are_present() -> None:
    for relative in ["Dockerfile", ".dockerignore", "Procfile", "render.yaml", "docs/DEPLOYMENT.md"]:
        assert (ROOT / relative).is_file()
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    render = (ROOT / "render.yaml").read_text(encoding="utf-8")
    assert 'os.getenv("PORT"' in app
    assert 'host = os.getenv("CAREERPROOF_HOST", "0.0.0.0")' in app
    assert "/api/health" in render
