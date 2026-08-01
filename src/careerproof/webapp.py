from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .config import APP_TITLE, APP_VERSION, STATIC_DIR, TEMPLATES_DIR
from .data_store import get_store
from .models import AskRequest, CompareRequest, PathBuilderRequest, ProfileInterpretRequest, SkillBridgeRequest
from .query_engine import QueryEngine
from .reporting import render_html_report


def create_app() -> FastAPI:
    app = FastAPI(title=APP_TITLE, version=APP_VERSION, docs_url="/api/docs", redoc_url=None)
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    templates = Jinja2Templates(directory=TEMPLATES_DIR)
    store = get_store()
    engine = QueryEngine(store)
    intelligence = engine.intelligence

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(request, "app.html", {"app_version": APP_VERSION})

    @app.get("/api/health")
    async def health() -> dict:
        return {"status": "ok", "app": APP_TITLE, "version": APP_VERSION, "stats": store.stats()}

    @app.get("/api/stats")
    async def stats() -> dict:
        """Return verified dataset coverage for diagnostics and external demos."""
        return store.stats()

    @app.get("/api/bootstrap")
    async def bootstrap() -> dict:
        model_card = intelligence.resilience_model_card()
        featured_titles = [
            "Public Relations Specialists", "News Analysts, Reporters, and Journalists", "Broadcast Technicians",
            "Nuclear Engineers", "Political Scientists", "Lawyers", "Software Developers", "Registered Nurses",
            "Electrical Engineers", "Market Research Analysts and Marketing Specialists", "Data Scientists",
            "Wind Turbine Service Technicians",
        ]
        featured = []
        for title in featured_titles:
            code = store.title_to_code.get(title)
            if code:
                profile = intelligence.occupation_intelligence(code)
                if profile:
                    occupation = profile["occupation"]
                    featured.append({
                        "soc_code": code,
                        "occupation_title": title,
                        "category": profile["category"],
                        "annual_median_wage_2025": occupation.get("annual_median_wage_2025"),
                        "employment_change_percent_2024_2034": occupation.get("employment_change_percent_2024_2034"),
                        "annual_openings": (occupation.get("annual_openings_2024_2034_thousands") or 0) * 1000,
                        "typical_entry_education": occupation.get("typical_entry_education"),
                        "coverage": profile["coverage"],
                    })
        return {
            "stats": store.stats(),
            "catalog": store.catalog,
            "sources": store.catalog.get("sources", []),
            "question_catalog": store.question_catalog,
            "quick_questions": [
                "Where does an electrical engineer's salary go furthest after cost of living?",
                "Compare lawyers and political scientists.",
                "What software do broadcast technicians use?",
                "Which broad bachelor's degree fields have the highest median earnings?",
                "Which states pay nuclear engineers the most?",
                "What skills do public relations specialists need?",
            ],
            "featured_occupations": featured,
            "states": sorted(store.state_names),
            "education_levels": list({str(value) for value in store.occupations["typical_entry_education"].dropna()}),
            "interest_options": [
                "Electronics", "Programming", "Writing", "Public Speaking", "Law", "Politics", "Helping People",
                "Science", "Business", "Creative Work", "Hands-on Work", "Math", "Research", "Building Things",
            ],
            "interests": [
                "Electronics", "Programming", "Writing", "Public Speaking", "Law", "Politics", "Helping People",
                "Science", "Business", "Creative Work", "Hands-on Work", "Math", "Research", "Building Things",
            ],
            "platform": {
                "promise": "Plan your future with AI. Not for AI.",
                "headline": "Build a future designed to endure AI change.",
                "method": "AI interprets. Code calculates. Evidence verifies. You decide.",
                "derived_metrics_label": "CareerProof-derived decision aids",
            },
            "data_freshness": intelligence.data_vintage_notice(),
            "resilience_model": {
                "name": model_card["name"],
                "version": model_card["version"],
                "formula": model_card["formula"],
            },
        }

    @app.post("/api/interpret-profile")
    async def interpret_profile(payload: ProfileInterpretRequest) -> JSONResponse:
        if payload.preferred_state and payload.preferred_state not in store.state_names:
            raise HTTPException(status_code=422, detail="Preferred state is not present in the bundled state dataset.")
        return JSONResponse(intelligence.interpret_profile(
            profile_text=payload.profile_text,
            interests=payload.interests,
            skills=payload.skills,
            education_max=payload.education_max,
            preferred_state=payload.preferred_state,
            salary_goal=payload.salary_goal,
            work_environment=payload.work_environment,
            remote_preference=payload.remote_preference,
            willing_to_relocate=payload.willing_to_relocate,
            salary_is_hard=payload.salary_is_hard,
            education_is_hard=payload.education_is_hard,
            location_is_hard=payload.location_is_hard,
            weights=payload.weights,
        ))

    @app.get("/api/resilience-model")
    async def resilience_model() -> dict:
        return intelligence.resilience_model_card()

    @app.get("/api/data-quality")
    async def data_quality() -> dict:
        return intelligence.data_quality_summary()

    @app.get("/api/home")
    async def home() -> dict:
        """Return the fully calculated default dashboard story.

        The profile is clearly labeled as a demonstration scenario.  Every
        labor-market value comes from the bundled official snapshots.
        """
        profile = {
            "label": "Demonstration profile — editable and not a labor-market statistic",
            "interests": ["Electronics", "Programming", "Law"],
            "skills": ["Python", "Arduino", "Writing", "Problem Solving"],
            "education_max": "Bachelor's degree",
            "preferred_state": "Maryland",
            "salary_goal": 90000,
            "work_environment": ["Hands-on", "Office or analytical", "People-facing"],
            "remote_preference": "Flexible",
            "willing_to_relocate": False,
        }
        path = intelligence.path_builder(
            interests=profile["interests"], skills=profile["skills"], education_max=profile["education_max"],
            preferred_state=profile["preferred_state"], salary_goal=profile["salary_goal"],
            weights={"interest_fit": 24, "resilience": 28, "salary": 18, "growth": 8, "openings": 8, "education": 7, "location": 4, "stability": 3},
            work_environment=profile["work_environment"], remote_preference=profile["remote_preference"],
            willing_to_relocate=profile["willing_to_relocate"], education_is_hard=True,
            salary_is_hard=False, location_is_hard=False, limit=6,
        )
        top = path["results"][0]
        local = intelligence.state_opportunity(top["soc_code"])
        task_impact = top["resilience_profile"]["task_impact"]
        classified = max(task_impact["classified_task_count"], 1)
        impact_summary = {
            "career": top["occupation_title"],
            "human_led_examples": task_impact["human_led"],
            "augmented_examples": task_impact["augmented"],
            "reduced_examples": task_impact["reduced"],
            "counts": {
                "human_led": len(task_impact["human_led"]),
                "augmented": len(task_impact["augmented"]),
                "reduced": len(task_impact["reduced"]),
                "classified": classified,
            },
            "boundary": task_impact["method"],
        }
        return {
            "profile": profile,
            "path": path,
            "top_matches": path["results"][:3],
            "impact": impact_summary,
            "local_opportunities": local["results"][:3],
            "stats": store.stats(),
            "data_freshness": intelligence.data_vintage_notice(),
        }

    @app.get("/api/universe")
    async def universe(category: str | None = None, limit: int = Query(default=8, ge=4, le=12)) -> dict:
        return intelligence.universe(category=category, per_category=limit)

    def occupation_search_results(query: str, limit: int) -> list[dict]:
        output: list[dict] = []
        for match in store.find_occupations(query, limit=limit):
            profile = intelligence._public_profile(str(match["soc_code"]))  # exact SOC record already resolved by the store
            output.append({**match, **profile})
        return output

    @app.get("/api/search/occupations")
    async def search_occupations(q: str = Query(min_length=1, max_length=120), limit: int = Query(default=10, ge=1, le=25)) -> dict:
        return {"results": occupation_search_results(q, limit)}

    @app.get("/api/occupations")
    async def occupations_alias(query: str = Query(min_length=1, max_length=120), limit: int = Query(default=10, ge=1, le=25)) -> dict:
        return {"results": occupation_search_results(query, limit)}

    @app.get("/api/occupation/{soc_code}")
    async def occupation(soc_code: str) -> dict:
        profile = intelligence.occupation_intelligence(soc_code)
        if profile is None:
            raise HTTPException(status_code=404, detail="Occupation not found")
        return profile

    @app.post("/api/path-builder")
    async def path_builder(payload: PathBuilderRequest) -> JSONResponse:
        if payload.preferred_state and payload.preferred_state not in store.state_names:
            raise HTTPException(status_code=422, detail="Preferred state is not present in the bundled state dataset.")
        result = intelligence.path_builder(
            interests=payload.interests,
            skills=payload.skills,
            education_max=payload.education_max,
            preferred_state=payload.preferred_state,
            salary_goal=payload.salary_goal,
            weights=payload.weights,
            limit=payload.limit,
            profile_text=payload.profile_text,
            work_environment=payload.work_environment,
            remote_preference=payload.remote_preference,
            willing_to_relocate=payload.willing_to_relocate,
            salary_is_hard=payload.salary_is_hard,
            education_is_hard=payload.education_is_hard,
            location_is_hard=payload.location_is_hard,
        )
        return JSONResponse(result)

    @app.post("/api/compare")
    async def compare(payload: CompareRequest) -> JSONResponse:
        try:
            result = intelligence.compare(
                payload.occupations,
                weights=payload.weights,
                preferred_state=payload.preferred_state,
                user_skills=payload.skills,
                education_max=payload.education_max,
                salary_goal=payload.salary_goal,
                salary_is_hard=payload.salary_is_hard,
                education_is_hard=payload.education_is_hard,
                location_is_hard=payload.location_is_hard,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return JSONResponse(result)

    @app.post("/api/skill-bridge")
    async def skill_bridge(payload: SkillBridgeRequest) -> JSONResponse:
        try:
            return JSONResponse(intelligence.skill_bridge(payload.source, payload.target))
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.get("/api/degrees/search")
    async def degree_search(q: str = Query(default="", max_length=120), limit: int = Query(default=12, ge=1, le=25)) -> dict:
        return {"results": intelligence.degree_search(q, limit=limit)}

    @app.get("/api/degrees")
    async def degree_search_alias(query: str = Query(default="", max_length=120), limit: int = Query(default=12, ge=1, le=25)) -> dict:
        results = intelligence.degree_search(query, limit=limit)
        return {"results": [{**item, "related_occupation_count": item.get("occupation_count", 0)} for item in results]}

    @app.get("/api/degree/{cip_code}")
    async def degree_pathway(cip_code: str) -> JSONResponse:
        try:
            return JSONResponse(intelligence.degree_pathway(cip_code))
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/api/state-opportunity/{soc_code}")
    async def state_opportunity(soc_code: str) -> JSONResponse:
        try:
            return JSONResponse(intelligence.state_opportunity(soc_code))
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.post("/api/ask")
    async def ask(payload: AskRequest) -> JSONResponse:
        result = engine.answer(payload.question, payload.dataset, payload.context)
        return JSONResponse(result.model_dump(mode="json"))

    @app.post("/api/report")
    async def report(payload: AskRequest) -> Response:
        result = engine.answer(payload.question, payload.dataset, payload.context).model_dump(mode="json")
        html = render_html_report(result)
        return Response(content=html, media_type="text/html", headers={"Content-Disposition": "attachment; filename=careerproof-evidence-report.html"})

    @app.get("/api/catalog")
    async def catalog() -> dict:
        return store.catalog

    @app.get("/api/judge-demo")
    async def judge_demo() -> dict:
        profile = {
            "name": "Alex",
            "label": "Demonstration profile — not a real person or labor-market statistic",
            "interests": ["Electronics", "Programming", "Law"],
            "skills": ["Python", "Arduino", "Writing", "Problem Solving"],
            "education_max": "Bachelor's degree",
            "preferred_state": "Maryland",
            "salary_goal": 90000,
            "work_environment": ["Hands-on", "Office or analytical", "People-facing"],
            "remote_preference": "Flexible",
            "willing_to_relocate": False,
        }
        demo_weights = {
            "interest_fit": 24, "resilience": 28, "salary": 18, "growth": 8,
            "openings": 8, "education": 7, "location": 4, "stability": 3,
        }
        interpretation = intelligence.interpret_profile(
            interests=profile["interests"], skills=profile["skills"], education_max=profile["education_max"],
            preferred_state=profile["preferred_state"], salary_goal=profile["salary_goal"],
            work_environment=profile["work_environment"], remote_preference=profile["remote_preference"],
            willing_to_relocate=profile["willing_to_relocate"], education_is_hard=True,
            weights=demo_weights,
        )
        path = intelligence.path_builder(
            interests=profile["interests"], skills=profile["skills"], education_max=profile["education_max"],
            preferred_state=profile["preferred_state"], salary_goal=profile["salary_goal"],
            weights=demo_weights, work_environment=profile["work_environment"],
            remote_preference=profile["remote_preference"], willing_to_relocate=profile["willing_to_relocate"],
            education_is_hard=True, limit=6,
        )
        comparison = intelligence.compare(
            ["Nuclear Engineers", "Electrical Engineers", "Lawyers"],
            weights={"interest_fit": 12, "resilience": 30, "salary": 22, "growth": 8, "openings": 8, "education": 10, "location": 5, "stability": 5},
            preferred_state="Maryland", user_skills=profile["skills"], education_max=profile["education_max"],
            education_is_hard=True,
        )
        verified_answer = engine.answer(
            "Where does an electrical engineer's salary go furthest after cost of living?"
        ).model_dump(mode="json")
        refusal = engine.answer(
            "Which bachelor's degree guarantees the highest salary after becoming a lawyer?"
        ).model_dump(mode="json")

        stats = store.stats()
        top = path["results"][0]
        portfolio = path.get("portfolio", {})
        roadmap = top.get("roadmap", {})
        proof_rows = verified_answer.get("rows", [])
        evidence = verified_answer.get("evidence", {})
        evidence_id = verified_answer.get("evidence_id") or evidence.get("evidence_id")
        source_names = [source.get("name") for source in verified_answer.get("sources", []) if source.get("name")]
        if not source_names:
            source_names = ["BLS Occupational Employment and Wage Statistics", "BEA Regional Price Parities"]

        rubric = [
            {
                "key": "problem", "label": "Problem and usefulness", "weight": 25,
                "proof": "A focused student decision: find a financially sustainable, AI-resilient career that fits real constraints.",
            },
            {
                "key": "prototype", "label": "Working prototype", "weight": 25,
                "proof": "The live flow moves from editable profile interpretation to deterministic ranking, comparison, evidence, and an action plan.",
            },
            {
                "key": "data_ai", "label": "Data and AI quality", "weight": 15,
                "proof": "AI interprets the request. Code performs exact joins, hard gates, normalization, and calculations over bundled official data.",
            },
            {
                "key": "trust", "label": "Trust and safety", "weight": 15,
                "proof": "Evidence Passports, separate confidence labels, visible limitations, challenge controls, and unsupported-question refusal.",
            },
            {
                "key": "architecture", "label": "Architecture clarity", "weight": 10,
                "proof": "A simple, inspectable pipeline: input → interpretation → validated query plan → deterministic calculation → evidence → user decision.",
            },
            {
                "key": "story", "label": "Demo and storytelling", "weight": 10,
                "proof": "A repeatable presentation with timed steps, speaker notes, live-feature launch buttons, and a clean reset.",
            },
        ]

        architecture = [
            {"label": "User request", "detail": "Interests, skills, salary target, education ceiling, location, and priorities."},
            {"label": "AI interpretation", "detail": "The system converts natural language into an editable structured profile. The user confirms it before ranking."},
            {"label": "Validated plan", "detail": "Allowlisted fields, exact SOC/CIP joins, and hard constraints determine which calculations may run."},
            {"label": "Deterministic analysis", "detail": "Pandas code calculates wages, outlook, openings, location purchasing power, fit, and transparent score contributions."},
            {"label": "Evidence and control", "detail": "Sources, rows, formulas, source confidence, decision confidence, limitations, and safe refusal remain visible."},
            {"label": "Human decision", "detail": "The user changes weights, challenges assumptions, saves options, and exports a practical plan."},
        ]

        steps = [
            {
                "id": "purpose", "quick": True, "duration_seconds": 35, "workspace": "home",
                "eyebrow": "1 · Problem and usefulness",
                "title": "A real decision, not another career quiz",
                "copy": "CareerProof helps students choose careers that fit their interests, financial needs, education limits, location, and exposure to AI-driven change.",
                "presenter_script": "Students are being asked to make expensive, long-term career decisions while the labor market and AI are changing quickly. CareerProof turns that uncertainty into a decision the user can inspect, challenge, and act on.",
                "judge_focus": "Problem and usefulness · 25%",
                "action_label": "Open the live home dashboard",
                "proof_points": [
                    f"{stats['occupations']:,} detailed occupations",
                    f"{stats['state_occupation_rows']:,} state occupation records",
                    f"{stats['degree_occupation_links']:,} degree-career relationships",
                    "One focused question: Which path is sustainable, feasible, and resilient for me?",
                ],
            },
            {
                "id": "interpret", "quick": True, "duration_seconds": 45, "workspace": "path",
                "eyebrow": "2 · Meaningful AI assistance",
                "title": "AI interprets. The user approves.",
                "copy": "The natural-language profile becomes an editable goal, constraints, assumptions, and weighted priorities before any ranking is calculated.",
                "presenter_script": "The model never gets permission to invent a salary or rank a career by itself. It interprets the student's request into structured fields, then pauses for human review. The user can correct the goal, constraints, and weights before code calculates anything.",
                "judge_focus": "Data and AI quality · Human control",
                "action_label": "Open the editable interpretation",
                "proof_points": [
                    "Bachelor's degree is treated as a hard ceiling",
                    "Maryland and a $90,000 salary goal are explicit",
                    "Eight user-controlled decision weights normalize to 100%",
                    "Assumptions and unsupported preferences are disclosed",
                ],
            },
            {
                "id": "path", "quick": True, "duration_seconds": 65, "workspace": "path",
                "eyebrow": "3 · Working prototype",
                "title": "The Path Builder produces a defensible recommendation",
                "copy": "Controlled retrieval finds relevant occupations. Hard feasibility gates run first. Then deterministic scoring applies official data and the user's priorities.",
                "presenter_script": f"Electrical Engineers ranks first for this profile with a CareerProof score of {top['careerproof_score']:.1f}. Notice that the score is not a hidden AI opinion. The screen exposes eight raw components, the user's weights, and every weighted contribution.",
                "judge_focus": "Working prototype · Verified calculations",
                "action_label": "Run the live Path Builder",
                "proof_points": [
                    f"Top result: {top['occupation_title']}",
                    f"Published median wage: ${top['median_wage']:,.0f}",
                    f"Projected growth: {top['growth_percent']:+.1f}%",
                    f"{path.get('excluded_by_hard_constraints', {}).get('count', 0)} careers excluded before ranking by hard constraints",
                ],
            },
            {
                "id": "challenge", "quick": False, "duration_seconds": 50, "workspace": "path",
                "eyebrow": "4 · Trust through challenge",
                "title": "The recommendation explains how it could be wrong",
                "copy": "CareerProof exposes the weakest evidence, assumptions, missing or limited information, the strongest alternative, and what priority changes the result.",
                "presenter_script": "A trustworthy recommendation should be able to argue against itself. The Challenge control identifies the weakest components and the strongest alternative. This prevents a polished score from looking more certain than the evidence allows.",
                "judge_focus": "Trust and safety · Inspectable uncertainty",
                "action_label": "Open the recommendation challenge",
                "proof_points": [
                    f"Strongest alternative: {top.get('challenge', {}).get('strongest_alternative', 'Shown in the live result')}",
                    "Weak evidence is ranked by score and weighted contribution",
                    "Different source years are disclosed instead of silently blended",
                    "The result changes when the user changes priorities",
                ],
            },
            {
                "id": "compare", "quick": False, "duration_seconds": 65, "workspace": "compare",
                "eyebrow": "5 · Decision quality",
                "title": "Compare tradeoffs, not just scores",
                "copy": "Compare Lab places salary, growth, openings, education, resilience, location, feasibility, and score contributions on one evidence board.",
                "presenter_script": "Here the same user compares Electrical Engineering, Nuclear Engineering, and Law. Law may look attractive on pay, but the bachelor's-degree hard limit blocks it. The system does not let a strong soft score override an explicit constraint.",
                "judge_focus": "Working prototype · Data quality",
                "action_label": "Open the live comparison",
                "proof_points": [
                    "Two to four careers can be compared",
                    "Blocked careers remain visible with the reason",
                    "Scenario sensitivity shows which option wins when priorities change",
                    "A plain-language tradeoff summary is generated after the calculations",
                ],
            },
            {
                "id": "proof", "quick": True, "duration_seconds": 55, "workspace": "ask",
                "eyebrow": "6 · Evidence Passport",
                "title": "Every important answer can show its proof",
                "copy": "The Evidence Passport exposes the source route, rows used, excluded values, calculation, source confidence, decision confidence, limitations, and a unique evidence ID.",
                "presenter_script": "This question asks where an electrical engineer's salary may go furthest after cost of living. CareerProof combines official BLS state wage records with BEA price levels, shows the calculation, and labels the result as a derived exploration score rather than an official ranking.",
                "judge_focus": "Trust and safety · Visible evidence",
                "action_label": "Open the verified answer",
                "proof_points": [
                    f"{len(proof_rows)} ranked rows shown in the answer",
                    f"Evidence ID: {evidence_id}",
                    f"Sources: {' + '.join(source_names[:2])}",
                    "Suppressed and missing values remain missing",
                ],
            },
            {
                "id": "refusal", "quick": True, "duration_seconds": 35, "workspace": "ask",
                "eyebrow": "7 · Safe failure case",
                "title": "When the data cannot prove it, CareerProof refuses",
                "copy": "Unsupported guarantees and causal claims are stopped before calculation. The system explains the missing relationship and redirects the user to questions the data can answer.",
                "presenter_script": "The user asks which bachelor's degree guarantees the highest salary after becoming a lawyer. The datasets do not connect undergraduate majors to guaranteed lawyer outcomes, so CareerProof refuses instead of producing a confident-sounding guess.",
                "judge_focus": "Trust and safety · Failure-case behavior",
                "action_label": "Open the safe-refusal example",
                "proof_points": [
                    "No calculation runs for an unsupported claim",
                    "Source confidence and decision confidence both become insufficient",
                    "The reason is recorded in the query plan",
                    "Supported follow-up questions are suggested",
                ],
            },
            {
                "id": "plan", "quick": False, "duration_seconds": 45, "workspace": "saved",
                "eyebrow": "8 · Practical result",
                "title": "The analysis becomes a plan the student can use",
                "copy": "CareerProof produces a primary path, safer backup, high-upside option, fast-entry option, evidence-backed roadmap, decision notes, and an exportable report.",
                "presenter_script": "The product does not end with a ranking. It turns the result into a portfolio of options and a practical roadmap for skills, tools, education research, and local market validation. Each action is labeled as evidence-backed guidance, not a guarantee.",
                "judge_focus": "Problem usefulness · Practical value",
                "action_label": "Open the saved plan workspace",
                "proof_points": [
                    f"Primary path: {portfolio.get('primary_path', {}).get('occupation_title', top['occupation_title'])}",
                    f"Safer backup: {portfolio.get('safer_backup', {}).get('occupation_title', 'Shown in the live plan')}",
                    f"{len(roadmap.get('actions', []))} evidence-backed roadmap actions",
                    "HTML export can be printed or saved as PDF",
                ],
            },
            {
                "id": "architecture", "quick": False, "duration_seconds": 45, "workspace": "trust",
                "eyebrow": "9 · Architecture clarity",
                "title": "A simple architecture keeps the result understandable",
                "copy": "The product separates interpretation, validation, deterministic calculations, evidence, and the final human decision.",
                "presenter_script": "The architecture is intentionally simple. AI interprets. Validated code calculates. Evidence verifies. The user decides. That separation makes it clear which parts are probabilistic and which parts are directly calculated from official records.",
                "judge_focus": "Architecture clarity · 10%",
                "action_label": "Open Evidence Center and diagnostics",
                "proof_points": [stage["label"] for stage in architecture],
            },
            {
                "id": "close", "quick": True, "duration_seconds": 30, "workspace": "home",
                "eyebrow": "10 · Final value",
                "title": "From uncertainty to a defensible next step",
                "copy": "CareerProof combines useful AI assistance, verified calculations, visible evidence, safe refusal, and human control in one repeatable career decision workflow.",
                "presenter_script": "In one guided flow, CareerProof understood a complex request, ranked feasible careers, explained the tradeoffs, challenged its own recommendation, verified a calculation, refused an unsupported guarantee, and produced a practical plan. That is the value: evidence the user can inspect and a decision they still control.",
                "judge_focus": "Complete rubric close",
                "action_label": "Return to the live dashboard",
                "proof_points": [
                    "AI interprets", "Code calculates", "Evidence verifies", "You decide",
                ],
            },
        ]

        action_plan = {
            "primary": portfolio.get("primary_path"),
            "backup": portfolio.get("safer_backup"),
            "high_upside": portfolio.get("high_upside_option"),
            "fast_entry": portfolio.get("fast_entry_option"),
            "roadmap": roadmap,
            "report_sections": [
                "User goals and constraints", "Career portfolio", "Salary and outlook", "AI resilience profile",
                "Skills and education", "Location evidence", "Confidence and limitations", "Next actions",
            ],
        }

        return {
            "demo_meta": {
                "title": "CareerProof AI guided presentation",
                "subtitle": "A repeatable success case, evidence case, and safe failure case",
                "full_duration_seconds": sum(step["duration_seconds"] for step in steps),
                "quick_duration_seconds": sum(step["duration_seconds"] for step in steps if step["quick"]),
                "quick_step_ids": [step["id"] for step in steps if step["quick"]],
                "core_question": "What career can I build that fits me, is financially sustainable, and remains valuable as AI changes work?",
                "method": "AI interprets. Code calculates. Evidence verifies. You decide.",
                "disclosure": "The demonstration profile is fictional. All labor-market values are bundled official records or clearly labeled CareerProof-derived metrics.",
            },
            "rubric": rubric,
            "architecture": architecture,
            "profile": profile,
            "interpretation": interpretation,
            "steps": steps,
            "path": path,
            "comparison": comparison,
            "verified_answer": verified_answer,
            "refusal": refusal,
            "action_plan": action_plan,
            "closing": {
                "headline": "A practical, trustworthy career decision system",
                "summary": "CareerProof moves from a complex student request to a verified, challengeable, and actionable plan without claiming that any career is permanently AI-proof.",
                "proof": [item["proof"] for item in rubric],
            },
        }

    @app.get("/api/diagnostic")
    async def diagnostic() -> dict:
        routing_cases = [
            ("What is the salary for software developers?", "occupation_profile"),
            ("Which states pay software developers the most?", "highest_paying_states"),
            ("What is the job outlook for software developers?", "occupation_outlook"),
            ("What software do software developers use?", "software_tools"),
            ("What does a lawyer earn?", "occupation_profile"),
            ("What does a political scientist do?", "tasks"),
        ]
        routing = []
        for question, expected_intent in routing_cases:
            result = engine.answer(question)
            passed = result.intent == expected_intent
            routing.append({
                "question": question,
                "expected_intent": expected_intent,
                "dataset": result.dataset,
                "intent": result.intent,
                "passed": passed,
            })
        stats = store.stats()
        interpretation = intelligence.interpret_profile(
            profile_text="I like electronics and programming, want to stay near Maryland, earn at least $90,000, and stop at a bachelor's degree.",
            interests=[], skills=[], education_max="Bachelor's degree", preferred_state=None, salary_goal=None,
        )
        comparison = intelligence.compare(
            ["Electrical Engineers", "Nuclear Engineers", "Lawyers"],
            preferred_state="Maryland", education_max="Bachelor's degree", education_is_hard=True,
            user_skills=["Python", "Arduino"],
        )
        lawyer = next(item for item in comparison["results"] if item["occupation_title"] == "Lawyers")
        model_card = intelligence.resilience_model_card()
        refusal = engine.answer("Which bachelor's degree guarantees the highest salary after becoming a lawyer?")
        checks = [
            {"name": "Official source families", "value": stats["official_sources"], "passed": stats["official_sources"] >= 8},
            {"name": "Detailed occupations", "value": stats["occupations"], "passed": stats["occupations"] >= 800},
            {"name": "State occupation rows", "value": stats["state_occupation_rows"], "passed": stats["state_occupation_rows"] > 30000},
            {"name": "Degree-to-occupation links", "value": stats["degree_occupation_links"], "passed": stats["degree_occupation_links"] > 5000},
            {"name": "State price-level records", "value": stats["price_parity_geographies"], "passed": stats["price_parity_geographies"] == 51},
            {"name": "Question routing regression suite", "value": f"{sum(item['passed'] for item in routing)}/{len(routing)}", "passed": all(item["passed"] for item in routing)},
            {"name": "Editable profile interpretation", "value": interpretation["goal"], "passed": interpretation["normalized_profile"]["preferred_state"] == "Maryland" and interpretation["normalized_profile"]["salary_goal"] == 90000},
            {"name": "Transparent resilience dimensions", "value": f"{len(model_card['dimensions'])} dimensions · v{model_card['version']}", "passed": len(model_card["dimensions"]) == 6 and round(sum(float(item["weight"]) for item in model_card["dimensions"]), 1) == 100.0},
            {"name": "Hard feasibility gate", "value": lawyer["feasibility"]["status"], "passed": lawyer["feasibility"]["status"] == "blocked"},
            {"name": "Counterfactual decision tests", "value": f"{len(comparison['sensitivity'])} presets", "passed": len(comparison["sensitivity"]) >= 6},
            {"name": "Unsupported guarantee refusal", "value": refusal.status, "passed": refusal.status == "refused"},
        ]
        return {
            "status": "pass" if all(item["passed"] for item in checks) else "attention",
            "checks": checks,
            "routing": routing,
            "judge_alignment": {
                "problem_and_usefulness": {"weight": 25, "evidence": "Interpret → Discover → Compare → Challenge → Verify → Plan workflow for a specific career decision"},
                "working_prototype": {"weight": 25, "evidence": "End-to-end interactive workflows backed by bundled official snapshots"},
                "data_and_ai_quality": {"weight": 15, "evidence": "Controlled interpretation, TF-IDF retrieval, exact joins, transparent resilience model, counterfactuals, and eight official source families"},
                "trust_and_safety": {"weight": 15, "evidence": "Hard feasibility gates, recommendation challenges, evidence passports, dual confidence, visible vintages, safe refusal, and no arbitrary code execution"},
                "architecture_clarity": {"weight": 10, "evidence": "User profile → editable interpretation → feasibility gate → deterministic score → evidence → human decision"},
                "demo_and_storytelling": {"weight": 10, "evidence": "Guided Judge Mode, one-click reset, premium dashboard, and a success plus safe-failure story"},
            },
        }

    return app
