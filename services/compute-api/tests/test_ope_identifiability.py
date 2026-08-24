from __future__ import annotations

import pytest

from routemind_compute.application.ope_identifiability import (
    OpeIdentifiabilityError,
    audit_ope_identifiability,
)

FIELDS = (
    "logged_propensity",
    "exploration_indicator",
    "action_overlap",
    "state_richness",
    "shared_resource_context",
)


def test_ope_audit_preserves_required_no_identifiability_result() -> None:
    report = audit_ope_identifiability({field: False for field in FIELDS})
    assert report.status == "OPE_NOT_IDENTIFIABLE_FROM_CURRENT_LOGS"
    assert report.available_fields == ()
    assert report.missing_fields == FIELDS
    assert "no logged propensities" in report.reason


def test_ope_audit_ready_branch_is_scoped() -> None:
    report = audit_ope_identifiability({field: True for field in FIELDS})
    assert report.status == "IDENTIFIABLE_FOR_SCOPE"
    assert report.available_fields == FIELDS
    assert report.missing_fields == ()
    assert "scope review" in report.reason


def test_ope_audit_rejects_shape_drift() -> None:
    with pytest.raises(OpeIdentifiabilityError, match="fields mismatch"):
        audit_ope_identifiability({"logged_propensity": False})
