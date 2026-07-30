"""Local, privacy-preserving audit logging."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from .config import AUDIT_LOG_PATH
from .privacy import mask_structure, mask_text
from .schema import ConfidenceResult, ExecutionResult, IntentPrediction, QueryPlan


def log_analysis_event(
    *,
    question: str,
    plan: QueryPlan,
    prediction: IntentPrediction,
    result: ExecutionResult,
    confidence: ConfidenceResult,
    dataset_fingerprint: str,
    execution_time_ms: float,
    path: Path = AUDIT_LOG_PATH,
) -> dict[str, Any]:
    event = {
        "event_id": str(uuid.uuid4()),
        "timestamp": datetime.now(UTC).isoformat(),
        "dataset_fingerprint": dataset_fingerprint,
        "question": mask_text(question),
        "intent": plan.intent,
        "intent_confidence": round(prediction.confidence, 4),
        "query_plan": mask_structure(plan.model_dump(mode="json")),
        "validation_status": "passed" if result.status != "unsupported" else "not_applicable",
        "rows_matched": result.rows_matched,
        "rows_used": result.rows_used,
        "confidence_label": confidence.label,
        "confidence_score": confidence.score,
        "answer_status": result.status,
        "proof_id": result.proof_id,
        "refusal_reason": mask_text(result.summary) if result.status == "unsupported" else None,
        "execution_time_ms": round(execution_time_ms, 2),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, default=str, sort_keys=True) + "\n")
    return event


def read_audit_log(path: Path = AUDIT_LOG_PATH) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    frame = pd.DataFrame(rows)
    if not frame.empty and "timestamp" in frame:
        frame = frame.sort_values("timestamp", ascending=False).reset_index(drop=True)
    return frame


def clear_audit_log(path: Path = AUDIT_LOG_PATH) -> None:
    if path.exists():
        path.unlink()
