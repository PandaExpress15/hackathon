from __future__ import annotations

import pandas as pd

from careerproof.query_executor import execute_query
from careerproof.schema import FilterClause, QueryPlan


def test_top_n_calculation_returns_evidence(bundle):
    plan = QueryPlan(
        intent="top_n",
        metric="row_count",
        group_by=["city"],
        filters=[FilterClause(column="experience_level", operator="equals", value="Entry Level")],
        limit=10,
    )
    result = execute_query(bundle.cleaned, plan, dataset_fingerprint=bundle.fingerprint)
    assert result.status == "supported"
    assert not result.table.empty
    assert result.rows_used > 0
    assert result.proof_id.startswith("CP-")
    assert int(result.table["Postings"].sum()) <= result.rows_used


def test_zero_row_query_returns_insufficient(bundle):
    plan = QueryPlan(
        intent="count",
        metric="row_count",
        filters=[FilterClause(column="city", operator="equals", value="Atlantis")],
    )
    result = execute_query(bundle.cleaned, plan, dataset_fingerprint=bundle.fingerprint)
    assert result.status == "insufficient"
    assert result.rows_used == 0


def test_salary_ranking_enforces_minimum_group_size(bundle):
    plan = QueryPlan(
        intent="median",
        metric="salary_midpoint",
        group_by=["company"],
        minimum_group_size=5,
    )
    result = execute_query(bundle.cleaned, plan, dataset_fingerprint=bundle.fingerprint)
    assert result.status == "supported"
    assert (result.table["Sample size"] >= 5).all()


def test_percentage_contains_numerator_and_denominator(bundle):
    plan = QueryPlan(intent="percentage", metric="missing_salary", chart_type="donut")
    result = execute_query(bundle.cleaned, plan, dataset_fingerprint=bundle.fingerprint)
    assert result.calculation["numerator"] + (result.calculation["denominator"] - result.calculation["numerator"]) == result.calculation["denominator"]
    assert result.table["Postings"].sum() == result.calculation["denominator"]


def test_missing_data_counts_null_and_blank_once(bundle):
    frame = bundle.cleaned.head(3).copy()
    frame["description_excerpt"] = pd.Series([None, "", "present"], index=frame.index)
    plan = QueryPlan(intent="missing_data", metric="missing_count", chart_type="bar")

    result = execute_query(frame, plan, dataset_fingerprint="missing-data-test")

    description_row = result.table.loc[result.table["Field"] == "description_excerpt"].iloc[0]
    assert int(description_row["Missing"]) == 2
