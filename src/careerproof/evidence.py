"""Evidence, provenance, and export bundle helpers."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

import pandas as pd

from .privacy import mask_dataframe, mask_structure, mask_text
from .query_executor import compute_proof_id, execute_query
from .schema import ConfidenceResult, ExecutionResult, IntentPrediction, QueryPlan

PROOF_SCHEMA_VERSION = "1.1"


def build_proof_bundle(
    *,
    question: str,
    plan: QueryPlan,
    result: ExecutionResult,
    confidence: ConfidenceResult,
    prediction: IntentPrediction,
    dataset_fingerprint: str,
    dataset_name: str,
) -> dict[str, Any]:
    """Create a portable, privacy-masked evidence bundle for one analysis."""

    masked_source = mask_dataframe(result.source_rows)
    masked_result = mask_dataframe(result.table)
    masked_plan = mask_structure(plan.model_dump(mode="json"))
    bundle = {
        "proof_schema_version": PROOF_SCHEMA_VERSION,
        "proof_id": result.proof_id,
        "generated_at": datetime.now(UTC).isoformat(),
        "integrity": {
            "algorithm": "SHA-256",
            "content_addressed_fields": ["dataset.fingerprint", "validated_query_plan", "result_table"],
        },
        "dataset": {
            "name": mask_text(dataset_name),
            "fingerprint": dataset_fingerprint,
        },
        "question": mask_text(question),
        "intent_prediction": mask_structure(prediction.model_dump(mode="json")),
        "validated_query_plan": masked_plan,
        "answer": {
            "status": result.status,
            "headline": mask_text(result.headline),
            "summary": mask_text(result.summary),
            "rows_matched": result.rows_matched,
            "rows_used": result.rows_used,
            "rows_excluded": result.rows_excluded,
        },
        "confidence": mask_structure(confidence.model_dump(mode="json")),
        "calculation": mask_structure(result.calculation),
        "result_table": json.loads(masked_result.to_json(orient="records", date_format="iso")),
        "masked_source_preview": json.loads(masked_source.head(25).to_json(orient="records", date_format="iso")),
    }
    return mask_structure(bundle)


def verify_proof_bundle(
    bundle: dict[str, Any],
    *,
    current_dataset_fingerprint: str | None = None,
    current_frame: pd.DataFrame | None = None,
) -> dict[str, Any]:
    """Verify the content-addressed Evidence Passport in a proof bundle.

    The internal check does not require the original dataset. It recomputes the
    Evidence ID from the bundled dataset fingerprint, validated query plan, and
    result table. When the active dataset is also supplied, CareerProof executes the
    validated plan again and confirms that the calculation is reproducible.
    """

    if not isinstance(bundle, dict):
        raise ValueError("The proof file must contain a JSON object.")
    required = {"proof_id", "dataset", "validated_query_plan", "result_table"}
    missing = sorted(required - set(bundle))
    if missing:
        raise ValueError("The proof bundle is missing required fields: " + ", ".join(missing))

    dataset = bundle.get("dataset")
    if not isinstance(dataset, dict) or not dataset.get("fingerprint"):
        raise ValueError("The proof bundle does not contain a dataset fingerprint.")
    fingerprint = str(dataset["fingerprint"])

    try:
        plan = QueryPlan.model_validate(bundle["validated_query_plan"])
    except Exception as exc:  # Pydantic exposes detailed errors; keep the UI message concise.
        raise ValueError("The validated query plan in the proof bundle is malformed.") from exc

    rows = bundle.get("result_table")
    if not isinstance(rows, list):
        raise ValueError("The proof bundle result table must be a JSON list.")
    result_table = pd.DataFrame(rows)
    expected = compute_proof_id(fingerprint, plan, result_table)
    supplied = str(bundle.get("proof_id", ""))
    internal_integrity_valid = supplied == expected
    dataset_match = (
        None
        if current_dataset_fingerprint is None
        else fingerprint == str(current_dataset_fingerprint)
    )
    recalculation_match: bool | None = None
    recalculated_proof_id: str | None = None
    if dataset_match is True and current_frame is not None:
        try:
            recalculated = execute_query(
                current_frame,
                plan,
                dataset_fingerprint=str(current_dataset_fingerprint),
            )
            recalculated_proof_id = recalculated.proof_id
            recalculation_match = recalculated_proof_id == supplied
        except Exception:
            # The verifier should return a clear result rather than exposing a stack
            # trace when a proof cannot be replayed against the active dataset.
            recalculation_match = False

    valid = internal_integrity_valid and recalculation_match is not False
    if not internal_integrity_valid:
        message = "The protected calculation fields have changed or the Evidence ID is invalid."
    elif dataset_match is False:
        message = "The proof is internally consistent, but it belongs to a different dataset fingerprint and was not replayed."
    elif recalculation_match is False:
        message = "The proof is internally consistent, but its result does not reproduce from the active dataset."
    elif recalculation_match is True:
        message = "The Evidence Passport is internally consistent and reproduces from the active dataset."
    else:
        message = "The Evidence Passport is internally consistent and matches the supplied dataset fingerprint."

    return {
        "valid": valid,
        "internal_integrity_valid": internal_integrity_valid,
        "dataset_match": dataset_match,
        "recalculation_match": recalculation_match,
        "message": message,
        "supplied_proof_id": supplied,
        "recomputed_proof_id": expected,
        "recalculated_proof_id": recalculated_proof_id,
        "proof_schema_version": str(bundle.get("proof_schema_version", "legacy")),
        "dataset_fingerprint": fingerprint,
        "current_dataset_fingerprint": current_dataset_fingerprint,
        "question": mask_text(bundle.get("question", "")),
        "generated_at": bundle.get("generated_at"),
    }


def proof_bundle_json(bundle: dict[str, Any]) -> str:
    return json.dumps(mask_structure(bundle), indent=2, sort_keys=True, default=str)
