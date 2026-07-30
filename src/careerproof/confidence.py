"""Confidence labels based on data evidence rather than model tone."""

from __future__ import annotations

from .schema import ConfidenceResult, DataQualityReport, ExecutionResult, IntentPrediction, QueryPlan


def calculate_confidence(
    result: ExecutionResult,
    report: DataQualityReport,
    prediction: IntentPrediction,
    plan: QueryPlan,
) -> ConfidenceResult:
    if result.status != "supported":
        reason = result.summary if result.status == "insufficient" else "The question was unsupported, so no factual confidence label is assigned."
        return ConfidenceResult(label="Insufficient evidence", score=0, reason=reason, breakdown={"evidence": 0, "completeness": 0, "intent": 0, "quality": 0})

    sample = result.rows_used
    if sample >= 50:
        evidence_score = 40
    elif sample >= 20:
        evidence_score = 34
    elif sample >= 10:
        evidence_score = 26
    elif sample >= 5:
        evidence_score = 17
    else:
        evidence_score = 6

    relevant_columns = set(plan.group_by)
    relevant_columns.update(clause.column for clause in plan.filters)
    if plan.metric in report.missing_by_column:
        relevant_columns.add(plan.metric)
    if plan.intent in {"median", "average", "comparison", "percentage"}:
        relevant_columns.update({"salary_min", "salary_max"})
    if plan.intent == "skill_frequency":
        relevant_columns.update(plan.skill_columns)

    missing_count = sum(report.missing_by_column.get(column, 0) for column in relevant_columns)
    possible = max(report.cleaned_rows * max(len(relevant_columns), 1), 1)
    missing_rate = missing_count / possible
    if missing_rate <= 0.05:
        completeness_score = 25
    elif missing_rate <= 0.20:
        completeness_score = 18
    else:
        completeness_score = 9

    if prediction.confidence >= 0.80:
        intent_score = 20
    elif prediction.confidence >= 0.60:
        intent_score = 15
    elif prediction.confidence >= 0.42:
        intent_score = 10
    else:
        intent_score = 5

    quality_score = round(report.quality_score * 0.15)
    total = int(min(100, evidence_score + completeness_score + intent_score + quality_score))
    if result.rows_used < plan.minimum_group_size:
        total = min(total, 49)

    if total >= 82:
        label = "High confidence"
    elif total >= 64:
        label = "Medium confidence"
    else:
        label = "Low confidence"

    reason = (
        f"Based on {result.rows_used:,} usable rows, {missing_rate:.1%} relevant-field missingness, "
        f"{prediction.confidence:.0%} question-intent confidence, and a {report.quality_score}/100 dataset quality score."
    )
    return ConfidenceResult(
        label=label,
        score=total,
        reason=reason,
        breakdown={
            "evidence": evidence_score,
            "completeness": completeness_score,
            "intent": intent_score,
            "quality": quality_score,
        },
    )
