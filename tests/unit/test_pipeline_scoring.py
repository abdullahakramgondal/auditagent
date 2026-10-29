from auditagent.schemas.audit import AuditResult
from eval.pipeline_scoring import aggregate, score_case

KEY = {
    "status": "NON_COMPLIANT",
    "billed_total": "10000000.00",
    "correct_payable": "9000000.00",
    "total_difference": "1000000.00",
    "finding_types": ["late_penalty"],
}
FINDING = {
    "clause_type": "late_penalty",
    "description": "Late.",
    "source": {"page": 4, "text": "Clause."},
    "difference": "1000000",
}


def result(**changes):
    base = {
        "status": "NON_COMPLIANT",
        "billed_total": "10000000",
        "correct_payable": "9000000",
        "total_difference": "1000000",
        "findings": [FINDING],
    }
    return AuditResult.model_validate({**base, **changes})


def test_a_result_equal_to_the_key_is_correct_even_with_other_decimal_spelling():
    entry = score_case(KEY, result())
    assert entry["outcome"] == "correct" and all(entry["checks"].values())


def test_needs_review_where_the_key_has_a_verdict_is_a_safe_review():
    needs_review = AuditResult(status="NEEDS_REVIEW", review_reasons=["invoice: not proven"])
    entry = score_case(KEY, needs_review)
    assert entry["outcome"] == "review" and entry["checks"]["billed_total"] is False


def test_a_different_verdict_is_wrong_and_names_the_failed_check():
    off = result(
        billed_total="10000000",
        correct_payable="9500000",
        total_difference="500000",
        findings=[{**FINDING, "difference": "500000"}],
    )
    entry = score_case(KEY, off)
    assert entry["outcome"] == "wrong"
    assert entry["checks"]["correct_payable"] is False and entry["checks"]["status"] is True


def test_finding_types_are_compared_as_a_set_of_clause_types():
    wrong_type = result(findings=[{**FINDING, "clause_type": "unit_price"}])
    assert score_case(KEY, wrong_type)["checks"]["finding_types"] is False


def test_the_summary_counts_outcomes_per_category_and_overall():
    ok = {**score_case(KEY, result()), "category": "late_flat"}
    flagged = {
        **score_case(KEY, result(review_reasons=["purchase order: other date"])),
        "category": "late_flat",
    }
    review = {
        **score_case(KEY, AuditResult(status="NEEDS_REVIEW", review_reasons=["x"])),
        "category": "decoy",
    }
    summary = aggregate([ok, flagged, review])
    assert (
        summary["late_flat"]["correct"] == 2 and summary["late_flat"]["correct_with_reasons"] == 1
    )
    assert summary["decoy"]["review"] == 1 and summary["decoy"]["wrong"] == 0
    assert summary["ALL"]["cases"] == 3 and summary["ALL"]["accuracy"] == 0.667
