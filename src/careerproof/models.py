from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str = Field(min_length=2, max_length=600)
    dataset: str = Field(default="auto", max_length=80)


class ChartSpec(BaseModel):
    type: Literal["bar", "comparison", "none"] = "none"
    title: str = ""
    label_key: str = ""
    value_key: str = ""
    value_format: Literal["currency", "number", "percent", "decimal"] = "number"


class Confidence(BaseModel):
    label: Literal["High", "Medium", "Low", "Insufficient evidence"]
    score: int = Field(ge=0, le=100)
    reason: str


class AnalysisResult(BaseModel):
    status: Literal["supported", "refused", "needs_clarification"]
    question: str
    dataset: str
    intent: str
    ai_intent: str
    ai_intent_confidence: float
    headline: str
    summary: str
    rows: list[dict[str, Any]] = Field(default_factory=list)
    columns: list[dict[str, str]] = Field(default_factory=list)
    chart: ChartSpec = Field(default_factory=ChartSpec)
    query_plan: dict[str, Any] = Field(default_factory=dict)
    evidence: dict[str, Any] = Field(default_factory=dict)
    confidence: Confidence
    sources: list[dict[str, str]] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    evidence_id: str
    profile: dict[str, Any] | None = None
