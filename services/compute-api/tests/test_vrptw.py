from __future__ import annotations

from types import SimpleNamespace
from typing import cast

import pytest

from routemind_compute.application.nearest import great_circle_distance_kilometres
from routemind_compute.application.registry import default_registry
from routemind_compute.application.vrptw import (
    MAX_VRP_STOPS,
    VrpProblem,
    VrpStop,
    VrptwRoutePlanner,
    VrptwStrategy,
    VrpVehicle,
)
from routemind_compute.domain.dispatch import (
    CourierCandidate,
    DispatchProblem,
    GeoPoint,
    TimeWindow,
)


def test_vrptw_insertion_is_deterministic_and_matches_small_reference_baseline() -> None:
    depot = GeoPoint(0, 0)
    problem = VrpProblem(
        "vrp-baseline",
        depot,
        (
            VrpStop("b", GeoPoint(0, 0.02), service_seconds=10),
            VrpStop("a", GeoPoint(0, 0.01), service_seconds=5),
        ),
        (VrpVehicle("vehicle-1", depot, 3),),
    )

    planner = VrptwRoutePlanner()
    first = planner.plan(problem)
    second = planner.plan(problem)

    assert first == second
    assert first.unassigned == ()
    assert first.routes[0].stop_ids == ("a", "b")
    assert first.routes[0].load_units == pytest.approx(2)
    assert first.routes[0].travel_seconds == pytest.approx(
        2 * great_circle_distance_kilometres(0, 0, 0, 0.02) / 30 * 3600,
        rel=0.02,
    )
    assert first.routes[0].departure_seconds[0] == pytest.approx(
        first.routes[0].service_start_seconds[0] + 5
    )


def test_vrptw_respects_capacity_and_reports_stable_reason() -> None:
    problem = VrpProblem(
        "vrp-capacity",
        GeoPoint(0, 0),
        (VrpStop("large", GeoPoint(0, 0.01), demand_units=2),),
        (VrpVehicle("small", GeoPoint(0, 0), 1),),
    )

    result = VrptwRoutePlanner().plan(problem)

    assert result.routes == ()
    assert result.unassigned == (("large", "capacity_insufficient"),)


def test_vrptw_time_window_waits_and_rejects_late_route() -> None:
    depot = GeoPoint(0, 0)
    waiting = VrpProblem(
        "vrp-wait",
        depot,
        (VrpStop("morning", depot, service_seconds=3, time_window=TimeWindow(10, 20)),),
        (VrpVehicle("vehicle", depot, 1),),
        return_to_depot=False,
    )
    assert VrptwRoutePlanner().plan(waiting).routes[0].service_start_seconds == (10,)

    late = VrpProblem(
        "vrp-late",
        depot,
        (VrpStop("late", GeoPoint(0, 0.1), time_window=TimeWindow(0, 1)),),
        (VrpVehicle("vehicle", depot, 1),),
        return_to_depot=False,
    )
    assert VrptwRoutePlanner().plan(late).unassigned == (("late", "time_window_missed"),)


def test_vrptw_strategy_is_registered_and_adapts_dispatch_constraints() -> None:
    registry = default_registry()
    assert "vrptw" in registry.names()
    problem = DispatchProblem(
        "dispatch-vrptw",
        GeoPoint(0, 0),
        (
            CourierCandidate("far", GeoPoint(0, 0.1), capacity_units=4),
            CourierCandidate("near", GeoPoint(0, 0.01), capacity_units=2),
        ),
        demand_units=2,
        service_seconds=5,
        delivery_window=TimeWindow(0, 30_000),
    )

    result = registry.solve("vrptw", problem)

    assert result.courier_id == "near"
    assert result.rationale == ("lowest feasible VRPTW route",)
    assert dict(result.metadata)["route_stop_count"] == "1"


def test_vrptw_strategy_exposes_route_infeasibility_after_baseline_filter() -> None:
    problem = DispatchProblem(
        "dispatch-vrptw-late",
        GeoPoint(0, 0),
        (CourierCandidate("courier", GeoPoint(0, 0.1), capacity_units=1),),
        delivery_window=TimeWindow(0, 1),
    )

    result = VrptwStrategy().solve(problem)

    assert result.courier_id is None
    assert result.rationale == ("no feasible VRPTW route", "dispatch-vrptw-late:time_window_missed")


def test_vrp_validation_rejects_duplicate_and_invalid_entities() -> None:
    point = GeoPoint(0, 0)
    with pytest.raises(ValueError, match="stop_id"):
        VrpStop(" ", point)
    with pytest.raises(ValueError, match="demand"):
        VrpStop("bad-demand", point, demand_units=0)
    with pytest.raises(ValueError, match="service"):
        VrpStop("bad-service", point, service_seconds=-1)
    with pytest.raises(ValueError, match="vehicle_id"):
        VrpVehicle(" ", point, 1)
    with pytest.raises(ValueError, match="capacity"):
        VrpVehicle("vehicle", point, -1)
    with pytest.raises(ValueError, match="availability"):
        VrpVehicle("vehicle", point, 1, available_from_seconds=-1)
    with pytest.raises(ValueError, match="availability window"):
        VrpVehicle("vehicle", point, 1, available_until_seconds=-1)
    with pytest.raises(ValueError, match="problem_id"):
        VrpProblem(" ", point, (), ())
    with pytest.raises(ValueError, match="stop identifiers"):
        VrpProblem(
            "duplicate",
            point,
            (VrpStop("same", point), VrpStop("same", point)),
            (),
        )
    with pytest.raises(ValueError, match="stop count"):
        VrpProblem(
            "too-many",
            point,
            tuple(VrpStop(f"stop-{index}", point) for index in range(MAX_VRP_STOPS + 1)),
            (),
        )
    with pytest.raises(ValueError, match="vehicle identifiers"):
        VrpProblem(
            "duplicate-vehicles",
            point,
            (),
            (VrpVehicle("same", point, 1), VrpVehicle("same", point, 1)),
        )


def test_vrptw_reports_vehicle_deadlines_and_empty_fleet() -> None:
    point = GeoPoint(0, 0)
    service_deadline = VrpProblem(
        "service-deadline",
        point,
        (VrpStop("stop", point, service_seconds=1),),
        (VrpVehicle("vehicle", point, 1, available_until_seconds=0),),
        return_to_depot=False,
    )
    assert VrptwRoutePlanner().plan(service_deadline).unassigned == (
        ("stop", "vehicle_unavailable_until"),
    )

    return_deadline = VrpProblem(
        "return-deadline",
        point,
        (VrpStop("stop", GeoPoint(0, 0.01)),),
        (VrpVehicle("vehicle", point, 1, available_until_seconds=140),),
    )
    assert VrptwRoutePlanner().plan(return_deadline).unassigned == (
        ("stop", "vehicle_unavailable_until"),
    )
    empty_fleet = VrpProblem("empty-fleet", point, (VrpStop("stop", point),), ())
    assert VrptwRoutePlanner().plan(empty_fleet).unassigned == (("stop", "no feasible route"),)


def test_vrptw_rejects_invalid_provider_results_and_ineligible_dispatch() -> None:
    class InvalidProvider:
        def estimate(self, origin: GeoPoint, destination: GeoPoint) -> object:
            return SimpleNamespace(seconds=cast(object, float("nan")))

    invalid_travel = VrpProblem(
        "invalid-travel",
        GeoPoint(0, 0),
        (VrpStop("stop", GeoPoint(0, 0.01)),),
        (VrpVehicle("vehicle", GeoPoint(0, 0), 1),),
    )
    with pytest.raises(ValueError, match="invalid seconds"):
        VrptwRoutePlanner(InvalidProvider()).plan(invalid_travel)  # type: ignore[arg-type]

    result = VrptwStrategy().solve(
        DispatchProblem(
            "ineligible",
            GeoPoint(0, 0),
            (CourierCandidate("offline", GeoPoint(0, 0), state="offline"),),
        )
    )
    assert result.rationale == (
        "no feasible VRPTW route",
        "offline:courier_state=offline",
    )
