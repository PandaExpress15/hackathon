"""End-to-end trustworthy analysis orchestration."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import plotly.graph_objects as go

from .audit import log_analysis_event
from .charts import build_result_chart
from .confidence import calculate_confidence
from .evidence import build_proof_bundle
from .explainer import explain_result
from .question_router import build_query_plan, closest_supported_questions, default_intent_model
from .query_executor import execute_query
from .query_validator import QueryValidationError
from .schema import ConfidenceResult, DatasetBundle, ExecutionResult, IntentPrediction, QueryPlan


@dataclass(slots=True)
class AnalysisResponse:
    question: str
    plan: QueryPlan
    prediction: IntentPrediction
    result: ExecutionResult
    confidence: ConfidenceResult
    explanation: str
    chart: go.Figure | None
    proof_bundle: dict[str, Any]
    suggestions: list[str]
    elapsed_ms: float


def analyze_question(question: str, bundle: DatasetBundle, *, write_audit: bool = True) -> AnalysisResponse:
    start = time.perf_counter()
    model = default_intent_model()
    plan, prediction = build_query_plan(question, bundle.cleaned, model)
    try:
        result = execute_query(bundle.cleaned, plan, dataset_fingerprint=bundle.fingerprint)
    except QueryValidationError as exc:
        plan = QueryPlan(
            intent="unsupported",
            metric="none",
            chart_type="table",
            unsupported_reason=str(exc),
            question_template="validation_refusal",
        )
        result = execute_query(bundle.cleaned, plan, dataset_fingerprint=bundle.fingerprint)
    confidence = calculate_confidence(result, bundle.report, prediction, plan)
    explanation = explain_result(result, confidence, plan)
    chart = build_result_chart(result, plan)
    proof_bundle = build_proof_bundle(
        question=question,
        plan=plan,
        result=result,
        confidence=confidence,
        prediction=prediction,
        dataset_fingerprint=bundle.fingerprint,
        dataset_name=bundle.display_name,
    )
    suggestions = closest_supported_questions(question) if result.status != "supported" else []
    elapsed_ms = (time.perf_counter() - start) * 1000
    if write_audit:
        log_analysis_event(
            question=question,
            plan=plan,
            prediction=prediction,
            result=result,
            confidence=confidence,
            dataset_fingerprint=bundle.fingerprint,
            execution_time_ms=elapsed_ms,
        )
    return AnalysisResponse(
        question=question,
        plan=plan,
        prediction=prediction,
        result=result,
        confidence=confidence,
        explanation=explanation,
        chart=chart,
        proof_bundle=proof_bundle,
        suggestions=suggestions,
        elapsed_ms=elapsed_ms,
    )
