from __future__ import annotations

import pytest

from careerproof.data_store import get_store


@pytest.mark.parametrize("title", [
    "Public Relations Specialists",
    "News Analysts, Reporters, and Journalists",
    "Broadcast Technicians",
    "Nuclear Engineers",
    "Political Scientists",
    "Lawyers",
    "Software Developers",
    "Registered Nurses",
    "Mechanical Engineers",
    "Electrical Engineers",
    "Communications Teachers, Postsecondary",
])
def test_broad_occupation_coverage(title: str) -> None:
    store = get_store()
    rows = store.occupations.loc[store.occupations["occupation_title"].eq(title)]
    assert len(rows) == 1
    assert rows.iloc[0]["soc_code"]


@pytest.mark.parametrize("query,expected", [
    ("mass communications", "Public Relations Specialists"),
    ("nuclear engineering", "Nuclear Engineers"),
    ("political science", "Political Scientists"),
    ("attorney", "Lawyers"),
    ("journalist", "News Analysts, Reporters, and Journalists"),
    ("software engineer", "Software Developers"),
])
def test_alias_search(query: str, expected: str) -> None:
    match = get_store().best_occupation(query)
    assert match is not None
    assert match["occupation_title"] == expected


def test_unified_profile_contains_onet_and_bls_data() -> None:
    store = get_store()
    code = store.title_to_code["Nuclear Engineers"]
    profile = store.occupation_profile(code)
    assert profile is not None
    assert profile["occupation"]["annual_median_wage_2025"] > 100000
    assert profile["occupation"]["typical_entry_education"] == "Bachelor's degree"
    assert len(profile["skills"]) >= 5
    assert len(profile["tasks"]) >= 5
