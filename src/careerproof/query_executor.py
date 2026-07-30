"""Deterministic Pandas calculations for allowlisted query plans."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

import numpy as np
import pandas as pd

from .privacy import mask_dataframe, mask_structure
from .query_validator import assert_valid_query_plan
from .schema import ExecutionResult, FilterClause, QueryPlan


def _apply_clause(frame: pd.DataFrame, clause: FilterClause) -> pd.Series:
    series = frame[clause.column]
    op = clause.operator
    value = clause.value
    if op == "equals":
        if series.dtype == object:
            return series.fillna("").astype(str).str.casefold() == str(value).casefold()
        return series == value
    if op == "not_equals":
        if series.dtype == object:
            return series.fillna("").astype(str).str.casefold() != str(value).casefold()
        return series != value
    if op == "contains":
        return series.fillna("").astype(str).str.contains(str(value), case=False, regex=False)
    if op == "in":
        if not isinstance(value, (list, tuple, set)):
            value = [value]
        if series.dtype == object:
            allowed = {str(item).casefold() for item in value}
            return series.fillna("").astype(str).str.casefold().isin(allowed)
        return series.isin(value)
    if op == "greater_than":
        return pd.to_numeric(series, errors="coerce") > float(value)
    if op == "greater_than_or_equal":
        return pd.to_numeric(series, errors="coerce") >= float(value)
    if op == "less_than":
        return pd.to_numeric(series, errors="coerce") < float(value)
    if op == "less_than_or_equal":
        return pd.to_numeric(series, errors="coerce") <= float(value)
    if op == "between":
        low, high = value
        return pd.to_numeric(series, errors="coerce").between(float(low), float(high), inclusive="both")
    raise ValueError(f"Unsupported operator: {op}")


def apply_filters(frame: pd.DataFrame, filters: list[FilterClause]) -> tuple[pd.DataFrame, list[str]]:
    filtered = frame.copy()
    descriptions: list[str] = []
    for clause in filters:
        mask = _apply_clause(filtered, clause)
        filtered = filtered.loc[mask].copy()
        descriptions.append(f"{clause.column} {clause.operator.replace('_', ' ')} {clause.value}")
    return filtered, descriptions


def compute_proof_id(fingerprint: str, plan: QueryPlan, table: pd.DataFrame) -> str:
    """Return a stable Evidence ID for the privacy-safe calculation payload.

    The same masked fields are placed in the downloadable Evidence Passport. This
    makes the exported proof independently reproducible without exposing contact
    information that may have appeared in user-supplied text or data.
    """

    stable_table = mask_dataframe(table.copy())
    payload = {
        "dataset": fingerprint,
        "plan": mask_structure(plan.model_dump(mode="json")),
        "result": json.loads(stable_table.to_json(orient="records", date_format="iso")),
    }
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()
    return "CP-" + digest[:16].upper()


def _insufficient(
    headline: str,
    summary: str,
    filtered: pd.DataFrame,
    plan: QueryPlan,
    fingerprint: str,
    calculation: dict[str, Any],
    warnings: list[str] | None = None,
) -> ExecutionResult:
    empty = pd.DataFrame()
    return ExecutionResult(
        status="insufficient",
        headline=headline,
        summary=summary,
        table=empty,
        source_rows=filtered.head(100),
        calculation=calculation,
        rows_matched=len(filtered),
        rows_used=0,
        rows_excluded=len(filtered),
        proof_id=compute_proof_id(fingerprint, plan, empty),
        warnings=warnings or [],
    )


def execute_query(
    frame: pd.DataFrame,
    plan: QueryPlan,
    *,
    dataset_fingerprint: str,
) -> ExecutionResult:
    validation_warnings = assert_valid_query_plan(plan, frame)
    timestamp = datetime.now(UTC).isoformat()

    if plan.intent == "unsupported":
        empty = pd.DataFrame()
        return ExecutionResult(
            status="unsupported",
            headline="The dataset cannot support that conclusion",
            summary=plan.unsupported_reason or "The question does not map to an allowlisted calculation.",
            table=empty,
            source_rows=empty,
            calculation={"intent": "unsupported", "timestamp": timestamp},
            rows_matched=0,
            rows_used=0,
            rows_excluded=0,
            proof_id=compute_proof_id(dataset_fingerprint, plan, empty),
            warnings=[],
        )

    filtered, filter_descriptions = apply_filters(frame, plan.filters)
    base_calculation: dict[str, Any] = {
        "intent": plan.intent,
        "metric": plan.metric,
        "fields_used": sorted(set(plan.group_by + [clause.column for clause in plan.filters] + ([plan.metric] if plan.metric in frame else []))),
        "filters_applied": filter_descriptions or ["None"],
        "rows_after_filters": len(filtered),
        "minimum_group_size": plan.minimum_group_size,
        "missing_value_treatment": "Rows missing fields required for the calculation are excluded and counted.",
        "calculated_at": timestamp,
    }

    if filtered.empty:
        return _insufficient(
            "No matching rows",
            "No records matched the selected filters, so no conclusion was generated.",
            filtered,
            plan,
            dataset_fingerprint,
            base_calculation,
            validation_warnings,
        )

    if plan.intent == "count":
        table = pd.DataFrame({"Metric": ["Matching postings"], "Value": [len(filtered)]})
        headline = f"{len(filtered):,} postings match the question"
        summary = f"Counted {len(filtered):,} cleaned records after applying {len(plan.filters)} filter(s)."
        used = len(filtered)
        source = filtered

    elif plan.intent == "top_n":
        if not plan.group_by:
            return _insufficient("No grouping field", "The question did not identify a field to rank.", filtered, plan, dataset_fingerprint, base_calculation)
        group_columns = plan.group_by
        grouped = filtered.groupby(group_columns, dropna=False).size().reset_index(name="Postings")
        grouped = grouped[grouped["Postings"] >= plan.minimum_group_size]
        grouped = grouped.sort_values("Postings", ascending=plan.sort == "ascending").head(plan.limit).reset_index(drop=True)
        if grouped.empty:
            return _insufficient("Not enough evidence", "No group met the minimum sample-size rule.", filtered, plan, dataset_fingerprint, base_calculation)
        table = grouped.rename(columns={column: column.replace("_", " ").title() for column in group_columns})
        top_name = str(table.iloc[0, 0])
        top_count = int(table.iloc[0]["Postings"])
        headline = f"{top_name} leads with {top_count:,} postings"
        summary = f"Grouped {len(filtered):,} matching postings by {', '.join(group_columns)}, counted rows, sorted {plan.sort}, and returned the top {len(table)}."
        used = len(filtered)
        source = filtered

    elif plan.intent == "skill_frequency":
        skill_rows: list[dict[str, Any]] = []
        for row_index, row in filtered.iterrows():
            unique_skills: set[str] = set()
            for column in plan.skill_columns:
                for skill in str(row.get(column, "") or "").split("|"):
                    skill = skill.strip()
                    if skill:
                        unique_skills.add(skill)
            for skill in unique_skills:
                skill_rows.append({"row_index": row_index, "Skill": skill})
        exploded = pd.DataFrame(skill_rows)
        if exploded.empty:
            return _insufficient("No usable skill evidence", "Matching rows did not contain parsed skill values.", filtered, plan, dataset_fingerprint, base_calculation)
        table = exploded.groupby("Skill").size().reset_index(name="Postings")
        table["Share of matched postings"] = table["Postings"] / len(filtered)
        table = table.sort_values(["Postings", "Skill"], ascending=[False, True]).head(plan.limit).reset_index(drop=True)
        top = table.iloc[0]
        headline = f"{top['Skill']} is the strongest signal in {int(top['Postings']):,} postings"
        summary = f"Exploded unique skills from {len(filtered):,} matching postings, counted each skill at most once per posting, and returned the top {len(table)}."
        used = len(filtered)
        source = filtered
        base_calculation["skill_columns"] = plan.skill_columns
        base_calculation["skill_counting_rule"] = "Each skill counts at most once per posting."

    elif plan.intent in {"median", "average", "comparison"}:
        salary_rows = filtered[filtered["salary_midpoint"].notna()].copy()
        excluded = len(filtered) - len(salary_rows)
        if len(salary_rows) < plan.minimum_group_size:
            return _insufficient(
                "Not enough salary evidence",
                f"Only {len(salary_rows)} matching rows had complete salary ranges; at least {plan.minimum_group_size} are required.",
                filtered,
                plan,
                dataset_fingerprint,
                {**base_calculation, "salary_rows_excluded": excluded},
            )
        agg_name = "median" if plan.intent in {"median", "comparison"} else "mean"
        if plan.group_by:
            group_column = plan.group_by[0]
            grouped = salary_rows.groupby(group_column, dropna=False).agg(
                sample_size=("salary_midpoint", "size"),
                salary_midpoint=("salary_midpoint", agg_name),
                salary_low=("salary_min", agg_name),
                salary_high=("salary_max", agg_name),
            ).reset_index()
            grouped = grouped[grouped["sample_size"] >= plan.minimum_group_size]
            grouped = grouped.sort_values("salary_midpoint", ascending=plan.sort == "ascending").head(plan.limit)
            if grouped.empty:
                return _insufficient("Not enough evidence per group", "No group met the minimum salary sample-size rule.", filtered, plan, dataset_fingerprint, base_calculation)
            label = group_column.replace("_", " ").title()
            table = grouped.rename(
                columns={
                    group_column: label,
                    "sample_size": "Sample size",
                    "salary_midpoint": f"{agg_name.title()} midpoint",
                    "salary_low": f"{agg_name.title()} low",
                    "salary_high": f"{agg_name.title()} high",
                }
            ).reset_index(drop=True)
            top = table.iloc[0]
            headline = f"{top[label]} has the highest {agg_name} midpoint at ${float(top[f'{agg_name.title()} midpoint']):,.0f}"
            summary = f"Used {len(salary_rows):,} rows with complete salary ranges, calculated each posting midpoint, grouped by {group_column}, enforced at least {plan.minimum_group_size} postings per group, and calculated the {agg_name}."
        else:
            function = np.nanmedian if agg_name == "median" else np.nanmean
            midpoint = float(function(salary_rows["salary_midpoint"]))
            low = float(function(salary_rows["salary_min"]))
            high = float(function(salary_rows["salary_max"]))
            table = pd.DataFrame(
                {
                    "Statistic": [agg_name.title()],
                    "Low": [low],
                    "High": [high],
                    "Midpoint": [midpoint],
                    "Sample size": [len(salary_rows)],
                }
            )
            headline = f"The {agg_name} salary midpoint is ${midpoint:,.0f}"
            summary = f"Calculated salary midpoints from {len(salary_rows):,} complete ranges and used the {agg_name}; {excluded:,} rows were excluded for missing or invalid salary data."
        used = len(salary_rows)
        source = salary_rows
        base_calculation["salary_rows_excluded"] = excluded
        base_calculation["salary_midpoint_formula"] = "(salary_min + salary_max) / 2"
        base_calculation["aggregation"] = agg_name

    elif plan.intent == "percentage":
        denominator = len(filtered)
        if plan.metric == "missing_salary":
            numerator = int((~filtered["salary_disclosed"]).sum())
            percentage = numerator / denominator if denominator else 0.0
            table = pd.DataFrame(
                {
                    "Salary status": ["Not disclosed", "Disclosed"],
                    "Postings": [numerator, denominator - numerator],
                    "Share": [percentage, 1 - percentage],
                }
            )
            headline = f"{percentage:.1%} of postings do not disclose a complete salary range"
            summary = f"Divided {numerator:,} postings without both salary endpoints by {denominator:,} matching postings."
            base_calculation["numerator"] = numerator
            base_calculation["denominator"] = denominator
            base_calculation["formula"] = "missing salary rows / matching rows"
            used = denominator
            source = filtered
        else:
            return _insufficient("Unsupported percentage", "The requested percentage metric is not implemented.", filtered, plan, dataset_fingerprint, base_calculation)

    elif plan.intent == "trend":
        dated = filtered[filtered["date_posted"].notna()].copy()
        if len(dated) < 5:
            return _insufficient("Not enough dated rows", "At least five valid dates are required for a trend.", filtered, plan, dataset_fingerprint, base_calculation)
        grain = plan.time_grain or "month"
        if grain == "month":
            dated["Period"] = dated["date_posted"].dt.to_period("M").astype(str)
        elif grain == "week":
            dated["Period"] = dated["date_posted"].dt.to_period("W").astype(str)
        else:
            dated["Period"] = dated["date_posted"].dt.date.astype(str)
        table = dated.groupby("Period").size().reset_index(name="Postings").sort_values("Period").reset_index(drop=True)
        if len(table) < 2:
            return _insufficient("Not enough time periods", "The data does not span enough periods for a trend.", filtered, plan, dataset_fingerprint, base_calculation)
        first, last = int(table.iloc[0]["Postings"]), int(table.iloc[-1]["Postings"])
        direction = "higher" if last > first else "lower" if last < first else "the same"
        headline = f"The latest period is {direction} than the earliest period"
        summary = f"Grouped {len(dated):,} valid posting dates by {grain} and counted listings in each of {len(table)} periods. This describes the supplied snapshot, not a forecast."
        used = len(dated)
        source = dated
        base_calculation["time_grain"] = grain
        base_calculation["invalid_or_missing_dates_excluded"] = len(filtered) - len(dated)

    elif plan.intent == "missing_data":
        rows = []
        for column in filtered.columns:
            series = filtered[column]
            if series.dtype == object:
                missing = int(
                    (
                        series.isna()
                        | series.fillna("").astype(str).str.strip().eq("")
                    ).sum()
                )
            else:
                missing = int(series.isna().sum())
            rows.append({"Field": column, "Missing": missing, "Share": missing / len(filtered)})
        table = pd.DataFrame(rows).sort_values(["Missing", "Field"], ascending=[False, True]).head(plan.limit).reset_index(drop=True)
        top = table.iloc[0]
        headline = f"{top['Field']} has the most missing values ({int(top['Missing']):,})"
        summary = f"Checked {len(filtered):,} cleaned rows across {len(filtered.columns)} columns and counted null or blank values."
        used = len(filtered)
        source = filtered

    else:
        return _insufficient("Unsupported calculation", "The structured plan passed validation but has no deterministic executor.", filtered, plan, dataset_fingerprint, base_calculation)

    base_calculation["rows_used"] = used
    base_calculation["rows_excluded"] = len(filtered) - used
    proof = compute_proof_id(dataset_fingerprint, plan, table)
    return ExecutionResult(
        status="supported",
        headline=headline,
        summary=summary,
        table=table,
        source_rows=source.head(100).copy(),
        calculation=base_calculation,
        rows_matched=len(filtered),
        rows_used=used,
        rows_excluded=len(filtered) - used,
        proof_id=proof,
        warnings=validation_warnings,
    )
