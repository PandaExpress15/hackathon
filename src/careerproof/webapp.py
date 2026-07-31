from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .config import APP_TITLE, APP_VERSION, STATIC_DIR, TEMPLATES_DIR
from .data_store import get_store, safe_value
from .models import AskRequest
from .query_engine import QueryEngine
from .reporting import render_html_report


def create_app() -> FastAPI:
    app = FastAPI(title=APP_TITLE, version=APP_VERSION, docs_url="/api/docs", redoc_url=None)
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    templates = Jinja2Templates(directory=TEMPLATES_DIR)
    store = get_store()
    engine = QueryEngine(store)

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(request, "app.html", {"app_version": APP_VERSION})

    @app.get("/api/health")
    async def health() -> dict:
        return {"status": "ok", "app": APP_TITLE, "version": APP_VERSION, "stats": store.stats()}

    @app.get("/api/bootstrap")
    async def bootstrap() -> dict:
        featured_titles = [
            "Public Relations Specialists", "News Analysts, Reporters, and Journalists", "Broadcast Technicians",
            "Nuclear Engineers", "Political Scientists", "Lawyers", "Software Developers", "Registered Nurses",
        ]
        featured = []
        for title in featured_titles:
            code = store.title_to_code.get(title)
            if code:
                profile = store.occupation_by_code(code)
                if profile:
                    featured.append({
                        "soc_code": code,
                        "occupation_title": title,
                        "annual_median_wage_2025": profile.get("annual_median_wage_2025"),
                        "employment_change_percent_2024_2034": profile.get("employment_change_percent_2024_2034"),
                        "typical_entry_education": profile.get("typical_entry_education"),
                    })
        return {
            "stats": store.stats(),
            "catalog": store.catalog,
            "question_catalog": store.question_catalog,
            "featured_occupations": featured,
            "states": sorted(store.state_names),
        }

    @app.get("/api/search/occupations")
    async def search_occupations(q: str = Query(min_length=1, max_length=120), limit: int = Query(default=10, ge=1, le=25)) -> dict:
        return {"results": store.find_occupations(q, limit=limit)}

    @app.get("/api/occupation/{soc_code}")
    async def occupation(soc_code: str) -> dict:
        profile = store.occupation_profile(soc_code)
        if profile is None:
            raise HTTPException(status_code=404, detail="Occupation not found")
        states = store.state_wages.loc[store.state_wages["soc_code"].eq(soc_code)].dropna(subset=["annual_median_wage_2025"]).nlargest(10, "annual_median_wage_2025")
        profile["top_states_by_pay"] = [
            {"state": row.state_name, "median_annual_wage": safe_value(row.annual_median_wage_2025), "employment": safe_value(row.employment_2025)}
            for row in states.itertuples()
        ]
        return profile

    @app.post("/api/ask")
    async def ask(payload: AskRequest) -> JSONResponse:
        result = engine.answer(payload.question, payload.dataset)
        return JSONResponse(result.model_dump(mode="json"))

    @app.post("/api/report")
    async def report(payload: AskRequest) -> Response:
        result = engine.answer(payload.question, payload.dataset).model_dump(mode="json")
        html = render_html_report(result)
        return Response(content=html, media_type="text/html", headers={"Content-Disposition": "attachment; filename=careerproof-evidence-report.html"})

    @app.get("/api/catalog")
    async def catalog() -> dict:
        return store.catalog

    return app
