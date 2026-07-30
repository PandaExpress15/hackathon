"""Deterministic dashboard and unique career-signal features."""

from __future__ import annotations

import re

import numpy as np
import pandas as pd


def dashboard_metrics(frame: pd.DataFrame) -> dict[str, str]:
    salary_coverage = float(frame.get("salary_disclosed", pd.Series(False, index=frame.index)).mean()) if len(frame) else 0.0
    return {
        "Postings": f"{len(frame):,}",
        "Companies": f"{frame['company'].nunique():,}" if "company" in frame else "0",
        "Locations": f"{frame[['city', 'state']].drop_duplicates().shape[0]:,}" if {"city", "state"}.issubset(frame.columns) else "0",
        "Salary coverage": f"{salary_coverage:.0%}",
    }


def explode_skills(frame: pd.DataFrame, column: str = "required_skills") -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    if column not in frame:
        return pd.DataFrame(columns=["Skill", "Postings"])
    for index, value in frame[column].fillna("").items():
        for skill in sorted({item.strip() for item in str(value).split("|") if item.strip()}):
            rows.append({"row_index": index, "Skill": skill})
    if not rows:
        return pd.DataFrame(columns=["Skill", "Postings"])
    return pd.DataFrame(rows)


def top_skills(frame: pd.DataFrame, limit: int = 12) -> pd.DataFrame:
    exploded = explode_skills(frame)
    if exploded.empty:
        return pd.DataFrame(columns=["Skill", "Postings", "Share"])
    result = exploded.groupby("Skill").size().reset_index(name="Postings")
    result["Share"] = result["Postings"] / max(len(frame), 1)
    return result.sort_values(["Postings", "Skill"], ascending=[False, True]).head(limit).reset_index(drop=True)


def career_signal_match(frame: pd.DataFrame, target_role: str, user_skills: str, limit: int = 12) -> tuple[pd.DataFrame, dict[str, object]]:
    subset = frame[frame["normalized_role"].astype(str).str.casefold() == target_role.casefold()].copy()
    signals = top_skills(subset, limit=limit)
    provided = {
        re.sub(r"\s+", " ", item.strip()).casefold()
        for item in re.split(r"[,;|\n]", user_skills or "")
        if item.strip()
    }
    if signals.empty:
        return signals, {"coverage": 0.0, "matched": [], "missing": [], "sample_size": len(subset)}
    signals["Status"] = signals["Skill"].map(lambda skill: "Matched" if skill.casefold() in provided else "Opportunity")
    matched = signals.loc[signals["Status"] == "Matched", "Skill"].tolist()
    missing = signals.loc[signals["Status"] == "Opportunity", "Skill"].tolist()
    weight_total = float(signals["Postings"].sum())
    weight_matched = float(signals.loc[signals["Status"] == "Matched", "Postings"].sum())
    coverage = weight_matched / weight_total if weight_total else 0.0
    return signals, {"coverage": coverage, "matched": matched, "missing": missing, "sample_size": len(subset)}


def scenario_compare(frame: pd.DataFrame, column: str, left: str, right: str) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for label, value in [("Scenario A", left), ("Scenario B", right)]:
        subset = frame[frame[column].astype(str) == value]
        salary = subset["salary_midpoint"].dropna() if "salary_midpoint" in subset else pd.Series(dtype=float)
        rows.append(
            {
                "Scenario": label,
                "Selection": value,
                "Postings": len(subset),
                "Companies": subset["company"].nunique() if "company" in subset else 0,
                "Salary coverage": float(subset["salary_disclosed"].mean()) if len(subset) else 0.0,
                "Median salary midpoint": float(np.median(salary)) if len(salary) else np.nan,
                "Top skill": top_skills(subset, 1).iloc[0]["Skill"] if not top_skills(subset, 1).empty else "Unavailable",
            }
        )
    return pd.DataFrame(rows)
