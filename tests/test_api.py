from __future__ import annotations

from fastapi.testclient import TestClient

from careerproof.webapp import create_app


client = TestClient(create_app())


def test_home_page_renders_product_shell() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "CareerProof AI" in response.text
    assert "Real career data" in response.text
    assert "Official sources only" in response.text


def test_health_endpoint() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["stats"]["occupations"] == 830


def test_bootstrap_endpoint_has_sources_and_questions() -> None:
    payload = client.get("/api/bootstrap").json()
    assert len(payload["catalog"]["sources"]) == 6
    assert len(payload["question_catalog"]) == 6
    assert len(payload["featured_occupations"]) >= 8


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


def test_report_endpoint() -> None:
    response = client.post("/api/report", json={"question": "How much do lawyers earn nationally?", "dataset": "auto"})
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Evidence Report" in response.text
    assert "U.S. Bureau of Labor Statistics" in response.text
