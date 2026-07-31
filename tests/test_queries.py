from __future__ import annotations

import pytest

from careerproof.data_store import get_store
from careerproof.query_engine import QueryEngine


@pytest.fixture(scope="module")
def engine() -> QueryEngine:
    return QueryEngine(get_store())


@pytest.mark.parametrize("question", [
    "Which states pay nuclear engineers the most?",
    "What skills do public relations specialists need?",
    "Which broad bachelor's degree fields have the highest median earnings?",
    "What is the job outlook for political scientists?",
    "How much do lawyers earn in Maryland?",
    "Compare lawyers and political scientists.",
    "What tasks do public relations specialists perform?",
    "What software do broadcast technicians use?",
    "How do national wages compare by typical entry-level education?",
    "Which states have the highest median wage for bachelor's-level occupations?",
    "What are the 10 highest-paying occupations?",
    "Which occupations have the most annual openings?",
])
def test_supported_questions_return_evidence(engine: QueryEngine, question: str) -> None:
    result = engine.answer(question)
    assert result.status == "supported"
    assert result.rows
    assert result.sources
    assert result.evidence_id.startswith("CP-")
    assert result.evidence["calculation"]
    assert result.confidence.score >= 80


def test_nuclear_engineer_state_ranking_uses_real_bls_rows(engine: QueryEngine) -> None:
    result = engine.answer("Which states pay nuclear engineers the most?")
    assert result.rows[0]["state"] == "District of Columbia"
    assert result.rows[0]["median_annual_wage"] == 195190.0
    assert result.dataset == "BLS OEWS State"


def test_degree_ranking_uses_census_values(engine: QueryEngine) -> None:
    result = engine.answer("Which broad bachelor's degree fields have the highest median earnings?")
    assert result.rows[0]["degree_field"] == "Engineering"
    assert result.rows[0]["median_earnings"] == 113242
    assert result.rows[1]["degree_field"] == "Computers, Mathematics, and Statistics"


def test_lawyer_maryland_profile(engine: QueryEngine) -> None:
    result = engine.answer("How much do lawyers earn in Maryland?")
    assert result.rows[0]["state"] == "Maryland"
    assert result.rows[0]["occupation"] == "Lawyers"
    assert result.rows[0]["median_annual_wage"] == 139110.0


def test_projection_question(engine: QueryEngine) -> None:
    result = engine.answer("What is the job outlook for political scientists?")
    assert result.rows[0]["growth_percent"] == -3.1
    assert result.rows[0]["annual_openings"] == 500.0
    assert result.rows[0]["education"] == "Master's degree"


def test_dataset_selector_can_force_onet(engine: QueryEngine) -> None:
    result = engine.answer("nuclear engineers", dataset="onet")
    assert result.dataset == "O*NET 30.3"
    assert result.intent == "skills"


def test_evidence_id_is_reproducible(engine: QueryEngine) -> None:
    question = "What skills do public relations specialists need?"
    first = engine.answer(question)
    second = engine.answer(question)
    assert first.evidence_id == second.evidence_id
