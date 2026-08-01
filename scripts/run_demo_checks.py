from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from careerproof.data_store import get_store
from careerproof.intelligence import CareerIntelligence
from careerproof.query_engine import QueryEngine

QUESTION_CHECKS = [
    ("Which states pay nuclear engineers the most?", "supported"),
    ("What skills do public relations specialists need?", "supported"),
    ("Which broad bachelor's degree fields have the highest median earnings?", "supported"),
    ("What is the job outlook for political scientists?", "supported"),
    ("How much do lawyers earn in Maryland?", "supported"),
    ("Compare lawyers and political scientists.", "supported"),
    ("What tasks do public relations specialists perform?", "supported"),
    ("What software do broadcast technicians use?", "supported"),
    ("How do national wages compare by typical entry-level education?", "supported"),
    ("Which states have the highest median wage for bachelor's-level occupations?", "supported"),
    ("What bachelor's degree should I pursue for the highest pay after becoming a lawyer?", "refused"),
    ("Which company has the happiest employees?", "refused"),
]


def check(name: str, function: Callable[[], tuple[bool, dict[str, Any]]]) -> dict[str, Any]:
    try:
        passed, detail = function()
        error = None
    except Exception as exc:  # A diagnostic must report the failure instead of hiding it.
        passed, detail, error = False, {}, f"{type(exc).__name__}: {exc}"
    return {"name": name, "passed": bool(passed), "detail": detail, "error": error}


def main() -> int:
    store = get_store()
    engine = QueryEngine(store)
    intelligence = CareerIntelligence(store)
    question_results: list[dict[str, Any]] = []
    failures = 0

    print("CAREERPROOF QUESTION AND REFUSAL CHECKS")
    print("=" * 72)
    for number, (question, expected) in enumerate(QUESTION_CHECKS, start=1):
        result = engine.answer(question)
        passed = result.status == expected and bool(result.evidence_id)
        if expected == "supported":
            passed = passed and bool(result.rows) and bool(result.sources) and bool(result.evidence.get("calculation"))
        else:
            passed = passed and bool(result.limitations or result.suggestions)
        if not passed:
            failures += 1
        question_results.append({
            "number": number,
            "question": question,
            "expected": expected,
            "actual": result.status,
            "dataset": result.dataset,
            "intent": result.intent,
            "rows": len(result.rows),
            "confidence": f"{result.confidence.label} ({result.confidence.score})",
            "evidence_id": result.evidence_id,
            "headline": result.headline,
            "result": "PASS" if passed else "FAIL",
        })
        print(f"[{number:02d}] {'PASS' if passed else 'FAIL'} | {result.intent:<26} | {question}")

    def path_builder_check() -> tuple[bool, dict[str, Any]]:
        result = intelligence.path_builder(
            interests=["Electronics", "Programming", "Law"],
            skills=["Python", "Arduino", "Writing", "Problem Solving"],
            education_max="Doctoral or professional degree",
            preferred_state="Maryland",
            salary_goal=100000,
            weights={"interest_fit": 30, "salary": 25, "growth": 10, "openings": 10, "education": 10, "location": 15},
            limit=6,
        )
        components = {"interest_fit", "resilience", "salary", "growth", "openings", "education", "location", "stability"}
        passed = (
            result.get("status") == "supported"
            and len(result.get("results", [])) >= 6
            and all(set(item.get("score_components", {})) == components for item in result["results"])
            and all(item.get("roadmap", {}).get("actions") for item in result["results"])
            and "TF-IDF" in result.get("method", {}).get("text_matching", "")
            and bool(result.get("interpreted_request", {}).get("requires_confirmation"))
            and len(result.get("sensitivity", [])) >= 6
            and all(item.get("challenge") for item in result["results"])
        )
        return passed, {
            "results": len(result.get("results", [])),
            "top_match": result.get("results", [{}])[0].get("occupation_title"),
            "formula": result.get("formula"),
            "roadmaps": sum(bool(item.get("roadmap")) for item in result.get("results", [])),
            "score_components": sorted(components),
            "counterfactual_scenarios": len(result.get("sensitivity", [])),
            "challenge_panels": sum(bool(item.get("challenge")) for item in result.get("results", [])),
        }

    def compare_check() -> tuple[bool, dict[str, Any]]:
        careers = ["Nuclear Engineers", "Electrical Engineers", "Lawyers"]
        salary_first = intelligence.compare(
            careers,
            weights={"interest_fit": 0, "salary": 55, "growth": 5, "openings": 5, "education": 5, "location": 30},
            preferred_state="Maryland",
            user_skills=["Python", "Arduino", "Writing"],
        )
        openings_first = intelligence.compare(
            careers,
            weights={"interest_fit": 0, "salary": 5, "growth": 10, "openings": 55, "education": 25, "location": 5},
            preferred_state="Maryland",
            user_skills=["Python", "Arduino", "Writing"],
        )
        first_scores = [item.get("careerproof_score") for item in salary_first.get("results", [])]
        second_scores = [item.get("careerproof_score") for item in openings_first.get("results", [])]
        passed = (
            len(first_scores) == 3
            and len(second_scores) == 3
            and first_scores != second_scores
            and all(item.get("decision_confidence") for item in salary_first.get("results", []))
            and "not an objective" in salary_first.get("summary", "").lower()
        )
        return passed, {
            "careers": careers,
            "salary_first_top": salary_first.get("results", [{}])[0].get("occupation_title"),
            "openings_first_top": openings_first.get("results", [{}])[0].get("occupation_title"),
            "scores_changed": first_scores != second_scores,
        }

    def skill_bridge_check() -> tuple[bool, dict[str, Any]]:
        result = intelligence.skill_bridge("Public Relations Specialists", "Political Scientists")
        components = result.get("component_scores", {})
        passed = (
            result.get("status") == "supported"
            and {"skill_importance_readiness", "software_overlap", "task_similarity"}.issubset(components)
            and bool(result.get("skills_to_build"))
            and bool(result.get("next_steps"))
            and result.get("source_confidence", {}).get("label") == "High"
        )
        return passed, {
            "overall_score": result.get("overlap_score"),
            "component_scores": components,
            "largest_gaps": len(result.get("skills_to_build", [])),
        }

    def degree_check() -> tuple[bool, dict[str, Any]]:
        matches = intelligence.degree_search("electrical engineering", limit=5)
        if not matches:
            return False, {"matches": 0}
        result = intelligence.degree_pathway(matches[0]["cip_code"])
        limitations = " ".join(result.get("limitations", [])).lower()
        passed = bool(result.get("results")) and "placement" in limitations and "not" in limitations
        return passed, {
            "degree": result.get("degree"),
            "linked_occupations": len(result.get("results", [])),
            "qualitative_boundary_present": "placement" in limitations,
        }

    def state_opportunity_check() -> tuple[bool, dict[str, Any]]:
        result = intelligence.state_opportunity("Electrical Engineers")
        formula = result.get("formula", "")
        passed = (
            result.get("status") == "supported"
            and len(result.get("results", [])) >= 10
            and "derived" in result.get("summary", "").lower()
            and "40%" in formula
            and all("regional_price_parity" in row for row in result.get("results", []))
        )
        return passed, {
            "states": len(result.get("results", [])),
            "top_state": result.get("results", [{}])[0].get("state"),
            "formula": formula,
        }

    def source_coverage_check() -> tuple[bool, dict[str, Any]]:
        stats = store.stats()
        passed = (
            stats["official_sources"] >= 8
            and stats["occupations"] >= 800
            and stats["state_occupation_rows"] > 30000
            and stats["degree_occupation_links"] > 5000
            and stats["price_parity_geographies"] == 51
        )
        return passed, stats

    def routing_check() -> tuple[bool, dict[str, Any]]:
        expected = {
            "What is the salary for software developers?": "occupation_profile",
            "Which states pay software developers the most?": "highest_paying_states",
            "What is the job outlook for software developers?": "occupation_outlook",
            "What software do software developers use?": "software_tools",
            "What does a lawyer earn?": "occupation_profile",
            "What does a political scientist do?": "tasks",
        }
        actual = {question: engine.answer(question).intent for question in expected}
        return actual == expected, {"expected": expected, "actual": actual}

    workflow_checks = [
        check("Official data coverage", source_coverage_check),
        check("Ambiguous question routing", routing_check),
        check("Personalized Path Builder", path_builder_check),
        check("User-controlled Compare Lab", compare_check),
        check("Multi-signal Skill Bridge", skill_bridge_check),
        check("Qualitative Degree Pathways", degree_check),
        check("BLS + BEA state opportunity", state_opportunity_check),
    ]

    print("\nADVANCED WORKFLOW CHECKS")
    print("=" * 72)
    for index, item in enumerate(workflow_checks, start=1):
        if not item["passed"]:
            failures += 1
        print(f"[W{index:02d}] {'PASS' if item['passed'] else 'FAIL'} | {item['name']}")
        if item["error"]:
            print(f"      {item['error']}")

    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    total = len(QUESTION_CHECKS) + len(workflow_checks)
    output = {
        "generated_at": generated_at,
        "passed": total - failures,
        "total": total,
        "question_checks": question_results,
        "workflow_checks": workflow_checks,
    }
    (ROOT / "docs/demo_check_results.json").write_text(json.dumps(output, indent=2), encoding="utf-8")

    lines = [
        "# Testing Report",
        "",
        f"Generated from real executions on **{generated_at}** by `python scripts/run_demo_checks.py`.",
        "",
        "## Summary",
        "",
        f"- Total demonstration and workflow checks passed: **{output['passed']}/{output['total']}**",
        f"- Natural-language and refusal checks: **{sum(row['result'] == 'PASS' for row in question_results)}/{len(question_results)}**",
        f"- Advanced workflow checks: **{sum(item['passed'] for item in workflow_checks)}/{len(workflow_checks)}**",
        "- Bundled labor-market and education records: **eight official source families only**",
        "- Synthetic labor-market records: **0**",
        "- Automated unit and integration tests: run with `pytest -q`",
        "",
        "## Natural-language and refusal results",
        "",
        "| # | Question | Expected | Actual | Dataset | Rows | Confidence | Evidence ID | Result |",
        "| ---: | --- | --- | --- | --- | ---: | --- | --- | --- |",
    ]
    for row in question_results:
        lines.append(
            f"| {row['number']} | {row['question'].replace('|', '/')} | {row['expected']} | {row['actual']} | {row['dataset']} | {row['rows']} | {row['confidence']} | `{row['evidence_id']}` | {row['result']} |"
        )
    lines.extend([
        "",
        "## Advanced workflow results",
        "",
        "| Workflow | Result | Executed evidence |",
        "| --- | --- | --- |",
    ])
    for item in workflow_checks:
        detail = json.dumps(item["detail"], ensure_ascii=False).replace("|", "/")
        lines.append(f"| {item['name']} | {'PASS' if item['passed'] else 'FAIL'} | `{detail}` |")
    lines.extend([
        "",
        "## Notes",
        "",
        "- Values are calculated from bundled official source snapshots.",
        "- Evidence IDs are content-derived and change when the route, query plan, or returned rows change.",
        "- Path Builder, comparison, similarity, and location scores are labeled CareerProof-derived decision aids and expose their formulas.",
        "- Refusal checks confirm that the application does not invent employer happiness, hiring guarantees, or lawyer-specific causal degree outcomes.",
        "- Passing this script does not replace a browser demonstration; it verifies the underlying workflows that the interface calls.",
    ])
    (ROOT / "docs/TESTING_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nSummary: {output['passed']}/{output['total']} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
