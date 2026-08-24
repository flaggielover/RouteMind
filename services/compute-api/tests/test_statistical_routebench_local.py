from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from routemind_compute.application.parameters import Metadata
from routemind_compute.application.registry import StrategyRegistry, default_registry
from routemind_compute.application.statistical_routebench_campaign import (
    CampaignAuthorization,
    PilotPairExecutionPlan,
    StatisticalRouteBenchCampaignPlan,
    build_pilot_campaign_plan,
    execute_campaign_pair,
)
from routemind_compute.application.statistical_routebench_local import (
    FrozenLocalPilotArmExecutor,
    RealizedStressScenario,
    realize_stress_scenario,
)
from routemind_compute.application.statistical_routebench_protocol import (
    StatisticalRouteBenchProtocol,
    load_statistical_routebench_protocol,
)
from routemind_compute.application.travel import DeterministicLocalTravelProvider
from routemind_compute.domain.dispatch import DispatchDecision, DispatchProblem

ROOT = Path(__file__).resolve().parents[3]
PROTOCOL_PATH = (
    ROOT
    / "docs"
    / "research"
    / "r3"
    / "manifests"
    / "statistical-routebench"
    / "statistical-routebench-v1.json"
)


def synthetic_protocol() -> StatisticalRouteBenchProtocol:
    return replace(
        load_statistical_routebench_protocol(PROTOCOL_PATH),
        protocol_id="synthetic-validation-r3-325",
    )


def synthetic_plan() -> StatisticalRouteBenchCampaignPlan:
    return build_pilot_campaign_plan(
        synthetic_protocol(),
        "synthetic-r3-325-pilot",
        CampaignAuthorization("1" * 40, 123456, "success", "2026-08-24T12:00:00Z"),
    )


def test_stress_generator_is_deterministic_and_content_addressed() -> None:
    protocol = synthetic_protocol()
    plan = synthetic_plan()
    pair = plan.pairs[0]
    regime = protocol.scenario_design.regimes[0]

    first = realize_stress_scenario(protocol, pair, regime)
    second = realize_stress_scenario(protocol, pair, regime)

    assert first == second
    assert first.scenario_digest == second.scenario_digest
    assert first.randomness.manifest_digest == second.randomness.manifest_digest
    assert len(first.requests) == 72
    assert len(first.couriers) == 12
    assert tuple(item.stream_name for item in first.randomness.realizations) == (
        "demand",
        "merchant",
        "courier",
        "traffic",
    )
    assert len({item.request_id for item in first.requests}) == 72


def test_every_frozen_stress_regime_changes_the_intended_scenario_dimension() -> None:
    protocol = synthetic_protocol()
    plan = synthetic_plan()
    first_by_regime = {
        pair.randomness.pair.regime_id: pair
        for pair in plan.pairs
        if pair.randomness.pair.replicate == 0
    }
    scenarios = {
        regime.regime_id: realize_stress_scenario(
            protocol, first_by_regime[regime.regime_id], regime
        )
        for regime in protocol.scenario_design.regimes
    }

    assert len(scenarios) == 8
    assert len(scenarios["surge"].requests) == 144
    assert len(scenarios["shortage"].couriers) == 6
    assert all(
        request.merchant_delay_ticks >= 5 for request in scenarios["merchant-delay"].requests
    )
    assert scenarios["travel-degradation"].regime.traffic_multiplier == 1.75
    stale = scenarios["location-staleness"]
    assert any(courier.actual_location != courier.reported_location for courier in stale.couriers)
    assert scenarios["compute-budget"].regime.decision_budget_millis == 5.0
    queue = scenarios["queue-pressure"]
    assert len(queue.requests) == 108
    assert queue.regime.demand_burst_size == 4
    assert queue.regime.merchant_queue_capacity == 4
    assert len({item.scenario_digest for item in scenarios.values()}) == 8


def test_synthetic_pair_runs_real_frozen_strategies_with_shared_randomness() -> None:
    protocol = synthetic_protocol()
    plan = synthetic_plan()
    pair = plan.pairs[0]
    executor = FrozenLocalPilotArmExecutor(
        protocol, default_registry(), DeterministicLocalTravelProvider()
    )

    record = execute_campaign_pair(pair, executor)

    assert record.complete
    assert len(record.attempts) == 2
    candidate = next(item for item in record.attempts if item.arm_role == "candidate")
    comparator = next(item for item in record.attempts if item.arm_role == "comparator")
    assert candidate.outcome == "COMPLETED"
    assert comparator.outcome == "COMPLETED"
    assert candidate.request_count == comparator.request_count == 72
    assert candidate.event_ids == comparator.event_ids
    assert candidate.scenario_manifest_digest == comparator.scenario_manifest_digest
    assert candidate.stream_realization_digests == comparator.stream_realization_digests
    assert 0.0 <= (candidate.scenario_risk_index or 0.0) <= 1.0
    assert 0.0 <= (comparator.scenario_risk_index or 0.0) <= 1.0

    repeated = execute_campaign_pair(
        pair,
        FrozenLocalPilotArmExecutor(
            protocol, default_registry(), DeterministicLocalTravelProvider()
        ),
    )
    assert tuple(item.deterministic_result_digest for item in record.attempts) == tuple(
        item.deterministic_result_digest for item in repeated.attempts
    )


def test_harness_defect_is_retried_once_and_never_fabricates_metrics() -> None:
    protocol = synthetic_protocol()
    pair = synthetic_plan().pairs[0]
    executor = FrozenLocalPilotArmExecutor(
        protocol, StrategyRegistry(), DeterministicLocalTravelProvider()
    )

    record = execute_campaign_pair(pair, executor)

    assert not record.complete
    assert len(record.attempts) == 4
    assert all(item.outcome == "HARNESS_DEFECT" for item in record.attempts)
    assert all(item.request_count is None for item in record.attempts)
    assert all(item.scenario_manifest_digest is None for item in record.attempts)
    assert tuple(item.attempt for item in record.attempts) == (1, 2, 1, 2)


def test_stress_generator_rejects_regime_identity_drift() -> None:
    protocol = synthetic_protocol()
    pair = synthetic_plan().pairs[0]
    with pytest.raises(ValueError, match="regime escaped"):
        realize_stress_scenario(protocol, pair, protocol.scenario_design.regimes[1])


class RaisingRegistry(StrategyRegistry):
    def solve(
        self, name: str, problem: DispatchProblem, configuration: Metadata = ()
    ) -> DispatchDecision:
        del name, problem, configuration
        raise RuntimeError("synthetic strategy failure")


class UnassignedRegistry(StrategyRegistry):
    def solve(
        self, name: str, problem: DispatchProblem, configuration: Metadata = ()
    ) -> DispatchDecision:
        del configuration
        return DispatchDecision(problem.request_id, name, None, None)


class MemoryExecutor(FrozenLocalPilotArmExecutor):
    def _scenario(self, pair: PilotPairExecutionPlan) -> RealizedStressScenario:
        del pair
        raise MemoryError


class WrongVersionStrategy:
    name = "risk-aware"
    version = "2.0.0"

    def solve(self, problem: DispatchProblem) -> DispatchDecision:
        return DispatchDecision(problem.request_id, self.name, None, None, (), self.version)


def test_solver_failure_timeout_and_unassigned_outcomes_are_retained() -> None:
    protocol = synthetic_protocol()
    pair = synthetic_plan().pairs[0]

    failed = FrozenLocalPilotArmExecutor(
        protocol,
        RaisingRegistry((WrongVersionStrategy(),)),
        DeterministicLocalTravelProvider(),
    )(pair, "candidate", 1)
    assert failed.outcome == "HARNESS_DEFECT"

    raising = RaisingRegistry()
    raising.register(default_registry().get("risk-aware"))
    strategy_failures = FrozenLocalPilotArmExecutor(
        protocol, raising, DeterministicLocalTravelProvider()
    )(pair, "candidate", 1)
    assert strategy_failures.outcome == "COMPLETED"
    assert strategy_failures.strategy_failure_count == 72
    assert strategy_failures.assigned_count == 0

    unassigned_registry = UnassignedRegistry()
    unassigned_registry.register(default_registry().get("risk-aware"))
    unassigned = FrozenLocalPilotArmExecutor(
        protocol, unassigned_registry, DeterministicLocalTravelProvider()
    )(pair, "candidate", 1)
    assert unassigned.outcome == "COMPLETED"
    assert unassigned.assigned_count == 0
    assert unassigned.scenario_risk_index == 1.0

    first_regime = replace(protocol.scenario_design.regimes[0], decision_budget_millis=-1.0)
    timeout_protocol = replace(
        protocol,
        scenario_design=replace(
            protocol.scenario_design,
            regimes=(first_regime, *protocol.scenario_design.regimes[1:]),
        ),
    )
    decision_timeouts = FrozenLocalPilotArmExecutor(
        timeout_protocol, default_registry(), DeterministicLocalTravelProvider()
    )(pair, "candidate", 1)
    assert decision_timeouts.outcome == "COMPLETED"
    assert decision_timeouts.timeout_count == 72
    assert decision_timeouts.assigned_count == 0


def test_memory_version_and_wall_timeout_fail_closed_with_frozen_scoring() -> None:
    protocol = synthetic_protocol()
    pair = synthetic_plan().pairs[0]
    memory = MemoryExecutor(protocol, default_registry(), DeterministicLocalTravelProvider())(
        pair, "candidate", 1
    )
    assert memory.outcome == "INFRASTRUCTURE_DEFECT"
    assert memory.failure_code == "PYTHON_MEMORY_ERROR"

    wrong_version = FrozenLocalPilotArmExecutor(
        protocol,
        StrategyRegistry((WrongVersionStrategy(),)),
        DeterministicLocalTravelProvider(),
    )(pair, "candidate", 1)
    assert wrong_version.outcome == "HARNESS_DEFECT"
    assert "version drifted" in (wrong_version.failure_code or "")

    timeout_protocol = replace(
        protocol,
        resource_envelope=replace(protocol.resource_envelope, arm_wall_timeout_seconds=0),
    )
    wall_timeout = FrozenLocalPilotArmExecutor(
        timeout_protocol, default_registry(), DeterministicLocalTravelProvider()
    )(pair, "candidate", 1)
    assert wall_timeout.outcome == "TIMEOUT"
    assert wall_timeout.assigned_count == 0
    assert wall_timeout.assignment_rate == 0.0
    assert wall_timeout.scenario_risk_index == 1.0
    assert wall_timeout.timeout_count == 72
