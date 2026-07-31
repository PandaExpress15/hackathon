from __future__ import annotations

from careerproof.config import ROOT


def test_blue_accents_and_existing_theme_are_present() -> None:
    css = (ROOT / "static/app.css").read_text(encoding="utf-8")
    assert "--blue-600:#2563eb" in css
    assert "--green-600:#0f9368" in css
    assert "--navy-950:#071a30" in css


def test_frontend_has_all_primary_workspaces() -> None:
    html = (ROOT / "templates/app.html").read_text(encoding="utf-8")
    for label in ["Ask CareerProof", "Occupation Explorer", "Question Library", "Data Catalog", "Trust Center"]:
        assert label in html


def test_frontend_discloses_official_data_and_no_synthetic_records() -> None:
    html = (ROOT / "templates/app.html").read_text(encoding="utf-8")
    assert "No synthetic job records" in html
    assert "BLS · Census · O*NET" in html
