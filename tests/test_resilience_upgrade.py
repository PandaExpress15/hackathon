from __future__ import annotations

from fastapi.testclient import TestClient
import pytest

from careerproof.data_store import get_store
from careerproof.intelligence import CareerIntelligence, RESILIENCE_MODEL_VERSION
from careerproof.webapp import create_app


@pytest.fixture(scope="module")
def intelligence() -> CareerIntelligence:
    return CareerIntelligence(get_store())


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(create_app())


def demo_payload() -> dict:
    return {
        "profile_text": "I like electronics and programming, want to stay near Maryland, earn at least $90,000, and stop at a bachelor's degree.",
        "interests": ["Electronics", "Programming", "Law"],
        "skills": ["Python", "Arduino", "Writing"],
        "education_max": "Bachelor's degree",
        "preferred_state": "Maryland",
        "salary_goal": 90000,
        "work_environment": ["Hands-on", "Office or analytical"],
        "remote_preference": "Flexible",
        "willing_to_relocate": False,
        "salary_is_hard": False,
        "education_is_hard": True,
        "location_is_hard": False,
        "weights": {
            "interest_fit": 24,
            "resilience": 28,
            "salary": 18,
            "growth": 8,
            "openings": 8,
            "education": 7,
            "location": 4,
            "stability": 3,
        },
        "limit": 6,
    }


def test_profile_interpretation_is_editable_and_does_not_override_form_toggles(intelligence: CareerIntelligence) -> None:
    result = intelligence.interpret_profile(**{key: value for key, value in demo_payload().items() if key != "limit"})
    profile = result["normalized_profile"]
    assert profile["preferred_state"] == "Maryland"
    assert profile["salary_goal"] == 90000
    assert profile["education_max"] == "Bachelor's degree"
    assert profile["salary_is_hard"] is False
    assert profile["education_is_hard"] is True
    assert result["requires_confirmation"] is True
    assert any("confirm the salary toggle" in warning for warning in result["warnings"])


def test_profile_parser_does_not_false_detect_cpp(intelligence: CareerIntelligence) -> None:
    result = intelligence.interpret_profile(profile_text="I like electronics and programming in Maryland.")
    assert "C++" not in result["skills"]
    positive = intelligence.interpret_profile(profile_text="I use C++ and Python for embedded electronics.")
    assert "C++" in positive["skills"]
    assert "Python" in positive["skills"]


def test_resilience_model_is_transparent_and_reproducible(intelligence: CareerIntelligence) -> None:
    card = intelligence.resilience_model_card()
    assert card["version"] == RESILIENCE_MODEL_VERSION
    assert len(card["dimensions"]) == 6
    assert round(sum(float(item["weight"]) for item in card["dimensions"]), 1) == 100.0
    assert all(item["keywords"] for item in card["dimensions"])
    assert "percentile" in card["normalization"].lower()
    assert card["validation"]["known_limitations"]


def test_electrical_engineering_resilience_profile_has_task_evidence(intelligence: CareerIntelligence) -> None:
    code = get_store().title_to_code["Electrical Engineers"]
    profile = intelligence.career_resilience_profile(code)
    assert profile["model_version"] == RESILIENCE_MODEL_VERSION
    assert 0 <= profile["overall_score"] <= 100
    assert len(profile["dimensions"]) == 6
    assert profile["task_impact"]["classified_task_count"] > 0
    assert "not an official automation probability" in profile["boundary"]


def test_path_builder_uses_hard_gate_counterfactuals_and_challenger(intelligence: CareerIntelligence) -> None:
    result = intelligence.path_builder(**demo_payload())
    assert result["status"] == "supported"
    assert result["results"][0]["occupation_title"] == "Electrical Engineers"
    assert result["results"][0]["feasibility"]["passes_hard_constraints"] is True
    assert result["results"][0]["challenge"]["weakest_evidence"]
    assert len(result["sensitivity"]) >= 6
    assert result["what_would_change_the_recommendation"]
    assert result["portfolio"]["primary_path"]["occupation_title"] == "Electrical Engineers"
    assert result["excluded_by_hard_constraints"]["count"] > 0


def test_compare_blocks_professional_degree_when_bachelors_is_hard(intelligence: CareerIntelligence) -> None:
    result = intelligence.compare(
        ["Electrical Engineers", "Nuclear Engineers", "Lawyers"],
        preferred_state="Maryland",
        education_max="Bachelor's degree",
        education_is_hard=True,
        user_skills=["Python", "Arduino"],
    )
    lawyer = next(item for item in result["results"] if item["occupation_title"] == "Lawyers")
    assert lawyer["feasibility"]["status"] == "blocked"
    assert result["tradeoff_summary"]["plain_language"]
    assert len(result["ranking_changes"]) >= 6


def test_new_public_endpoints_are_complete(client: TestClient) -> None:
    interpretation = client.post("/api/interpret-profile", json=demo_payload()).json()
    assert interpretation["normalized_profile"]["preferred_state"] == "Maryland"

    model = client.get("/api/resilience-model")
    assert model.status_code == 200
    assert model.json()["version"] == RESILIENCE_MODEL_VERSION

    quality = client.get("/api/data-quality")
    assert quality.status_code == 200
    assert quality.json()["status"] == "transparent"
    assert quality.json()["checks"]

    home = client.get("/api/home")
    assert home.status_code == 200
    assert home.json()["top_matches"][0]["occupation_title"] == "Electrical Engineers"


def test_search_and_degree_aliases_support_new_frontend(client: TestClient) -> None:
    occupations = client.get("/api/occupations", params={"query": "electrical engineer"}).json()["results"]
    assert occupations[0]["occupation_title"] == "Electrical Engineers"
    assert "resilience_score" in occupations[0]

    degrees = client.get("/api/degrees", params={"query": "electrical engineering"}).json()["results"]
    assert degrees
    assert "related_occupation_count" in degrees[0]


def test_judge_mode_contains_complete_timed_presentation(client: TestClient) -> None:
    payload = client.get("/api/judge-demo").json()
    steps = payload["steps"]
    step_ids = [step["id"] for step in steps]

    assert step_ids == [
        "purpose", "interpret", "path", "challenge", "compare",
        "proof", "refusal", "plan", "architecture", "close",
    ]
    assert all(step["presenter_script"] for step in steps)
    assert all(step["proof_points"] for step in steps)
    assert all(int(step["duration_seconds"]) > 0 for step in steps)
    assert all(step["workspace"] for step in steps)

    meta = payload["demo_meta"]
    assert meta["full_duration_seconds"] == sum(int(step["duration_seconds"]) for step in steps)
    assert meta["quick_duration_seconds"] == sum(int(step["duration_seconds"]) for step in steps if step["quick"])
    assert meta["quick_duration_seconds"] < meta["full_duration_seconds"] <= 600
    assert set(meta["quick_step_ids"]) == {step["id"] for step in steps if step["quick"]}

    assert len(payload["rubric"]) == 6
    assert sum(int(item["weight"]) for item in payload["rubric"]) == 100
    assert len(payload["architecture"]) == 6
    assert payload["action_plan"]["primary"]
    assert payload["action_plan"]["roadmap"]

    assert payload["path"]["results"][0]["occupation_title"] == "Electrical Engineers"
    assert payload["verified_answer"]["status"] == "supported"
    assert payload["refusal"]["status"] == "refused"


def test_live_diagnostic_covers_98_upgrade(client: TestClient) -> None:
    payload = client.get("/api/diagnostic").json()
    assert payload["status"] == "pass"
    names = {item["name"] for item in payload["checks"]}
    assert {
        "Editable profile interpretation",
        "Transparent resilience dimensions",
        "Hard feasibility gate",
        "Counterfactual decision tests",
        "Unsupported guarantee refusal",
    } <= names
    assert all(item["passed"] for item in payload["checks"])
