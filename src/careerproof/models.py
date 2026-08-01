from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class AskRequest(BaseModel):
    question: str = Field(min_length=2, max_length=600)
    dataset: str = Field(default="auto", max_length=80)
    context: dict[str, Any] | None = None


class ChartSpec(BaseModel):
    type: Literal["bar", "comparison", "line", "radar", "map", "none"] = "none"
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
    decision_confidence: Confidence | None = None
    sources: list[dict[str, str]] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    evidence_id: str
    profile: dict[str, Any] | None = None
    interpreted_question: str | None = None
    input_corrections: list[dict[str, str]] = Field(default_factory=list)
    human_error_checks: list[str] = Field(default_factory=list)


class ProfileInterpretRequest(BaseModel):
    profile_text: str = Field(default="", max_length=1200)
    interests: list[str] = Field(default_factory=list, max_length=12)
    skills: list[str] = Field(default_factory=list, max_length=20)
    education_max: str | None = Field(default="Bachelor's degree", max_length=80)
    preferred_state: str | None = Field(default=None, max_length=80)
    salary_goal: float | None = Field(default=None, ge=0, le=2_000_000)
    work_environment: list[str] = Field(default_factory=list, max_length=8)
    remote_preference: str | None = Field(default="Flexible", max_length=40)
    willing_to_relocate: bool = True
    salary_is_hard: bool = False
    education_is_hard: bool = True
    location_is_hard: bool = False
    weights: dict[str, float] | None = None

    @field_validator("interests", "skills", "work_environment")
    @classmethod
    def clean_profile_list(cls, values: list[str]) -> list[str]:
        return [" ".join(value.split())[:100] for value in values if value.strip()]


class PathBuilderRequest(ProfileInterpretRequest):
    limit: int = Field(default=8, ge=3, le=12)
    confirmed_interpretation: bool = False


class CompareRequest(BaseModel):
    occupations: list[str] = Field(min_length=2, max_length=4)
    weights: dict[str, float] | None = None
    preferred_state: str | None = Field(default=None, max_length=80)
    skills: list[str] = Field(default_factory=list, max_length=20)
    education_max: str | None = Field(default=None, max_length=80)
    salary_goal: float | None = Field(default=None, ge=0, le=2_000_000)
    salary_is_hard: bool = False
    education_is_hard: bool = False
    location_is_hard: bool = False

    @field_validator("occupations", "skills")
    @classmethod
    def clean_compare_list(cls, values: list[str]) -> list[str]:
        return [" ".join(value.split())[:120] for value in values if value.strip()]


class SkillBridgeRequest(BaseModel):
    source: str = Field(min_length=2, max_length=120)
    target: str = Field(min_length=2, max_length=120)
