"""Allowlist validation for structured query plans."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .schema import QueryPlan

ALLOWED_COLUMNS = {
    "posting_id",
    "date_posted",
    "job_title",
    "normalized_role",
    "role_family",
    "company",
    "industry",
    "city",
    "state",
    "country",
    "work_mode",
    "experience_level",
    "employment_type",
    "salary_min",
    "salary_max",
    "salary_midpoint",
    "salary_disclosed",
    "required_skills",
    "preferred_skills",
    "education_requirement",
    "years_experience_required",
    "remote_eligible",
}
ALLOWED_METRICS = {
    "row_count",
    "posting_count",
    "salary_midpoint",
    "missing_salary",
    "missing_count",
    "none",
}
SENSITIVE_COLUMNS = {"recruiter_name", "recruiter_email", "recruiter_phone", "source_record_id"}


@dataclass(slots=True)
class ValidationResult:
    valid: bool
    errors: list[str]
    warnings: list[str]


class QueryValidationError(ValueError):
    pass


def validate_query_plan(plan: QueryPlan, frame: pd.DataFrame) -> ValidationResult:
    if plan.intent == "unsupported":
        return ValidationResult(valid=True, errors=[], warnings=[])

    errors: list[str] = []
    warnings: list[str] = []
    requested_columns = set(plan.group_by)
    requested_columns.update(plan.requested_fields)
    requested_columns.update(filter_clause.column for filter_clause in plan.filters)
    requested_columns.update(plan.skill_columns if plan.intent == "skill_frequency" else [])
    if plan.metric in ALLOWED_COLUMNS:
        requested_columns.add(plan.metric)

    forbidden = requested_columns & SENSITIVE_COLUMNS
    if forbidden:
        errors.append("Sensitive fields cannot be used for analysis: " + ", ".join(sorted(forbidden)))

    unknown = requested_columns - ALLOWED_COLUMNS
    if unknown:
        errors.append("The query plan requested non-allowlisted fields: " + ", ".join(sorted(unknown)))

    missing = {column for column in requested_columns if column not in frame.columns}
    if missing:
        errors.append("The dataset is missing fields required for this question: " + ", ".join(sorted(missing)))

    if plan.metric not in ALLOWED_METRICS:
        errors.append(f"Metric '{plan.metric}' is not allowlisted.")

    if plan.intent in {"median", "average", "comparison"} and "salary_midpoint" not in frame:
        errors.append("Salary fields are unavailable.")
    if plan.intent == "trend" and ("date_posted" not in frame or frame["date_posted"].notna().sum() == 0):
        errors.append("Valid posting dates are unavailable for a trend calculation.")
    if plan.intent == "skill_frequency" and all(
        column not in frame or frame[column].fillna("").astype(str).str.strip().eq("").all()
        for column in plan.skill_columns
    ):
        errors.append("The dataset has no usable skill values.")
    if plan.limit > 25:
        warnings.append("Large result limits may make the evidence harder to read.")

    return ValidationResult(valid=not errors, errors=errors, warnings=warnings)


def assert_valid_query_plan(plan: QueryPlan, frame: pd.DataFrame) -> list[str]:
    result = validate_query_plan(plan, frame)
    if not result.valid:
        raise QueryValidationError(" ".join(result.errors))
    return result.warnings
