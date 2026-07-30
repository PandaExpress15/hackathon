from __future__ import annotations

from careerproof.query_validator import validate_query_plan
from careerproof.schema import FilterClause, QueryPlan


def test_sensitive_column_is_rejected(bundle):
    plan = QueryPlan(
        intent="top_n",
        metric="row_count",
        group_by=["recruiter_email"],
    )
    result = validate_query_plan(plan, bundle.cleaned)
    assert result.valid is False
    assert any("Sensitive" in error for error in result.errors)


def test_unknown_column_is_rejected(bundle):
    plan = QueryPlan(intent="top_n", metric="row_count", group_by=["made_up_column"])
    result = validate_query_plan(plan, bundle.cleaned)
    assert result.valid is False


def test_arbitrary_code_is_not_a_supported_operation(bundle):
    plan = QueryPlan(
        intent="count",
        metric="row_count",
        filters=[FilterClause(column="job_title", operator="contains", value="__import__('os').system('rm -rf /')")],
    )
    result = validate_query_plan(plan, bundle.cleaned)
    assert result.valid is True
    # It remains a literal string filter and is never executed.
