from __future__ import annotations

from io import StringIO

from careerproof.data_loader import load_dataset
from careerproof.analysis_engine import analyze_question
from careerproof.config import SYNTHETIC_DISCLOSURE
from careerproof.privacy import contains_unmasked_pii
from careerproof.reporting import (
    build_report_html,
    evidence_csv_bytes,
    proof_json_bytes,
    query_plan_json_bytes,
)
from careerproof.schema import FilterClause, QueryPlan


def test_evidence_export_contains_no_raw_pii(bundle):
    response = analyze_question("Which cities have the most entry-level job postings?", bundle, write_audit=False)
    exported = evidence_csv_bytes(response.result).decode("utf-8")
    assert "@example.com" in exported  # domain is retained
    assert not contains_unmasked_pii(exported)
    assert "(206) 555" not in exported


def test_html_report_contains_disclosure_and_proof(bundle):
    response = analyze_question("What are the ten most requested skills for remote jobs?", bundle, write_audit=False)
    chart_html = response.chart.to_html(full_html=False, include_plotlyjs=False) if response.chart else None
    report = build_report_html(
        question=response.question,
        plan=response.plan,
        result=response.result,
        confidence=response.confidence,
        prediction=response.prediction,
        report=bundle.report,
        dataset_fingerprint=bundle.fingerprint,
        dataset_name=bundle.display_name,
        chart_html=chart_html,
    )
    assert SYNTHETIC_DISCLOSURE in report
    assert response.result.proof_id in report
    assert "jordan.lee@example.com" not in report


def test_proof_bundle_is_json(bundle):
    response = analyze_question("How has job-posting volume changed over time?", bundle, write_audit=False)
    payload = proof_json_bytes(response.proof_bundle).decode("utf-8")
    assert response.result.proof_id in payload
    assert '"validated_query_plan"' in payload


def test_report_masks_pii_in_user_question(bundle):
    question = "How many postings are there? Email jordan.lee@example.com or call (206) 555-0101."
    response = analyze_question(question, bundle, write_audit=False)
    report = build_report_html(
        question=question,
        plan=response.plan,
        result=response.result,
        confidence=response.confidence,
        prediction=response.prediction,
        report=bundle.report,
        dataset_fingerprint=bundle.fingerprint,
        dataset_name=bundle.display_name,
        chart_html=None,
    )
    assert "jordan.lee@example.com" not in report
    assert "(206) 555-0101" not in report
    assert not contains_unmasked_pii(report)


def test_query_plan_export_masks_sensitive_filter_values():
    plan = QueryPlan(
        intent="top_n",
        metric="row_count",
        group_by=["company"],
        filters=[
            FilterClause(
                column="company",
                operator="equals",
                value="jordan.lee@example.com",
            )
        ],
        question_template="privacy_export_test",
    )
    payload = query_plan_json_bytes(plan).decode("utf-8")

    assert "jordan.lee@example.com" not in payload
    assert not contains_unmasked_pii(payload)


def test_user_upload_report_does_not_claim_the_upload_is_synthetic():
    uploaded = load_dataset(
        StringIO(
            "title,company,posted_date,location,skills,min_salary,max_salary,remote_type,seniority\n"
            "Junior Data Analyst,Example Corp,2026-07-01,Seattle WA,SQL;Excel,50000,65000,remote,new grad\n"
        ),
        display_name="user-upload.csv",
    )
    response = analyze_question("How many postings are there?", uploaded, write_audit=False)
    report = build_report_html(
        question=response.question,
        plan=response.plan,
        result=response.result,
        confidence=response.confidence,
        prediction=response.prediction,
        report=uploaded.report,
        dataset_fingerprint=uploaded.fingerprint,
        dataset_name=uploaded.display_name,
        is_synthetic=uploaded.is_synthetic,
    )
    assert "generated from user-supplied data" in report
    assert SYNTHETIC_DISCLOSURE not in report
