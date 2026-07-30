"""Local, deterministic result explanation templates."""

from __future__ import annotations

from .schema import ConfidenceResult, ExecutionResult, QueryPlan


def explain_result(result: ExecutionResult, confidence: ConfidenceResult, plan: QueryPlan) -> str:
    if result.status == "unsupported":
        return (
            f"{result.summary} CareerProof AI refuses unsupported conclusions instead of filling gaps with a plausible-sounding answer."
        )
    if result.status == "insufficient":
        return f"{result.summary} Try broader filters or a dataset with more complete fields."
    caution = ""
    if plan.intent in {"median", "average", "comparison"}:
        caution = " Salary differences describe this synthetic snapshot and do not establish causation."
    elif plan.intent == "trend":
        caution = " The timeline is descriptive and should not be treated as a forecast."
    return f"{result.summary} Confidence is {confidence.label.lower()} because {confidence.reason}{caution}"
