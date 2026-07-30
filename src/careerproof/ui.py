"""Gradio interface for CareerProof AI."""

from __future__ import annotations

import html
import json
import os
from pathlib import Path
from typing import Any

import gradio as gr
import numpy as np
import pandas as pd
import plotly.express as px

from .analysis_engine import AnalysisResponse, analyze_question
from .audit import clear_audit_log, read_audit_log
from .charts import (
    BLUE,
    GREEN,
    ORANGE,
    build_career_match_chart,
    build_confidence_gauge,
    build_dashboard_charts,
    build_missingness_chart,
    build_quality_gauge,
    build_scenario_chart,
)
from .config import (
    APP_NAME,
    APP_TAGLINE,
    DATA_DIR,
    PROJECT_ROOT,
    SYNTHETIC_DISCLOSURE,
    TRACK,
    TRUST_STATEMENT,
    VERSION,
)
from .data_loader import load_bundled_dataset, load_dataset
from .data_quality import (
    cleaning_actions_dataframe,
    issues_dataframe,
    missingness_dataframe,
    quality_report_markdown,
)
from .evidence import verify_proof_bundle
from .insights import career_signal_match, dashboard_metrics, scenario_compare
from .intent_training_data import SUPPORTED_DEMO_QUESTIONS
from .privacy import detect_pii_columns, mask_dataframe, mask_structure, mask_text
from .query_plan import plan_to_steps
from .reporting import (
    build_report_html,
    evidence_csv_bytes,
    proof_json_bytes,
    query_plan_json_bytes,
    result_csv_bytes,
    write_report,
)
from .schema import DatasetBundle

CSS = """
:root {
  --cp-navy:#102A43; --cp-deep:#0B1F33; --cp-green:#14805E; --cp-mint:#DFF4EC;
  --cp-blue:#2F6BFF; --cp-orange:#E8871E; --cp-bg:#F2F6F8; --cp-line:#D9E2EC;
}
.gradio-container { max-width: 1500px !important; margin: 0 auto !important; background: var(--cp-bg) !important; }
footer { display:none !important; }
.cp-hero {
  position:relative; overflow:hidden; border-radius:28px; padding:38px 42px; margin:14px 0 18px;
  background: radial-gradient(circle at 85% 20%, rgba(52,211,153,.24), transparent 26%),
              radial-gradient(circle at 73% 100%, rgba(47,107,255,.22), transparent 28%),
              linear-gradient(135deg,#0B1F33 0%,#123B53 58%,#0C6A55 100%);
  box-shadow:0 22px 60px rgba(16,42,67,.22); color:white;
}
.cp-hero:after { content:""; position:absolute; width:240px; height:240px; border:1px solid rgba(255,255,255,.12); border-radius:50%; right:-70px; top:-90px; }
.cp-eyebrow { display:inline-flex; gap:8px; align-items:center; padding:7px 11px; border:1px solid rgba(255,255,255,.24); border-radius:999px; background:rgba(255,255,255,.08); font-size:12px; letter-spacing:.12em; text-transform:uppercase; font-weight:800; }
.cp-hero h1 { font-size:48px; line-height:1.04; margin:18px 0 8px; color:white !important; letter-spacing:-.035em; }
.cp-hero p { margin:0; max-width:820px; font-size:18px; color:#D9F3EA; }
.cp-badges { display:flex; flex-wrap:wrap; gap:9px; margin-top:22px; }
.cp-badge { padding:8px 11px; border-radius:10px; background:rgba(255,255,255,.10); border:1px solid rgba(255,255,255,.15); font-size:13px; font-weight:700; }
.cp-card { background:white; border:1px solid var(--cp-line); border-radius:18px; padding:20px; box-shadow:0 8px 26px rgba(16,42,67,.06); }
.cp-dataset { display:grid; grid-template-columns:repeat(5,minmax(120px,1fr)); gap:10px; }
.cp-stat { background:#F8FBFC; border:1px solid #E3EBF0; border-radius:14px; padding:14px 15px; }
.cp-stat .label { color:#627D98; font-size:12px; font-weight:700; text-transform:uppercase; letter-spacing:.07em; }
.cp-stat .value { color:var(--cp-navy); font-size:23px; font-weight:850; margin-top:3px; }
.cp-stat .sub { color:#829AB1; font-size:11px; margin-top:2px; }
.cp-answer { border-left:6px solid var(--cp-green); background:linear-gradient(135deg,#FFFFFF 0%,#F5FBF8 100%); }
.cp-answer.warn { border-left-color:var(--cp-orange); background:linear-gradient(135deg,#FFFFFF 0%,#FFF9EF 100%); }
.cp-answer .status { display:inline-flex; padding:6px 10px; border-radius:999px; background:var(--cp-mint); color:#0B684D; font-size:12px; font-weight:850; text-transform:uppercase; letter-spacing:.06em; }
.cp-answer.warn .status { background:#FFF0D7; color:#965A05; }
.cp-answer h2 { color:var(--cp-navy) !important; font-size:29px; line-height:1.16; margin:14px 0 8px; }
.cp-answer p { color:#486581; font-size:15px; margin:7px 0; }
.cp-proof-id { display:inline-block; margin-top:12px; color:var(--cp-blue); font-family:ui-monospace,Consolas,monospace; font-size:13px; font-weight:700; }
.cp-proofline { display:grid; grid-template-columns:repeat(5,1fr); gap:8px; align-items:stretch; }
.cp-proof-step { position:relative; padding:12px 10px; text-align:center; border:1px solid #DCE6EC; border-radius:12px; background:white; color:#486581; font-size:12px; font-weight:750; }
.cp-proof-step strong { display:block; color:var(--cp-navy); font-size:13px; margin-bottom:2px; }
.cp-proof-step.done { border-color:#9FDAC6; background:#F0FBF7; }
.cp-kpi-grid { display:grid; grid-template-columns:repeat(4,1fr); gap:12px; }
.cp-kpi { background:white; border:1px solid var(--cp-line); border-radius:16px; padding:17px; box-shadow:0 8px 24px rgba(16,42,67,.05); }
.cp-kpi span { color:#627D98; font-size:12px; font-weight:750; text-transform:uppercase; letter-spacing:.06em; }
.cp-kpi b { display:block; color:var(--cp-navy); font-size:28px; margin-top:4px; }
.cp-signal { background:linear-gradient(135deg,#102A43,#174B63); color:white; border-radius:18px; padding:20px; }
.cp-signal h3 { color:white !important; margin:0 0 8px; }
.cp-signal p { color:#D9EAF3; margin:4px 0; }
.cp-trust-grid { display:grid; grid-template-columns:repeat(3,1fr); gap:14px; }
.cp-trust-card { background:white; border:1px solid var(--cp-line); border-radius:16px; padding:19px; }
.cp-trust-card h3 { color:var(--cp-navy) !important; margin:0 0 8px; }
.cp-trust-card p { color:#627D98; font-size:14px; }
.cp-mini-code { font-family:ui-monospace,Consolas,monospace; background:#0E2235; color:#DFF4EC; padding:13px; border-radius:10px; font-size:12px; overflow:auto; }
.cp-note { border:1px solid #F1C27D; background:#FFF8E8; color:#7C4A03; border-radius:13px; padding:14px 16px; }
.cp-success { border:1px solid #A9DEC9; background:#F0FBF7; color:#0B684D; border-radius:13px; padding:14px 16px; }
.cp-error { border:1px solid #F4B4B8; background:#FFF1F2; color:#9B1C31; border-radius:13px; padding:14px 16px; }
.cp-arch { display:grid; grid-template-columns:repeat(6,1fr); gap:8px; align-items:center; }
.cp-node { min-height:90px; display:flex; flex-direction:column; justify-content:center; text-align:center; padding:12px; border-radius:14px; border:1px solid #C9D8E3; background:white; }
.cp-node b { color:var(--cp-navy); font-size:13px; }
.cp-node small { color:#627D98; margin-top:4px; }
.cp-node.ai { border-color:#A7BFFF; background:#F2F5FF; }
.cp-node.safe { border-color:#9FDAC6; background:#F0FBF7; }
.cp-node.evidence { border-color:#F1C27D; background:#FFF8E8; }
.tabs > .tab-nav { background:white !important; border-radius:15px !important; padding:6px !important; border:1px solid var(--cp-line) !important; }
button.primary { background:linear-gradient(135deg,#14805E,#0E6A52) !important; border:none !important; box-shadow:0 8px 20px rgba(20,128,94,.22) !important; }
button.secondary { border-color:#C6D5DF !important; }
.block { border-radius:16px !important; }
@media (max-width:900px) {
  .cp-dataset,.cp-kpi-grid,.cp-trust-grid { grid-template-columns:repeat(2,1fr); }
  .cp-proofline,.cp-arch { grid-template-columns:1fr; }
  .cp-hero h1 { font-size:37px; }
}
"""

THEME = gr.themes.Soft(
    primary_hue=gr.themes.colors.emerald,
    secondary_hue=gr.themes.colors.blue,
    neutral_hue=gr.themes.colors.slate,
    radius_size=gr.themes.sizes.radius_lg,
    spacing_size=gr.themes.sizes.spacing_md,
    text_size=gr.themes.sizes.text_md,
)


def _hero_html() -> str:
    return f"""
    <section class="cp-hero">
      <div class="cp-eyebrow">{TRACK} · Secure AI Hackathon</div>
      <h1>{APP_NAME}</h1>
      <p>{APP_TAGLINE} Natural-language job-market analysis with code-verified answers, visible evidence, and privacy protection.</p>
      <div class="cp-badges">
        <span class="cp-badge">Deterministic calculations</span>
        <span class="cp-badge">Evidence Passport</span>
        <span class="cp-badge">Privacy Shield</span>
        <span class="cp-badge">Safe refusal</span>
        <span class="cp-badge">Runs without an API key</span>
      </div>
    </section>
    """


def _dataset_summary_html(bundle: DatasetBundle) -> str:
    report = bundle.report
    salary_coverage = 1.0 - report.missing_salary_percentage
    synthetic = "Synthetic demo" if bundle.is_synthetic else "User upload"
    return f"""
    <div class="cp-card">
      <div style="display:flex;justify-content:space-between;gap:14px;align-items:center;margin-bottom:12px;flex-wrap:wrap">
        <div><strong style="font-size:16px;color:#102A43">Active dataset: {html.escape(bundle.display_name)}</strong><br>
        <span style="color:#627D98;font-size:12px">Fingerprint {bundle.fingerprint} · {synthetic}</span></div>
        <span style="padding:6px 10px;border-radius:999px;background:#DFF4EC;color:#0B684D;font-size:12px;font-weight:800">Privacy masking active</span>
      </div>
      <div class="cp-dataset">
        <div class="cp-stat"><div class="label">Cleaned rows</div><div class="value">{report.cleaned_rows:,}</div><div class="sub">from {report.raw_rows:,} raw</div></div>
        <div class="cp-stat"><div class="label">Quality score</div><div class="value">{report.quality_score}/100</div><div class="sub">rule-based</div></div>
        <div class="cp-stat"><div class="label">Salary coverage</div><div class="value">{salary_coverage:.0%}</div><div class="sub">complete ranges</div></div>
        <div class="cp-stat"><div class="label">PII fields</div><div class="value">{len(report.pii_columns_detected)}</div><div class="sub">masked in output</div></div>
        <div class="cp-stat"><div class="label">Date range</div><div class="value" style="font-size:16px">{report.date_min or 'N/A'}</div><div class="sub">to {report.date_max or 'N/A'}</div></div>
      </div>
    </div>
    """


def _kpi_html(bundle: DatasetBundle) -> str:
    metrics = dashboard_metrics(bundle.cleaned)
    return '<div class="cp-kpi-grid">' + "".join(
        f'<div class="cp-kpi"><span>{html.escape(label)}</span><b>{html.escape(value)}</b></div>'
        for label, value in metrics.items()
    ) + "</div>"


def _answer_html(response: AnalysisResponse) -> str:
    warning = response.result.status != "supported"
    status_label = {
        "supported": "Verified by code",
        "unsupported": "Safe refusal",
        "insufficient": "Insufficient evidence",
    }[response.result.status]
    return f"""
    <section class="cp-card cp-answer {'warn' if warning else ''}">
      <span class="status">{status_label}</span>
      <h2>{html.escape(response.result.headline)}</h2>
      <p>{html.escape(response.result.summary)}</p>
      <p>{html.escape(response.explanation)}</p>
      <span class="cp-proof-id">Evidence ID {response.result.proof_id}</span>
    </section>
    """


def _proofline_html(response: AnalysisResponse) -> str:
    labels = [
        ("1", "Question", "Natural language"),
        ("2", "Plan", response.plan.intent.replace("_", " ").title()),
        ("3", "Validate", "Allowlist passed" if response.result.status != "unsupported" else "Refused safely"),
        ("4", "Calculate", f"{response.result.rows_used:,} rows used"),
        ("5", "Prove", response.result.proof_id[-8:]),
    ]
    return '<div class="cp-proofline">' + "".join(
        f'<div class="cp-proof-step done"><strong>{number}. {title}</strong>{html.escape(detail)}</div>'
        for number, title, detail in labels
    ) + "</div>"


def _calculation_markdown(response: AnalysisResponse) -> str:
    calc = response.result.calculation
    filters = calc.get("filters_applied", ["None"])
    fields = calc.get("fields_used", [])
    lines = [
        "### How this was calculated",
        f"- **Intent detected:** {response.plan.intent.replace('_', ' ')}",
        f"- **Question interpretation confidence:** {response.prediction.confidence:.0%}",
        f"- **Fields used:** {', '.join(fields) if fields else 'No dataset fields'}",
        f"- **Filters:** {'; '.join(mask_text(value) for value in filters)}",
        f"- **Rows matched:** {response.result.rows_matched:,}",
        f"- **Rows used:** {response.result.rows_used:,}",
        f"- **Rows excluded:** {response.result.rows_excluded:,}",
        f"- **Minimum group size:** {response.plan.minimum_group_size}",
        f"- **Evidence ID:** `{response.result.proof_id}`",
        "",
        "**Visible query steps**",
        *[f"1. {mask_text(step)}" for step in plan_to_steps(response.plan)],
    ]
    if "formula" in calc:
        lines.append(f"- **Formula:** {calc['formula']}")
    if "salary_midpoint_formula" in calc:
        lines.append(f"- **Salary midpoint:** `{calc['salary_midpoint_formula']}`")
    return "\n".join(lines)


def _suggestions_markdown(response: AnalysisResponse) -> str:
    if not response.suggestions:
        return ""
    return "### Closest answerable questions\n" + "\n".join(f"- {question}" for question in response.suggestions)


def _format_display_table(frame: pd.DataFrame) -> pd.DataFrame:
    display = frame.copy()
    for column in display.columns:
        normalized = str(column).casefold()
        if "salary" in normalized or "midpoint" in normalized or normalized in {"low", "high"}:
            display[column] = display[column].map(lambda value: f"${value:,.0f}" if pd.notna(value) else "")
        elif "share" in normalized or "percent" in normalized:
            display[column] = display[column].map(lambda value: f"{value:.1%}" if pd.notna(value) else "")
    return display


def _write_bundle_files(response: AnalysisResponse, bundle: DatasetBundle) -> tuple[str, str, str, str, str]:
    runtime = DATA_DIR / "runtime"
    runtime.mkdir(parents=True, exist_ok=True)
    stem = response.result.proof_id.lower()
    chart_html = response.chart.to_html(full_html=False, include_plotlyjs=True) if response.chart is not None else None
    report_html = build_report_html(
        question=response.question,
        plan=response.plan,
        result=response.result,
        confidence=response.confidence,
        prediction=response.prediction,
        report=bundle.report,
        dataset_fingerprint=bundle.fingerprint,
        dataset_name=bundle.display_name,
        is_synthetic=bundle.is_synthetic,
        chart_html=chart_html,
    )
    report_path = write_report(runtime / f"{stem}-report.html", report_html)
    evidence_path = runtime / f"{stem}-masked-evidence.csv"
    evidence_path.write_bytes(evidence_csv_bytes(response.result))
    proof_path = runtime / f"{stem}-proof.json"
    proof_path.write_bytes(proof_json_bytes(response.proof_bundle))
    query_path = runtime / f"{stem}-query-plan.json"
    query_path.write_bytes(query_plan_json_bytes(response.plan))
    result_path = runtime / f"{stem}-result.csv"
    result_path.write_bytes(result_csv_bytes(response.result))
    return str(report_path), str(evidence_path), str(proof_path), str(query_path), str(result_path)


def _analysis_outputs(question: str, bundle: DatasetBundle) -> tuple[Any, ...]:
    response = analyze_question(question, bundle, write_audit=True)
    report_path, evidence_path, proof_path, query_path, result_path = _write_bundle_files(response, bundle)
    masked_source = mask_dataframe(response.result.source_rows).head(50)
    return (
        _answer_html(response),
        _proofline_html(response),
        response.chart,
        _format_display_table(response.result.table),
        masked_source,
        _calculation_markdown(response),
        mask_structure(response.plan.model_dump(mode="json")),
        build_confidence_gauge(response.confidence),
        _suggestions_markdown(response),
        report_path,
        evidence_path,
        proof_path,
        query_path,
        result_path,
        response,
    )


def _initial_response(bundle: DatasetBundle) -> AnalysisResponse:
    return analyze_question(SUPPORTED_DEMO_QUESTIONS[1], bundle, write_audit=False)


def _prepare_initial_files(response: AnalysisResponse, bundle: DatasetBundle) -> tuple[str, str, str, str, str]:
    return _write_bundle_files(response, bundle)


def _quality_schema_dataframe(bundle: DatasetBundle) -> pd.DataFrame:
    frame = bundle.cleaned
    pii = set(detect_pii_columns(frame))
    rows = []
    for column in frame.columns:
        rows.append(
            {
                "Field": column,
                "Type": str(frame[column].dtype),
                "Non-missing": int(frame[column].notna().sum()),
                "Unique": int(frame[column].nunique(dropna=True)),
                "Privacy": "Masked" if column in pii else "Analysis-safe",
            }
        )
    return pd.DataFrame(rows)


def _cleaned_download_path(bundle: DatasetBundle) -> str:
    path = DATA_DIR / "runtime" / f"cleaned-{bundle.fingerprint}.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    mask_dataframe(bundle.cleaned).to_csv(path, index=False)
    return str(path)


def _quality_download_path(bundle: DatasetBundle) -> str:
    path = DATA_DIR / "runtime" / f"quality-{bundle.fingerprint}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(quality_report_markdown(bundle.report), encoding="utf-8")
    return str(path)


def _dataset_views(bundle: DatasetBundle) -> tuple[Any, ...]:
    charts = build_dashboard_charts(bundle.cleaned)
    missing = missingness_dataframe(bundle.report)
    roles = sorted(bundle.cleaned["normalized_role"].dropna().astype(str).unique().tolist())
    work_modes = sorted(bundle.cleaned["work_mode"].dropna().astype(str).unique().tolist())
    exp_levels = sorted(bundle.cleaned["experience_level"].dropna().astype(str).unique().tolist())
    scenario_values = work_modes or ["Unknown"]
    return (
        _dataset_summary_html(bundle),
        _cleaned_download_path(bundle),
        _kpi_html(bundle),
        charts["roles"],
        charts["work_mode"],
        charts["skills"],
        charts["salary"],
        charts["trend"],
        build_quality_gauge(bundle.report.quality_score),
        build_missingness_chart(missing),
        issues_dataframe(bundle.report),
        cleaning_actions_dataframe(bundle.report),
        _quality_schema_dataframe(bundle),
        _quality_download_path(bundle),
        gr.update(choices=roles, value=[]),
        gr.update(choices=work_modes, value=[]),
        gr.update(choices=exp_levels, value=[]),
        gr.update(choices=roles, value=roles[0] if roles else None),
        gr.update(choices=scenario_values, value=scenario_values[0]),
        gr.update(choices=scenario_values, value=scenario_values[1] if len(scenario_values) > 1 else scenario_values[0]),
    )


def _load_upload(file_path: str | None, current: DatasetBundle) -> tuple[Any, ...]:
    if not file_path:
        return (current, '<div class="cp-error">Choose a CSV or XLSX file first.</div>', *_dataset_views(current))
    try:
        bundle = load_dataset(file_path, display_name=Path(file_path).name)
        if bundle.report.cleaned_rows < 1:
            raise ValueError("The uploaded file contains no usable rows.")
        message = f'<div class="cp-success"><strong>Dataset loaded.</strong> {bundle.report.cleaned_rows:,} cleaned rows are ready. Re-run a question to calculate against this fingerprint.</div>'
        return (bundle, message, *_dataset_views(bundle))
    except Exception as exc:
        message = f'<div class="cp-error"><strong>Upload failed.</strong> {html.escape(str(exc))}</div>'
        return (current, message, *_dataset_views(current))


def _reset_dataset() -> tuple[Any, ...]:
    bundle = load_bundled_dataset()
    message = '<div class="cp-success"><strong>Bundled demonstration dataset restored.</strong></div>'
    return (bundle, message, *_dataset_views(bundle))


def _filter_explore(bundle: DatasetBundle, roles: list[str] | None, modes: list[str] | None, levels: list[str] | None) -> tuple[Any, ...]:
    frame = bundle.cleaned.copy()
    if roles:
        frame = frame[frame["normalized_role"].isin(roles)]
    if modes:
        frame = frame[frame["work_mode"].isin(modes)]
    if levels:
        frame = frame[frame["experience_level"].isin(levels)]
    if frame.empty:
        return (
            '<div class="cp-error">No rows match those exploration filters.</div>',
            None, None, None, None, None,
        )
    temp = DatasetBundle(bundle.raw, frame, bundle.report, bundle.fingerprint, bundle.display_name, bundle.is_synthetic)
    charts = build_dashboard_charts(frame)
    return _kpi_html(temp), charts["roles"], charts["work_mode"], charts["skills"], charts["salary"], charts["trend"]


def _career_match(bundle: DatasetBundle, target_role: str, skills: str) -> tuple[str, pd.DataFrame, Any]:
    signals, summary = career_signal_match(bundle.cleaned, target_role, skills)
    coverage = float(summary["coverage"])
    missing = summary["missing"][:5]
    matched = summary["matched"][:5]
    card = f"""
    <div class="cp-signal">
      <h3>Career Signal Match: {coverage:.0%}</h3>
      <p>Compared your listed skills with the strongest required-skill signals across {summary['sample_size']:,} synthetic {html.escape(target_role)} postings.</p>
      <p><strong>Matched:</strong> {html.escape(', '.join(matched) if matched else 'No top signals yet')}</p>
      <p><strong>Opportunities:</strong> {html.escape(', '.join(missing) if missing else 'You matched all displayed signals')}</p>
      <p style="font-size:12px;opacity:.82">This is a descriptive skill-overlap tool, not a hiring prediction.</p>
    </div>
    """
    display = signals.copy()
    if not display.empty:
        display["Share"] = display["Share"].map(lambda value: f"{value:.0%}")
    return card, display, build_career_match_chart(signals)


def _scenario_choices(dimension: str, bundle: DatasetBundle) -> tuple[Any, Any]:
    values = sorted(bundle.cleaned[dimension].dropna().astype(str).unique().tolist())
    if not values:
        values = ["Unknown"]
    return (
        gr.update(choices=values, value=values[0]),
        gr.update(choices=values, value=values[1] if len(values) > 1 else values[0]),
    )


def _run_scenario(bundle: DatasetBundle, dimension: str, left: str, right: str) -> tuple[pd.DataFrame, Any, str]:
    if left == right:
        return pd.DataFrame(), None, '<div class="cp-note">Choose two different scenarios.</div>'
    result = scenario_compare(bundle.cleaned, dimension, left, right)
    display = result.copy()
    display["Salary coverage"] = display["Salary coverage"].map(lambda value: f"{value:.0%}")
    display["Median salary midpoint"] = display["Median salary midpoint"].map(lambda value: f"${value:,.0f}" if pd.notna(value) else "Unavailable")
    note = '<div class="cp-note">Scenario comparison is descriptive. Differences do not establish that work mode, experience level, location, or role caused the outcome.</div>'
    return display, build_scenario_chart(result), note


def _audit_display() -> pd.DataFrame:
    frame = read_audit_log()
    if frame.empty:
        return pd.DataFrame(columns=["timestamp", "question", "intent", "rows_used", "confidence_label", "answer_status", "proof_id", "execution_time_ms"])
    columns = [column for column in ["timestamp", "question", "intent", "rows_used", "confidence_label", "answer_status", "proof_id", "execution_time_ms"] if column in frame]
    return frame[columns]


def _clear_audit() -> tuple[pd.DataFrame, str]:
    clear_audit_log()
    return _audit_display(), '<div class="cp-success">Local audit log cleared.</div>'


def _verify_proof_upload(file_path: str | None, bundle: DatasetBundle) -> tuple[str, dict[str, Any]]:
    if not file_path:
        return '<div class="cp-error">Choose a CareerProof proof-bundle JSON file first.</div>', {}
    try:
        path = Path(file_path)
        if path.stat().st_size > 2_000_000:
            return '<div class="cp-error">The proof file is larger than the 2 MB verification limit.</div>', {}
        payload = json.loads(path.read_text(encoding="utf-8"))
        result = verify_proof_bundle(
            payload,
            current_dataset_fingerprint=bundle.fingerprint,
            current_frame=bundle.cleaned,
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        return f'<div class="cp-error"><strong>Verification failed.</strong> {html.escape(str(exc))}</div>', {}

    proof_id = html.escape(str(result["supplied_proof_id"]))
    recomputed = html.escape(str(result["recomputed_proof_id"]))
    if not result["valid"]:
        card = (
            '<div class="cp-error"><strong>Integrity check failed.</strong> '
            f'{html.escape(result["message"])}<br><span class="cp-proof-id">'
            f'Supplied {proof_id} · Recomputed {recomputed}</span></div>'
        )
    elif result["dataset_match"] is False:
        card = (
            '<div class="cp-note"><strong>Internally consistent proof, different dataset.</strong> '
            f'{html.escape(result["message"])}<br><span class="cp-proof-id">{proof_id}</span></div>'
        )
    else:
        card = (
            '<div class="cp-success"><strong>Evidence Passport verified.</strong> '
            f'{html.escape(result["message"])}<br><span class="cp-proof-id">{proof_id}</span></div>'
        )
    return card, mask_structure(result)


def _trust_center_html() -> str:
    return f"""
    <div class="cp-trust-grid">
      <div class="cp-trust-card"><h3>AI interprets</h3><p>A local TF-IDF and logistic-regression model identifies the analysis intent. It never writes or runs calculation code.</p></div>
      <div class="cp-trust-card"><h3>Code calculates</h3><p>Only allowlisted Pandas operations can count, group, compare, summarize, or calculate salary statistics.</p></div>
      <div class="cp-trust-card"><h3>Evidence proves</h3><p>Every supported answer includes a chart, result table, masked source rows, calculation steps, confidence score, and verifiable Evidence ID.</p></div>
      <div class="cp-trust-card"><h3>Privacy Shield</h3><p>Names, emails, phone numbers, and source IDs are masked before interface display, downloads, reports, and local logs.</p></div>
      <div class="cp-trust-card"><h3>Safe refusal</h3><p>Questions about employee happiness, guaranteed hiring, protected attributes, future prediction, or unavailable fields are refused.</p></div>
      <div class="cp-trust-card"><h3>Confidence is earned</h3><p>Confidence depends on usable rows, missingness, intent clarity, and dataset quality. Model wording does not increase confidence.</p></div>
    </div>
    <br>
    <div class="cp-card">
      <h3 style="margin-top:0">Evidence Passport</h3>
      <p>CareerProof creates a reproducible Evidence ID from the dataset fingerprint, validated query plan, and result table. Change the data, plan, or result and the ID changes. The verifier below recomputes that ID from an exported proof bundle.</p>
      <div class="cp-mini-code">SHA-256(dataset fingerprint + validated query plan + deterministic result) → CP-XXXXXXXXXXXX</div>
    </div>
    <br>
    <div class="cp-note"><strong>Known limitation:</strong> {SYNTHETIC_DISCLOSURE} CareerProof does not predict hiring, judge employer quality, or replace current labor-market research.</div>
    """


def _architecture_html() -> str:
    nodes = [
        ("Dataset", "CSV or XLSX", ""),
        ("Validate", "schema + cleaning", "safe"),
        ("Local AI", "intent only", "ai"),
        ("Query Plan", "allowlisted JSON", "safe"),
        ("Pandas", "verified math", "safe"),
        ("Evidence", "chart + proof", "evidence"),
    ]
    return '<div class="cp-arch">' + "".join(
        f'<div class="cp-node {cls}"><b>{title}</b><small>{subtitle}</small></div>'
        for title, subtitle, cls in nodes
    ) + "</div>"


def create_app() -> gr.Blocks:
    bundle = load_bundled_dataset()
    initial = _initial_response(bundle)
    report_path, evidence_path, proof_path, query_path, result_path = _prepare_initial_files(initial, bundle)
    initial_views = _dataset_views(bundle)
    initial_charts = build_dashboard_charts(bundle.cleaned)
    role_choices = sorted(bundle.cleaned["normalized_role"].unique().tolist())
    work_choices = sorted(bundle.cleaned["work_mode"].unique().tolist())
    exp_choices = sorted(bundle.cleaned["experience_level"].unique().tolist())

    with gr.Blocks(title=f"{APP_NAME} - {APP_TAGLINE}", fill_width=True) as demo:
        dataset_state = gr.State(bundle)
        response_state = gr.State(initial)

        gr.HTML(_hero_html(), container=False)

        with gr.Accordion("Data Dock - upload, validate, and switch datasets", open=False):
            dataset_summary = gr.HTML(_dataset_summary_html(bundle), container=False)
            with gr.Row():
                upload = gr.File(label="Upload a job-posting CSV or XLSX", file_types=[".csv", ".xlsx"], type="filepath", scale=3)
                apply_upload = gr.Button("Validate and use upload", variant="primary", scale=1)
                reset_data = gr.Button("Restore bundled demo", variant="secondary", scale=1)
            upload_message = gr.HTML('<div class="cp-note">The bundled 654-row synthetic dataset is active. Uploaded files stay local to this running application.</div>', container=False)
            with gr.Row():
                cleaned_download = gr.DownloadButton("Download masked cleaned CSV", value=_cleaned_download_path(bundle), size="sm")
                gr.Markdown(f"**Data policy:** {SYNTHETIC_DISCLOSURE}", container=False)

        with gr.Tabs():
            with gr.Tab("Ask the Data"):
                with gr.Row():
                    with gr.Column(scale=5):
                        question = gr.Textbox(
                            value=SUPPORTED_DEMO_QUESTIONS[1],
                            label="Ask a question about the active dataset",
                            placeholder="Example: What are the ten most requested skills for remote jobs?",
                            lines=2,
                            submit_btn=False,
                        )
                    with gr.Column(scale=1, min_width=180):
                        analyze_button = gr.Button("Analyze with proof", variant="primary", size="lg")
                        refusal_button = gr.Button("Show a safe refusal", variant="secondary", size="sm")

                gr.Markdown("#### Judge-ready questions", container=False)
                suggestion_buttons: list[gr.Button] = []
                for start in range(0, len(SUPPORTED_DEMO_QUESTIONS), 2):
                    with gr.Row():
                        for prompt in SUPPORTED_DEMO_QUESTIONS[start : start + 2]:
                            suggestion_buttons.append(gr.Button(prompt, size="sm", variant="secondary"))

                answer_html = gr.HTML(_answer_html(initial), container=False)
                proofline_html = gr.HTML(_proofline_html(initial), container=False)

                with gr.Row(equal_height=False):
                    with gr.Column(scale=3):
                        result_plot = gr.Plot(value=initial.chart, label="Verified chart", show_label=False)
                    with gr.Column(scale=1):
                        confidence_plot = gr.Plot(value=build_confidence_gauge(initial.confidence), label="Confidence", show_label=False)

                result_table = gr.Dataframe(
                    value=_format_display_table(initial.result.table),
                    label="Verified result table",
                    interactive=False,
                    wrap=True,
                    buttons=["fullscreen", "copy"],
                )
                with gr.Accordion("Inspect the evidence and calculation", open=True):
                    calculation_md = gr.Markdown(_calculation_markdown(initial))
                    with gr.Row():
                        with gr.Column(scale=2):
                            source_table = gr.Dataframe(
                                value=mask_dataframe(initial.result.source_rows).head(50),
                                label="Masked source rows - preview limited to 50",
                                interactive=False,
                                max_height=430,
                                wrap=False,
                                show_search="filter",
                                buttons=["fullscreen", "copy"],
                            )
                        with gr.Column(scale=1):
                            query_json = gr.JSON(
                                value=mask_structure(initial.plan.model_dump(mode="json")),
                                label="Validated query plan",
                                open=False,
                            )
                suggestions_md = gr.Markdown("")
                gr.Markdown("#### Download the proof", container=False)
                with gr.Row():
                    report_download = gr.DownloadButton("HTML evidence report", value=report_path, variant="primary", size="sm")
                    evidence_download = gr.DownloadButton("Masked source CSV", value=evidence_path, size="sm")
                    proof_download = gr.DownloadButton("Proof bundle JSON", value=proof_path, size="sm")
                    query_download = gr.DownloadButton("Query plan JSON", value=query_path, size="sm")
                    result_download = gr.DownloadButton("Result table CSV", value=result_path, size="sm")

            with gr.Tab("Explore"):
                explore_kpis = gr.HTML(_kpi_html(bundle), container=False)
                with gr.Accordion("Filter the exploration dashboard", open=False):
                    with gr.Row():
                        role_filter = gr.Dropdown(role_choices, multiselect=True, label="Roles")
                        mode_filter = gr.Dropdown(work_choices, multiselect=True, label="Work modes")
                        exp_filter = gr.Dropdown(exp_choices, multiselect=True, label="Experience levels")
                        apply_filters_button = gr.Button("Apply filters", variant="primary")
                with gr.Row():
                    role_plot = gr.Plot(initial_charts["roles"], show_label=False)
                    work_plot = gr.Plot(initial_charts["work_mode"], show_label=False)
                with gr.Row():
                    skill_plot = gr.Plot(initial_charts["skills"], show_label=False)
                    salary_plot = gr.Plot(initial_charts["salary"], show_label=False)
                trend_plot = gr.Plot(initial_charts["trend"], show_label=False)

                gr.Markdown("## Career Signal Lab", container=False)
                gr.HTML('<div class="cp-note"><strong>Unique feature:</strong> Compare skills you already have with the most frequent required-skill signals for a selected role. This is descriptive overlap, not a hiring score.</div>', container=False)
                with gr.Row():
                    target_role = gr.Dropdown(role_choices, value=role_choices[0], label="Target role")
                    user_skills = gr.Textbox(value="Python, Git, SQL, Arduino", label="Your skills", lines=2)
                    match_button = gr.Button("Build signal map", variant="primary")
                match_card = gr.HTML()
                with gr.Row():
                    match_table = gr.Dataframe(interactive=False, label="Role skill signals")
                    match_plot = gr.Plot(show_label=False)

                gr.Markdown("## Scenario Compare", container=False)
                with gr.Row():
                    scenario_dimension = gr.Dropdown(
                        choices=[("Work mode", "work_mode"), ("Experience level", "experience_level"), ("State", "state"), ("Role", "normalized_role")],
                        value="work_mode",
                        label="Compare by",
                    )
                    scenario_left = gr.Dropdown(work_choices, value=work_choices[0], label="Scenario A")
                    scenario_right = gr.Dropdown(work_choices, value=work_choices[1] if len(work_choices) > 1 else work_choices[0], label="Scenario B")
                    scenario_button = gr.Button("Compare scenarios", variant="primary")
                scenario_note = gr.HTML()
                with gr.Row():
                    scenario_table = gr.Dataframe(interactive=False, label="Comparison table")
                    scenario_plot = gr.Plot(show_label=False)

            with gr.Tab("Data Quality"):
                with gr.Row():
                    quality_gauge = gr.Plot(build_quality_gauge(bundle.report.quality_score), show_label=False)
                    missing_plot = gr.Plot(build_missingness_chart(missingness_dataframe(bundle.report)), show_label=False)
                quality_download = gr.DownloadButton("Download quality report", value=_quality_download_path(bundle), size="sm")
                issues_table = gr.Dataframe(issues_dataframe(bundle.report), label="Detected issues", interactive=False, wrap=True)
                actions_table = gr.Dataframe(cleaning_actions_dataframe(bundle.report), label="Cleaning ledger - nothing is removed silently", interactive=False, wrap=True)
                schema_table = gr.Dataframe(_quality_schema_dataframe(bundle), label="Detected schema and privacy classification", interactive=False, show_search="filter")

            with gr.Tab("Trust Center"):
                gr.HTML(_trust_center_html(), container=False)
                gr.Markdown("## What the dataset can answer", container=False)
                coverage = pd.DataFrame(
                    [
                        ["Role, company, city, state, work mode, experience", "Yes", "Counts, rankings, distributions"],
                        ["Required skills", "Yes", "Frequency calculated per posting"],
                        ["Salary", "Yes, with limits", "Complete ranges only and minimum sample sizes"],
                        ["Posting dates", "Yes", "Descriptive trends only"],
                        ["Employee happiness or culture", "No", "Field is absent"],
                        ["Guaranteed hiring or future outcomes", "No", "Unsupported prediction"],
                        ["Protected attributes", "Blocked", "Safety policy"],
                        ["Raw recruiter contact data", "Blocked", "Privacy policy"],
                    ],
                    columns=["Question domain", "Status", "Rule"],
                )
                gr.Dataframe(coverage, interactive=False, wrap=True)

                gr.Markdown("## Evidence Passport Verifier", container=False)
                gr.HTML(
                    '<div class="cp-note"><strong>Unique trust feature:</strong> Download a proof-bundle JSON from any result, then re-upload it here. CareerProof recomputes the content-addressed Evidence ID and, when the dataset matches, reruns the validated plan to confirm the result reproduces.</div>',
                    container=False,
                )
                with gr.Row():
                    proof_upload = gr.File(
                        label="Upload CareerProof proof-bundle JSON",
                        file_types=[".json"],
                        type="filepath",
                        scale=3,
                    )
                    proof_verify_button = gr.Button("Verify Evidence Passport", variant="primary", scale=1)
                proof_verification_message = gr.HTML(container=False)
                proof_verification_details = gr.JSON(label="Verification details", open=False)

            with gr.Tab("Audit Log"):
                gr.HTML('<div class="cp-note">Audit events are stored locally. Questions are privacy-masked before logging, and raw uploaded rows are never written to the log.</div>', container=False)
                with gr.Row():
                    refresh_audit = gr.Button("Refresh log", variant="primary", size="sm")
                    clear_audit_button = gr.Button("Clear local log", variant="secondary", size="sm")
                audit_message = gr.HTML()
                audit_table = gr.Dataframe(_audit_display(), label="Local analysis events", interactive=False, wrap=True, show_search="filter")

            with gr.Tab("About"):
                gr.Markdown(f"# {APP_NAME}\n\n**{APP_TAGLINE}**\n\n{TRUST_STATEMENT}\n\nBuilt for **{TRACK}**. Version {VERSION}.")
                gr.HTML(_architecture_html(), container=False)
                gr.Markdown(
                    """
## Target users
High school students, college students, recent graduates, career counselors, and workforce-development organizations.

## What makes it different
- Every factual result is calculated by deterministic code.
- The local AI component only interprets the question.
- The Evidence Passport fingerprints each answer.
- The Refusal Coach suggests nearby questions that the data can actually answer.
- The Career Signal Lab turns role-level skill frequencies into a transparent overlap map.
- The cleaning ledger shows what changed instead of silently hiding data problems.

## Important limitation
This dataset is synthetic and was generated for demonstration and evaluation. It does not represent current real-world hiring conditions. The tool does not predict hiring, rank employer quality, or give legal, financial, or employment guarantees.
                    """
                )

        analysis_outputs = [
            answer_html,
            proofline_html,
            result_plot,
            result_table,
            source_table,
            calculation_md,
            query_json,
            confidence_plot,
            suggestions_md,
            report_download,
            evidence_download,
            proof_download,
            query_download,
            result_download,
            response_state,
        ]
        analyze_button.click(_analysis_outputs, inputs=[question, dataset_state], outputs=analysis_outputs)
        question.submit(_analysis_outputs, inputs=[question, dataset_state], outputs=analysis_outputs)
        refusal_button.click(lambda: "Which company has the happiest employees?", outputs=question).then(
            _analysis_outputs, inputs=[question, dataset_state], outputs=analysis_outputs
        )
        for button, prompt in zip(suggestion_buttons, SUPPORTED_DEMO_QUESTIONS, strict=True):
            button.click(lambda value=prompt: value, outputs=question).then(
                _analysis_outputs, inputs=[question, dataset_state], outputs=analysis_outputs
            )

        dataset_outputs = [
            dataset_summary,
            cleaned_download,
            explore_kpis,
            role_plot,
            work_plot,
            skill_plot,
            salary_plot,
            trend_plot,
            quality_gauge,
            missing_plot,
            issues_table,
            actions_table,
            schema_table,
            quality_download,
            role_filter,
            mode_filter,
            exp_filter,
            target_role,
            scenario_left,
            scenario_right,
        ]
        apply_upload.click(
            _load_upload,
            inputs=[upload, dataset_state],
            outputs=[dataset_state, upload_message, *dataset_outputs],
        )
        reset_data.click(
            _reset_dataset,
            outputs=[dataset_state, upload_message, *dataset_outputs],
        )

        apply_filters_button.click(
            _filter_explore,
            inputs=[dataset_state, role_filter, mode_filter, exp_filter],
            outputs=[explore_kpis, role_plot, work_plot, skill_plot, salary_plot, trend_plot],
        )
        match_button.click(
            _career_match,
            inputs=[dataset_state, target_role, user_skills],
            outputs=[match_card, match_table, match_plot],
        )
        scenario_dimension.change(
            _scenario_choices,
            inputs=[scenario_dimension, dataset_state],
            outputs=[scenario_left, scenario_right],
        )
        scenario_button.click(
            _run_scenario,
            inputs=[dataset_state, scenario_dimension, scenario_left, scenario_right],
            outputs=[scenario_table, scenario_plot, scenario_note],
        )
        refresh_audit.click(_audit_display, outputs=audit_table)
        clear_audit_button.click(_clear_audit, outputs=[audit_table, audit_message])
        proof_verify_button.click(
            _verify_proof_upload,
            inputs=[proof_upload, dataset_state],
            outputs=[proof_verification_message, proof_verification_details],
        )

    return demo


def main() -> None:
    demo = create_app()
    server_name = os.getenv("CAREERPROOF_SERVER_NAME", "127.0.0.1")
    server_port = int(os.getenv("CAREERPROOF_SERVER_PORT", "7860"))
    debug = os.getenv("CAREERPROOF_DEBUG", "false").casefold() == "true"
    demo.launch(
        server_name=server_name,
        server_port=server_port,
        share=False,
        show_error=debug,
        max_file_size="25mb",
        allowed_paths=[str(PROJECT_ROOT), str(DATA_DIR / "runtime")],
        theme=THEME,
        css=CSS,
        footer_links=[],
        quiet=not debug,
    )


if __name__ == "__main__":
    main()
