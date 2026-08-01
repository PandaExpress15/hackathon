from __future__ import annotations

from careerproof.data_store import get_store
from careerproof.intelligence import CareerIntelligence
from careerproof.query_engine import QueryEngine


def intelligence() -> CareerIntelligence:
    return CareerIntelligence(get_store())


def test_path_builder_is_transparent_and_uses_official_inputs() -> None:
    result = intelligence().path_builder(
        interests=["Electronics", "Programming"],
        skills=["Python", "Arduino"],
        education_max="Bachelor's degree",
        preferred_state="Maryland",
        salary_goal=90000,
        weights={"interest_fit": 24, "resilience": 28, "salary": 18, "growth": 8, "openings": 8, "education": 7, "location": 4, "stability": 3},
        limit=8,
    )
    assert result["status"] == "supported"
    assert len(result["results"]) == 8
    assert "TF-IDF" in result["method"]["text_matching"]
    assert "not government ratings" in " ".join(result["limitations"])
    expected_components = {"interest_fit", "resilience", "salary", "growth", "openings", "education", "location", "stability"}
    assert all(set(item["score_components"]) == expected_components for item in result["results"])
    assert result["interpreted_request"]["requires_confirmation"] is True
    assert result["what_would_change_the_recommendation"]
    assert result["portfolio"]["primary_path"]
    assert all(item["challenge"]["weakest_evidence"] for item in result["results"])


def test_comparison_changes_by_user_control_and_exposes_confidence() -> None:
    ci = intelligence()
    salary_first = ci.compare(
        ["Nuclear Engineers", "Electrical Engineers", "Lawyers"],
        weights={"interest_fit": 0, "resilience": 0, "salary": 50, "growth": 0, "openings": 0, "education": 0, "location": 50, "stability": 0},
        preferred_state="Maryland",
    )
    openings_first = ci.compare(
        ["Nuclear Engineers", "Electrical Engineers", "Lawyers"],
        weights={"interest_fit": 0, "resilience": 0, "salary": 0, "growth": 0, "openings": 50, "education": 50, "location": 0, "stability": 0},
        preferred_state="Maryland",
    )
    assert salary_first["results"][0]["careerproof_score"] != openings_first["results"][0]["careerproof_score"]
    assert all("decision_confidence" in item for item in salary_first["results"])
    assert "not an objective" in salary_first["summary"]


def test_cost_of_living_ranking_is_labeled_derived() -> None:
    result = intelligence().state_opportunity("Electrical Engineers")
    assert result["status"] == "supported"
    assert result["results"]
    assert "derived" in result["summary"].lower()
    assert "40%" in result["formula"]
    assert all("regional_price_parity" in item for item in result["results"])


def test_degree_pathway_is_qualitative_not_placement_claim() -> None:
    ci = intelligence()
    search = ci.degree_search("electrical engineering", limit=5)
    assert search
    result = ci.degree_pathway(search[0]["cip_code"])
    assert result["results"]
    limitation = " ".join(result["limitations"]).lower()
    assert "not" in limitation and "placement" in limitation


def test_skill_bridge_has_transition_boundaries() -> None:
    result = intelligence().skill_bridge("Public Relations Specialists", "Political Scientists")
    assert result["status"] == "supported"
    assert result["source_confidence"]["label"] == "High"
    assert result["decision_confidence"]["label"] == "Medium"
    assert "does not measure" in result["decision_confidence"]["reason"]


def test_routing_regressions_for_software_and_what_does() -> None:
    engine = QueryEngine(get_store())
    expected = {
        "What is the salary for software developers?": "occupation_profile",
        "Which states pay software developers the most?": "highest_paying_states",
        "What is the job outlook for software developers?": "occupation_outlook",
        "What software do software developers use?": "software_tools",
        "What does a lawyer earn?": "occupation_profile",
        "What does a political scientist do?": "tasks",
    }
    for question, intent in expected.items():
        assert engine.answer(question).intent == intent
