from __future__ import annotations

import pytest

from routemind_compute.application.interference_audit import (
    InterferenceAuditError,
    audit_interference_support,
)

FIELDS = (
    "shared_supply",
    "zone_spillover",
    "carryover",
    "treatment_assignments",
    "outcome_observations",
)


def test_interference_audit_preserves_simulation_no_data_boundary() -> None:
    report = audit_interference_support({field: False for field in FIELDS})
    assert report.status == "INSUFFICIENT_DATA"
    assert report.available_fields == ()
    assert report.missing_fields == FIELDS
    assert "no simulation outcomes" in report.reason


def test_interference_audit_ready_branch_is_explicit() -> None:
    report = audit_interference_support({field: True for field in FIELDS})
    assert report.status == "READY_FOR_ANALYSIS"
    assert report.available_fields == FIELDS
    assert report.missing_fields == ()


def test_interference_audit_rejects_shape_drift() -> None:
    with pytest.raises(InterferenceAuditError, match="fields mismatch"):
        audit_interference_support({"shared_supply": False})
