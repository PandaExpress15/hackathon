"""Helpers for producing human-readable and serializable query plans."""

from __future__ import annotations

from .schema import QueryPlan


def plan_to_steps(plan: QueryPlan) -> list[str]:
    steps = [f"Intent: {plan.intent.replace('_', ' ')}"]
    if plan.filters:
        for clause in plan.filters:
            steps.append(f"Filter {clause.column} {clause.operator.replace('_', ' ')} {clause.value}")
    if plan.group_by:
        steps.append("Group by " + ", ".join(plan.group_by))
    steps.append(f"Calculate {plan.metric.replace('_', ' ')}")
    if plan.sort:
        steps.append(f"Sort {plan.sort}")
    if plan.limit:
        steps.append(f"Return up to {plan.limit} rows")
    if plan.minimum_group_size > 1:
        steps.append(f"Require at least {plan.minimum_group_size} rows per group")
    return steps
