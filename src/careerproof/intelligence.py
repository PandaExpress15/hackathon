from __future__ import annotations

import math
import re
from collections import defaultdict
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any, Iterable

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .data_store import DataStore, normalize, record_to_dict, safe_value


EDUCATION_ORDER = {
    "No formal educational credential": 0,
    "High school diploma or equivalent": 1,
    "Some college, no degree": 2,
    "Postsecondary nondegree award": 2,
    "Associate's degree": 3,
    "Bachelor's degree": 4,
    "Master's degree": 5,
    "Doctoral or professional degree": 6,
}

CATEGORY_META: dict[str, dict[str, str]] = {
    "Engineering & Technology": {"slug": "engineering", "icon": "circuit", "accent": "blue"},
    "Communications & Creative": {"slug": "communications", "icon": "signal", "accent": "violet"},
    "Law, Policy & Government": {"slug": "policy", "icon": "columns", "accent": "gold"},
    "Business & Finance": {"slug": "business", "icon": "chart", "accent": "cyan"},
    "Health & Human Services": {"slug": "health", "icon": "pulse", "accent": "green"},
    "Science & Research": {"slug": "science", "icon": "atom", "accent": "teal"},
    "Education": {"slug": "education", "icon": "book", "accent": "indigo"},
    "Skilled Trades & Operations": {"slug": "trades", "icon": "gear", "accent": "orange"},
}

FEATURED_BY_CATEGORY: dict[str, list[str]] = {
    "Engineering & Technology": [
        "Nuclear Engineers", "Electrical Engineers", "Software Developers", "Aerospace Engineers",
        "Mechanical Engineers", "Information Security Analysts", "Computer Hardware Engineers", "Data Scientists",
    ],
    "Communications & Creative": [
        "Public Relations Specialists", "News Analysts, Reporters, and Journalists", "Technical Writers",
        "Broadcast Technicians", "Writers and Authors", "Producers and Directors", "Graphic Designers",
        "Communications Teachers, Postsecondary",
    ],
    "Law, Policy & Government": [
        "Lawyers", "Political Scientists", "Urban and Regional Planners", "Paralegals and Legal Assistants",
        "Economists", "Judges, Magistrate Judges, and Magistrates", "Emergency Management Directors",
        "Social and Community Service Managers",
    ],
    "Business & Finance": [
        "Financial and Investment Analysts", "Management Analysts", "Market Research Analysts and Marketing Specialists",
        "Accountants and Auditors", "Human Resources Specialists", "Project Management Specialists",
        "Operations Research Analysts", "Personal Financial Advisors",
    ],
    "Health & Human Services": [
        "Registered Nurses", "Physician Assistants", "Medical and Health Services Managers", "Physical Therapists",
        "Mental Health Counselors", "Occupational Therapists", "Epidemiologists", "Healthcare Social Workers",
    ],
    "Science & Research": [
        "Chemists", "Physicists", "Biochemists and Biophysicists", "Environmental Scientists and Specialists, Including Health",
        "Microbiologists", "Geoscientists, Except Hydrologists and Geographers", "Medical Scientists, Except Epidemiologists",
        "Survey Researchers",
    ],
    "Education": [
        "Secondary School Teachers, Except Special and Career/Technical Education", "Elementary School Teachers, Except Special Education",
        "Instructional Coordinators", "Education Administrators, Postsecondary", "Career/Technical Education Teachers, Secondary School",
        "Special Education Teachers, Secondary School", "Librarians and Media Collections Specialists", "Tutors",
    ],
    "Skilled Trades & Operations": [
        "Electricians", "Aircraft Mechanics and Service Technicians", "Industrial Machinery Mechanics", "Plumbers, Pipefitters, and Steamfitters",
        "Wind Turbine Service Technicians", "Solar Photovoltaic Installers", "Construction Managers", "First-Line Supervisors of Mechanics, Installers, and Repairers",
    ],
}

INTEREST_KEYWORDS: dict[str, str] = {
    "building things": "engineering design construction fabrication mechanics",
    "electronics": "electrical electronics circuits embedded controls power hardware",
    "programming": "software programming coding computing data algorithms cybersecurity",
    "writing": "writing communication journalism public relations technical writing media",
    "public speaking": "speaking presentation communication teaching advocacy public relations",
    "law": "law legal policy courts regulation government compliance",
    "politics": "political government policy public administration economics",
    "helping people": "health counseling social service education care community",
    "science": "science research laboratory physics chemistry biology environment",
    "business": "business finance management marketing entrepreneurship operations",
    "creative work": "creative design media arts writing production visual",
    "hands-on work": "repair install machinery construction maintenance field operations",
    "math": "mathematics statistics quantitative modeling analysis engineering",
    "research": "research analysis evidence experiments policy science data",
}

INTEREST_CATEGORIES: dict[str, tuple[str, ...]] = {
    "electronics": ("Engineering & Technology", "Skilled Trades & Operations"),
    "programming": ("Engineering & Technology",),
    "writing": ("Communications & Creative", "Law, Policy & Government"),
    "public speaking": ("Communications & Creative", "Law, Policy & Government", "Education"),
    "law": ("Law, Policy & Government",),
    "politics": ("Law, Policy & Government",),
    "helping people": ("Health & Human Services", "Education"),
    "science": ("Science & Research", "Engineering & Technology"),
    "business": ("Business & Finance",),
    "creative work": ("Communications & Creative",),
    "hands on work": ("Skilled Trades & Operations", "Engineering & Technology"),
    "math": ("Science & Research", "Engineering & Technology", "Business & Finance"),
    "research": ("Science & Research", "Law, Policy & Government"),
    "building things": ("Engineering & Technology", "Skilled Trades & Operations"),
}


# CareerProof Resilience Model v1.0
#
# The model intentionally uses a small, inspectable set of lexical signals from
# official O*NET task, skill, knowledge, and occupation-description text.  The
# scores are relative percentiles across the 830 bundled occupations.  They are
# CareerProof-derived decision aids, not BLS or O*NET automation predictions.
RESILIENCE_MODEL_VERSION = "1.0.0"
RESILIENCE_DIMENSIONS: dict[str, dict[str, Any]] = {
    "human_trust": {
        "label": "Human trust",
        "weight": 0.18,
        "description": "Relationship, teaching, counseling, persuasion, leadership, and negotiation signals.",
        "keywords": (
            "advise", "counsel", "teach", "train", "negotiate", "persuade", "communicate", "coordinate",
            "collaborate", "interview", "support", "care", "customer", "client", "patient", "student",
            "community", "relationship", "lead", "supervise", "mentor", "represent",
        ),
    },
    "physical_world": {
        "label": "Physical-world complexity",
        "weight": 0.18,
        "description": "Installation, repair, inspection, field, equipment, and unpredictable physical-environment signals.",
        "keywords": (
            "install", "repair", "maintain", "inspect", "operate", "equipment", "machinery", "field", "site",
            "construct", "assemble", "fabricate", "calibrate", "test", "vehicle", "patient", "laboratory",
            "physical", "hands", "tools", "emergency", "respond", "troubleshoot",
        ),
    },
    "high_stakes_judgment": {
        "label": "High-stakes judgment",
        "weight": 0.20,
        "description": "Safety, diagnosis, legal, ethical, approval, and technical-accountability signals.",
        "keywords": (
            "diagnose", "evaluate", "assess", "approve", "authorize", "safety", "risk", "legal", "ethical",
            "compliance", "regulation", "decision", "judgment", "interpret", "investigate", "emergency",
            "quality", "audit", "review", "standards", "responsible", "liability", "protect",
        ),
    },
    "creativity_adaptation": {
        "label": "Creativity and adaptation",
        "weight": 0.16,
        "description": "Original design, strategy, research, unfamiliar problem-solving, and innovation signals.",
        "keywords": (
            "design", "develop", "create", "research", "innovate", "strategy", "plan", "solve", "analyze",
            "investigate", "experiment", "adapt", "concept", "original", "improve", "invent", "model",
            "forecast", "synthesize", "write", "direct", "produce",
        ),
    },
    "regulation_credentials": {
        "label": "Credential and regulatory barrier",
        "weight": 0.12,
        "description": "Licensing, professional authority, regulated practice, and higher-entry-education signals.",
        "keywords": (
            "license", "licensed", "certification", "certified", "regulation", "regulatory", "law", "legal",
            "medical", "clinical", "professional", "standards", "code", "permit", "credential", "accredit",
            "compliance", "authority", "court", "engineer", "pharmac", "architect",
        ),
    },
    "automation_exposure": {
        "label": "Routine automation exposure",
        "weight": 0.16,
        "description": "Repetitive information-processing, scheduling, data-entry, and standardized-document signals.",
        "keywords": (
            "data entry", "enter data", "record", "compile", "routine", "repetitive", "schedule", "file",
            "transcribe", "format", "standard form", "process forms", "calculate", "tabulate", "sort",
            "verify information", "clerical", "bookkeeping", "prepare reports", "update records",
        ),
    },
}

AI_AUGMENTATION_KEYWORDS = (
    "analyze", "model", "simulate", "forecast", "detect", "diagnose", "optimize", "design", "research",
    "monitor", "quality", "visualize", "program", "software", "data", "decision", "draft", "document",
)

TASK_IMPACT_LEXICONS: dict[str, tuple[str, ...]] = {
    "human_led": (
        "approve", "authorize", "negotiate", "counsel", "teach", "supervise", "lead", "represent", "inspect",
        "repair", "install", "respond", "patient", "client", "court", "safety", "emergency", "operate",
        "direct", "persuade", "interview", "care", "coordinate",
    ),
    "augmented": (
        "analyze", "model", "simulate", "forecast", "research", "diagnose", "detect", "design", "evaluate",
        "optimize", "monitor", "investigate", "develop", "quality", "test", "plan", "review",
    ),
    "reduced": (
        "data entry", "enter data", "record", "compile", "routine", "schedule", "file", "transcribe", "format",
        "calculate", "tabulate", "sort", "prepare reports", "update records", "process forms", "verify information",
    ),
}

WEIGHT_DEFAULTS: dict[str, float] = {
    "interest_fit": 22.0,
    "resilience": 23.0,
    "salary": 18.0,
    "growth": 10.0,
    "openings": 9.0,
    "education": 8.0,
    "location": 5.0,
    "stability": 5.0,
}

SCENARIO_PRESETS: dict[str, dict[str, float]] = {
    "balanced": WEIGHT_DEFAULTS,
    "maximize_income": {"interest_fit": 10, "resilience": 15, "salary": 40, "growth": 8, "openings": 8, "education": 7, "location": 5, "stability": 7},
    "maximize_resilience": {"interest_fit": 15, "resilience": 45, "salary": 10, "growth": 7, "openings": 6, "education": 6, "location": 5, "stability": 6},
    "maximize_opportunity": {"interest_fit": 12, "resilience": 18, "salary": 12, "growth": 20, "openings": 22, "education": 5, "location": 5, "stability": 6},
    "minimize_education": {"interest_fit": 16, "resilience": 20, "salary": 12, "growth": 9, "openings": 10, "education": 25, "location": 4, "stability": 4},
    "stay_near_home": {"interest_fit": 15, "resilience": 20, "salary": 12, "growth": 8, "openings": 8, "education": 7, "location": 24, "stability": 6},
}

KNOWN_SKILLS = (
    "python", "arduino", "c++", "javascript", "writing", "public speaking", "research", "autocad", "mathematics",
    "leadership", "troubleshooting", "data analysis", "programming", "electronics", "communication", "design",
    "project management", "problem solving", "excel", "matlab", "cad", "teaching", "sales", "negotiation",
)


@dataclass(frozen=True)
class ResolvedOccupation:
    soc_code: str
    occupation_title: str


class CareerIntelligence:
    """Controlled decision-support layer built on official occupation data.

    All recommendation and comparison scores are CareerProof-derived. They are
    calculated transparently from published variables and user-selected weights.
    """

    def __init__(self, store: DataStore) -> None:
        self.store = store
        self.occupations = store.occupations.copy()
        self.occupations["category"] = self.occupations.apply(self._category_for_row, axis=1)
        self._prepare_metrics()
        self._prepare_text_index()
        self._prepare_skill_indexes()
        self._prepare_resilience_metrics()

    @staticmethod
    def _category_for_row(row: pd.Series) -> str:
        title = str(row.get("occupation_title", "")).lower()
        try:
            major = int(str(row.get("soc_code", "00"))[:2])
        except ValueError:
            major = 0
        policy_words = ("political", "economist", "urban and regional", "survey researcher", "government", "legislator")
        if major in {15, 17}:
            return "Engineering & Technology"
        if major == 27:
            return "Communications & Creative"
        if major in {23, 33} or any(word in title for word in policy_words):
            return "Law, Policy & Government"
        if major in {11, 13}:
            return "Business & Finance"
        if major in {21, 29, 31}:
            return "Health & Human Services"
        if major == 25:
            return "Education"
        if major == 19:
            return "Science & Research"
        return "Skilled Trades & Operations"

    @staticmethod
    def _percentile(series: pd.Series, *, log: bool = False, higher_is_better: bool = True) -> pd.Series:
        numeric = pd.to_numeric(series, errors="coerce")
        if log:
            numeric = np.log1p(numeric.clip(lower=0))
        ranks = numeric.rank(pct=True, method="average") * 100
        if not higher_is_better:
            ranks = 100 - ranks
        return ranks.fillna(0).clip(0, 100)

    def _prepare_metrics(self) -> None:
        occ = self.occupations
        occ["salary_score"] = self._percentile(occ["annual_median_wage_2025"])
        occ["growth_score"] = self._percentile(occ["employment_change_percent_2024_2034"])
        occ["openings_score"] = self._percentile(occ["annual_openings_2024_2034_thousands"], log=True)
        occ["employment_score"] = self._percentile(occ["employment_2025"], log=True)
        coverage = self.store.state_wages.groupby("soc_code")["state_name"].nunique().rename("state_coverage_count")
        occ = occ.merge(coverage, how="left", left_on="soc_code", right_index=True)
        occ["state_coverage_count"] = occ["state_coverage_count"].fillna(0)
        occ["location_score"] = (occ["state_coverage_count"] / 51 * 100).clip(0, 100)
        occ["education_rank"] = occ["typical_entry_education"].map(EDUCATION_ORDER).fillna(4)
        occ["education_access_score"] = (100 - occ["education_rank"] / 6 * 100).clip(0, 100)
        occ["stability_score"] = (
            occ["employment_score"] * 0.45 + occ["openings_score"] * 0.35 + occ["location_score"] * 0.20
        ).clip(0, 100)
        self.occupations = occ
        self._row_by_soc = {str(row.soc_code): row for row in occ.itertuples(index=False)}
        self._state_row_by_key = {
            (str(row.soc_code), str(row.state_name)): row
            for row in self.store.state_wages.itertuples(index=False)
        }
        self._rpp_by_state = {
            str(row.state_name): float(row.regional_price_parity_2024)
            for row in self.store.rpp.itertuples(index=False)
            if pd.notna(row.regional_price_parity_2024)
        }
        self._degrees_by_soc: dict[str, list[dict[str, str]]] = defaultdict(list)
        for row in self.store.degree_crosswalk.drop_duplicates(subset=["soc_code", "cip_code", "cip_title"]).itertuples(index=False):
            self._degrees_by_soc[str(row.soc_code)].append({"cip_code": str(row.cip_code), "cip_title": str(row.cip_title)})

    def _prepare_text_index(self) -> None:
        skill_text = self.store.skills.groupby("soc_code")["skill"].apply(lambda values: " ".join(map(str, values))).to_dict()
        knowledge_text = self.store.knowledge.groupby("soc_code")["knowledge_area"].apply(lambda values: " ".join(map(str, values))).to_dict()
        software_text = self.store.software.groupby("soc_code")["software_or_tool"].apply(lambda values: " ".join(map(str, values))).to_dict()
        corpus: list[str] = []
        for row in self.occupations.itertuples(index=False):
            corpus.append(" ".join([
                str(row.occupation_title), str(getattr(row, "description", "") or ""), str(row.category),
                skill_text.get(row.soc_code, ""), knowledge_text.get(row.soc_code, ""), software_text.get(row.soc_code, ""),
            ]))
        self.vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), min_df=1, max_features=30000, sublinear_tf=True)
        self.text_matrix = self.vectorizer.fit_transform(corpus)
        self._corpus_by_soc = dict(zip(self.occupations["soc_code"], corpus))

    def _prepare_skill_indexes(self) -> None:
        self._skills_by_soc: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in self.store.skills.itertuples(index=False):
            self._skills_by_soc[str(row.soc_code)].append({
                "skill": str(row.skill), "importance": float(row.importance), "rank": int(row.rank),
            })
        self._software_by_soc: dict[str, list[str]] = defaultdict(list)
        self._software_details_by_soc: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in self.store.software.itertuples(index=False):
            soc = str(row.soc_code)
            tool = str(row.software_or_tool)
            self._software_by_soc[soc].append(tool)
            self._software_details_by_soc[soc].append({
                "software": tool,
                "category": safe_value(row.software_category),
                "hot_technology": str(row.hot_technology) == "Y",
                "in_demand": str(row.in_demand) == "Y",
                "rank": int(row.rank),
            })
        self._tasks_by_soc: dict[str, list[str]] = defaultdict(list)
        for row in self.store.tasks.itertuples(index=False):
            self._tasks_by_soc[str(row.soc_code)].append(str(row.task))

    @staticmethod
    def _keyword_hits(text: str, keywords: Iterable[str]) -> tuple[int, list[str]]:
        normalized_text = normalize(text)
        matched: list[str] = []
        for keyword in keywords:
            key = normalize(keyword)
            if key and key in normalized_text:
                matched.append(keyword)
        return len(matched), matched

    def _prepare_resilience_metrics(self) -> None:
        """Precompute transparent relative resilience dimensions.

        The lexical signals come only from bundled official occupation and O*NET
        text.  Percentiles are computed across the complete occupation table so
        repeated API calls remain fast and reproducible.
        """

        raw_by_dimension: dict[str, list[float]] = {key: [] for key in RESILIENCE_DIMENSIONS}
        augmentation_raw: list[float] = []
        evidence_by_soc: dict[str, dict[str, list[str]]] = {}
        for row in self.occupations.itertuples(index=False):
            soc = str(row.soc_code)
            task_text = " ".join(self._tasks_by_soc.get(soc, [])[:24])
            skill_text = " ".join(item["skill"] for item in self._skills_by_soc.get(soc, [])[:20])
            knowledge_rows = self.store.knowledge.loc[self.store.knowledge["soc_code"].eq(soc)].head(20)
            knowledge_text = " ".join(knowledge_rows["knowledge_area"].astype(str).tolist())
            description = str(getattr(row, "description", "") or "")
            title = str(row.occupation_title)
            combined = " ".join([title, description, task_text, skill_text, knowledge_text])
            evidence_by_soc[soc] = {}
            for key, meta in RESILIENCE_DIMENSIONS.items():
                count, matched = self._keyword_hits(combined, meta["keywords"])
                raw = math.log1p(count) * 20.0
                if key == "regulation_credentials":
                    education_rank = float(getattr(row, "education_rank", 4.0))
                    job_zone = safe_value(getattr(row, "onet_job_zone", None))
                    raw += education_rank * 5.0
                    if job_zone is not None:
                        raw += max(float(job_zone) - 1.0, 0.0) * 2.5
                if key == "physical_world" and int(str(soc)[:2]) in {29, 31, 33, 35, 37, 39, 45, 47, 49, 51, 53}:
                    raw += 8.0
                raw_by_dimension[key].append(raw)
                evidence_by_soc[soc][key] = matched[:10]
            aug_count, aug_matches = self._keyword_hits(combined, AI_AUGMENTATION_KEYWORDS)
            augmentation_raw.append(math.log1p(aug_count) * 20.0)
            evidence_by_soc[soc]["ai_augmentation"] = aug_matches[:10]

        for key, values in raw_by_dimension.items():
            self.occupations[f"resilience_{key}"] = self._percentile(pd.Series(values))
        self.occupations["ai_augmentation_score"] = self._percentile(pd.Series(augmentation_raw))
        positive = sum(
            self.occupations[f"resilience_{key}"] * float(meta["weight"])
            for key, meta in RESILIENCE_DIMENSIONS.items()
            if key != "automation_exposure"
        )
        exposure = self.occupations["resilience_automation_exposure"]
        exposure_weight = float(RESILIENCE_DIMENSIONS["automation_exposure"]["weight"])
        self.occupations["resilience_score"] = (positive + (100.0 - exposure) * exposure_weight).clip(0, 100)
        self._resilience_evidence_by_soc = evidence_by_soc
        self._row_by_soc = {str(row.soc_code): row for row in self.occupations.itertuples(index=False)}

    @staticmethod
    def _resilience_label(score: float) -> str:
        if score >= 78:
            return "Very strong"
        if score >= 64:
            return "Strong"
        if score >= 48:
            return "Moderate"
        return "Developing"

    def _task_impact(self, soc_code: str) -> dict[str, Any]:
        buckets: dict[str, list[str]] = {"human_led": [], "augmented": [], "reduced": []}
        unclassified = 0
        for task in self._tasks_by_soc.get(soc_code, [])[:24]:
            normalized_task = normalize(task)
            assigned = False
            for bucket in ("human_led", "augmented", "reduced"):
                if any(normalize(term) in normalized_task for term in TASK_IMPACT_LEXICONS[bucket]):
                    if task not in buckets[bucket]:
                        buckets[bucket].append(task)
                    assigned = True
                    break
            if not assigned:
                unclassified += 1
        total_classified = sum(len(values) for values in buckets.values())
        return {
            "human_led": buckets["human_led"][:5],
            "augmented": buckets["augmented"][:5],
            "reduced": buckets["reduced"][:5],
            "classified_task_count": total_classified,
            "unclassified_task_count": unclassified,
            "method": "Transparent keyword routing over official O*NET task statements. Categories are examples, not forecasts of job loss.",
        }

    def career_resilience_profile(self, soc_code: str) -> dict[str, Any]:
        if soc_code not in self._row_by_soc:
            raise ValueError("Occupation not found.")
        row = self._row_by_soc[soc_code]
        dimensions: list[dict[str, Any]] = []
        for key, meta in RESILIENCE_DIMENSIONS.items():
            score = float(getattr(row, f"resilience_{key}"))
            if key == "automation_exposure":
                interpretation = "Lower is generally more resilient; this is a relative routine-task signal."
            else:
                interpretation = "Higher means more of this human or real-world advantage appears in the official work profile."
            dimensions.append({
                "key": key,
                "label": meta["label"],
                "score": round(score, 1),
                "weight": round(float(meta["weight"]) * 100, 1),
                "description": meta["description"],
                "interpretation": interpretation,
                "matched_signals": self._resilience_evidence_by_soc.get(soc_code, {}).get(key, [])[:8],
            })
        overall = round(float(row.resilience_score), 1)
        return {
            "model_version": RESILIENCE_MODEL_VERSION,
            "overall_score": overall,
            "label": self._resilience_label(overall),
            "dimensions": dimensions,
            "ai_augmentation_potential": {
                "score": round(float(row.ai_augmentation_score), 1),
                "label": self._resilience_label(float(row.ai_augmentation_score)),
                "matched_signals": self._resilience_evidence_by_soc.get(soc_code, {}).get("ai_augmentation", [])[:8],
            },
            "task_impact": self._task_impact(soc_code),
            "formula": "Overall resilience = 18% human trust + 18% physical-world complexity + 20% high-stakes judgment + 16% creativity/adaptation + 12% credential/regulatory barrier + 16% inverse routine-automation exposure.",
            "boundary": "This is a transparent relative profile built from official occupation text. It is not an official automation probability, a prediction that a job will survive, or a guarantee of individual outcomes.",
        }

    def resilience_model_card(self) -> dict[str, Any]:
        return {
            "name": "CareerProof Career Resilience Profile",
            "version": RESILIENCE_MODEL_VERSION,
            "purpose": "Help users compare human, physical-world, judgment, creative, credential, and routine-task signals across occupations.",
            "population": f"{len(self.occupations)} detailed occupations in the bundled official snapshots",
            "inputs": [
                "BLS/O*NET occupation title and description",
                "O*NET task statements",
                "O*NET essential skills and knowledge areas",
                "O*NET job zone and BLS typical entry education for the credential dimension",
            ],
            "normalization": "Each dimension is converted to a percentile across all bundled occupations. A 75 means the occupation contains more signals for that dimension than roughly 75% of occupations in this dataset; it is not a 75% probability.",
            "dimensions": [
                {
                    "key": key,
                    "label": meta["label"],
                    "weight": round(float(meta["weight"]) * 100, 1),
                    "description": meta["description"],
                    "keywords": list(meta["keywords"]),
                }
                for key, meta in RESILIENCE_DIMENSIONS.items()
            ],
            "formula": "18% human trust + 18% physical-world complexity + 20% high-stakes judgment + 16% creativity/adaptation + 12% credential/regulatory barrier + 16% inverse routine-automation exposure.",
            "validation": {
                "checks": [
                    "All scores are reproducible from bundled source text.",
                    "Every displayed occupation exposes matched signals and task examples.",
                    "Sensitivity presets show how a user decision changes when resilience receives more or less weight.",
                    "Missing official work-content fields reduce evidence coverage rather than being silently imputed.",
                ],
                "known_limitations": [
                    "Keyword presence cannot capture every nuance of a task or workplace.",
                    "Occupations contain varied roles and employers that a single national profile cannot represent.",
                    "The model does not use proprietary automation forecasts or claim causal prediction.",
                    "Credential signals do not prove a license is legally required in every state.",
                ],
            },
        }

    def data_quality_summary(self) -> dict[str, Any]:
        occupations = self.occupations
        state = self.store.state_wages
        skills_by_soc = set(self.store.skills["soc_code"].astype(str))
        tasks_by_soc = set(self.store.tasks["soc_code"].astype(str))
        degrees_by_soc = set(self.store.degree_crosswalk["soc_code"].astype(str))
        checks = [
            {
                "name": "National median wages",
                "available": int(occupations["annual_median_wage_2025"].notna().sum()),
                "total": int(len(occupations)),
                "missing": int(occupations["annual_median_wage_2025"].isna().sum()),
            },
            {
                "name": "Employment projections",
                "available": int(occupations["employment_change_percent_2024_2034"].notna().sum()),
                "total": int(len(occupations)),
                "missing": int(occupations["employment_change_percent_2024_2034"].isna().sum()),
            },
            {
                "name": "O*NET skills",
                "available": sum(str(code) in skills_by_soc for code in occupations["soc_code"]),
                "total": int(len(occupations)),
                "missing": sum(str(code) not in skills_by_soc for code in occupations["soc_code"]),
            },
            {
                "name": "O*NET tasks",
                "available": sum(str(code) in tasks_by_soc for code in occupations["soc_code"]),
                "total": int(len(occupations)),
                "missing": sum(str(code) not in tasks_by_soc for code in occupations["soc_code"]),
            },
            {
                "name": "Degree relationships",
                "available": sum(str(code) in degrees_by_soc for code in occupations["soc_code"]),
                "total": int(len(occupations)),
                "missing": sum(str(code) not in degrees_by_soc for code in occupations["soc_code"]),
            },
        ]
        for check in checks:
            check["coverage_percent"] = round(check["available"] / max(check["total"], 1) * 100, 1)
            check["status"] = "Strong" if check["coverage_percent"] >= 90 else "Partial" if check["coverage_percent"] >= 60 else "Limited"
        state_suppression = {
            "median_wage_missing": int(state["annual_median_wage_2025"].isna().sum()),
            "employment_missing": int(state["employment_2025"].isna().sum()),
            "wage_p10_missing": int(state["annual_wage_p10_2025"].isna().sum()),
            "wage_p90_missing": int(state["annual_wage_p90_2025"].isna().sum()),
            "total_state_rows": int(len(state)),
        }
        return {
            "status": "transparent",
            "checks": checks,
            "state_suppression": state_suppression,
            "vintage_alignment": self.data_vintage_notice(),
            "rules": [
                "Suppressed or missing official values are never filled with invented numbers.",
                "State rankings exclude rows when the required metric is unavailable and disclose the exclusion.",
                "Qualitative degree links are not interpreted as placement rates or legal requirements.",
                "CareerProof-derived scores are always labeled separately from direct official values.",
            ],
        }

    def resolve(self, value: str) -> ResolvedOccupation | None:
        value = value.strip()
        if value in self._row_by_soc:
            row = self._row_by_soc[value]
            return ResolvedOccupation(value, str(row.occupation_title))
        match = self.store.best_occupation(value)
        if not match:
            return None
        return ResolvedOccupation(str(match["soc_code"]), str(match["occupation_title"]))

    def _related_degrees(self, soc_code: str, limit: int = 5) -> list[dict[str, str]]:
        return [dict(item) for item in self._degrees_by_soc.get(soc_code, [])[:limit]]

    def _public_profile(self, soc_code: str) -> dict[str, Any]:
        row = self._row_by_soc[soc_code]
        annual_openings = safe_value(row.annual_openings_2024_2034_thousands)
        annual_openings = annual_openings * 1000 if annual_openings is not None else None
        resilience_score = round(float(row.resilience_score), 1)
        return {
            "soc_code": soc_code,
            "occupation_title": str(row.occupation_title),
            "category": str(row.category),
            "description": safe_value(row.description),
            "median_wage": safe_value(row.annual_median_wage_2025),
            "wage_p10": safe_value(row.annual_wage_p10_2025),
            "wage_p90": safe_value(row.annual_wage_p90_2025),
            "employment": safe_value(row.employment_2025),
            "growth_percent": safe_value(row.employment_change_percent_2024_2034),
            "annual_openings": annual_openings,
            "education": safe_value(row.typical_entry_education),
            "job_zone": safe_value(row.onet_job_zone),
            "state_coverage": int(row.state_coverage_count),
            "stability_score": round(float(row.stability_score), 1),
            "resilience_score": resilience_score,
            "resilience_label": self._resilience_label(resilience_score),
            "wage_range": {
                "p10": safe_value(row.annual_wage_p10_2025),
                "median": safe_value(row.annual_median_wage_2025),
                "p90": safe_value(row.annual_wage_p90_2025),
                "label": "Published national wage percentiles, not an individual offer range",
            },
            "related_degrees": self._related_degrees(soc_code),
            "top_skills": self._skills_by_soc.get(soc_code, [])[:6],
        }

    def universe(self, category: str | None = None, per_category: int = 8) -> dict[str, Any]:
        categories: list[dict[str, Any]] = []
        nodes: list[dict[str, Any]] = []
        edges: list[dict[str, str]] = []
        selected_categories = [category] if category in CATEGORY_META else list(CATEGORY_META)
        for cat_index, cat in enumerate(selected_categories):
            meta = CATEGORY_META[cat]
            category_id = f"category:{meta['slug']}"
            cat_rows = self.occupations.loc[self.occupations["category"].eq(cat)]
            categories.append({
                "id": category_id,
                "label": cat,
                "slug": meta["slug"],
                "icon": meta["icon"],
                "accent": meta["accent"],
                "occupation_count": int(len(cat_rows)),
                "median_wage": safe_value(cat_rows["annual_median_wage_2025"].median()),
                "median_growth": safe_value(cat_rows["employment_change_percent_2024_2034"].median()),
                "total_openings": safe_value(cat_rows["annual_openings_2024_2034_thousands"].sum() * 1000),
                "index": cat_index,
            })
            wanted = FEATURED_BY_CATEGORY.get(cat, [])
            chosen: list[str] = []
            for title in wanted:
                code = self.store.title_to_code.get(title)
                if code and code in set(cat_rows["soc_code"]):
                    chosen.append(code)
            if len(chosen) < per_category:
                score = cat_rows[["soc_code", "salary_score", "growth_score", "openings_score", "employment_score"]].copy()
                score["blend"] = score[["salary_score", "growth_score", "openings_score", "employment_score"]].mean(axis=1)
                for code in score.nlargest(per_category * 2, "blend")["soc_code"]:
                    if code not in chosen:
                        chosen.append(str(code))
                    if len(chosen) >= per_category:
                        break
            for index, code in enumerate(chosen[:per_category]):
                profile = self._public_profile(code)
                node_id = f"career:{code}"
                nodes.append({**profile, "id": node_id, "parent": category_id, "index": index})
                edges.append({"source": category_id, "target": node_id, "type": "category"})
        return {
            "center": {"id": "careerproof", "label": "Your Future", "subtitle": "Powered by proof"},
            "categories": categories,
            "nodes": nodes,
            "edges": edges,
            "legend": [
                {"label": "Official value", "description": "Published directly by BLS, Census, BEA, NCES, or O*NET"},
                {"label": "CareerProof-derived", "description": "Transparent calculation from official variables"},
            ],
        }

    def _education_fit(self, required: Any, maximum: str | None) -> float:
        if not maximum or maximum == "No limit":
            return 80.0
        req_rank = EDUCATION_ORDER.get(str(required), 4)
        max_rank = EDUCATION_ORDER.get(maximum, 6)
        if req_rank <= max_rank:
            return 100.0
        if req_rank == max_rank + 1:
            return 35.0
        return 0.0

    def _state_score_for_soc(self, soc_code: str, state: str | None) -> tuple[float, dict[str, Any] | None]:
        if not state:
            row = self._row_by_soc[soc_code]
            return float(row.location_score), None
        item = self._state_row_by_key.get((soc_code, state))
        if item is None:
            return 0.0, None
        rpp_value = self._rpp_by_state.get(state, 100.0)
        nominal = safe_value(item.annual_median_wage_2025)
        adjusted = float(nominal) * 100 / rpp_value if nominal is not None else None
        employment = safe_value(item.employment_2025)
        lq = safe_value(item.location_quotient)
        score = 35.0
        if employment is not None:
            score += min(25.0, math.log10(float(employment) + 1) / 6 * 25)
        if lq is not None:
            score += min(20.0, float(lq) / 2 * 20)
        if nominal is not None:
            score += 20.0
        return min(score, 100.0), {
            "state": state,
            "nominal_median_wage": nominal,
            "purchasing_power_wage": round(adjusted, 0) if adjusted is not None else None,
            "regional_price_parity": rpp_value,
            "employment": employment,
            "location_quotient": lq,
        }

    @staticmethod
    def _normalize_weights(weights: dict[str, float] | None) -> dict[str, float]:
        defaults = dict(WEIGHT_DEFAULTS)
        if weights:
            for key in defaults:
                if key in weights:
                    defaults[key] = max(0.0, float(weights[key]))
        total = sum(defaults.values()) or 1.0
        return {key: value / total for key, value in defaults.items()}

    @staticmethod
    def _category_affinity(category: str, interests: list[str]) -> float:
        if not interests:
            return 50.0
        affinities: list[float] = []
        for interest in interests:
            categories = INTEREST_CATEGORIES.get(normalize(interest), ())
            if not categories:
                continue
            if category == categories[0]:
                affinities.append(100.0)
            elif category in categories[1:]:
                affinities.append(70.0)
            else:
                affinities.append(0.0)
        if not affinities:
            return 50.0
        return max(affinities) * 0.7 + (sum(affinities) / len(affinities)) * 0.3

    def _roadmap_for_soc(self, soc_code: str, selected_skills: list[str], preferred_state: str | None) -> dict[str, Any]:
        profile = self._public_profile(soc_code)
        selected = {normalize(item) for item in selected_skills if normalize(item)}
        missing_skills = [
            item for item in self._skills_by_soc.get(soc_code, [])
            if normalize(item["skill"]) not in selected
        ][:4]
        software = self._software_details_by_soc.get(soc_code, [])[:4]
        degrees = profile.get("related_degrees", [])[:3]
        actions: list[dict[str, str]] = []
        if missing_skills:
            names = ", ".join(item["skill"] for item in missing_skills[:3])
            actions.append({"type": "skill", "label": "Build evidence of key skills", "detail": names})
        if software:
            names = ", ".join(item["software"] for item in software[:3])
            actions.append({"type": "tool", "label": "Practice common tools", "detail": names})
        if degrees:
            names = ", ".join(item["cip_title"] for item in degrees[:2])
            actions.append({"type": "education", "label": "Explore related programs", "detail": names})
        if preferred_state:
            actions.append({"type": "location", "label": f"Validate the {preferred_state} market", "detail": "Compare state employment, purchasing-power pay, and concentration before deciding."})
        return {
            "label": "CareerProof action roadmap",
            "actions": actions[:4],
            "boundary": "These are evidence-backed research prompts, not required steps or a guarantee of employment.",
        }

    @staticmethod
    def data_vintage_notice() -> dict[str, Any]:
        return {
            "headline": "Official sources describe different measurement periods",
            "message": "Wages use May 2025 estimates, projections cover 2024–2034, O*NET work content uses release 30.3, degree earnings use the 2024 ACS, and regional price levels use 2024 BEA RPP. They should not be treated as one synchronized snapshot.",
            "vintages": [
                {"source": "BLS OEWS", "vintage": "May 2025", "use": "Wages and employment"},
                {"source": "BLS Employment Projections", "vintage": "2024–2034", "use": "Growth and annual openings"},
                {"source": "O*NET", "vintage": "30.3", "use": "Skills, knowledge, tasks, tools, and job zones"},
                {"source": "Census ACS", "vintage": "2024 1-Year", "use": "Broad degree-field earnings"},
                {"source": "BEA RPP", "vintage": "2024", "use": "State price-level adjustment"},
                {"source": "NCES/BLS crosswalk", "vintage": "CIP 2020 / SOC 2018", "use": "Qualitative degree relationships"},
            ],
        }

    def interpret_profile(
        self,
        *,
        profile_text: str = "",
        interests: list[str] | None = None,
        skills: list[str] | None = None,
        education_max: str | None = "Bachelor's degree",
        preferred_state: str | None = None,
        salary_goal: float | None = None,
        work_environment: list[str] | None = None,
        remote_preference: str | None = "Flexible",
        willing_to_relocate: bool = True,
        salary_is_hard: bool = False,
        education_is_hard: bool = True,
        location_is_hard: bool = False,
        weights: dict[str, float] | None = None,
    ) -> dict[str, Any]:
        """Return a structured, editable interpretation before ranking.

        This is deliberately controlled parsing.  The user approves or edits the
        interpretation before the deterministic calculation is run.
        """

        raw_text = " ".join(profile_text.split())[:1200]
        profile_replacements = {
            "enginering": "engineering", "enginer": "engineer", "salery": "salary",
            "resillent": "resilient", "resiliant": "resilient", "automatoin": "automation",
            "nucelar": "nuclear", "maryalnd": "Maryland", "bachlors": "bachelor's",
        }
        corrected_text = raw_text
        input_corrections: list[dict[str, str]] = []
        for wrong, right in profile_replacements.items():
            match = re.search(rf"\b{re.escape(wrong)}\b", corrected_text, flags=re.IGNORECASE)
            if match:
                input_corrections.append({"from": match.group(0), "to": right})
                corrected_text = re.sub(rf"\b{re.escape(wrong)}\b", right, corrected_text, flags=re.IGNORECASE)
        raw_text = corrected_text
        normalized_text = normalize(raw_text)
        def unique_casefold(values: list[str]) -> list[str]:
            seen: set[str] = set()
            output: list[str] = []
            for value in values:
                cleaned = " ".join(str(value).split())
                key = cleaned.casefold()
                if cleaned and key not in seen:
                    seen.add(key); output.append(cleaned)
            return output
        interpreted_interests = unique_casefold(interests or [])
        interest_patterns = {
            "Electronics": ("electronics", "electrical circuits", "circuit design", "hardware", "arduino"),
            "Programming": ("programming", "coding", "software development", "computer science"),
            "Writing": ("writing", "journalism", "technical writing", "author"),
            "Public Speaking": ("public speaking", "presenting", "presentations", "debate"),
            "Law": (" law ", "legal", "lawyer", "attorney", "court"),
            "Politics": ("politics", "political", "public policy", "government"),
            "Helping People": ("helping people", "care for people", "counseling", "community service"),
            "Science": ("science", "laboratory", "physics", "chemistry", "biology"),
            "Business": ("business", "finance", "marketing", "entrepreneurship"),
            "Creative Work": ("creative work", "creative design", "visual design", "artistic"),
            "Hands-on Work": ("hands on", "hands-on", "repairing", "building things", "field work"),
            "Math": ("mathematics", " math ", "statistics", "quantitative"),
            "Research": ("research", "experiments", "investigation"),
            "Building Things": ("building things", "fabrication", "construction", "prototyping"),
        }
        padded_text = f" {normalized_text} "
        for canonical, patterns in interest_patterns.items():
            if any(normalize(pattern) in padded_text for pattern in patterns):
                if canonical not in interpreted_interests:
                    interpreted_interests.append(canonical)
        interpreted_skills = unique_casefold(skills or [])
        for skill in KNOWN_SKILLS:
            normalized_skill = normalize(skill)
            if skill == "c++":
                found = "c++" in raw_text.lower()
            else:
                found = len(normalized_skill) >= 3 and f" {normalized_skill} " in padded_text
            label = "C++" if skill == "c++" else skill.title()
            if found and label not in interpreted_skills:
                interpreted_skills.append(label)

        detected_states = self.store.find_states(raw_text)
        if not preferred_state and detected_states:
            preferred_state = detected_states[0]

        if salary_goal is None and raw_text:
            match = re.search(r"\$\s*([0-9]{2,3})(?:,?([0-9]{3}))?", raw_text)
            if match:
                salary_goal = float(match.group(1) + (match.group(2) or "000"))
            else:
                match = re.search(r"\b([0-9]{2,3})\s*k\b", normalized_text)
                if match:
                    salary_goal = float(match.group(1)) * 1000

        education_aliases = [
            ("Doctoral or professional degree", ("doctoral degree", "professional degree", "doctorate", "phd")),
            ("Master's degree", ("master's degree", "masters degree", "master degree")),
            ("Bachelor's degree", ("bachelor's degree", "bachelors degree", "bachelor degree", "four year degree")),
            ("Associate's degree", ("associate's degree", "associates degree", "associate degree", "two year degree")),
            ("Postsecondary nondegree award", ("postsecondary certificate", "nondegree award", "trade certificate")),
            ("High school diploma or equivalent", ("high school diploma", "ged", "no college")),
        ]
        for canonical, aliases in education_aliases:
            if any(normalize(alias) in normalized_text for alias in aliases):
                education_max = canonical
                break
        detected_constraint_language: list[str] = []
        if any(term in normalized_text for term in ("no more than", "maximum", "at most", "education ceiling")):
            detected_constraint_language.append("The wording sounds like a hard education ceiling; confirm the education toggle before ranking.")
        if any(term in normalized_text for term in ("must stay", "cannot relocate", "will not relocate", "only in")):
            detected_constraint_language.append("The wording sounds like a required location; confirm the location and relocation toggles before ranking.")
        if any(term in normalized_text for term in ("at least", "minimum salary", "salary floor", "must earn")) and salary_goal:
            detected_constraint_language.append("The wording sounds like a salary floor; confirm the salary toggle before ranking.")

        environments = list(dict.fromkeys(work_environment or []))
        environment_map = {
            "hands on": "Hands-on",
            "field": "Field or on-site",
            "office": "Office or analytical",
            "people": "People-facing",
            "laboratory": "Laboratory",
            "creative": "Creative",
            "remote": "Remote-compatible",
        }
        for token, label in environment_map.items():
            if token in normalized_text and label not in environments:
                environments.append(label)

        normalized_weights = self._normalize_weights(weights)
        sorted_priorities = sorted(normalized_weights.items(), key=lambda item: -item[1])
        priority_labels = {
            "interest_fit": "Interest and skill fit", "resilience": "AI resilience", "salary": "Salary",
            "growth": "Projected growth", "openings": "Annual openings", "education": "Education access",
            "location": "Location fit", "stability": "Market stability",
        }
        constraints: list[dict[str, str]] = []
        if education_max and education_max != "No limit":
            constraints.append({"label": "Education ceiling", "value": education_max, "strength": "Hard" if education_is_hard else "Preference"})
        if preferred_state:
            constraints.append({"label": "Location", "value": preferred_state, "strength": "Hard" if location_is_hard else "Preference"})
        if salary_goal:
            constraints.append({"label": "Median salary target", "value": f"${salary_goal:,.0f}+", "strength": "Hard" if salary_is_hard else "Preference"})
        constraints.append({"label": "Relocation", "value": "Willing" if willing_to_relocate else "Not willing", "strength": "User choice"})
        if remote_preference:
            constraints.append({"label": "Remote preference", "value": remote_preference, "strength": "Preference"})

        warnings: list[str] = []
        warnings.extend(detected_constraint_language)
        if remote_preference and normalize(remote_preference) not in {"flexible", "no preference"}:
            warnings.append("The bundled datasets do not provide a reliable occupation-level remote-work rate, so remote preference is shown but not used as a hard score.")
        if not interpreted_interests and not interpreted_skills:
            warnings.append("Add at least one interest or skill for a more personal match. Otherwise the result will lean on opportunity and resilience variables.")
        if input_corrections:
            repairs = ", ".join(f"{item['from']} → {item['to']}" for item in input_corrections)
            warnings.append(f"CareerProof repaired likely input errors for review: {repairs}. Your original intent was not otherwise changed.")
        if salary_goal is not None and salary_goal < 20_000:
            warnings.append("The salary target is unusually low for an annual salary. Confirm that you did not enter an hourly rate or omit a zero.")
        if salary_goal is not None and salary_goal > 500_000:
            warnings.append("The salary target is unusually high for an occupation-level median. Confirm the amount before using it as a hard constraint.")
        if salary_is_hard and not salary_goal:
            warnings.append("Salary is marked as a hard constraint, but no salary target is entered. The hard toggle will have no effect.")
        if education_is_hard and (not education_max or education_max == "No limit"):
            warnings.append("Education is marked as a hard constraint, but no education ceiling is selected.")
        if not willing_to_relocate and not preferred_state:
            warnings.append("Relocation is disabled but no preferred state is selected. Add a location so CareerProof can check geographic coverage.")
        if preferred_state:
            valid_states = {str(value).casefold() for value in self.store.state_names}
            if str(preferred_state).casefold() not in valid_states:
                warnings.append(f"{preferred_state} was not found in the bundled state data. Review the spelling or choose a published state.")
        if any(term in normalized_text for term in ("no college", "avoid college", "without college")) and education_max in {"Bachelor's degree", "Master's degree", "Doctoral or professional degree"}:
            warnings.append("Your text suggests avoiding college, but the selected education ceiling allows a four-year or graduate degree. Review this conflict before calculating.")
        goal_parts = []
        if interpreted_interests:
            goal_parts.append("matches " + ", ".join(interpreted_interests[:3]))
        goal_parts.append("remains valuable as AI changes work")
        if salary_goal:
            goal_parts.append(f"targets a published median near ${salary_goal:,.0f}")
        goal = "Find careers that " + ", ".join(goal_parts) + "."
        return {
            "status": "ready",
            "goal": goal,
            "interests": interpreted_interests[:12],
            "skills": interpreted_skills[:20],
            "work_environment": environments[:8],
            "constraints": constraints,
            "priorities": [
                {"key": key, "label": priority_labels[key], "weight": round(value * 100, 1)}
                for key, value in sorted_priorities
            ],
            "assumptions": [
                "Median wage is treated as an occupation-level comparison, not an individual salary prediction.",
                "AI resilience is a transparent relative profile, not a guarantee that a career cannot be automated.",
                "Preferred-state records are used only when BLS published the occupation in that state.",
            ],
            "warnings": warnings,
            "input_review": {
                "status": "review_needed" if warnings else "clear",
                "corrections": input_corrections,
                "checks": [
                    "Duplicate interests and skills were removed without changing meaning.",
                    "Salary, education, location, and relocation settings were checked for conflicts.",
                    "Likely spelling repairs are disclosed and remain editable before ranking.",
                ],
            },
            "requires_confirmation": True,
            "normalized_profile": {
                "profile_text": raw_text,
                "interests": interpreted_interests[:12],
                "skills": interpreted_skills[:20],
                "education_max": education_max,
                "preferred_state": preferred_state,
                "salary_goal": salary_goal,
                "work_environment": environments[:8],
                "remote_preference": remote_preference,
                "willing_to_relocate": willing_to_relocate,
                "salary_is_hard": salary_is_hard,
                "education_is_hard": education_is_hard,
                "location_is_hard": location_is_hard,
                "weights": {key: round(value * 100, 1) for key, value in normalized_weights.items()},
            },
        }

    def _feasibility_for_row(
        self,
        row: Any,
        *,
        education_max: str | None,
        preferred_state: str | None,
        salary_goal: float | None,
        salary_is_hard: bool,
        education_is_hard: bool,
        location_is_hard: bool,
    ) -> dict[str, Any]:
        checks: list[dict[str, Any]] = []
        hard_failures: list[str] = []
        warnings: list[str] = []
        education_fit = self._education_fit(row.typical_entry_education, education_max)
        education_pass = education_fit > 0
        checks.append({
            "key": "education", "label": "Education ceiling", "passed": education_pass,
            "hard": education_is_hard, "required": safe_value(row.typical_entry_education), "selected": education_max or "No limit",
        })
        if not education_pass:
            message = f"Typical entry education is {row.typical_entry_education}, above the selected {education_max}."
            (hard_failures if education_is_hard else warnings).append(message)

        wage = safe_value(row.annual_median_wage_2025)
        salary_pass = salary_goal is None or (wage is not None and float(wage) >= float(salary_goal))
        checks.append({
            "key": "salary", "label": "Median salary target", "passed": salary_pass,
            "hard": salary_is_hard, "published_median": wage, "selected": salary_goal,
        })
        if not salary_pass and salary_goal:
            message = "The published national median wage does not meet the selected target." if wage is not None else "The median wage is not published."
            (hard_failures if salary_is_hard else warnings).append(message)

        location_pass = True
        if preferred_state:
            location_pass = (str(row.soc_code), preferred_state) in self._state_row_by_key
            checks.append({
                "key": "location", "label": "Preferred-state coverage", "passed": location_pass,
                "hard": location_is_hard, "selected": preferred_state,
            })
            if not location_pass:
                message = f"BLS did not publish a May 2025 {preferred_state} estimate for this occupation."
                (hard_failures if location_is_hard else warnings).append(message)

        status = "blocked" if hard_failures else "tradeoff" if warnings else "passes"
        return {
            "status": status,
            "passes_hard_constraints": not hard_failures,
            "checks": checks,
            "hard_failures": hard_failures,
            "warnings": warnings,
        }

    @staticmethod
    def _scenario_label(key: str) -> str:
        return {
            "balanced": "Balance everything",
            "maximize_income": "Maximize income",
            "maximize_resilience": "Maximize AI resilience",
            "maximize_opportunity": "Maximize opportunity",
            "minimize_education": "Minimize education burden",
            "stay_near_home": "Prioritize location",
        }.get(key, key.replace("_", " ").title())

    def _sensitivity_analysis(self, candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
        scenarios: list[dict[str, Any]] = []
        for scenario_key, weights in SCENARIO_PRESETS.items():
            normalized = self._normalize_weights(weights)
            ranked = sorted(
                candidates,
                key=lambda item: -sum(float(item["score_components"].get(key, 0)) * normalized[key] for key in normalized),
            )
            if not ranked:
                continue
            top_rows = []
            for rank, item in enumerate(ranked[:4], start=1):
                score = sum(float(item["score_components"].get(key, 0)) * normalized[key] for key in normalized)
                top_rows.append({"rank": rank, "soc_code": item["soc_code"], "occupation_title": item["occupation_title"], "score": round(score, 1)})
            scenarios.append({
                "key": scenario_key,
                "label": self._scenario_label(scenario_key),
                "top_career": top_rows[0],
                "ranking": top_rows,
                "weights": {key: round(value * 100, 1) for key, value in normalized.items()},
            })
        return scenarios

    @staticmethod
    def _component_contributions(components: dict[str, float], weights: dict[str, float]) -> dict[str, float]:
        return {key: round(float(components.get(key, 0)) * float(weights[key]), 2) for key in weights}

    def _recommendation_challenge(
        self,
        item: dict[str, Any],
        alternative: dict[str, Any] | None,
        normalized_weights: dict[str, float],
    ) -> dict[str, Any]:
        weakest = sorted(item["score_components"].items(), key=lambda pair: pair[1])[:3]
        missing: list[str] = []
        if item.get("median_wage") is None:
            missing.append("National median wage is suppressed or unavailable.")
        if item.get("growth_percent") is None:
            missing.append("Projected growth is unavailable.")
        if item.get("annual_openings") is None:
            missing.append("Annual openings are unavailable.")
        if item.get("preferred_state_detail") is None:
            missing.append("The selected-state lens is missing or was not selected.")
        alternative_message = None
        if alternative:
            advantages = []
            for key, value in alternative["score_components"].items():
                if value - item["score_components"].get(key, 0) >= 8:
                    advantages.append(key.replace("_", " "))
            alternative_message = (
                f"{alternative['occupation_title']} is the strongest challenger"
                + (f" because it is stronger on {', '.join(advantages[:2])}." if advantages else ".")
            )
        return {
            "weakest_evidence": [
                {"component": key, "score": round(float(score), 1), "weighted_contribution": round(float(score) * normalized_weights[key], 2)}
                for key, score in weakest
            ],
            "missing_or_limited_evidence": missing or ["No core variable is missing, but national occupation data still cannot describe a specific employer or individual outcome."],
            "assumptions": [
                "User-selected weights correctly represent the decision.",
                "National occupation profiles are a useful approximation for the user's intended role.",
                "Different source vintages can be compared as decision context but not as one synchronized measurement.",
            ],
            "strongest_alternative": alternative_message,
            "question_to_ask": "Which priority would you be most willing to trade away, and what evidence would change your mind?",
        }

    @staticmethod
    def _dedupe_group(items: list[dict[str, Any]], limit: int = 3) -> list[dict[str, Any]]:
        seen: set[str] = set()
        output: list[dict[str, Any]] = []
        for item in items:
            if item["soc_code"] in seen:
                continue
            seen.add(item["soc_code"])
            output.append(item)
            if len(output) >= limit:
                break
        return output

    def _result_groups(self, candidates: list[dict[str, Any]], preferred_state: str | None) -> dict[str, list[dict[str, Any]]]:
        relevant = sorted(candidates, key=lambda item: -item["careerproof_score"])
        high_upside = sorted(candidates, key=lambda item: -(item["score_components"]["salary"] * 0.45 + item["score_components"]["growth"] * 0.35 + item["score_components"]["openings"] * 0.20))
        fastest = sorted(candidates, key=lambda item: (EDUCATION_ORDER.get(str(item.get("education")), 6), -item["careerproof_score"]))
        highest_pay = sorted(candidates, key=lambda item: -(item.get("median_wage") or 0))
        resilient = sorted(candidates, key=lambda item: -item.get("resilience_score", 0))
        location = sorted(candidates, key=lambda item: -item["score_components"]["location"])
        unexpected = [item for item in relevant if item["score_components"]["interest_fit"] < 55 and item["careerproof_score"] >= 55]
        return {
            "strongest_matches": self._dedupe_group(relevant, 4),
            "high_upside_alternatives": self._dedupe_group(high_upside, 3),
            "unexpected_matches": self._dedupe_group(unexpected or relevant[4:], 3),
            "fastest_entry": self._dedupe_group(fastest, 3),
            "highest_pay": self._dedupe_group(highest_pay, 3),
            "strongest_resilience": self._dedupe_group(resilient, 3),
            "best_geographic_matches": self._dedupe_group(location, 3) if preferred_state else [],
        }

    def path_builder(
        self,
        *,
        interests: list[str],
        skills: list[str],
        education_max: str | None,
        preferred_state: str | None,
        salary_goal: float | None,
        weights: dict[str, float] | None,
        limit: int = 8,
        profile_text: str = "",
        work_environment: list[str] | None = None,
        remote_preference: str | None = "Flexible",
        willing_to_relocate: bool = True,
        salary_is_hard: bool = False,
        education_is_hard: bool = True,
        location_is_hard: bool = False,
    ) -> dict[str, Any]:
        interpretation = self.interpret_profile(
            profile_text=profile_text,
            interests=interests,
            skills=skills,
            education_max=education_max,
            preferred_state=preferred_state,
            salary_goal=salary_goal,
            work_environment=work_environment or [],
            remote_preference=remote_preference,
            willing_to_relocate=willing_to_relocate,
            salary_is_hard=salary_is_hard,
            education_is_hard=education_is_hard,
            location_is_hard=location_is_hard,
            weights=weights,
        )
        profile = interpretation["normalized_profile"]
        interests = list(profile["interests"])
        skills = list(profile["skills"])
        education_max = profile["education_max"]
        preferred_state = profile["preferred_state"]
        salary_goal = profile["salary_goal"]
        work_environment = list(profile["work_environment"])
        salary_is_hard = bool(profile["salary_is_hard"])
        education_is_hard = bool(profile["education_is_hard"])
        location_is_hard = bool(profile["location_is_hard"])

        expanded_interests = [INTEREST_KEYWORDS.get(normalize(item), item) for item in interests]
        query_parts = [*expanded_interests, *skills, *work_environment]
        query = " ".join(part for part in query_parts if part).strip() or "career opportunity skills"
        query_vector = self.vectorizer.transform([query])
        similarities = cosine_similarity(query_vector, self.text_matrix)[0]
        similarity_scaled = similarities / max(float(similarities.max()), 1e-9) * 100
        interest_similarities: list[np.ndarray] = []
        for interest_query in expanded_interests:
            vector = self.vectorizer.transform([interest_query])
            values = cosine_similarity(vector, self.text_matrix)[0]
            interest_similarities.append(values / max(float(values.max()), 1e-9) * 100)
        normalized_weights = self._normalize_weights(weights)
        selected_skill_tokens = [normalize(item) for item in skills if normalize(item)]
        environment_tokens = {normalize(item) for item in work_environment}
        candidates: list[dict[str, Any]] = []
        excluded: list[dict[str, Any]] = []

        for index, row in enumerate(self.occupations.itertuples(index=False)):
            corpus = normalize(self._corpus_by_soc.get(row.soc_code, ""))
            direct_matches = [skill for skill in selected_skill_tokens if skill in corpus]
            direct_skill_score = len(direct_matches) / max(len(selected_skill_tokens), 1) * 100 if selected_skill_tokens else 50.0
            if interest_similarities:
                per_interest = sorted((float(values[index]) for values in interest_similarities), reverse=True)
                focused_interest_score = sum(per_interest[: min(2, len(per_interest))]) / min(2, len(per_interest))
            else:
                focused_interest_score = 50.0
            semantic_score = float(similarity_scaled[index]) * 0.60 + focused_interest_score * 0.40
            category_score = self._category_affinity(str(row.category), interests)
            environment_scores: list[float] = []
            if any(token in environment_tokens for token in {"hands on", "field or on site", "laboratory"}):
                environment_scores.append(float(row.resilience_physical_world))
            if "people facing" in environment_tokens:
                environment_scores.append(float(row.resilience_human_trust))
            if "creative" in environment_tokens:
                environment_scores.append(float(row.resilience_creativity_adaptation))
            if "office or analytical" in environment_tokens or "remote compatible" in environment_tokens:
                environment_scores.append(float(row.ai_augmentation_score))
            environment_score = sum(environment_scores) / len(environment_scores) if environment_scores else 50.0
            interest_score = semantic_score * 0.50 + category_score * 0.25 + direct_skill_score * 0.15 + environment_score * 0.10
            education_score = self._education_fit(row.typical_entry_education, education_max)
            location_score, location_detail = self._state_score_for_soc(row.soc_code, preferred_state)
            feasibility = self._feasibility_for_row(
                row,
                education_max=education_max,
                preferred_state=preferred_state,
                salary_goal=salary_goal,
                salary_is_hard=salary_is_hard,
                education_is_hard=education_is_hard,
                location_is_hard=location_is_hard,
            )
            components = {
                "interest_fit": round(interest_score, 1),
                "resilience": round(float(row.resilience_score), 1),
                "salary": round(float(row.salary_score), 1),
                "growth": round(float(row.growth_score), 1),
                "openings": round(float(row.openings_score), 1),
                "education": round(education_score, 1),
                "location": round(location_score, 1),
                "stability": round(float(row.stability_score), 1),
            }
            contributions = self._component_contributions(components, normalized_weights)
            total_score = round(sum(contributions.values()), 1)
            annual_openings = safe_value(row.annual_openings_2024_2034_thousands)
            annual_openings = annual_openings * 1000 if annual_openings is not None else None
            profile_item = {
                "soc_code": str(row.soc_code),
                "occupation_title": str(row.occupation_title),
                "category": str(row.category),
                "description": safe_value(row.description),
                "median_wage": safe_value(row.annual_median_wage_2025),
                "wage_p10": safe_value(row.annual_wage_p10_2025),
                "wage_p90": safe_value(row.annual_wage_p90_2025),
                "employment": safe_value(row.employment_2025),
                "growth_percent": safe_value(row.employment_change_percent_2024_2034),
                "annual_openings": annual_openings,
                "education": safe_value(row.typical_entry_education),
                "job_zone": safe_value(row.onet_job_zone),
                "state_coverage": int(row.state_coverage_count),
                "stability_score": round(float(row.stability_score), 1),
                "resilience_score": round(float(row.resilience_score), 1),
                "resilience_label": self._resilience_label(float(row.resilience_score)),
            }
            top_components = sorted(contributions.items(), key=lambda item: item[1], reverse=True)[:4]
            reason_labels = {
                "interest_fit": "matches your interests, skills, and work-style signals",
                "resilience": "has a strong transparent human-and-real-world resilience profile",
                "salary": "has comparatively strong published wage outcomes",
                "growth": "has a comparatively strong 2024–2034 projection",
                "openings": "has comparatively strong projected annual openings",
                "education": "fits your selected education ceiling",
                "location": "has a stronger published geographic fit for your selection",
                "stability": "combines market size, openings, and geographic breadth",
            }
            reasons = [reason_labels[key] for key, _ in top_components]
            item = {
                **profile_item,
                "careerproof_score": total_score,
                "score_components": components,
                "weighted_contributions": contributions,
                "matched_skills": direct_matches,
                "interest_breakdown": {
                    "semantic_relevance": round(semantic_score, 1),
                    "career_field_affinity": round(category_score, 1),
                    "selected_skill_evidence": round(direct_skill_score, 1),
                    "work_environment_fit": round(environment_score, 1),
                },
                "reasons": reasons,
                "preferred_state_detail": location_detail,
                "salary_goal_met": bool(salary_goal and safe_value(row.annual_median_wage_2025) is not None and float(row.annual_median_wage_2025) >= salary_goal),
                "feasibility": feasibility,
            }
            if feasibility["passes_hard_constraints"]:
                candidates.append(item)
            else:
                excluded.append(item)

        candidates.sort(key=lambda item: (-item["careerproof_score"], -item["score_components"]["interest_fit"], item["occupation_title"]))
        excluded.sort(key=lambda item: (-item["careerproof_score"], item["occupation_title"]))
        fallback_used = False
        if not candidates:
            candidates = excluded[: max(3, min(limit, 12))]
            fallback_used = True

        selected: list[dict[str, Any]] = []
        category_counts: dict[str, int] = defaultdict(int)
        for item in candidates:
            category = str(item["category"])
            if category_counts[category] >= 4:
                continue
            item["path_label"] = "Primary match" if len(selected) < 3 else "High-upside alternative" if len(selected) < 6 else "Unexpected match"
            selected.append(item)
            category_counts[category] += 1
            if len(selected) >= max(3, min(limit, 12)):
                break

        runner_up = selected[1] if len(selected) > 1 else None

        sensitivity = self._sensitivity_analysis(candidates[:120])
        current_top = selected[0] if selected else None
        changes = []
        if current_top:
            for scenario in sensitivity:
                if scenario["top_career"]["soc_code"] != current_top["soc_code"]:
                    changes.append({
                        "scenario": scenario["label"],
                        "new_top": scenario["top_career"]["occupation_title"],
                        "explanation": f"{scenario['top_career']['occupation_title']} moves to first when you choose the {scenario['label'].lower()} preset.",
                    })
        ranking_explanation = None
        if current_top and runner_up:
            contribution_deltas = {
                key: round(current_top["weighted_contributions"][key] - runner_up["weighted_contributions"][key], 2)
                for key in normalized_weights
            }
            strongest_advantages = sorted(contribution_deltas.items(), key=lambda item: -item[1])[:2]
            strongest_tradeoffs = sorted(contribution_deltas.items(), key=lambda item: item[1])[:2]
            ranking_explanation = {
                "winner": current_top["occupation_title"],
                "runner_up": runner_up["occupation_title"],
                "score_gap": round(current_top["careerproof_score"] - runner_up["careerproof_score"], 1),
                "advantages": [{"component": key, "contribution_gap": value} for key, value in strongest_advantages],
                "tradeoffs": [{"component": key, "contribution_gap": value} for key, value in strongest_tradeoffs],
                "plain_language": f"{current_top['occupation_title']} ranks above {runner_up['occupation_title']} mainly because of " + ", ".join(key.replace("_", " ") for key, _ in strongest_advantages) + ".",
            }

        groups = self._result_groups(candidates[:150], preferred_state)
        portfolio = {}
        if selected:
            primary = selected[0]
            alternatives = [item for item in candidates[:30] if item["soc_code"] != primary["soc_code"]]
            safer = max(alternatives, key=lambda item: item["stability_score"], default=None)
            high_upside = max(alternatives, key=lambda item: item["score_components"]["salary"] * 0.55 + item["score_components"]["growth"] * 0.45, default=None)
            fast_entry = min(alternatives, key=lambda item: EDUCATION_ORDER.get(str(item.get("education")), 6), default=None)
            portfolio = {
                "primary_path": primary,
                "safer_backup": safer,
                "high_upside_option": high_upside,
                "fast_entry_option": fast_entry,
                "boundary": "A portfolio is a planning structure, not a prediction that any path will produce a specific outcome.",
            }

        # Enrich only records that are actually returned. This keeps the full
        # 830-occupation calculation responsive while preserving detailed
        # evidence, task impact, degrees, roadmaps, and confidence on every
        # visible card.
        returned_items: list[dict[str, Any]] = [*selected]
        for values in groups.values():
            returned_items.extend(values)
        for key in ("primary_path", "safer_backup", "high_upside_option", "fast_entry_option"):
            value = portfolio.get(key)
            if isinstance(value, dict):
                returned_items.append(value)
        returned_items.extend(excluded[:5])
        enriched_codes: set[str] = set()
        for item in returned_items:
            soc_code = str(item["soc_code"])
            if soc_code in enriched_codes:
                continue
            enriched_codes.add(soc_code)
            detailed = self._public_profile(soc_code)
            item.update(detailed)
            item["resilience_profile"] = self.career_resilience_profile(soc_code)
            item["roadmap"] = self._roadmap_for_soc(soc_code, skills, preferred_state)
            item["source_confidence"] = {
                "label": "High",
                "score": 94,
                "reason": "Core values are exact SOC-code joins across official BLS and O*NET snapshots.",
            }
            item["decision_confidence"] = self._decision_confidence(soc_code, preferred_state)

        for item in selected:
            alternative = next((candidate for candidate in selected if candidate["soc_code"] != item["soc_code"]), None)
            item["challenge"] = self._recommendation_challenge(item, alternative, normalized_weights)

        return {
            "status": "needs_constraint_review" if fallback_used else "supported",
            "headline": f"{selected[0]['occupation_title']} is the strongest current match" if selected else "No result could be calculated",
            "summary": "CareerProof first interprets the user's goal, then exact code applies hard constraints and calculates a transparent ranking from official occupation data. The ranking changes when the user changes priorities.",
            "interpreted_request": interpretation,
            "results": selected,
            "result_groups": groups,
            "portfolio": portfolio,
            "weights": {key: round(value * 100, 1) for key, value in normalized_weights.items()},
            "query_profile": profile,
            "formula": "Score = user-weighted interest fit + resilience profile + wage percentile + growth percentile + openings percentile + education fit + location fit + market-stability score. Hard constraints are checked before ranking.",
            "method": {
                "interpretation": "Controlled parsing converts free text and form inputs into an editable goal, constraints, and priority profile.",
                "text_matching": "TF-IDF similarity across official occupation descriptions and O*NET work content, calibrated with field affinity, explicit skill evidence, and work-environment signals.",
                "numeric_scoring": "Percentile normalization across 830 detailed occupations with user-controlled weights.",
                "resilience": f"CareerProof Resilience Model {RESILIENCE_MODEL_VERSION}; transparent relative dimensions from official work-profile text.",
                "feasibility_gate": "Education, salary, and location can be treated as hard constraints. Blocked careers are excluded before ranking and reported as near misses.",
                "human_control": "The user reviews the interpretation, chooses all weights, can challenge any recommendation, and makes the final decision.",
            },
            "ranking_explanation": ranking_explanation,
            "sensitivity": sensitivity,
            "what_would_change_the_recommendation": changes[:5] or [{"scenario": "Current tested presets", "new_top": selected[0]["occupation_title"] if selected else None, "explanation": "The same career remains first across the tested presets; changing hard constraints or adding new evidence could still change it."}],
            "excluded_by_hard_constraints": {
                "count": len(excluded),
                "near_misses": excluded[:5],
                "fallback_used": fallback_used,
            },
            "data_freshness": self.data_vintage_notice(),
            "resilience_model": self.resilience_model_card(),
            "sources": [
                self.store.source("bls-oews-national-2025"),
                self.store.source("bls-projections-2024-2034"),
                self.store.source("onet-30-3"),
                self.store.source("bls-oews-state-2025"),
                self.store.source("bea-rpp-2024"),
                self.store.source("nces-cip-soc-2020-2018"),
            ],
            "limitations": [
                "CareerProof scores are derived decision aids, not government ratings or predictions of individual success.",
                "The resilience profile is a transparent relative model, not an official automation probability or a claim that a career cannot be replaced.",
                "Remote-work preference is disclosed but not scored because the bundled data does not support a reliable occupation-level remote rate.",
                "CIP-to-SOC links are qualitative and do not represent placement probabilities.",
            ],
        }

    def compare(
        self,
        occupations: list[str],
        *,
        weights: dict[str, float] | None = None,
        preferred_state: str | None = None,
        user_skills: list[str] | None = None,
        education_max: str | None = None,
        salary_goal: float | None = None,
        salary_is_hard: bool = False,
        education_is_hard: bool = False,
        location_is_hard: bool = False,
    ) -> dict[str, Any]:
        resolved: list[ResolvedOccupation] = []
        for value in occupations:
            item = self.resolve(value)
            if item and item.soc_code not in {entry.soc_code for entry in resolved}:
                resolved.append(item)
        if len(resolved) < 2:
            raise ValueError("Choose at least two distinct occupations.")
        if len(resolved) > 4:
            resolved = resolved[:4]
        normalized_weights = self._normalize_weights(weights)
        selected_skill_tokens = [normalize(item) for item in (user_skills or []) if normalize(item)]
        results: list[dict[str, Any]] = []
        for item in resolved:
            row = self._row_by_soc[item.soc_code]
            corpus = normalize(self._corpus_by_soc.get(item.soc_code, ""))
            skill_score = len([skill for skill in selected_skill_tokens if skill in corpus]) / max(len(selected_skill_tokens), 1) * 100 if selected_skill_tokens else 50.0
            location_score, location_detail = self._state_score_for_soc(item.soc_code, preferred_state)
            education_score = self._education_fit(row.typical_entry_education, education_max) if education_max else float(row.education_access_score)
            components = {
                "interest_fit": round(skill_score, 1),
                "resilience": round(float(row.resilience_score), 1),
                "salary": round(float(row.salary_score), 1),
                "growth": round(float(row.growth_score), 1),
                "openings": round(float(row.openings_score), 1),
                "education": round(float(education_score), 1),
                "location": round(float(location_score), 1),
                "stability": round(float(row.stability_score), 1),
            }
            contributions = self._component_contributions(components, normalized_weights)
            score = round(sum(contributions.values()), 1)
            feasibility = self._feasibility_for_row(
                row,
                education_max=education_max,
                preferred_state=preferred_state,
                salary_goal=salary_goal,
                salary_is_hard=salary_is_hard,
                education_is_hard=education_is_hard,
                location_is_hard=location_is_hard,
            )
            results.append({
                **self._public_profile(item.soc_code),
                "careerproof_score": score,
                "score_components": components,
                "weighted_contributions": contributions,
                "preferred_state_detail": location_detail,
                "feasibility": feasibility,
                "resilience_profile": self.career_resilience_profile(item.soc_code),
                "source_confidence": {"label": "High", "score": 94, "reason": "Core variables are direct BLS and O*NET occupation records joined by exact SOC code."},
                "decision_confidence": self._decision_confidence(item.soc_code, preferred_state),
            })
        results.sort(key=lambda item: (not item["feasibility"]["passes_hard_constraints"], -item["careerproof_score"]))
        for item in results:
            alternative = next((candidate for candidate in results if candidate["soc_code"] != item["soc_code"]), None)
            item["challenge"] = self._recommendation_challenge(item, alternative, normalized_weights)

        top = results[0]
        runner = results[1]
        contribution_deltas = {
            key: round(top["weighted_contributions"][key] - runner["weighted_contributions"][key], 2)
            for key in normalized_weights
        }
        advantages = sorted(contribution_deltas.items(), key=lambda item: -item[1])
        disadvantages = sorted(contribution_deltas.items(), key=lambda item: item[1])
        top_advantage = advantages[0][0].replace("_", " ") if advantages else "the selected priorities"
        runner_advantage = disadvantages[0][0].replace("_", " ") if disadvantages and disadvantages[0][1] < 0 else None
        tradeoff = f"{top['occupation_title']} ranks first mainly because of {top_advantage}."
        if runner_advantage:
            tradeoff += f" {runner['occupation_title']} is stronger on {runner_advantage}."
        if not top["feasibility"]["passes_hard_constraints"]:
            tradeoff += " Every selected career conflicts with at least one hard constraint, so the user should revise the comparison constraints."

        sensitivity = self._sensitivity_analysis(results)
        changes = [
            {
                "scenario": scenario["label"],
                "top_career": scenario["top_career"]["occupation_title"],
                "changed": scenario["top_career"]["soc_code"] != top["soc_code"],
            }
            for scenario in sensitivity
        ]
        return {
            "status": "supported",
            "headline": f"{top['occupation_title']} ranks first for the current priorities",
            "summary": "Raw official values remain visible while the user-controlled score explains the tradeoff. This is not an objective ranking, and hard constraints are shown separately from soft preferences.",
            "results": results,
            "weights": {key: round(value * 100, 1) for key, value in normalized_weights.items()},
            "formula": "Weighted score uses interest/skill evidence, CareerProof resilience, wage, growth, openings, education fit, location fit, and a transparent market-stability score. Hard constraints are evaluated before the ranking is interpreted.",
            "tradeoff_summary": {
                "plain_language": tradeoff,
                "winner": top["occupation_title"],
                "runner_up": runner["occupation_title"],
                "score_gap": round(top["careerproof_score"] - runner["careerproof_score"], 1),
                "advantages": [{"component": key, "contribution_gap": value} for key, value in advantages[:3]],
                "disadvantages": [{"component": key, "contribution_gap": value} for key, value in disadvantages[:3]],
            },
            "sensitivity": sensitivity,
            "ranking_changes": changes,
            "data_freshness": self.data_vintage_notice(),
            "resilience_model_version": RESILIENCE_MODEL_VERSION,
            "sources": [
                self.store.source("bls-oews-national-2025"), self.store.source("bls-projections-2024-2034"),
                self.store.source("onet-30-3"), self.store.source("bls-oews-state-2025"), self.store.source("bea-rpp-2024"),
            ],
            "limitations": [
                "Scores reflect user-selected weights and should not replace personal research, advising, or direct employer information.",
                "National wage and projection records describe occupations, not guaranteed individual outcomes.",
                "The resilience profile is a transparent CareerProof-derived model, not an official automation forecast.",
            ],
        }

    def _decision_confidence(self, soc_code: str, state: str | None = None) -> dict[str, Any]:
        row = self._row_by_soc[soc_code]
        employment = safe_value(row.employment_2025)
        reason = "Large national employment base and broad state coverage."
        score = 90
        label = "High"
        if state:
            state_row = self._state_row_by_key.get((soc_code, state))
            if state_row is None:
                return {"label": "Low", "score": 35, "reason": "No published state estimate is available for the selected occupation."}
            employment = safe_value(state_row.employment_2025)
        if employment is None:
            label, score, reason = "Medium", 65, "Employment is suppressed or unavailable, so practical market size is uncertain."
        elif float(employment) < 500:
            label, score, reason = "Low", 48, "The published estimate represents a small labor market, so rankings should be interpreted cautiously."
        elif float(employment) < 5000:
            label, score, reason = "Medium", 72, "The occupation has a moderate or specialized employment base."
        return {"label": label, "score": score, "reason": reason, "employment_basis": employment}

    def skill_bridge(self, source: str, target: str) -> dict[str, Any]:
        source_item = self.resolve(source)
        target_item = self.resolve(target)
        if not source_item or not target_item:
            raise ValueError("Both source and target occupations must be recognized.")

        source_skills = {normalize(item["skill"]): item for item in self._skills_by_soc.get(source_item.soc_code, [])[:20]}
        target_skills = {normalize(item["skill"]): item for item in self._skills_by_soc.get(target_item.soc_code, [])[:20]}
        shared_keys = [key for key in target_skills if key in source_skills]
        skill_rows: list[dict[str, Any]] = []
        gap_rows: list[dict[str, Any]] = []
        total_target_importance = sum(float(item["importance"]) for item in target_skills.values()) or 1.0
        total_gap = 0.0
        for key, target_skill in target_skills.items():
            source_importance = float(source_skills.get(key, {}).get("importance", 0.0))
            target_importance = float(target_skill["importance"])
            gap = max(target_importance - source_importance, 0.0)
            total_gap += gap
            row = {
                "skill": target_skill["skill"],
                "target_importance": target_importance,
                "source_importance": source_importance,
                "importance_gap": round(gap, 2),
            }
            if key in source_skills:
                skill_rows.append(row)
            if gap >= 0.24:
                gap_rows.append(row)
        skill_readiness = max(0.0, 100 * (1 - total_gap / total_target_importance))
        gap_rows.sort(key=lambda item: (-item["importance_gap"], -item["target_importance"], item["skill"]))

        source_software = {normalize(item["software"]): item for item in self._software_details_by_soc.get(source_item.soc_code, [])[:25]}
        target_software = {normalize(item["software"]): item for item in self._software_details_by_soc.get(target_item.soc_code, [])[:25]}
        shared_software_keys = [key for key in target_software if key in source_software]
        target_only_software = [target_software[key] for key in target_software if key not in source_software]
        software_overlap = len(shared_software_keys) / max(len(target_software), 1) * 100

        source_task_text = " ".join(self._tasks_by_soc.get(source_item.soc_code, [])[:12])
        target_task_text = " ".join(self._tasks_by_soc.get(target_item.soc_code, [])[:12])
        if source_task_text and target_task_text:
            task_vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), min_df=1)
            task_matrix = task_vectorizer.fit_transform([source_task_text, target_task_text])
            task_similarity = float(cosine_similarity(task_matrix[0], task_matrix[1])[0, 0] * 100)
        else:
            task_similarity = 0.0

        transition_similarity = skill_readiness * 0.55 + software_overlap * 0.25 + task_similarity * 0.20
        source_row = self._row_by_soc[source_item.soc_code]
        target_row = self._row_by_soc[target_item.soc_code]
        education_delta = int(target_row.education_rank - source_row.education_rank)
        next_steps = [
            f"Build evidence of {item['skill']} because its O*NET importance is {item['target_importance']:.2f} for the target profile."
            for item in gap_rows[:3]
        ]
        next_steps.extend(
            f"Practice {item['software']}, which appears in the target occupation's O*NET technology profile."
            for item in target_only_software[:2]
        )
        if not next_steps:
            next_steps.append("Compare the occupations' core tasks and education requirements; their top skill labels are similar, but the work context may still differ.")

        return {
            "status": "supported",
            "headline": f"Skill Bridge: {source_item.occupation_title} → {target_item.occupation_title}",
            "summary": f"CareerProof estimates {transition_similarity:.0f}% occupational-profile similarity by combining O*NET skill-importance gaps, technology overlap, and task-language similarity.",
            "source": self._public_profile(source_item.soc_code),
            "target": self._public_profile(target_item.soc_code),
            "overlap_score": round(transition_similarity, 1),
            "component_scores": {
                "skill_importance_readiness": round(skill_readiness, 1),
                "software_overlap": round(software_overlap, 1),
                "task_similarity": round(task_similarity, 1),
            },
            "shared_skills": sorted(skill_rows, key=lambda item: (-item["target_importance"], item["skill"])),
            "skills_to_build": gap_rows[:8],
            "shared_software": [target_software[key] for key in shared_software_keys[:10]],
            "software_to_learn": target_only_software[:8],
            "education_delta": education_delta,
            "wage_difference": safe_value(
                float(target_row.annual_median_wage_2025) - float(source_row.annual_median_wage_2025)
                if pd.notna(target_row.annual_median_wage_2025) and pd.notna(source_row.annual_median_wage_2025) else None
            ),
            "growth_difference": safe_value(
                float(target_row.employment_change_percent_2024_2034) - float(source_row.employment_change_percent_2024_2034)
                if pd.notna(target_row.employment_change_percent_2024_2034) and pd.notna(source_row.employment_change_percent_2024_2034) else None
            ),
            "next_steps": next_steps[:5],
            "formula": "CareerProof transition similarity = 55% skill-importance readiness + 25% target-technology overlap + 20% TF-IDF task similarity.",
            "source_confidence": {"label": "High", "score": 92, "reason": "Skill importance, technology examples, and core tasks come directly from O*NET 30.3."},
            "decision_confidence": {"label": "Medium", "score": 76, "reason": "The derived similarity compares occupational profiles; it does not measure a person's proficiency, readiness, credentials, or likelihood of making the transition."},
            "sources": [self.store.source("onet-30-3"), self.store.source("bls-oews-national-2025"), self.store.source("bls-projections-2024-2034")],
        }

    def degree_search(self, query: str, limit: int = 12) -> list[dict[str, Any]]:
        query_norm = normalize(query)
        unique = self.store.degree_crosswalk[["cip_code", "cip_title"]].drop_duplicates()
        scored: list[tuple[float, str, str]] = []
        for row in unique.itertuples(index=False):
            title_norm = normalize(row.cip_title)
            if not query_norm:
                score = 0.1
            elif query_norm in title_norm:
                score = 2.0 + len(query_norm) / 100
            else:
                q_tokens = set(query_norm.split())
                t_tokens = set(title_norm.split())
                overlap = len(q_tokens & t_tokens) / max(len(q_tokens | t_tokens), 1)
                score = overlap * 0.7 + SequenceMatcher(None, query_norm, title_norm).ratio() * 0.3
            if score >= 0.25:
                scored.append((score, str(row.cip_code), str(row.cip_title)))
        scored.sort(key=lambda item: (-item[0], item[2]))
        results = []
        for score, code, title in scored[:limit]:
            occupation_count = int(self.store.degree_crosswalk.loc[self.store.degree_crosswalk["cip_code"].eq(code), "soc_code"].nunique())
            results.append({"cip_code": code, "cip_title": title, "occupation_count": occupation_count, "match_score": round(score, 3)})
        return results

    def degree_pathway(self, cip_code: str, limit: int = 18) -> dict[str, Any]:
        rows = self.store.degree_crosswalk.loc[self.store.degree_crosswalk["cip_code"].eq(cip_code)]
        if rows.empty:
            raise ValueError("Degree program not found.")
        cip_title = str(rows.iloc[0]["cip_title"])
        soc_codes = rows["soc_code"].drop_duplicates().tolist()
        careers = self.occupations.loc[self.occupations["soc_code"].isin(soc_codes)].copy()
        careers["pathway_rank"] = (
            careers["salary_score"] * 0.30 + careers["growth_score"] * 0.20 + careers["openings_score"] * 0.25
            + careers["employment_score"] * 0.15 + careers["location_score"] * 0.10
        )
        careers = careers.nlargest(limit, "pathway_rank")
        results = []
        for row in careers.itertuples(index=False):
            item = self._public_profile(str(row.soc_code))
            item["pathway_rank"] = round(float(row.pathway_rank), 1)
            results.append(item)
        return {
            "status": "supported",
            "cip_code": cip_code,
            "cip_title": cip_title,
            "headline": f"Officially crosswalked occupation possibilities for {cip_title}",
            "results": results,
            "relationship_count": int(rows["soc_code"].nunique()),
            "formula": "Displayed careers are NCES/BLS qualitative crosswalk matches, ranked for exploration using published wage, growth, openings, employment, and geographic coverage variables.",
            "source_confidence": {"label": "High", "score": 94, "reason": "The degree-to-occupation links come directly from the official NCES/BLS crosswalk."},
            "decision_confidence": {"label": "Medium", "score": 68, "reason": "The crosswalk is qualitative and conceptual; it is not an empirical placement rate or required-degree map."},
            "sources": [self.store.source("nces-cip-soc-2020-2018"), self.store.source("bls-oews-national-2025"), self.store.source("bls-projections-2024-2034")],
            "limitations": [
                "A crosswalk match means the instructional program and occupation are conceptually related; it is not a placement rate and does not mean the degree is required or that graduates enter the occupation.",
            ],
        }

    def state_opportunity(self, occupation: str) -> dict[str, Any]:
        item = self.resolve(occupation)
        if not item:
            raise ValueError("Occupation not found.")
        rows = self.store.state_wages.loc[self.store.state_wages["soc_code"].eq(item.soc_code)].copy()
        rows = rows.merge(self.store.rpp[["state_name", "regional_price_parity_2024"]], on="state_name", how="left")
        rows["purchasing_power_wage"] = rows["annual_median_wage_2025"] * 100 / rows["regional_price_parity_2024"]
        rows["adjusted_pay_score"] = self._percentile(rows["purchasing_power_wage"])
        rows["employment_score"] = self._percentile(rows["employment_2025"], log=True)
        rows["concentration_score"] = self._percentile(rows["location_quotient"])
        rows["data_quality_score"] = (100 - pd.to_numeric(rows["employment_relative_standard_error"], errors="coerce").fillna(25).clip(0, 100)).clip(0, 100)
        rows["opportunity_score"] = (
            rows["adjusted_pay_score"] * 0.40 + rows["employment_score"] * 0.30
            + rows["concentration_score"] * 0.20 + rows["data_quality_score"] * 0.10
        )
        output = []
        for row in rows.sort_values("opportunity_score", ascending=False).itertuples(index=False):
            employment = safe_value(row.employment_2025)
            confidence = "High" if employment and float(employment) >= 5000 else "Medium" if employment and float(employment) >= 500 else "Low"
            output.append({
                "state": row.state_name,
                "abbreviation": row.state_abbreviation,
                "nominal_median_wage": safe_value(row.annual_median_wage_2025),
                "purchasing_power_wage": safe_value(round(row.purchasing_power_wage, 0) if pd.notna(row.purchasing_power_wage) else None),
                "regional_price_parity": safe_value(row.regional_price_parity_2024),
                "employment": employment,
                "employment_rse": safe_value(row.employment_relative_standard_error),
                "location_quotient": safe_value(row.location_quotient),
                "wage_p10": safe_value(row.annual_wage_p10_2025),
                "wage_p90": safe_value(row.annual_wage_p90_2025),
                "opportunity_score": round(float(row.opportunity_score), 1),
                "decision_confidence": confidence,
            })
        return {
            "status": "supported",
            "occupation": self._public_profile(item.soc_code),
            "headline": f"Where {item.occupation_title.lower()} pay may go furthest",
            "summary": "CareerProof combines published state median wages with BEA regional price parities, employment, concentration, and OEWS sampling quality. The result is a derived exploration score, not an official ranking.",
            "results": output,
            "formula": "Opportunity score = 40% purchasing-power wage percentile + 30% employment percentile + 20% location-quotient percentile + 10% inverse employment-estimate RSE.",
            "data_freshness": self.data_vintage_notice(),
            "sources": [self.store.source("bls-oews-state-2025"), self.store.source("bea-rpp-2024")],
            "source_confidence": {"label": "High", "score": 94, "reason": "Wages, employment, concentration, and price levels are published official estimates."},
            "decision_confidence": {"label": "Medium", "score": 78, "reason": "The combined score is CareerProof-derived and does not include taxes, housing choice, or individual living costs."},
            "limitations": [
                "Regional price parities compare average state price levels and do not represent every household or local area.",
                "States with suppressed wage values cannot receive a complete score.",
            ],
        }

    def occupation_intelligence(self, soc_code: str) -> dict[str, Any] | None:
        if soc_code not in self._row_by_soc:
            return None
        base = self.store.occupation_profile(soc_code)
        if base is None:
            return None
        state = self.state_opportunity(soc_code)
        row = self._row_by_soc[soc_code]
        coverage_components = {
            "national_wage": int(pd.notna(row.annual_median_wage_2025)),
            "projection": int(pd.notna(row.employment_change_percent_2024_2034)),
            "skills": int(bool(base["skills"])),
            "tasks": int(bool(base["tasks"])),
            "education": int(bool(row.typical_entry_education)),
            "states": min(1.0, float(row.state_coverage_count) / 51),
            "degrees": int(bool(self._related_degrees(soc_code))),
        }
        coverage_score = round(sum(float(value) for value in coverage_components.values()) / len(coverage_components) * 100)
        return {
            **base,
            "category": str(row.category),
            "related_degrees": self._related_degrees(soc_code, 8),
            "coverage": {
                "score": coverage_score,
                "components": coverage_components,
                "labels": {
                    "national_wage": "Available" if coverage_components["national_wage"] else "Unavailable",
                    "projection": "Available" if coverage_components["projection"] else "Unavailable",
                    "skills": "Available" if coverage_components["skills"] else "Unavailable",
                    "tasks": "Available" if coverage_components["tasks"] else "Unavailable",
                    "education": "Available" if coverage_components["education"] else "Unavailable",
                    "states": f"{int(row.state_coverage_count)} published geographies",
                    "degrees": "Available" if coverage_components["degrees"] else "Partial or unavailable",
                },
                "source_years": {
                    "wages": "May 2025",
                    "outlook": "2024–2034",
                    "work_content": "O*NET 30.3",
                    "cost_of_living": "BEA 2024",
                    "degree_links": "CIP 2020 / SOC 2018",
                },
            },
            "opportunity_states": state["results"][:10],
            "resilience_profile": self.career_resilience_profile(soc_code),
            "data_freshness": self.data_vintage_notice(),
            "source_confidence": {"label": "High", "score": 94, "reason": "Profile fields are joined by exact SOC code across official source snapshots."},
            "decision_confidence": self._decision_confidence(soc_code),
            "data_lineage": [
                {"source": "BLS OEWS", "provides": "National and state wages, employment, and concentration"},
                {"source": "BLS Employment Projections", "provides": "2024–2034 growth, openings, and entry education"},
                {"source": "O*NET 30.3", "provides": "Skills, knowledge, tasks, software, and job-zone information"},
                {"source": "BEA RPP", "provides": "State price-level adjustment"},
                {"source": "NCES/BLS CIP-SOC", "provides": "Qualitative instructional-program relationships"},
            ],
        }
