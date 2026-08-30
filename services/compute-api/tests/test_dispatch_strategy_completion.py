from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import routemind_compute.api.app as app_module
import routemind_compute.application.local_search as local_search_module
from routemind_compute.api.app import app
from routemind_compute.application.flow import BatchDispatchProblem, BatchDispatchRequest
from routemind_compute.application.insertion import DynamicInsertionRequest, insert_order
from routemind_compute.application.local_search import LocalSearchConfig, LocalSearchStrategy
from routemind_compute.application.registry import default_registry
from routemind_compute.application.replanning import (
    DynamicReplanningPolicy,
    ReplanMetrics,
    ReplanRequest,
    ReplanTrigger,
)
from routemind_compute.application.simulation import (
    CourierState,
    DemandEvent,
    ScenarioKernel,
    ScenarioManifest,
    compare_strategies,
)
from routemind_compute.application.travel import (
    DeterministicLocalTravelProvider,
    DynamicTravelContext,
    FallbackTravelTimeProvider,
    TravelTime,
)
from routemind_compute.application.vrptw import VrpProblem, VrpRoute, VrpStop, VrpVehicle
from routemind_compute.domain.dispatch import (
    CourierCandidate,
    DispatchDecision,
    DispatchProblem,
    GeoPoint,
)


class BrokenProvider(DeterministicLocalTravelProvider):
    name = "broken"

    def estimate(
        self,
        origin: GeoPoint,
        destination: GeoPoint,
        context: DynamicTravelContext | None = None,
    ) -> TravelTime:
        del origin, destination, context
        raise RuntimeError("provider down")


def test_local_search_is_bounded_deterministic_and_verified() -> None:
    point = GeoPoint(0, 0)
    problem = BatchDispatchProblem(
        "batch",
        (
            BatchDispatchRequest("b", GeoPoint(0, 0.02)),
            BatchDispatchRequest("a", GeoPoint(0, 0.01)),
        ),
        (
            CourierCandidate("courier-b", point, capacity_units=1),
            CourierCandidate("courier-a", GeoPoint(0, 0.03), capacity_units=1),
        ),
    )
    strategy = LocalSearchStrategy(LocalSearchConfig(max_iterations=4))
    first = strategy.assign_batch(problem)
    second = strategy.assign_batch(problem)
    assert first.assignments == second.assignments
    assert first.unassigned == second.unassigned
    assert first.total_cost == second.total_cost
    assert first.strategy == "local-search"
    assert first.assignments

    single = default_registry().solve(
        "local-search",
        DispatchProblem("request", point, problem.candidates),
        (("max_iterations", "4"),),
    )
    assert single.courier_id == "courier-b"
    assert dict(single.metadata)["optimality_claim"] == "none"


def test_local_search_covers_infeasibility_and_bounded_pair_improvement(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(ValueError, match="between 1 and 256"):
        LocalSearchConfig(max_iterations=0)
    offline = BatchDispatchProblem(
        "offline",
        (BatchDispatchRequest("request", GeoPoint(0, 0)),),
        (CourierCandidate("offline", GeoPoint(0, 0), state="offline"),),
    )
    assert LocalSearchStrategy().assign_batch(offline).unassigned == (
        ("request", "offline:courier_state=offline"),
    )

    costs = {
        ("a", "courier-1"): 0.0,
        ("a", "courier-2"): 1.0,
        ("b", "courier-1"): 100.0,
        ("b", "courier-2"): 1000.0,
    }
    monkeypatch.setattr(
        local_search_module,
        "_distance",
        lambda request, candidate: costs[(request.request_id, candidate.courier_id)],
    )
    problem = BatchDispatchProblem(
        "swap",
        (
            BatchDispatchRequest("a", GeoPoint(0, 0)),
            BatchDispatchRequest("b", GeoPoint(0, 0)),
        ),
        (
            CourierCandidate("courier-1", GeoPoint(0, 0)),
            CourierCandidate("courier-2", GeoPoint(0, 0)),
        ),
    )
    result = LocalSearchStrategy().assign_batch(problem)
    assert [(item.request_id, item.courier_id) for item in result.assignments] == [
        ("a", "courier-2"),
        ("b", "courier-1"),
    ]


def test_scenario_comparison_keeps_fixed_runs_separate_and_reports_incompatibility() -> None:
    manifest = ScenarioManifest(
        "comparison",
        7,
        (DemandEvent("request", GeoPoint(0, 0), 0),),
        (CourierState("courier", GeoPoint(0, 0.01)),),
    )
    comparison = compare_strategies(
        default_registry(),
        DeterministicLocalTravelProvider(),
        manifest,
        ("nearest", "local-search", "missing"),
    )
    assert [run.decisions[0].strategy for run in comparison.results] == [
        "nearest",
        "local-search",
    ]
    assert all(
        not observation.switch_occurred
        for run in comparison.results
        for observation in run.observations
    )
    assert comparison.incompatible == (("missing", "'unknown dispatch strategy: missing'"),)


def test_fallback_provider_state_reaches_rm237_observation() -> None:
    manifest = ScenarioManifest(
        "fallback",
        7,
        (DemandEvent("request", GeoPoint(0, 0), 0),),
        (CourierState("courier", GeoPoint(0, 0.01)),),
    )
    provider = FallbackTravelTimeProvider(BrokenProvider(), DeterministicLocalTravelProvider())
    run = ScenarioKernel(default_registry(), provider, strategy="nearest").run(manifest)
    assert run.observations[0].fallback_state == "FALLBACK_USED"
    assert dict(run.observations[0].provenance)["travel_fallback_reason"] in {
        "runtimeerror",
        "timeout",
    }


def test_insertion_and_replanning_preserve_provenance_without_mutation() -> None:
    depot = GeoPoint(0, 0)
    problem = VrpProblem(
        "plan-1",
        depot,
        (VrpStop("existing", GeoPoint(0, 0.01)),),
        (VrpVehicle("vehicle", depot, 2),),
        return_to_depot=False,
    )
    active_route = VrpRoute("vehicle", ("existing",), (0,), (0,), (0,), 1, 0, 0)
    request = DynamicInsertionRequest(
        "scenario",
        11,
        "plan:old",
        "vrptw",
        problem,
        active_route,
        VrpStop("new", GeoPoint(0, 0.02)),
    )
    first = insert_order(request)
    second = insert_order(request)
    assert first.replay_digest == second.replay_digest
    assert first.decision.accepted is True
    assert first.request.active_route == active_route
    assert first.resulting_plan_reference is not None

    with pytest.raises(ValueError, match="scenario_id"):
        DynamicInsertionRequest(
            " ", 11, "plan:old", "vrptw", problem, active_route, VrpStop("new-2", depot)
        )
    with pytest.raises(ValueError, match="seed"):
        DynamicInsertionRequest(
            "scenario", -1, "plan:old", "vrptw", problem, active_route, VrpStop("new-3", depot)
        )
    with pytest.raises(ValueError, match="previous"):
        DynamicInsertionRequest(
            "scenario", 11, " ", "vrptw", problem, active_route, VrpStop("new-4", depot)
        )
    with pytest.raises(ValueError, match="selected"):
        DynamicInsertionRequest(
            "scenario", 11, "plan:old", " ", problem, active_route, VrpStop("new-5", depot)
        )

    def metrics(travel: float) -> ReplanMetrics:
        return ReplanMetrics(1, 0, 0, travel, 1)

    replan_request = ReplanRequest(
        ReplanTrigger("event", "material_change", 300, "trace"),
        metrics(200),
        metrics(100),
        "plan:old",
        "vrptw",
        (("traffic_multiplier", "2.0"),),
    )
    decision = DynamicReplanningPolicy().evaluate(replan_request).decision
    assert decision.action == "replan"
    assert decision.previous_plan_reference == "plan:old"
    assert decision.selected_strategy == "vrptw"
    assert decision.replay_digest is not None

    with pytest.raises(ValueError, match="previous_plan_reference"):
        DynamicReplanningPolicy().evaluate(
            ReplanRequest(
                replan_request.trigger,
                replan_request.before,
                replan_request.after,
                " ",
            )
        )
    with pytest.raises(ValueError, match="triggering_state keys"):
        DynamicReplanningPolicy().evaluate(
            ReplanRequest(
                replan_request.trigger,
                replan_request.before,
                replan_request.after,
                "plan:old",
                "vrptw",
                (("duplicate", "1"), ("duplicate", "2")),
            )
        )


def test_api_exposes_registry_parameters_and_explicit_capability_paths() -> None:
    client = TestClient(app)
    catalog = client.get("/api/v1/strategies").json()
    capabilities = client.get("/api/v1/dispatch/capabilities")
    assert capabilities.status_code == 200
    assert {item["name"] for item in capabilities.json()} == {
        "dynamic-insertion",
        "dynamic-replanning",
        "batch-zone-orchestration",
        "generic-vrp",
    }
    local = next(item for item in catalog if item["name"] == "local-search")
    assert local["maturity"] == "ENGINEERING"
    assert local["parameters"][0]["key"] == "max_iterations"
    invalid = client.post(
        "/api/v1/strategies/execute",
        json={
            "scenario_id": "s",
            "seed": 1,
            "request_id": "r",
            "strategy": "local-search",
            "configuration": [["max_iterations", "0"]],
            "pickup": {"latitude": 0, "longitude": 0},
            "candidates": [],
        },
    )
    assert invalid.status_code == 422

    unknown = client.post(
        "/api/v1/strategies/execute",
        json={
            "scenario_id": "s",
            "seed": 1,
            "request_id": "r",
            "strategy": "missing",
            "pickup": {"latitude": 0, "longitude": 0},
            "candidates": [],
        },
    )
    assert unknown.status_code == 400


def test_strategy_execution_keeps_solver_failures_explicit() -> None:
    client = TestClient(app)

    class BrokenStrategy:
        name = "broken"
        version = "1.0.0"
        capabilities = ("dispatch",)

        def solve(self, problem: DispatchProblem) -> DispatchDecision:
            raise RuntimeError("injected failure")

    app_module.REGISTRY = default_registry()
    app_module.REGISTRY.register(BrokenStrategy())
    response = client.post(
        "/api/v1/strategies/execute",
        json={
            "scenario_id": "s",
            "seed": 1,
            "request_id": "r",
            "strategy": "broken",
            "pickup": {"latitude": 0, "longitude": 0},
            "candidates": [],
        },
    )
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "strategy_unavailable"
    app_module.REGISTRY = app_module.RUNTIME.registry


def test_api_exposes_insertion_and_replan_provenance_boundaries() -> None:
    client = TestClient(app)
    insertion = client.post(
        "/api/v1/dispatch/insertion",
        json={
            "scenario_id": "scenario",
            "seed": 11,
            "previous_plan_reference": "plan:old",
            "selected_strategy": "vrptw",
            "problem_id": "plan-1",
            "depot": {"latitude": 0, "longitude": 0},
            "stops": [{"stop_id": "existing", "location": {"latitude": 0, "longitude": 0.01}}],
            "vehicles": [
                {
                    "vehicle_id": "vehicle",
                    "start_location": {"latitude": 0, "longitude": 0},
                    "capacity_units": 2,
                }
            ],
            "return_to_depot": False,
            "active_route": {"vehicle_id": "vehicle", "stop_ids": ["existing"]},
            "new_stop": {"stop_id": "new", "location": {"latitude": 0, "longitude": 0.02}},
        },
    )
    assert insertion.status_code == 200
    assert insertion.json()["accepted"] is True
    assert insertion.json()["previous_plan_reference"] == "plan:old"
    assert len(insertion.json()["replay_digest"]) == 64

    replan = client.post(
        "/api/v1/dispatch/replan",
        json={
            "event_id": "event",
            "kind": "traffic_degradation",
            "observed_at_seconds": 300,
            "trace_id": "trace",
            "before": {
                "assigned_count": 1,
                "unassigned_count": 1,
                "late_count": 1,
                "total_travel_seconds": 200,
                "active_route_count": 1,
            },
            "after": {
                "assigned_count": 1,
                "unassigned_count": 0,
                "late_count": 0,
                "total_travel_seconds": 100,
                "active_route_count": 1,
            },
            "previous_plan_reference": "plan:old",
            "selected_strategy": "vrptw",
            "triggering_state": [["traffic_multiplier", "2.0"]],
        },
    )
    assert replan.status_code == 200
    assert replan.json()["action"] == "replan"
    assert replan.json()["previous_plan_reference"] == "plan:old"
    assert len(replan.json()["replay_digest"]) == 64
