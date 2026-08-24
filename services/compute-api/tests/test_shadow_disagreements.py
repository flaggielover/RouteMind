from __future__ import annotations

import pytest

from routemind_compute.application.shadow_disagreements import (
    ShadowDisagreementError,
    audit_shadow_disagreements,
)


def test_audit_preserves_no_data_boundary_for_decision_corpus_fixture() -> None:
    report = audit_shadow_disagreements(
        [{"decision_id": "one", "action": "assign"}, {"decision_id": "two", "action": "assign"}]
    )
    assert report.status == "INSUFFICIENT_DATA"
    assert report.record_count == 2
    assert report.disagreement_count == 0
    assert report.missing_fields == (
        "alternate_strategy_outcome",
        "regime",
        "geography",
        "delay",
        "scarcity",
        "risk",
        "compute",
    )
    assert report.claim_boundary.endswith("CANDIDATE_SUPERIORITY")


def test_audit_reports_ready_and_category_counts_with_complete_support() -> None:
    record = {
        "alternate_strategy_outcome": True,
        "regime": "peak",
        "geography": "zone-a",
        "delay": "high",
        "scarcity": "low",
        "risk": "elevated",
        "compute": "bounded",
    }
    report = audit_shadow_disagreements([record, {**record, "alternate_strategy_outcome": False}])
    assert report.status == "READY_FOR_ANALYSIS"
    assert report.disagreement_count == 1
    assert report.missing_fields == ()
    assert report.category_counts == (
        ("regime", 2),
        ("geography", 2),
        ("delay", 2),
        ("scarcity", 2),
        ("risk", 2),
        ("compute", 2),
    )


def test_audit_rejects_non_array_input() -> None:
    with pytest.raises(ShadowDisagreementError, match="array"):
        audit_shadow_disagreements("invalid")  # type: ignore[arg-type]
