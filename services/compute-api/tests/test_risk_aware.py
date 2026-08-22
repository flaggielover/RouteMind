from __future__ import annotations

import pytest

from routemind_compute.application.risk_aware import RiskAwareScoringStrategy, RiskAwareWeights
from routemind_compute.domain.dispatch import CourierCandidate, DispatchProblem, GeoPoint


def test_risk_aware_scoring_prefers_lower_risk_with_versioned_components() -> None:
    problem = DispatchProblem(
        "risk-1",
        GeoPoint(31.2304, 121.4737),
        (
            CourierCandidate(
                "near-risky",
                GeoPoint(31.2305, 121.4738),
                capacity_units=4,
                service_risk=0.9,
                overtime_risk=0.8,
            ),
            CourierCandidate(
                "far-safe",
                GeoPoint(31.24, 121.48),
                capacity_units=4,
                service_risk=0.0,
                overtime_risk=0.0,
            ),
        ),
    )

    decision = RiskAwareScoringStrategy().solve(problem)

    assert decision.courier_id == "far-safe"
    assert decision.strategy_version == "1.0.0"
    assert dict(decision.metadata)["weight_service_risk"] == "2.000"
    assert decision.rationale[0] == "capacity/readiness/overtime/risk/balance weighted score"


def test_risk_aware_weights_are_validated_and_deterministic() -> None:
    with pytest.raises(ValueError, match="not all zero"):
        RiskAwareWeights(0, 0, 0, 0, 0)
    first = RiskAwareWeights().metadata()
    second = RiskAwareWeights().metadata()
    assert first == second


def test_risk_aware_reports_infeasible_candidates_without_silent_fallback() -> None:
    problem = DispatchProblem(
        "risk-2",
        GeoPoint(0, 0),
        (CourierCandidate("offline", GeoPoint(0, 0), state="offline"),),
    )

    decision = RiskAwareScoringStrategy().solve(problem)

    assert decision.courier_id is None
    assert "offline:courier_state=offline" in decision.rationale
