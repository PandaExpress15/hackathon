from __future__ import annotations

import json
import math
import re
from difflib import SequenceMatcher
from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd

from .config import METADATA_DIR, PROCESSED_DIR


def safe_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value


def record_to_dict(record: pd.Series | dict[str, Any]) -> dict[str, Any]:
    raw = record.to_dict() if hasattr(record, "to_dict") else dict(record)
    return {str(key): safe_value(value) for key, value in raw.items()}


def normalize(text: str) -> str:
    text = text.lower().replace("&", " and ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


class DataStore:
    def __init__(self) -> None:
        self.occupations = pd.read_csv(PROCESSED_DIR / "occupations.csv", low_memory=False)
        self.state_wages = pd.read_csv(PROCESSED_DIR / "state_wages.csv", low_memory=False)
        self.skills = pd.read_csv(PROCESSED_DIR / "onet_essential_skills.csv")
        self.knowledge = pd.read_csv(PROCESSED_DIR / "onet_knowledge.csv")
        self.software = pd.read_csv(PROCESSED_DIR / "onet_software_tools.csv")
        self.tasks = pd.read_csv(PROCESSED_DIR / "onet_tasks.csv")
        self.onet_education = pd.read_csv(PROCESSED_DIR / "onet_education_responses.csv")
        self.degree_earnings = pd.read_csv(PROCESSED_DIR / "census_degree_earnings_2024.csv")
        self.education_wages = pd.read_csv(PROCESSED_DIR / "education_wages_2025.csv", low_memory=False)
        self.catalog = json.loads((METADATA_DIR / "data_catalog.json").read_text(encoding="utf-8"))
        self.question_catalog = json.loads((METADATA_DIR / "question_catalog.json").read_text(encoding="utf-8"))
        self.aliases = json.loads((METADATA_DIR / "occupation_aliases.json").read_text(encoding="utf-8"))
        self._prepare_indexes()

    def _prepare_indexes(self) -> None:
        self.occupations["normalized_title"] = self.occupations["occupation_title"].fillna("").map(normalize)
        self.state_wages["normalized_title"] = self.state_wages["occupation_title"].fillna("").map(normalize)
        self.title_to_code = dict(zip(self.occupations["occupation_title"], self.occupations["soc_code"]))
        self.normalized_title_to_title = dict(zip(self.occupations["normalized_title"], self.occupations["occupation_title"]))
        self.aliases_normalized = {normalize(key): value for key, value in self.aliases.items()}
        self.state_names = sorted(self.state_wages["state_name"].dropna().unique().tolist(), key=len, reverse=True)
        self.state_abbreviations = {
            str(row.state_abbreviation).upper(): str(row.state_name)
            for row in self.state_wages[["state_abbreviation", "state_name"]].drop_duplicates().itertuples()
            if isinstance(row.state_abbreviation, str)
        }
        self.degree_aliases = {
            "computer science": "Computers, Mathematics, and Statistics",
            "computers": "Computers, Mathematics, and Statistics",
            "mathematics": "Computers, Mathematics, and Statistics",
            "biology": "Biological, Agricultural, and Environmental Sciences",
            "environmental science": "Biological, Agricultural, and Environmental Sciences",
            "physical science": "Physical and Related Sciences",
            "physics": "Physical and Related Sciences",
            "psychology": "Psychology",
            "political science": "Social Sciences",
            "social science": "Social Sciences",
            "engineering": "Engineering",
            "business": "Business",
            "education": "Education",
            "english": "Literature and Languages",
            "literature": "Literature and Languages",
            "languages": "Literature and Languages",
            "history": "Liberal Arts and History",
            "liberal arts": "Liberal Arts and History",
            "visual arts": "Visual and Performing Arts",
            "performing arts": "Visual and Performing Arts",
            "communications": "Communications",
            "mass communications": "Communications",
            "multidisciplinary": "Multidisciplinary Studies",
        }

    def source(self, source_id: str) -> dict[str, str]:
        for source in self.catalog.get("sources", []):
            if source.get("id") == source_id:
                return {
                    "id": str(source.get("id", "")),
                    "title": str(source.get("title", "")),
                    "agency": str(source.get("agency", "")),
                    "vintage": str(source.get("vintage", "")),
                    "url": str(source.get("authoritative_url", "")),
                }
        return {"id": source_id, "title": source_id, "agency": "", "vintage": "", "url": ""}

    def find_occupations(self, query: str, limit: int = 8) -> list[dict[str, Any]]:
        query_norm = normalize(query)
        if not query_norm:
            return []
        candidates: list[tuple[float, str]] = []
        for alias, title in self.aliases_normalized.items():
            if alias in query_norm or query_norm in alias:
                candidates.append((2.0 + len(alias) / 100, title))
        for title_norm, title in self.normalized_title_to_title.items():
            score = 0.0
            if title_norm in query_norm:
                score = 1.95 + min(len(title_norm), 60) / 100
            elif query_norm in title_norm:
                score = 1.75
            else:
                q_tokens = set(query_norm.split())
                t_tokens = set(title_norm.split())
                overlap = len(q_tokens & t_tokens) / max(len(q_tokens | t_tokens), 1)
                sequence = SequenceMatcher(None, query_norm, title_norm).ratio()
                score = overlap * 0.7 + sequence * 0.3
            if score >= 0.28:
                candidates.append((score, title))
        best: dict[str, float] = {}
        for score, title in candidates:
            best[title] = max(best.get(title, 0.0), score)
        results = []
        for title, score in sorted(best.items(), key=lambda item: (-item[1], item[0]))[:limit]:
            row = self.occupations.loc[self.occupations["occupation_title"].eq(title)].iloc[0]
            results.append({
                "soc_code": row["soc_code"],
                "occupation_title": title,
                "score": round(float(score), 3),
                "annual_median_wage_2025": safe_value(row.get("annual_median_wage_2025")),
                "typical_entry_education": safe_value(row.get("typical_entry_education")),
            })
        return results

    def best_occupation(self, query: str) -> dict[str, Any] | None:
        matches = self.find_occupations(query, limit=1)
        return matches[0] if matches else None

    def occupation_by_code(self, soc_code: str) -> dict[str, Any] | None:
        rows = self.occupations.loc[self.occupations["soc_code"].eq(soc_code)]
        if rows.empty:
            return None
        return record_to_dict(rows.iloc[0])

    def occupation_profile(self, soc_code: str) -> dict[str, Any] | None:
        base = self.occupation_by_code(soc_code)
        if base is None:
            return None
        skills = [record_to_dict(row) for _, row in self.skills.loc[self.skills["soc_code"].eq(soc_code)].head(10).iterrows()]
        knowledge = [record_to_dict(row) for _, row in self.knowledge.loc[self.knowledge["soc_code"].eq(soc_code)].head(10).iterrows()]
        software = [record_to_dict(row) for _, row in self.software.loc[self.software["soc_code"].eq(soc_code)].head(12).iterrows()]
        tasks = [record_to_dict(row) for _, row in self.tasks.loc[self.tasks["soc_code"].eq(soc_code)].head(8).iterrows()]
        education = [record_to_dict(row) for _, row in self.onet_education.loc[self.onet_education["soc_code"].eq(soc_code)].head(5).iterrows()]
        return {"occupation": base, "skills": skills, "knowledge": knowledge, "software": software, "tasks": tasks, "education_responses": education}

    def find_states(self, text: str) -> list[str]:
        lowered = text.lower()
        found: list[str] = []
        for name in self.state_names:
            if name.lower() in lowered and name not in found:
                found.append(name)
        tokens = re.findall(r"\b[A-Z]{2}\b", text)
        for token in tokens:
            name = self.state_abbreviations.get(token)
            if name and name not in found:
                found.append(name)
        return found

    def find_degree_fields(self, text: str) -> list[str]:
        lowered = normalize(text)
        found: list[str] = []
        for alias, canonical in sorted(self.degree_aliases.items(), key=lambda item: len(item[0]), reverse=True):
            if normalize(alias) in lowered and canonical not in found:
                found.append(canonical)
        for field in self.degree_earnings["bachelors_field_group"].tolist():
            if field.startswith("All "):
                continue
            if normalize(field) in lowered and field not in found:
                found.append(field)
        return found

    def stats(self) -> dict[str, Any]:
        return {
            "occupations": int(len(self.occupations)),
            "state_occupation_rows": int(len(self.state_wages)),
            "states_and_districts": int(self.state_wages["state_name"].nunique()),
            "degree_field_groups": int(len(self.degree_earnings) - 1),
            "education_geographies": int(self.education_wages["geography"].nunique()),
            "official_sources": int(len(self.catalog.get("sources", []))),
            "latest_wage_vintage": "May 2025",
            "projection_window": "2024–2034",
            "onet_release": "30.3",
            "census_vintage": "2024 ACS 1-Year",
        }


@lru_cache(maxsize=1)
def get_store() -> DataStore:
    return DataStore()
