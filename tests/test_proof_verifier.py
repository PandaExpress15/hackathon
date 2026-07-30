from __future__ import annotations

from copy import deepcopy

import pandas as pd

from careerproof.analysis_engine import analyze_question
from careerproof.confidence import calculate_confidence
from careerproof.evidence import build_proof_bundle, verify_proof_bundle
from careerproof.privacy import contains_unmasked_pii, mask_dataframe, mask_structure
from careerproof.query_executor import compute_proof_id, execute_query
from careerproof.reporting import proof_json_bytes
from careerproof.schema import FilterClause, IntentPrediction, QueryPlan


def test_generated_proof_verifies_against_active_dataset(bundle):
    response = analyze_question(
        "What are the ten most requested skills for remote jobs?",
        bundle,
        write_audit=False,
    )
    verification = verify_proof_bundle(
        response.proof_bundle,
        current_dataset_fingerprint=bundle.fingerprint,
        current_frame=bundle.cleaned,
    )
    assert verification["valid"] is True
    assert verification["internal_integrity_valid"] is True
    assert verification["dataset_match"] is True
    assert verification["recalculation_match"] is True
    assert verification["supplied_proof_id"] == response.result.proof_id
    assert verification["recomputed_proof_id"] == response.result.proof_id
    assert verification["recalculated_proof_id"] == response.result.proof_id


def test_tampered_result_table_fails_integrity_check(bundle):
    response = analyze_question(
        "Which cities have the most entry-level job postings?",
        bundle,
        write_audit=False,
    )
    tampered = deepcopy(response.proof_bundle)
    tampered["result_table"][0]["Postings"] += 1
    verification = verify_proof_bundle(
        tampered,
        current_dataset_fingerprint=bundle.fingerprint,
        current_frame=bundle.cleaned,
    )
    assert verification["valid"] is False
    assert verification["internal_integrity_valid"] is False
    assert verification["recomputed_proof_id"] != verification["supplied_proof_id"]


def test_replay_catches_a_tampered_result_even_when_evidence_id_is_recomputed(bundle):
    response = analyze_question(
        "Which cities have the most entry-level job postings?",
        bundle,
        write_audit=False,
    )
    tampered = deepcopy(response.proof_bundle)
    tampered["result_table"][0]["Postings"] += 1
    tampered_plan = QueryPlan.model_validate(tampered["validated_query_plan"])
    tampered_frame = pd.DataFrame(tampered["result_table"])
    tampered["proof_id"] = compute_proof_id(bundle.fingerprint, tampered_plan, tampered_frame)

    verification = verify_proof_bundle(
        tampered,
        current_dataset_fingerprint=bundle.fingerprint,
        current_frame=bundle.cleaned,
    )
    assert verification["internal_integrity_valid"] is True
    assert verification["dataset_match"] is True
    assert verification["recalculation_match"] is False
    assert verification["valid"] is False


def test_valid_proof_can_belong_to_a_different_dataset(bundle):
    response = analyze_question(
        "How has job-posting volume changed over time?",
        bundle,
        write_audit=False,
    )
    verification = verify_proof_bundle(
        response.proof_bundle,
        current_dataset_fingerprint="different-dataset",
        current_frame=bundle.cleaned,
    )
    assert verification["valid"] is True
    assert verification["internal_integrity_valid"] is True
    assert verification["dataset_match"] is False
    assert verification["recalculation_match"] is None


def test_proof_bundle_masks_pii_in_user_question(bundle):
    response = analyze_question(
        "How many postings are there? Contact jordan.lee@example.com or (206) 555-0101.",
        bundle,
        write_audit=False,
    )
    payload = proof_json_bytes(response.proof_bundle).decode("utf-8")
    assert "jordan.lee@example.com" not in payload
    assert "(206) 555-0101" not in payload
    assert not contains_unmasked_pii(payload)


def test_privacy_masked_plan_and_result_remain_verifiable(bundle):
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
        question_template="privacy_proof_test",
    )
    result = execute_query(bundle.cleaned, plan, dataset_fingerprint=bundle.fingerprint)
    prediction = IntentPrediction(label="ranking", confidence=0.99, method="rule")
    confidence = calculate_confidence(result, bundle.report, prediction, plan)
    proof = build_proof_bundle(
        question="Count jordan.lee@example.com postings",
        plan=plan,
        result=result,
        confidence=confidence,
        prediction=prediction,
        dataset_fingerprint=bundle.fingerprint,
        dataset_name=bundle.display_name,
    )

    payload = proof_json_bytes(proof).decode("utf-8")
    assert "jordan.lee@example.com" not in payload
    exported_plan = QueryPlan.model_validate(mask_structure(plan.model_dump(mode="json")))
    exported_table = mask_dataframe(result.table)
    assert proof["proof_id"] == compute_proof_id(bundle.fingerprint, exported_plan, exported_table)
    verification = verify_proof_bundle(proof)
    assert verification["valid"] is True
    assert verification["internal_integrity_valid"] is True


def test_proof_bundle_preserves_non_person_dataset_name(bundle):
    response = analyze_question(
        "Which cities have the most entry-level job postings?",
        bundle,
        write_audit=False,
    )
    assert response.proof_bundle["dataset"]["name"] == bundle.display_name

