from __future__ import annotations

import pytest

from routemind_compute.domain.dispatch import (
    CourierCandidate,
    DispatchDecision,
    DispatchProblem,
    DispatchStrategy,
    GeoPoint,
    TimeWindow,
)


class FirstCandidateStrategy:
    @property
    def name(self) -> str:
        return "first-candidate-test"

    def solve(self, problem: DispatchProblem) -> DispatchDecision:
        courier_id = problem.candidates[0].courier_id if problem.candidates else None
        score = 0.0 if courier_id else None
        return DispatchDecision(problem.request_id, self.name, courier_id, score)


def test_strategy_protocol_accepts_a_stateless_implementation() -> None:
    strategy = FirstCandidateStrategy()
    problem = DispatchProblem(
        request_id="request-1",
        pickup=GeoPoint(31.2304, 121.4737),
        candidates=(CourierCandidate("courier-1", GeoPoint(31.22, 121.48)),),
    )

    assert isinstance(strategy, DispatchStrategy)
    assert strategy.solve(problem).courier_id == "courier-1"


@pytest.mark.parametrize(
    ("latitude", "longitude"),
    [(90.1, 0.0), (-90.1, 0.0), (0.0, 180.1), (0.0, -180.1)],
)
def test_geo_point_rejects_out_of_range_coordinates(latitude: float, longitude: float) -> None:
    with pytest.raises(ValueError):
        GeoPoint(latitude, longitude)


def test_dispatch_problem_rejects_duplicate_candidates() -> None:
    point = GeoPoint(31.2304, 121.4737)

    with pytest.raises(ValueError, match="unique"):
        DispatchProblem(
            request_id="request-1",
            pickup=point,
            candidates=(CourierCandidate("courier-1", point), CourierCandidate("courier-1", point)),
        )


def test_courier_candidate_rejects_a_blank_identifier() -> None:
    with pytest.raises(ValueError, match="must not be blank"):
        CourierCandidate(" ", GeoPoint(31.2304, 121.4737))


def test_dispatch_problem_rejects_a_blank_request_identifier() -> None:
    with pytest.raises(ValueError, match="must not be blank"):
        DispatchProblem(" ", GeoPoint(31.2304, 121.4737), ())


def test_dispatch_decision_rejects_blank_identifiers() -> None:
    with pytest.raises(ValueError, match="request_id"):
        DispatchDecision(" ", "test", None, None)

    with pytest.raises(ValueError, match="strategy"):
        DispatchDecision("request-1", " ", None, None)


def test_unassigned_decision_rejects_a_score() -> None:
    with pytest.raises(ValueError, match="cannot have a score"):
        DispatchDecision("request-1", "test", None, 1.0)


def test_dispatch_decision_rejects_invalid_latency_and_version() -> None:
    with pytest.raises(ValueError, match="latency"):
        DispatchDecision("request-1", "test", None, None, latency_millis=-1.0)

    with pytest.raises(ValueError, match="version"):
        DispatchDecision("request-1", "test", None, None, strategy_version=" ")


def test_constraint_model_filters_capacity_state_risk_and_time_windows_deterministically() -> None:
    problem = DispatchProblem(
        "constrained-1",
        GeoPoint(31.2304, 121.4737),
        (
            CourierCandidate(
                "offline-courier",
                GeoPoint(31.2304, 121.4737),
                state="offline",
            ),
            CourierCandidate(
                "small-courier",
                GeoPoint(31.2304, 121.4737),
                capacity_units=1,
            ),
            CourierCandidate(
                "safe-courier",
                GeoPoint(31.2304, 121.4737),
                capacity_units=4,
                service_risk=0.1,
                estimated_travel_seconds=25,
            ),
        ),
        demand_units=2,
        service_seconds=10,
        delivery_window=TimeWindow(0, 60),
        max_service_risk=0.5,
    )

    assert [candidate.courier_id for candidate in problem.eligible_candidates()] == ["safe-courier"]
    assert problem.infeasibility_reasons() == (
        "offline-courier:courier_state=offline",
        "offline-courier:capacity_insufficient=1.000",
        "small-courier:capacity_insufficient=1.000",
    )


def test_constraint_model_reports_explicit_infeasibility_reasons() -> None:
    problem = DispatchProblem(
        "constrained-2",
        GeoPoint(0, 0),
        (
            CourierCandidate(
                "late-courier",
                GeoPoint(0, 0),
                estimated_travel_seconds=90,
            ),
        ),
        delivery_window=TimeWindow(0, 30),
    )

    assert problem.eligible_candidates() == ()
    assert problem.infeasibility_reasons() == ("late-courier:delivery_window_missed=30.000",)

    with pytest.raises(ValueError, match="ordered"):
        TimeWindow(10, 1)


def test_constraint_model_rejects_non_finite_and_invalid_candidate_bounds() -> None:
    point = GeoPoint(0, 0)
    with pytest.raises(ValueError, match="finite"):
        TimeWindow(float("nan"), 1)
    with pytest.raises(ValueError, match="capacity"):
        CourierCandidate("bad-capacity", point, capacity_units=-1)
    with pytest.raises(ValueError, match="current_load"):
        CourierCandidate("bad-load", point, current_load_units=-1)
    with pytest.raises(ValueError, match="exceed"):
        CourierCandidate("overloaded", point, capacity_units=1, current_load_units=2)
    with pytest.raises(ValueError, match="available_from"):
        CourierCandidate("bad-start", point, available_from_seconds=-1)
    with pytest.raises(ValueError, match="available_until"):
        CourierCandidate("bad-end", point, available_until_seconds=-1)
    with pytest.raises(ValueError, match="state"):
        CourierCandidate("bad-state", point, state="unknown")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="service_risk"):
        CourierCandidate("bad-risk", point, service_risk=2)
    with pytest.raises(ValueError, match="estimated_travel"):
        CourierCandidate("bad-travel", point, estimated_travel_seconds=-1)


def test_constraint_model_rejects_invalid_problem_parameters() -> None:
    point = GeoPoint(0, 0)
    with pytest.raises(ValueError, match="demand"):
        DispatchProblem("bad-demand", point, (), demand_units=0)
    with pytest.raises(ValueError, match="pickup_ready"):
        DispatchProblem("bad-ready", point, (), pickup_ready_at_seconds=-1)
    with pytest.raises(ValueError, match="service_seconds"):
        DispatchProblem("bad-service", point, (), service_seconds=-1)
    with pytest.raises(ValueError, match="max_service_risk"):
        DispatchProblem("bad-risk", point, (), max_service_risk=2)


def test_constraint_model_reports_risk_and_courier_deadline_rejections() -> None:
    problem = DispatchProblem(
        "constrained-3",
        GeoPoint(0, 0),
        (
            CourierCandidate(
                "risky",
                GeoPoint(0, 0),
                service_risk=0.8,
            ),
            CourierCandidate(
                "short-shift",
                GeoPoint(0, 0),
                available_until_seconds=5,
                estimated_travel_seconds=10,
            ),
        ),
        service_seconds=1,
        max_service_risk=0.5,
    )

    assert problem.eligible_candidates() == ()
    assert problem.infeasibility_reasons() == (
        "risky:service_risk_exceeded=0.800",
        "short-shift:courier_unavailable_until=5.000",
    )
