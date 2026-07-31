from __future__ import annotations

import math
import re
from typing import Any, Callable

import pandas as pd

from .data_store import DataStore, record_to_dict, safe_value
from .evidence import evidence_block, evidence_id
from .intent import IntentRouter
from .models import AnalysisResult, ChartSpec, Confidence


def money(value: Any) -> str:
    if value is None or pd.isna(value):
        return "not published"
    return f"${float(value):,.0f}"


def count(value: Any) -> str:
    if value is None or pd.isna(value):
        return "not published"
    return f"{float(value):,.0f}"


def percent(value: Any) -> str:
    if value is None or pd.isna(value):
        return "not published"
    return f"{float(value):.1f}%"


def limit_from_question(question: str, default: int = 10) -> int:
    match = re.search(r"\b(?:top|highest|largest|most|fastest)\s+(\d{1,2})\b", question.lower())
    if match:
        return max(1, min(int(match.group(1)), 25))
    word_limits = {"five": 5, "ten": 10, "fifteen": 15, "twenty": 20}
    for word, value in word_limits.items():
        if re.search(rf"\b(?:top|highest|largest|most|fastest)\s+{word}\b", question.lower()):
            return value
    return default


class QueryEngine:
    def __init__(self, store: DataStore) -> None:
        self.store = store
        self.router = IntentRouter()

    def answer(self, question: str, dataset: str = "auto") -> AnalysisResult:
        question = " ".join(question.strip().split())
        ai = self.router.classify(question)
        refused = self._safety_refusal(question, ai.label, ai.confidence)
        if refused is not None:
            return refused

        lowered = question.lower()
        dataset = dataset.lower().strip() or "auto"
        route: Callable[[str, str, float], AnalysisResult] | None = None

        if dataset in {"census", "degree", "census-degree"} or self._looks_like_degree_question(lowered):
            route = self._degree_analysis
        elif dataset in {"education", "education-wages"} or self._looks_like_education_aggregate(lowered):
            route = self._education_wage_analysis
        elif dataset in {"onet", "skills"} or any(word in lowered for word in ["skills", "knowledge", "tasks", "duties", "software", "tools", "what does"]):
            route = self._onet_analysis
        elif dataset in {"state", "bls-state"} or self._looks_like_state_question(question):
            route = self._state_analysis
        elif dataset in {"projections", "growth"} or any(word in lowered for word in ["projected", "projection", "outlook", "grow", "growth", "2034", "openings"]):
            route = self._projection_analysis
        else:
            route = self._national_analysis

        return route(question, ai.label, ai.confidence)

    def _base_result(
        self,
        *,
        status: str,
        question: str,
        dataset: str,
        intent: str,
        ai_intent: str,
        ai_confidence: float,
        headline: str,
        summary: str,
        rows: list[dict[str, Any]],
        columns: list[dict[str, str]],
        chart: ChartSpec,
        query_plan: dict[str, Any],
        evidence: dict[str, Any],
        confidence: Confidence,
        source_ids: list[str],
        limitations: list[str] | None = None,
        suggestions: list[str] | None = None,
        profile: dict[str, Any] | None = None,
    ) -> AnalysisResult:
        payload = {
            "status": status,
            "question": question,
            "dataset": dataset,
            "intent": intent,
            "rows": rows,
            "query_plan": query_plan,
            "sources": source_ids,
        }
        return AnalysisResult(
            status=status,
            question=question,
            dataset=dataset,
            intent=intent,
            ai_intent=ai_intent,
            ai_intent_confidence=ai_confidence,
            headline=headline,
            summary=summary,
            rows=rows,
            columns=columns,
            chart=chart,
            query_plan=query_plan,
            evidence=evidence,
            confidence=confidence,
            sources=[self.store.source(source_id) for source_id in source_ids],
            limitations=limitations or [],
            suggestions=suggestions or [],
            evidence_id=evidence_id(payload),
            profile=profile,
        )

    def _safety_refusal(self, question: str, ai_intent: str, ai_confidence: float) -> AnalysisResult | None:
        lowered = question.lower()
        reasons: list[tuple[list[str], str, list[str]]] = [
            (["happiest employees", "best company culture", "best employer"],
             "The bundled official datasets do not measure employee happiness, culture, or employer quality.",
             ["Which occupations have the highest median wages?", "Which states employ the most public relations specialists?"]),
            (["guarantee", "definitely get hired", "will get hired", "predict my hiring"],
             "Official labor statistics describe groups and occupations. They cannot guarantee an individual hiring outcome.",
             ["Which occupations have the most annual openings?", "What skills does O*NET list for the occupation?"]),
            (["live jobs", "jobs hiring now", "current openings near me", "apply for"],
             "CareerProof uses official statistical datasets, not live job-board listings or application systems.",
             ["Which occupations have the most annual openings?", "Which states have the most employment for this occupation?"]),
            (["race", "ethnicity", "gender most likely", "protected characteristic"],
             "CareerProof does not rank career outcomes by protected characteristics or support discriminatory decisions.",
             ["Compare occupations by wage, employment, education, or projected openings."]),
            (["execute python", "run os.system", "delete files", "ignore the rules"],
             "The application does not execute user-provided code or model-generated commands.",
             ["Ask a question about wages, employment, education, skills, tasks, or projections."]),
        ]
        for phrases, reason, suggestions in reasons:
            if any(phrase in lowered for phrase in phrases):
                return self._refusal(question, reason, suggestions, ai_intent, ai_confidence)

        lawyer_degree = ("lawyer" in lowered or "attorney" in lowered) and any(word in lowered for word in ["bachelor", "major", "degree"]) and any(word in lowered for word in ["highest pay", "highest salary", "earn the most", "after becoming"])
        if lawyer_degree:
            return self._refusal(
                question,
                "The bundled official datasets cannot link a person's bachelor's major to their later earnings specifically as a lawyer. Census B15013 reports earnings by broad first-major field across all occupations, while BLS reports lawyer wages separately. Combining them would not prove that a major caused higher lawyer pay.",
                [
                    "Which broad bachelor's degree fields have the highest national median earnings?",
                    "What education is typically required for lawyers?",
                    "What are lawyers' national wage and 2024–2034 outlook?",
                ],
                ai_intent,
                ai_confidence,
            )
        return None

    def _refusal(self, question: str, reason: str, suggestions: list[str], ai_intent: str, ai_confidence: float) -> AnalysisResult:
        return self._base_result(
            status="refused", question=question, dataset="Trust boundary", intent="unsupported",
            ai_intent=ai_intent, ai_confidence=ai_confidence,
            headline="The available data cannot support that conclusion", summary=reason,
            rows=[], columns=[], chart=ChartSpec(),
            query_plan={"operation": "refuse", "reason": reason},
            evidence=evidence_block(calculation="No calculation was run because the requested claim is outside the supported data.", filters=[], rows_considered=0, rows_returned=0),
            confidence=Confidence(label="Insufficient evidence", score=0, reason="The required variable or causal link is not present in the bundled datasets."),
            source_ids=[], limitations=[reason], suggestions=suggestions,
        )

    def _clarify(self, question: str, message: str, suggestions: list[str], ai_intent: str, ai_confidence: float) -> AnalysisResult:
        return self._base_result(
            status="needs_clarification", question=question, dataset="Automatic routing", intent="clarification",
            ai_intent=ai_intent, ai_confidence=ai_confidence,
            headline="Add an occupation or comparison target", summary=message,
            rows=[], columns=[], chart=ChartSpec(), query_plan={"operation": "clarify"},
            evidence=evidence_block(calculation="No calculation was run because a required entity was not identified.", filters=[], rows_considered=0, rows_returned=0),
            confidence=Confidence(label="Insufficient evidence", score=0, reason="The question does not identify enough information for a reproducible query."),
            source_ids=[], suggestions=suggestions,
        )

    @staticmethod
    def _looks_like_degree_question(lowered: str) -> bool:
        return any(term in lowered for term in ["bachelor's degree field", "bachelors degree field", "degree earnings", "major earnings", "which major", "communications degree", "engineering degree", "business degree", "social sciences degree"])

    @staticmethod
    def _looks_like_education_aggregate(lowered: str) -> bool:
        return any(term in lowered for term in ["typical entry-level education", "typical entry education", "bachelor's-level occupations", "bachelors-level occupations", "wages by education", "education level wages", "requiring a bachelor's degree", "requiring a bachelor degree", "doctoral or professional degree jobs"])

    def _looks_like_state_question(self, question: str) -> bool:
        lowered = question.lower()
        return bool(self.store.find_states(question)) or any(term in lowered for term in ["which states", "highest paying states", "most concentrated", "location quotient"])

    def _occupation_matches(self, question: str, limit: int = 2) -> list[dict[str, Any]]:
        found: list[dict[str, Any]] = []
        lowered = question.lower()
        for alias, title in sorted(self.store.aliases.items(), key=lambda item: len(item[0]), reverse=True):
            if alias.lower() in lowered and title not in [item["occupation_title"] for item in found]:
                code = self.store.title_to_code.get(title)
                if code:
                    found.append({"soc_code": code, "occupation_title": title, "score": 2.0})
        if len(found) < limit:
            for match in self.store.find_occupations(question, limit=8):
                if match["occupation_title"] not in [item["occupation_title"] for item in found]:
                    found.append(match)
                if len(found) >= limit:
                    break
        return found[:limit]

    def _national_analysis(self, question: str, ai_intent: str, ai_confidence: float) -> AnalysisResult:
        lowered = question.lower()
        data = self.store.occupations.copy()
        limit = limit_from_question(question)
        if any(term in lowered for term in ["highest-paying", "highest paying", "pay the most", "top paying"]):
            ranked = data.dropna(subset=["annual_median_wage_2025"]).nlargest(limit, "annual_median_wage_2025")
            rows = [{
                "occupation": row.occupation_title,
                "median_annual_wage": safe_value(row.annual_median_wage_2025),
                "employment": safe_value(row.employment_2025),
                "education": safe_value(row.typical_entry_education),
                "soc_code": row.soc_code,
            } for row in ranked.itertuples()]
            return self._base_result(
                status="supported", question=question, dataset="BLS OEWS National", intent="highest_pay",
                ai_intent=ai_intent, ai_confidence=ai_confidence,
                headline=f"{rows[0]['occupation']} has the highest published median wage in this ranking",
                summary=f"The top result is {money(rows[0]['median_annual_wage'])} per year in the May 2025 national OEWS estimates.",
                rows=rows, columns=[
                    {"key": "occupation", "label": "Occupation"}, {"key": "median_annual_wage", "label": "Median annual wage", "format": "currency"},
                    {"key": "employment", "label": "Employment", "format": "number"}, {"key": "education", "label": "Typical entry education"},
                ],
                chart=ChartSpec(type="bar", title=f"Top {len(rows)} national median wages", label_key="occupation", value_key="median_annual_wage", value_format="currency"),
                query_plan={"dataset": "BLS OEWS May 2025 national", "filter": "detailed occupations with published median wage", "grouping": None, "sort": "annual_median_wage_2025 descending", "limit": limit},
                evidence=evidence_block(calculation="Filtered to detailed occupations with a published annual median wage, sorted descending, and returned the requested number of rows.", filters=["O_GROUP = detailed", "annual median wage is published"], rows_considered=len(data), rows_returned=len(rows)),
                confidence=Confidence(label="High", score=96, reason="Direct published BLS estimates with no modeled calculation beyond sorting."),
                source_ids=["bls-oews-national-2025"],
                limitations=["OEWS estimates describe occupations, not individual offers. Some highly paid occupations may have small employment counts."],
                suggestions=["Which occupations have the most employment?", "Which occupations are projected to grow fastest from 2024 to 2034?"],
            )
        if any(term in lowered for term in ["largest occupations", "most jobs", "most employed", "highest employment"]):
            ranked = data.dropna(subset=["employment_2025"]).nlargest(limit, "employment_2025")
            rows = [{"occupation": row.occupation_title, "employment": safe_value(row.employment_2025), "median_annual_wage": safe_value(row.annual_median_wage_2025), "soc_code": row.soc_code} for row in ranked.itertuples()]
            return self._base_result(
                status="supported", question=question, dataset="BLS OEWS National", intent="largest_employment",
                ai_intent=ai_intent, ai_confidence=ai_confidence,
                headline=f"{rows[0]['occupation']} has the largest published employment estimate",
                summary=f"BLS estimates {count(rows[0]['employment'])} people employed nationally in that detailed occupation in May 2025.",
                rows=rows, columns=[{"key": "occupation", "label": "Occupation"}, {"key": "employment", "label": "Employment", "format": "number"}, {"key": "median_annual_wage", "label": "Median annual wage", "format": "currency"}],
                chart=ChartSpec(type="bar", title=f"Top {len(rows)} occupations by employment", label_key="occupation", value_key="employment", value_format="number"),
                query_plan={"dataset": "BLS OEWS May 2025 national", "sort": "employment_2025 descending", "limit": limit},
                evidence=evidence_block(calculation="Sorted detailed occupation employment estimates from highest to lowest.", filters=["O_GROUP = detailed", "employment estimate is published"], rows_considered=len(data), rows_returned=len(rows)),
                confidence=Confidence(label="High", score=96, reason="Direct published BLS employment estimates."), source_ids=["bls-oews-national-2025"],
                limitations=["OEWS excludes self-employed workers and some other groups from its employment estimates."],
            )

        matches = self._occupation_matches(question, limit=2 if any(term in lowered for term in ["compare", "versus", " vs ", " or "]) else 1)
        if len(matches) >= 2 and any(term in lowered for term in ["compare", "versus", " vs ", " or "]):
            rows = []
            for match in matches[:2]:
                row = self.store.occupations.loc[self.store.occupations["soc_code"].eq(match["soc_code"])].iloc[0]
                rows.append({
                    "occupation": row["occupation_title"], "median_annual_wage": safe_value(row["annual_median_wage_2025"]),
                    "employment": safe_value(row["employment_2025"]), "growth_2024_2034": safe_value(row["employment_change_percent_2024_2034"]),
                    "annual_openings": safe_value(row["annual_openings_2024_2034_thousands"] * 1000 if pd.notna(row["annual_openings_2024_2034_thousands"]) else None),
                    "education": safe_value(row["typical_entry_education"]), "soc_code": row["soc_code"],
                })
            return self._base_result(
                status="supported", question=question, dataset="Unified BLS occupation profile", intent="occupation_compare",
                ai_intent=ai_intent, ai_confidence=ai_confidence,
                headline=f"{rows[0]['occupation']} and {rows[1]['occupation']} compared with official wage and outlook data",
                summary=f"The comparison uses May 2025 OEWS wages and BLS 2024–2034 projections. {rows[0]['occupation']} has a median wage of {money(rows[0]['median_annual_wage'])}; {rows[1]['occupation']} has {money(rows[1]['median_annual_wage'])}.",
                rows=rows, columns=[
                    {"key": "occupation", "label": "Occupation"}, {"key": "median_annual_wage", "label": "Median wage", "format": "currency"},
                    {"key": "employment", "label": "Employment", "format": "number"}, {"key": "growth_2024_2034", "label": "Growth 2024–34", "format": "percent"},
                    {"key": "annual_openings", "label": "Annual openings", "format": "number"}, {"key": "education", "label": "Typical education"},
                ],
                chart=ChartSpec(type="comparison", title="Median annual wage comparison", label_key="occupation", value_key="median_annual_wage", value_format="currency"),
                query_plan={"datasets": ["BLS OEWS May 2025", "BLS Employment Projections 2024–2034"], "soc_codes": [item["soc_code"] for item in matches[:2]], "operation": "side-by-side comparison"},
                evidence=evidence_block(calculation="Matched two occupation titles to SOC codes and displayed their published wage, employment, growth, openings, and education fields.", filters=[f"SOC in {', '.join(item['soc_code'] for item in matches[:2])}"], rows_considered=2, rows_returned=2),
                confidence=Confidence(label="High", score=94, reason="Both occupations matched exact SOC records and use direct official estimates."),
                source_ids=["bls-oews-national-2025", "bls-projections-2024-2034"],
                limitations=["The wage and projection vintages differ by one year. The comparison is descriptive, not causal."],
            )

        if not matches:
            return self._clarify(question, "Name an occupation such as nuclear engineer, public relations specialist, political scientist, lawyer, journalist, or software developer.", ["How much do nuclear engineers earn?", "Compare public relations specialists and journalists."], ai_intent, ai_confidence)
        match = matches[0]
        profile = self.store.occupation_profile(match["soc_code"])
        assert profile is not None
        occ = profile["occupation"]
        rows = [{
            "occupation": occ["occupation_title"], "median_annual_wage": occ.get("annual_median_wage_2025"),
            "mean_annual_wage": occ.get("annual_mean_wage_2025"), "employment": occ.get("employment_2025"),
            "growth_2024_2034": occ.get("employment_change_percent_2024_2034"),
            "annual_openings": (occ.get("annual_openings_2024_2034_thousands") or 0) * 1000 if occ.get("annual_openings_2024_2034_thousands") is not None else None,
            "education": occ.get("typical_entry_education"), "soc_code": occ["soc_code"],
        }]
        return self._base_result(
            status="supported", question=question, dataset="Unified occupation profile", intent="occupation_profile",
            ai_intent=ai_intent, ai_confidence=ai_confidence,
            headline=f"{occ['occupation_title']}: {money(occ.get('annual_median_wage_2025'))} national median wage",
            summary=f"BLS estimated {count(occ.get('employment_2025'))} people employed in May 2025. The occupation is projected to change {percent(occ.get('employment_change_percent_2024_2034'))} from 2024 to 2034, with about {count(rows[0]['annual_openings'])} openings per year on average.",
            rows=rows, columns=[
                {"key": "occupation", "label": "Occupation"}, {"key": "median_annual_wage", "label": "Median annual wage", "format": "currency"},
                {"key": "employment", "label": "Employment", "format": "number"}, {"key": "growth_2024_2034", "label": "Growth 2024–34", "format": "percent"},
                {"key": "annual_openings", "label": "Annual openings", "format": "number"}, {"key": "education", "label": "Typical education"},
            ],
            chart=ChartSpec(type="comparison", title="Published wage distribution", label_key="label", value_key="value", value_format="currency"),
            query_plan={"operation": "occupation profile", "soc_code": match["soc_code"], "joins": ["OEWS national", "Employment Projections", "O*NET"]},
            evidence=evidence_block(calculation="Matched the occupation to its SOC code and joined official national wage, employment projection, and O*NET profile records.", filters=[f"SOC = {match['soc_code']}"], rows_considered=1, rows_returned=1),
            confidence=Confidence(label="High", score=95, reason="Exact SOC-level official records were found across the core datasets."),
            source_ids=["bls-oews-national-2025", "bls-projections-2024-2034", "onet-30-3"],
            limitations=["National estimates do not represent a specific employer, offer, or person's future pay."],
            suggestions=[f"Which states pay {occ['occupation_title'].lower()} the most?", f"What skills do {occ['occupation_title'].lower()} need?"],
            profile=profile,
        )

    def _projection_analysis(self, question: str, ai_intent: str, ai_confidence: float) -> AnalysisResult:
        lowered = question.lower()
        data = self.store.occupations.copy()
        limit = limit_from_question(question)
        if any(term in lowered for term in ["fastest growing", "grow fastest", "highest growth"]):
            ranked = data.dropna(subset=["employment_change_percent_2024_2034"]).nlargest(limit, "employment_change_percent_2024_2034")
            rows = [{
                "occupation": row.occupation_title, "growth_percent": safe_value(row.employment_change_percent_2024_2034),
                "employment_change": safe_value(row.employment_change_2024_2034_thousands * 1000),
                "annual_openings": safe_value(row.annual_openings_2024_2034_thousands * 1000),
                "education": safe_value(row.typical_entry_education), "soc_code": row.soc_code,
            } for row in ranked.itertuples()]
            return self._base_result(
                status="supported", question=question, dataset="BLS Employment Projections", intent="fastest_growth",
                ai_intent=ai_intent, ai_confidence=ai_confidence,
                headline=f"{rows[0]['occupation']} has the fastest projected percentage growth in this ranking",
                summary=f"BLS projects {percent(rows[0]['growth_percent'])} employment growth from 2024 to 2034.",
                rows=rows, columns=[{"key": "occupation", "label": "Occupation"}, {"key": "growth_percent", "label": "Growth 2024–34", "format": "percent"}, {"key": "employment_change", "label": "Employment change", "format": "number"}, {"key": "annual_openings", "label": "Annual openings", "format": "number"}, {"key": "education", "label": "Typical education"}],
                chart=ChartSpec(type="bar", title=f"Top {len(rows)} projected growth rates", label_key="occupation", value_key="growth_percent", value_format="percent"),
                query_plan={"dataset": "BLS Employment Projections 2024–2034", "sort": "employment change percent descending", "limit": limit},
                evidence=evidence_block(calculation="Sorted detailed occupations by BLS projected percentage employment change for 2024–2034.", filters=["Occupation type = Line item", "growth estimate is published"], rows_considered=len(data), rows_returned=len(rows)),
                confidence=Confidence(label="High", score=95, reason="Direct BLS projection fields; calculation is a transparent sort."),
                source_ids=["bls-projections-2024-2034"],
                limitations=["A high growth rate can occur in a small occupation. Annual openings provide additional scale context."],
            )
        if any(term in lowered for term in ["most annual openings", "most openings", "highest openings"]):
            ranked = data.dropna(subset=["annual_openings_2024_2034_thousands"]).nlargest(limit, "annual_openings_2024_2034_thousands")
            rows = [{"occupation": row.occupation_title, "annual_openings": safe_value(row.annual_openings_2024_2034_thousands * 1000), "growth_percent": safe_value(row.employment_change_percent_2024_2034), "education": safe_value(row.typical_entry_education), "soc_code": row.soc_code} for row in ranked.itertuples()]
            return self._base_result(
                status="supported", question=question, dataset="BLS Employment Projections", intent="most_openings",
                ai_intent=ai_intent, ai_confidence=ai_confidence,
                headline=f"{rows[0]['occupation']} has the most projected annual openings in this ranking",
                summary=f"BLS projects about {count(rows[0]['annual_openings'])} openings per year on average from 2024 to 2034.",
                rows=rows, columns=[{"key": "occupation", "label": "Occupation"}, {"key": "annual_openings", "label": "Annual openings", "format": "number"}, {"key": "growth_percent", "label": "Growth 2024–34", "format": "percent"}, {"key": "education", "label": "Typical education"}],
                chart=ChartSpec(type="bar", title=f"Top {len(rows)} occupations by annual openings", label_key="occupation", value_key="annual_openings", value_format="number"),
                query_plan={"dataset": "BLS Employment Projections 2024–2034", "sort": "annual openings descending", "limit": limit},
                evidence=evidence_block(calculation="Sorted detailed occupations by the BLS annual-average openings estimate.", filters=["Occupation type = Line item", "annual openings published"], rows_considered=len(data), rows_returned=len(rows)),
                confidence=Confidence(label="High", score=95, reason="Direct BLS projection fields."), source_ids=["bls-projections-2024-2034"],
                limitations=["Openings include growth and replacement needs; they are not live vacancies."],
            )
        matches = self._occupation_matches(question, limit=2 if "compare" in lowered else 1)
        if not matches:
            return self._clarify(question, "Name an occupation to see its 2024–2034 growth, annual openings, and education requirements.", ["What is the outlook for nuclear engineers?", "Compare the outlook for public relations specialists and journalists."], ai_intent, ai_confidence)
        if len(matches) >= 2 and "compare" in lowered:
            rows = []
            for match in matches:
                row = data.loc[data["soc_code"].eq(match["soc_code"])].iloc[0]
                rows.append({"occupation": row.occupation_title, "growth_percent": safe_value(row.employment_change_percent_2024_2034), "annual_openings": safe_value(row.annual_openings_2024_2034_thousands * 1000), "employment_2024": safe_value(row.employment_2024_thousands * 1000), "education": safe_value(row.typical_entry_education), "soc_code": row.soc_code})
            return self._base_result(
                status="supported", question=question, dataset="BLS Employment Projections", intent="projection_compare", ai_intent=ai_intent, ai_confidence=ai_confidence,
                headline=f"Projected outlook: {rows[0]['occupation']} compared with {rows[1]['occupation']}",
                summary=f"BLS projects {percent(rows[0]['growth_percent'])} growth for {rows[0]['occupation']} and {percent(rows[1]['growth_percent'])} for {rows[1]['occupation']} from 2024 to 2034.",
                rows=rows, columns=[{"key": "occupation", "label": "Occupation"}, {"key": "growth_percent", "label": "Growth 2024–34", "format": "percent"}, {"key": "annual_openings", "label": "Annual openings", "format": "number"}, {"key": "employment_2024", "label": "Employment 2024", "format": "number"}, {"key": "education", "label": "Typical education"}],
                chart=ChartSpec(type="comparison", title="Projected employment growth", label_key="occupation", value_key="growth_percent", value_format="percent"),
                query_plan={"operation": "projection comparison", "soc_codes": [item["soc_code"] for item in matches]},
                evidence=evidence_block(calculation="Matched two occupations to SOC codes and displayed BLS projection fields side by side.", filters=[f"SOC in {', '.join(item['soc_code'] for item in matches)}"], rows_considered=2, rows_returned=2),
                confidence=Confidence(label="High", score=94, reason="Exact BLS occupation projection records."), source_ids=["bls-projections-2024-2034"],
                limitations=["Projections are scenarios based on assumptions, not guarantees."],
            )
        match = matches[0]
        row = data.loc[data["soc_code"].eq(match["soc_code"])].iloc[0]
        rows = [{"occupation": row.occupation_title, "employment_2024": safe_value(row.employment_2024_thousands * 1000), "employment_2034": safe_value(row.employment_2034_thousands * 1000), "growth_percent": safe_value(row.employment_change_percent_2024_2034), "annual_openings": safe_value(row.annual_openings_2024_2034_thousands * 1000), "education": safe_value(row.typical_entry_education), "work_experience": safe_value(row.related_work_experience), "training": safe_value(row.on_the_job_training)}]
        return self._base_result(
            status="supported", question=question, dataset="BLS Employment Projections", intent="occupation_outlook", ai_intent=ai_intent, ai_confidence=ai_confidence,
            headline=f"{row.occupation_title}: {percent(row.employment_change_percent_2024_2034)} projected growth from 2024 to 2034",
            summary=f"BLS projects employment moving from {count(row.employment_2024_thousands * 1000)} to {count(row.employment_2034_thousands * 1000)}, with about {count(row.annual_openings_2024_2034_thousands * 1000)} openings per year. Typical entry education: {row.typical_entry_education}.",
            rows=rows, columns=[{"key": "occupation", "label": "Occupation"}, {"key": "growth_percent", "label": "Growth 2024–34", "format": "percent"}, {"key": "annual_openings", "label": "Annual openings", "format": "number"}, {"key": "education", "label": "Typical education"}, {"key": "training", "label": "On-the-job training"}],
            chart=ChartSpec(type="comparison", title="Employment 2024 vs 2034", label_key="label", value_key="value", value_format="number"),
            query_plan={"operation": "occupation outlook", "soc_code": row.soc_code},
            evidence=evidence_block(calculation="Selected the occupation's line-item record from BLS Table 1.2 and displayed employment, growth, openings, education, experience, and training fields.", filters=[f"SOC = {row.soc_code}"], rows_considered=1, rows_returned=1),
            confidence=Confidence(label="High", score=95, reason="Exact line-item BLS projection record."), source_ids=["bls-projections-2024-2034"],
            limitations=["Projected openings are annual averages, not current vacancies."],
            suggestions=[f"Which states pay {row.occupation_title.lower()} the most?", f"What skills do {row.occupation_title.lower()} need?"],
        )

    def _state_analysis(self, question: str, ai_intent: str, ai_confidence: float) -> AnalysisResult:
        lowered = question.lower()
        matches = self._occupation_matches(question, limit=1)
        if not matches:
            return self._clarify(question, "Name an occupation for a state comparison.", ["Which states pay nuclear engineers the most?", "Which states employ the most public relations specialists?"], ai_intent, ai_confidence)
        match = matches[0]
        rows_for_occ = self.store.state_wages.loc[self.store.state_wages["soc_code"].eq(match["soc_code"])].copy()
        if rows_for_occ.empty:
            return self._refusal(question, "BLS did not publish state rows for that occupation in the bundled May 2025 file.", ["Show the national occupation profile."], ai_intent, ai_confidence)
        states = self.store.find_states(question)
        if len(states) >= 2 and any(term in lowered for term in ["compare", "versus", " vs ", " and "]):
            selected = rows_for_occ.loc[rows_for_occ["state_name"].isin(states[:2])]
            rows = [{"state": row.state_name, "median_annual_wage": safe_value(row.annual_median_wage_2025), "employment": safe_value(row.employment_2025), "location_quotient": safe_value(row.location_quotient)} for row in selected.itertuples()]
            return self._base_result(
                status="supported", question=question, dataset="BLS OEWS State", intent="state_compare", ai_intent=ai_intent, ai_confidence=ai_confidence,
                headline=f"{match['occupation_title']} in {' and '.join(states[:2])}",
                summary="The table compares published May 2025 state wage, employment, and concentration estimates.", rows=rows,
                columns=[{"key": "state", "label": "State"}, {"key": "median_annual_wage", "label": "Median annual wage", "format": "currency"}, {"key": "employment", "label": "Employment", "format": "number"}, {"key": "location_quotient", "label": "Location quotient", "format": "decimal"}],
                chart=ChartSpec(type="comparison", title="State median wage comparison", label_key="state", value_key="median_annual_wage", value_format="currency"),
                query_plan={"dataset": "BLS OEWS May 2025 state", "soc_code": match["soc_code"], "states": states[:2], "operation": "side-by-side comparison"},
                evidence=evidence_block(calculation="Filtered the state OEWS file to one SOC code and two named states.", filters=[f"SOC = {match['soc_code']}", f"state in {states[:2]}"], rows_considered=len(rows_for_occ), rows_returned=len(rows)),
                confidence=Confidence(label="High" if len(rows) == 2 else "Medium", score=94 if len(rows) == 2 else 72, reason="Direct state estimates; confidence is lower if a requested state estimate is suppressed or missing."),
                source_ids=["bls-oews-state-2025"], limitations=["State estimates may be suppressed for small occupations."],
            )
        if len(states) == 1:
            selected = rows_for_occ.loc[rows_for_occ["state_name"].eq(states[0])]
            if selected.empty:
                return self._refusal(question, f"No published May 2025 state estimate was found for {match['occupation_title']} in {states[0]}.", [f"Which states pay {match['occupation_title'].lower()} the most?", f"Show the national profile for {match['occupation_title'].lower()}."], ai_intent, ai_confidence)
            row = selected.iloc[0]
            rows = [{"state": row.state_name, "occupation": row.occupation_title, "median_annual_wage": safe_value(row.annual_median_wage_2025), "mean_annual_wage": safe_value(row.annual_mean_wage_2025), "employment": safe_value(row.employment_2025), "jobs_per_1000": safe_value(row.jobs_per_1000), "location_quotient": safe_value(row.location_quotient)}]
            return self._base_result(
                status="supported", question=question, dataset="BLS OEWS State", intent="state_occupation_profile", ai_intent=ai_intent, ai_confidence=ai_confidence,
                headline=f"{match['occupation_title']} in {states[0]}: {money(row.annual_median_wage_2025)} median annual wage",
                summary=f"BLS published an employment estimate of {count(row.employment_2025)} and a location quotient of {safe_value(row.location_quotient) or 'not published'} for May 2025.",
                rows=rows, columns=[{"key": "state", "label": "State"}, {"key": "occupation", "label": "Occupation"}, {"key": "median_annual_wage", "label": "Median wage", "format": "currency"}, {"key": "employment", "label": "Employment", "format": "number"}, {"key": "location_quotient", "label": "Location quotient", "format": "decimal"}],
                chart=ChartSpec(type="comparison", title="Published wage percentiles", label_key="label", value_key="value", value_format="currency"),
                query_plan={"dataset": "BLS OEWS May 2025 state", "soc_code": match["soc_code"], "state": states[0]},
                evidence=evidence_block(calculation="Filtered the state OEWS file to an exact SOC code and state.", filters=[f"SOC = {match['soc_code']}", f"state = {states[0]}"], rows_considered=len(rows_for_occ), rows_returned=1),
                confidence=Confidence(label="High", score=94, reason="Direct published BLS state estimate."), source_ids=["bls-oews-state-2025"],
                limitations=["This is an occupational estimate for the state, not a guaranteed offer."],
            )
        limit = limit_from_question(question)
        metric = "annual_median_wage_2025"
        intent = "highest_paying_states"
        headline_word = "pays"
        chart_format = "currency"
        if any(term in lowered for term in ["employ the most", "most employment", "most jobs"]):
            metric, intent, headline_word, chart_format = "employment_2025", "highest_employment_states", "employs", "number"
        elif any(term in lowered for term in ["concentrated", "location quotient"]):
            metric, intent, headline_word, chart_format = "location_quotient", "highest_concentration_states", "has the highest concentration for", "decimal"
        ranked = rows_for_occ.dropna(subset=[metric]).nlargest(limit, metric)
        rows = [{"state": row.state_name, "median_annual_wage": safe_value(row.annual_median_wage_2025), "employment": safe_value(row.employment_2025), "location_quotient": safe_value(row.location_quotient)} for row in ranked.itertuples()]
        value = rows[0]["median_annual_wage" if metric == "annual_median_wage_2025" else "employment" if metric == "employment_2025" else "location_quotient"]
        value_text = money(value) if metric == "annual_median_wage_2025" else count(value) if metric == "employment_2025" else f"{float(value):.2f}"
        return self._base_result(
            status="supported", question=question, dataset="BLS OEWS State", intent=intent, ai_intent=ai_intent, ai_confidence=ai_confidence,
            headline=f"{rows[0]['state']} {headline_word} {match['occupation_title'].lower()} at the top of this published ranking",
            summary=f"The leading value is {value_text}. Only states with a published May 2025 estimate are included.",
            rows=rows, columns=[{"key": "state", "label": "State"}, {"key": "median_annual_wage", "label": "Median annual wage", "format": "currency"}, {"key": "employment", "label": "Employment", "format": "number"}, {"key": "location_quotient", "label": "Location quotient", "format": "decimal"}],
            chart=ChartSpec(type="bar", title=f"State ranking for {match['occupation_title']}", label_key="state", value_key="median_annual_wage" if metric == "annual_median_wage_2025" else "employment" if metric == "employment_2025" else "location_quotient", value_format=chart_format),
            query_plan={"dataset": "BLS OEWS May 2025 state", "soc_code": match["soc_code"], "sort": f"{metric} descending", "limit": limit, "missing": "exclude suppressed/unpublished values"},
            evidence=evidence_block(calculation=f"Filtered state records to SOC {match['soc_code']}, removed rows without a published {metric}, sorted descending, and returned the top {limit}.", filters=[f"SOC = {match['soc_code']}", f"{metric} is published"], rows_considered=len(rows_for_occ), rows_returned=len(rows), data_quality_notes=[f"BLS published this occupation for {len(rows_for_occ)} state or district areas in the bundled file."]),
            confidence=Confidence(label="High", score=93, reason="Direct published state estimates; suppressed values are excluded and disclosed."), source_ids=["bls-oews-state-2025"],
            limitations=["States with suppressed estimates cannot appear in the ranking. Cost of living is not included."],
        )

    def _onet_analysis(self, question: str, ai_intent: str, ai_confidence: float) -> AnalysisResult:
        lowered = question.lower()
        matches = self._occupation_matches(question, limit=1)
        if not matches:
            return self._clarify(question, "Name an occupation to retrieve its O*NET skills, knowledge, tasks, tools, or education responses.", ["What skills do nuclear engineers need?", "What tasks do public relations specialists perform?"], ai_intent, ai_confidence)
        match = matches[0]
        soc = match["soc_code"]
        profile = self.store.occupation_profile(soc)
        assert profile is not None
        source_frame: pd.DataFrame
        value_key: str
        label_key: str
        intent: str
        headline: str
        summary: str
        columns: list[dict[str, str]]
        chart_format = "decimal"
        if "software" in lowered or "tools" in lowered or "technology" in lowered:
            source_frame = self.store.software.loc[self.store.software["soc_code"].eq(soc)].head(12)
            rows = [{"software_or_tool": row.software_or_tool, "category": row.software_category, "in_demand": row.in_demand, "hot_technology": row.hot_technology} for row in source_frame.itertuples()]
            intent, label_key, value_key = "software_tools", "software_or_tool", "rank"
            headline = f"Software and technology examples for {match['occupation_title']}"
            summary = "O*NET lists workplace technology examples associated with this occupation. In-demand and hot-technology flags are shown when published."
            columns = [{"key": "software_or_tool", "label": "Software or tool"}, {"key": "category", "label": "Category"}, {"key": "in_demand", "label": "In demand"}, {"key": "hot_technology", "label": "Hot technology"}]
            chart = ChartSpec()
        elif "knowledge" in lowered:
            source_frame = self.store.knowledge.loc[self.store.knowledge["soc_code"].eq(soc)].head(10)
            rows = [{"knowledge_area": row.knowledge_area, "importance": safe_value(row.importance), "rank": int(row.rank)} for row in source_frame.itertuples()]
            intent, label_key, value_key = "knowledge", "knowledge_area", "importance"
            headline = f"Top O*NET knowledge areas for {match['occupation_title']}"
            summary = "Importance uses O*NET's occupation-level rating scale. Higher values indicate greater reported importance."
            columns = [{"key": "knowledge_area", "label": "Knowledge area"}, {"key": "importance", "label": "Importance", "format": "decimal"}]
            chart = ChartSpec(type="bar", title="Knowledge importance", label_key=label_key, value_key=value_key, value_format=chart_format)
        elif "task" in lowered or "duties" in lowered or "what does" in lowered or "daily work" in lowered:
            source_frame = self.store.tasks.loc[self.store.tasks["soc_code"].eq(soc)].head(10)
            rows = [{"task": row.task, "task_type": row.task_type, "rank": int(row.rank)} for row in source_frame.itertuples()]
            intent, label_key, value_key = "tasks", "task", "rank"
            headline = f"Core O*NET tasks for {match['occupation_title']}"
            summary = str(profile["occupation"].get("description") or "O*NET task statements describe the work associated with this occupation.")
            columns = [{"key": "task", "label": "Task"}, {"key": "task_type", "label": "Type"}]
            chart = ChartSpec()
        else:
            source_frame = self.store.skills.loc[self.store.skills["soc_code"].eq(soc)].head(10)
            rows = [{"skill": row.skill, "importance": safe_value(row.importance), "rank": int(row.rank)} for row in source_frame.itertuples()]
            intent, label_key, value_key = "skills", "skill", "importance"
            headline = f"Top O*NET essential skills for {match['occupation_title']}"
            summary = "Importance uses O*NET's occupation-level rating scale. The list is descriptive and is not a hiring score."
            columns = [{"key": "skill", "label": "Skill"}, {"key": "importance", "label": "Importance", "format": "decimal"}]
            chart = ChartSpec(type="bar", title="Essential skill importance", label_key=label_key, value_key=value_key, value_format=chart_format)
        if not rows:
            return self._refusal(question, f"O*NET did not publish that profile component for {match['occupation_title']} in the bundled release.", [f"Show the full profile for {match['occupation_title'].lower()}."], ai_intent, ai_confidence)
        return self._base_result(
            status="supported", question=question, dataset="O*NET 30.3", intent=intent, ai_intent=ai_intent, ai_confidence=ai_confidence,
            headline=headline, summary=summary, rows=rows, columns=columns, chart=chart,
            query_plan={"dataset": "O*NET 30.3", "soc_code": soc, "component": intent, "sort": "O*NET importance or source priority", "limit": len(rows)},
            evidence=evidence_block(calculation=f"Matched the occupation to SOC {soc}, selected the O*NET {intent} records, and returned the highest-priority published rows.", filters=[f"SOC base = {soc}"], rows_considered=int(len(source_frame)), rows_returned=len(rows)),
            confidence=Confidence(label="High", score=92, reason="Direct O*NET occupation-profile records. Importance ratings are survey or analyst measures, not model-generated scores."),
            source_ids=["onet-30-3"], limitations=["O*NET describes typical occupational content; individual jobs vary."],
            suggestions=[f"What is the national wage and outlook for {match['occupation_title'].lower()}?", f"Which states pay {match['occupation_title'].lower()} the most?"],
            profile=profile,
        )

    def _degree_analysis(self, question: str, ai_intent: str, ai_confidence: float) -> AnalysisResult:
        lowered = question.lower()
        data = self.store.degree_earnings.copy()
        fields = self.store.find_degree_fields(question)
        if len(fields) >= 2 or "compare" in lowered:
            if len(fields) < 2:
                return self._clarify(question, "Name two broad degree fields from the Census table, such as communications, engineering, social sciences, business, psychology, or education.", ["Compare communications and engineering degree earnings.", "Compare social sciences and business degree earnings."], ai_intent, ai_confidence)
            selected = data.loc[data["bachelors_field_group"].isin(fields[:2])]
            rows = [{"degree_field": row.bachelors_field_group, "median_earnings": int(row.median_earnings_2024), "margin_of_error": int(row.margin_of_error_90_percent)} for row in selected.itertuples()]
            higher = max(rows, key=lambda item: item["median_earnings"])
            return self._base_result(
                status="supported", question=question, dataset="Census ACS Degree Earnings", intent="degree_compare", ai_intent=ai_intent, ai_confidence=ai_confidence,
                headline=f"{higher['degree_field']} has the higher national median earnings in this comparison",
                summary=f"The 2024 ACS estimate is {money(higher['median_earnings'])}. These figures cover people age 25–64 with earnings and a bachelor's degree or higher, across all occupations.",
                rows=rows, columns=[{"key": "degree_field", "label": "First bachelor's degree field"}, {"key": "median_earnings", "label": "Median earnings", "format": "currency"}, {"key": "margin_of_error", "label": "90% margin of error", "format": "currency"}],
                chart=ChartSpec(type="comparison", title="National median earnings by degree field", label_key="degree_field", value_key="median_earnings", value_format="currency"),
                query_plan={"dataset": "ACS 2024 1-Year B15013", "fields": fields[:2], "operation": "side-by-side published estimates"},
                evidence=evidence_block(calculation="Selected two published Census B15013 field groups and displayed their median earnings estimates and 90% margins of error.", filters=[f"field in {fields[:2]}", "geography = United States"], rows_considered=len(data), rows_returned=len(rows)),
                confidence=Confidence(label="High", score=91, reason="Direct published ACS estimates with margins of error shown."), source_ids=["census-acs-b15013-2024"],
                limitations=["These are broad first-major field groups across all occupations. They do not prove that a major caused the earnings difference or predict an individual's pay."],
            )
        if len(fields) == 1:
            selected = data.loc[data["bachelors_field_group"].eq(fields[0])].iloc[0]
            rows = [{"degree_field": selected.bachelors_field_group, "median_earnings": int(selected.median_earnings_2024), "margin_of_error": int(selected.margin_of_error_90_percent)}]
            return self._base_result(
                status="supported", question=question, dataset="Census ACS Degree Earnings", intent="degree_field_profile", ai_intent=ai_intent, ai_confidence=ai_confidence,
                headline=f"{selected.bachelors_field_group}: {money(selected.median_earnings_2024)} national median earnings",
                summary=f"The 2024 ACS 1-year estimate has a 90% margin of error of ±{money(selected.margin_of_error_90_percent)} for this broad field group.",
                rows=rows, columns=[{"key": "degree_field", "label": "First bachelor's degree field"}, {"key": "median_earnings", "label": "Median earnings", "format": "currency"}, {"key": "margin_of_error", "label": "90% margin of error", "format": "currency"}],
                chart=ChartSpec(type="comparison", title="Published median earnings", label_key="degree_field", value_key="median_earnings", value_format="currency"),
                query_plan={"dataset": "ACS 2024 1-Year B15013", "field": fields[0], "geography": "United States"},
                evidence=evidence_block(calculation="Selected the exact published Census field group from B15013.", filters=[f"field = {fields[0]}", "geography = United States"], rows_considered=len(data), rows_returned=1),
                confidence=Confidence(label="High", score=91, reason="Direct ACS estimate and margin of error."), source_ids=["census-acs-b15013-2024"],
                limitations=["The table groups people by first bachelor's major and includes many different occupations and experience levels."],
                suggestions=["Which broad bachelor's degree fields have the highest median earnings?", "What occupations typically require a bachelor's degree?"],
            )
        limit = limit_from_question(question)
        ranked = data.loc[~data["bachelors_field_group"].str.startswith("All ")].nlargest(limit, "median_earnings_2024")
        rows = [{"degree_field": row.bachelors_field_group, "median_earnings": int(row.median_earnings_2024), "margin_of_error": int(row.margin_of_error_90_percent)} for row in ranked.itertuples()]
        return self._base_result(
            status="supported", question=question, dataset="Census ACS Degree Earnings", intent="highest_degree_earnings", ai_intent=ai_intent, ai_confidence=ai_confidence,
            headline=f"{rows[0]['degree_field']} has the highest national median earnings among the published broad field groups",
            summary=f"The 2024 ACS estimate is {money(rows[0]['median_earnings'])}. The result is an association across people age 25–64 with earnings and a bachelor's degree or higher, not a guarantee or causal ranking.",
            rows=rows, columns=[{"key": "degree_field", "label": "First bachelor's degree field"}, {"key": "median_earnings", "label": "Median earnings", "format": "currency"}, {"key": "margin_of_error", "label": "90% margin of error", "format": "currency"}],
            chart=ChartSpec(type="bar", title="National median earnings by broad first-major field", label_key="degree_field", value_key="median_earnings", value_format="currency"),
            query_plan={"dataset": "ACS 2024 1-Year B15013", "filter": "leaf field groups, excluding all-fields total", "sort": "median earnings descending", "limit": limit},
            evidence=evidence_block(calculation="Excluded the all-fields total, sorted the published broad field groups by median earnings, and returned the requested number of rows.", filters=["geography = United States", "exclude all-fields total"], rows_considered=len(data), rows_returned=len(rows)),
            confidence=Confidence(label="High", score=91, reason="Direct ACS estimates with 90% margins of error included."), source_ids=["census-acs-b15013-2024"],
            limitations=["Field groups are broad and do not control for occupation, location, age, experience, or graduate education. Ranking does not establish causation."],
            suggestions=["Compare communications and engineering degree earnings.", "How do national wages compare by typical entry-level education?"],
        )

    def _education_wage_analysis(self, question: str, ai_intent: str, ai_confidence: float) -> AnalysisResult:
        lowered = question.lower()
        data = self.store.education_wages.copy()
        category_aliases = {
            "doctoral or professional": "Doctoral or professional degree",
            "doctoral": "Doctoral or professional degree",
            "professional degree": "Doctoral or professional degree",
            "master": "Master's degree",
            "bachelor": "Bachelor's degree",
            "associate": "Associate's degree",
            "postsecondary nondegree": "Postsecondary nondegree award",
            "high school": "High school diploma or equivalent",
            "no formal": "No formal educational credential",
        }
        category = None
        for alias, value in category_aliases.items():
            if alias in lowered:
                category = value
                break
        geography_type = "National"
        if "metro" in lowered or "metropolitan" in lowered:
            geography_type = "Metropolitan Area"
        elif "state" in lowered or "states" in lowered:
            geography_type = "State"
        if geography_type == "National" and category is None:
            selected = data.loc[data["geography_type"].eq("National")].copy().sort_values("annual_median_wage_2025", ascending=False)
            rows = [{"education_category": row.education_category, "employment": safe_value(row.employment_2025), "share_of_employment": safe_value(row.share_of_employment_percent), "median_annual_wage": safe_value(row.annual_median_wage_2025)} for row in selected.itertuples()]
            return self._base_result(
                status="supported", question=question, dataset="BLS Education Wage Aggregates", intent="national_education_wages", ai_intent=ai_intent, ai_confidence=ai_confidence,
                headline=f"{rows[0]['education_category']} has the highest median wage among the BLS typical-entry education groups",
                summary=f"Its May 2025 national median wage is {money(rows[0]['median_annual_wage'])}. This groups occupations by the education BLS typically assigns for entry, not by each worker's personal degree.",
                rows=rows, columns=[{"key": "education_category", "label": "Typical entry education"}, {"key": "median_annual_wage", "label": "Median annual wage", "format": "currency"}, {"key": "employment", "label": "Employment", "format": "number"}, {"key": "share_of_employment", "label": "Share of employment", "format": "percent"}],
                chart=ChartSpec(type="bar", title="National median wage by typical entry education", label_key="education_category", value_key="median_annual_wage", value_format="currency"),
                query_plan={"dataset": "BLS OEWS May 2025 education aggregation", "geography_type": "National", "sort": "annual median wage descending"},
                evidence=evidence_block(calculation="Selected the national BLS education aggregation and sorted education categories by annual median wage.", filters=["geography type = National"], rows_considered=len(selected), rows_returned=len(rows)),
                confidence=Confidence(label="High", score=94, reason="Direct BLS special-tabulation estimates."), source_ids=["bls-oews-education-2025"],
                limitations=["Categories reflect the education typically needed to enter an occupation, not every worker's education or a causal return to a degree."],
            )
        if category is None:
            return self._clarify(question, "Specify an education category such as bachelor's degree, master's degree, associate's degree, or doctoral or professional degree.", ["Which states have the highest median wage for bachelor's-level occupations?", "Which metro areas pay the most for occupations typically requiring a bachelor's degree?"], ai_intent, ai_confidence)
        selected = data.loc[data["geography_type"].eq(geography_type) & data["education_category"].eq(category)].dropna(subset=["annual_median_wage_2025"])
        if selected.empty:
            return self._refusal(question, f"No published {geography_type.lower()} records were found for {category} in the bundled BLS education aggregation.", ["How do national wages compare by typical entry-level education?"], ai_intent, ai_confidence)
        limit = limit_from_question(question)
        if geography_type == "National":
            ranked = selected.head(1)
        else:
            ranked = selected.nlargest(limit, "annual_median_wage_2025")
        rows = [{"geography": row.geography, "education_category": row.education_category, "median_annual_wage": safe_value(row.annual_median_wage_2025), "employment": safe_value(row.employment_2025), "share_of_employment": safe_value(row.share_of_employment_percent)} for row in ranked.itertuples()]
        return self._base_result(
            status="supported", question=question, dataset="BLS Education Wage Aggregates", intent="education_geography_ranking", ai_intent=ai_intent, ai_confidence=ai_confidence,
            headline=f"{rows[0]['geography']} has the highest published median wage in this {geography_type.lower()} ranking for {category.lower()} occupations",
            summary=f"The May 2025 median wage is {money(rows[0]['median_annual_wage'])}. The category is based on the education typically needed to enter each occupation.",
            rows=rows, columns=[{"key": "geography", "label": geography_type}, {"key": "education_category", "label": "Typical entry education"}, {"key": "median_annual_wage", "label": "Median annual wage", "format": "currency"}, {"key": "employment", "label": "Employment", "format": "number"}, {"key": "share_of_employment", "label": "Share of employment", "format": "percent"}],
            chart=ChartSpec(type="bar", title=f"{geography_type} median wage ranking: {category}", label_key="geography", value_key="median_annual_wage", value_format="currency"),
            query_plan={"dataset": "BLS OEWS May 2025 education aggregation", "geography_type": geography_type, "education_category": category, "sort": "annual median wage descending", "limit": limit},
            evidence=evidence_block(calculation=f"Filtered the BLS education aggregation to {geography_type} rows for {category}, removed unpublished median wages, and sorted descending.", filters=[f"geography type = {geography_type}", f"education category = {category}"], rows_considered=len(selected), rows_returned=len(rows)),
            confidence=Confidence(label="High", score=93, reason="Direct BLS education-by-geography special tabulation."), source_ids=["bls-oews-education-2025"],
            limitations=["Geographic wage differences do not account for cost of living. The grouping is by typical occupational entry education, not individual educational attainment."],
        )
