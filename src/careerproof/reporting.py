"""Masked evidence and HTML report exports."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .config import REPORT_TEMPLATE_PATH, SYNTHETIC_DISCLOSURE, TRUST_STATEMENT
from .evidence import build_proof_bundle
from .privacy import mask_dataframe, mask_structure, mask_text
from .schema import ConfidenceResult, DataQualityReport, ExecutionResult, IntentPrediction, QueryPlan


def evidence_csv_bytes(result: ExecutionResult) -> bytes:
    return mask_dataframe(result.source_rows).to_csv(index=False).encode("utf-8")


def result_csv_bytes(result: ExecutionResult) -> bytes:
    return mask_dataframe(result.table).to_csv(index=False).encode("utf-8")


def query_plan_json_bytes(plan: QueryPlan) -> bytes:
    return json.dumps(mask_structure(plan.model_dump(mode="json")), indent=2, sort_keys=True).encode("utf-8")


def proof_json_bytes(bundle: dict[str, Any]) -> bytes:
    return json.dumps(mask_structure(bundle), indent=2, sort_keys=True, default=str).encode("utf-8")


def build_report_html(
    *,
    question: str,
    plan: QueryPlan,
    result: ExecutionResult,
    confidence: ConfidenceResult,
    prediction: IntentPrediction,
    report: DataQualityReport,
    dataset_fingerprint: str,
    dataset_name: str,
    is_synthetic: bool = True,
    chart_html: str | None = None,
) -> str:
    env = Environment(
        loader=FileSystemLoader(str(REPORT_TEMPLATE_PATH.parent)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template(REPORT_TEMPLATE_PATH.name)
    bundle = build_proof_bundle(
        question=mask_text(question),
        plan=plan,
        result=result,
        confidence=confidence,
        prediction=prediction,
        dataset_fingerprint=dataset_fingerprint,
        dataset_name=dataset_name,
    )
    return template.render(
        generated_at=datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC"),
        question=mask_text(question),
        result=result,
        confidence=confidence,
        prediction=prediction,
        plan=plan,
        data_quality=report,
        dataset_fingerprint=dataset_fingerprint,
        dataset_name=dataset_name,
        result_table_html=mask_dataframe(result.table).to_html(index=False, border=0, classes="data-table"),
        source_table_html=mask_dataframe(result.source_rows).head(25).to_html(index=False, border=0, classes="data-table compact"),
        chart_html=chart_html,
        proof_json=json.dumps(mask_structure(bundle), indent=2, default=str),
        synthetic_disclosure=SYNTHETIC_DISCLOSURE,
        is_synthetic=is_synthetic,
        trust_statement=TRUST_STATEMENT,
    )


def write_report(path: Path, html: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")
    return path
