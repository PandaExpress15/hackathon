from __future__ import annotations

from fastapi.testclient import TestClient

from careerproof.webapp import create_app


client = TestClient(create_app())


def test_home_page_renders_product_shell() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "CareerProof AI" in response.text
    assert "Plan your future" in response.text
    assert "Real career data" in response.text
    assert "Official sources only" in response.text
    assert "No synthetic job records" in response.text


def test_health_endpoint() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["stats"]["occupations"] == 830
    assert payload["stats"]["official_sources"] >= 8
    assert payload["stats"]["degree_occupation_links"] > 5000
    assert payload["stats"]["price_parity_geographies"] == 51


def test_stats_endpoint_matches_verified_coverage() -> None:
    response = client.get("/api/stats")
    assert response.status_code == 200
    payload = response.json()
    assert payload["occupations"] == 830
    assert payload["state_occupation_rows"] == 36168
    assert payload["degree_occupation_links"] == 5917
    assert payload["official_sources"] >= 8


def test_bootstrap_endpoint_has_sources_questions_and_planning_inputs() -> None:
    payload = client.get("/api/bootstrap").json()
    assert len(payload["catalog"]["sources"]) >= 8
    assert len(payload["question_catalog"]) >= 6
    assert len(payload["featured_occupations"]) >= 8
    assert "Electronics" in payload["interest_options"]
    assert payload["platform"]["promise"] == "Plan your future with AI. Not for AI."


def test_search_endpoint() -> None:
    payload = client.get("/api/search/occupations", params={"q": "nuclear engineer"}).json()
    assert payload["results"][0]["occupation_title"] == "Nuclear Engineers"


def test_ask_endpoint() -> None:
    response = client.post("/api/ask", json={"question": "What skills do nuclear engineers need?", "dataset": "auto"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "supported"
    assert payload["dataset"] == "O*NET 30.3"
    assert payload["rows"]
    assert payload["evidence_id"]


def test_report_endpoint() -> None:
    response = client.post("/api/report", json={"question": "How much do lawyers earn nationally?", "dataset": "auto"})
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Evidence Report" in response.text
    assert "U.S. Bureau of Labor Statistics" in response.text


def test_advanced_endpoints() -> None:
    universe = client.get("/api/universe", params={"limit": 4})
    assert universe.status_code == 200
    assert len(universe.json()["categories"]) == 8

    path = client.post(
        "/api/path-builder",
        json={
            "interests": ["Electronics", "Programming"],
            "skills": ["Python", "Arduino"],
            "education_max": "Bachelor's degree",
            "preferred_state": "Maryland",
            "salary_goal": 90000,
            "weights": {"interest_fit": 35, "salary": 20, "growth": 15, "openings": 10, "education": 10, "location": 10},
            "limit": 6,
        },
    )
    assert path.status_code == 200
    assert len(path.json()["results"]) == 6
    assert all("careerproof_score" in item for item in path.json()["results"])

    comparison = client.post(
        "/api/compare",
        json={"occupations": ["Nuclear Engineers", "Electrical Engineers", "Lawyers"], "preferred_state": "Maryland"},
    )
    assert comparison.status_code == 200
    assert len(comparison.json()["results"]) == 3

    degree = client.get("/api/degrees/search", params={"q": "electrical engineering", "limit": 5})
    assert degree.status_code == 200
    assert degree.json()["results"]


def test_diagnostic_passes_all_critical_checks() -> None:
    payload = client.get("/api/diagnostic").json()
    assert payload["status"] == "pass"
    assert all(item["passed"] for item in payload["checks"])
    assert all(item["passed"] for item in payload["routing"])
