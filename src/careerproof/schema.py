"""Shared data models and the canonical job-posting schema."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

import pandas as pd
from pydantic import BaseModel, Field


class DataIssue(BaseModel):
    severity: Literal["info", "warning", "error"]
    code: str
    message: str
    count: int = 1
    columns: list[str] = Field(default_factory=list)


class CleaningAction(BaseModel):
    action: str
    count: int
    detail: str


class DataQualityReport(BaseModel):
    raw_rows: int
    cleaned_rows: int
    removed_duplicate_ids: int = 0
    removed_exact_duplicates: int = 0
    near_duplicate_candidates: int = 0
    invalid_dates: int = 0
    invalid_salary_rows: int = 0
    unknown_work_modes: int = 0
    unknown_experience_levels: int = 0
    missing_salary_rows: int = 0
    missing_salary_percentage: float = 0.0
    missing_by_column: dict[str, int] = Field(default_factory=dict)
    columns_detected: list[str] = Field(default_factory=list)
    pii_columns_detected: list[str] = Field(default_factory=list)
    date_min: str | None = None
    date_max: str | None = None
    quality_score: int = 0
    schema_mapping: dict[str, str] = Field(default_factory=dict)
    issues: list[DataIssue] = Field(default_factory=list)
    cleaning_actions: list[CleaningAction] = Field(default_factory=list)


@dataclass(slots=True)
class DatasetBundle:
    raw: pd.DataFrame
    cleaned: pd.DataFrame
    report: DataQualityReport
    fingerprint: str
    display_name: str
    is_synthetic: bool


class FilterClause(BaseModel):
    column: str
    operator: Literal[
        "equals",
        "not_equals",
        "contains",
        "in",
        "greater_than",
        "greater_than_or_equal",
        "less_than",
        "less_than_or_equal",
        "between",
    ]
    value: Any


class QueryPlan(BaseModel):
    intent: Literal[
        "count",
        "top_n",
        "average",
        "median",
        "percentage",
        "distribution",
        "comparison",
        "trend",
        "skill_frequency",
        "missing_data",
        "career_match",
        "unsupported",
    ]
    metric: str = "row_count"
    group_by: list[str] = Field(default_factory=list)
    filters: list[FilterClause] = Field(default_factory=list)
    sort: Literal["ascending", "descending"] = "descending"
    limit: int = Field(default=10, ge=1, le=50)
    chart_type: Literal["bar", "line", "grouped_bar", "donut", "table", "radar"] = "bar"
    minimum_group_size: int = Field(default=1, ge=1, le=100)
    time_grain: Literal["day", "week", "month"] | None = None
    skill_columns: list[str] = Field(default_factory=lambda: ["required_skills"])
    requested_fields: list[str] = Field(default_factory=list)
    question_template: str = ""
    unsupported_reason: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class IntentPrediction(BaseModel):
    label: str
    confidence: float = Field(ge=0.0, le=1.0)
    method: Literal["model", "rule", "fallback"]


class ConfidenceResult(BaseModel):
    label: Literal["High confidence", "Medium confidence", "Low confidence", "Insufficient evidence"]
    score: int = Field(ge=0, le=100)
    reason: str
    breakdown: dict[str, int] = Field(default_factory=dict)


@dataclass(slots=True)
class ExecutionResult:
    status: Literal["supported", "unsupported", "insufficient"]
    headline: str
    summary: str
    table: pd.DataFrame
    source_rows: pd.DataFrame
    calculation: dict[str, Any]
    rows_matched: int
    rows_used: int
    rows_excluded: int
    proof_id: str
    warnings: list[str]
