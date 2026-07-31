from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any


def evidence_id(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16].upper()
    return f"CP-{digest}"


def evidence_block(
    *,
    calculation: str,
    filters: list[str],
    rows_considered: int,
    rows_returned: int,
    data_quality_notes: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "calculation": calculation,
        "filters": filters,
        "rows_considered": int(rows_considered),
        "rows_returned": int(rows_returned),
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "data_quality_notes": data_quality_notes or [],
        "trust_boundary": "The language model only classifies intent. Deterministic Pandas code calculates every number shown.",
    }
