"""Safe entity extraction from natural-language questions."""

from __future__ import annotations

import re
from collections.abc import Iterable

import pandas as pd

from .schema import FilterClause

EXPERIENCE_PATTERNS = {
    "Internship": [r"\bintern(ship|ships)?\b"],
    "Entry Level": [r"\bentry[ -]?level\b", r"\bnew grad\b", r"\bjunior\b"],
    "Associate": [r"\bassociate\b"],
    "Mid Level": [r"\bmid[ -]?level\b"],
    "Senior": [r"\bsenior\b", r"\bsr\.?\b"],
}
WORK_MODE_PATTERNS = {
    "Remote": [r"\bremote\b", r"work from home"],
    "Hybrid": [r"\bhybrid\b"],
    "On-site": [r"\bon[ -]?site\b", r"in[ -]?office"],
}
ROLE_PATTERNS = {
    "Electrical Engineer": [r"electrical engineer", r"electrical engineering"],
    "Embedded Systems Engineer": [r"embedded systems?", r"firmware"],
    "Software Engineer": [r"software engineer", r"software engineering"],
    "Data Analyst": [r"data analyst", r"data analytics"],
    "Cybersecurity Analyst": [r"cybersecurity", r"security analyst", r"soc analyst"],
    "IT Support Specialist": [r"it support", r"help desk"],
    "Automation Engineer": [r"automation engineer", r"controls engineer", r"plc engineer"],
    "Product Analyst": [r"product analyst"],
    "Network Engineer": [r"network engineer"],
    "Junior Developer": [r"junior developer", r"web developer"],
}


def _first_matches(text: str, patterns: dict[str, list[str]]) -> list[str]:
    matches: list[str] = []
    for value, expressions in patterns.items():
        if any(re.search(expression, text, re.I) for expression in expressions):
            matches.append(value)
    return matches


def _dataset_values(frame: pd.DataFrame, column: str) -> Iterable[str]:
    if column not in frame:
        return []
    values = frame[column].dropna().astype(str).unique().tolist()
    return sorted(values, key=len, reverse=True)


def extract_filters(question: str, frame: pd.DataFrame) -> list[FilterClause]:
    original_text = question
    text = question.casefold()
    filters: list[FilterClause] = []

    experiences = _first_matches(text, EXPERIENCE_PATTERNS)
    if len(experiences) == 1:
        filters.append(FilterClause(column="experience_level", operator="equals", value=experiences[0]))
    elif len(experiences) > 1:
        filters.append(FilterClause(column="experience_level", operator="in", value=experiences))

    work_modes = _first_matches(text, WORK_MODE_PATTERNS)
    if len(work_modes) == 1:
        filters.append(FilterClause(column="work_mode", operator="equals", value=work_modes[0]))
    elif len(work_modes) > 1:
        filters.append(FilterClause(column="work_mode", operator="in", value=work_modes))

    roles = _first_matches(text, ROLE_PATTERNS)
    if len(roles) == 1:
        filters.append(FilterClause(column="normalized_role", operator="equals", value=roles[0]))
    elif len(roles) > 1:
        filters.append(FilterClause(column="normalized_role", operator="in", value=roles))
    elif "engineering job" in text or "engineering role" in text:
        filters.append(FilterClause(column="role_family", operator="contains", value="Engineering"))

    for column in ["city", "state", "company"]:
        for value in _dataset_values(frame, column):
            if len(value) < 2:
                continue
            if column == "state" and len(value) == 2:
                matched = bool(re.search(rf"(?<![A-Za-z]){re.escape(value)}(?![A-Za-z])", original_text))
            else:
                matched = bool(re.search(rf"(?<!\w){re.escape(value.casefold())}(?!\w)", text))
            if matched:
                filters.append(FilterClause(column=column, operator="equals", value=value))
                break

    return filters
