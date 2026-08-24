"""Frozen local stress generator and arm executor for R3-325."""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import UTC, datetime
from math import ceil
from statistics import fmean
from time import perf_counter

from routemind_compute.application.execution import canonical_digest
from routemind_compute.application.registry import StrategyRegistry
from routemind_compute.application.statistical_routebench_campaign import (
    ArmExecutionAttempt,
    ArmOutcome,
    ArmRole,
    PilotPairExecutionPlan,
)
from routemind_compute.application.statistical_routebench_protocol import (
    StatisticalRouteBenchArm,
    StatisticalRouteBenchProtocol,
    StatisticalRouteBenchRegime,
)
from routemind_compute.application.statistical_routebench_randomness import (
    PairedRandomnessManifest,
    freeze_pair_randomness,
)
from routemind_compute.application.travel import TravelTimeProvider
from routemind_compute.domain.dispatch import CourierCandidate, DispatchProblem, GeoPoint


@dataclass(frozen=True, slots=True)
class StressRequest:
    request_id: str
    tick: int
    pickup: GeoPoint
    merchant_delay_ticks: int
    traffic_jitter: float

    def payload(self) -> dict[str, object]:
        return {
            "request_id": self.request_id,
            "tick": self.tick,
            "pickup": [self.pickup.latitude, self.pickup.longitude],
            "merchant_delay_ticks": self.merchant_delay_ticks,
            "traffic_jitter": self.traffic_jitter,
        }


@dataclass(frozen=True, slots=True)
class StressCourier:
    courier_id: str
    actual_location: GeoPoint
    reported_location: GeoPoint
    service_risk: float
    overtime_risk: float

    def payload(self) -> dict[str, object]:
        return {
            "courier_id": self.courier_id,
            "actual_location": [
                self.actual_location.latitude,
                self.actual_location.longitude,
            ],
            "reported_location": [
                self.reported_location.latitude,
                self.reported_location.longitude,
            ],
            "service_risk": self.service_risk,
            "overtime_risk": self.overtime_risk,
        }


@dataclass(frozen=True, slots=True)
class RealizedStressScenario:
    regime: StatisticalRouteBenchRegime
    randomness: PairedRandomnessManifest
    requests: tuple[StressRequest, ...]
    couriers: tuple[StressCourier, ...]

    @property
    def scenario_digest(self) -> str:
        return canonical_digest(self.payload())

    def payload(self) -> dict[str, object]:
        return {
            "regime": {
                "regime_id": self.regime.regime_id,
                "demand_multiplier": self.regime.demand_multiplier,
                "demand_burst_size": self.regime.demand_burst_size,
                "supply_multiplier": self.regime.supply_multiplier,
                "merchant_delay_ticks": self.regime.merchant_delay_ticks,
                "traffic_multiplier": self.regime.traffic_multiplier,
                "location_staleness_seconds": self.regime.location_staleness_seconds,
                "decision_budget_millis": self.regime.decision_budget_millis,
                "merchant_queue_capacity": self.regime.merchant_queue_capacity,
            },
            "randomness": self.randomness.payload(),
            "requests": [item.payload() for item in self.requests],
            "couriers": [item.payload() for item in self.couriers],
        }


@dataclass(slots=True)
class _CourierRuntime:
    actual_location: GeoPoint
    reported_location: GeoPoint
    reported_offset: tuple[float, float]
    available_tick: int
    service_risk: float
    overtime_risk: float


class FrozenLocalPilotArmExecutor:
    """Execute one arm at a time while caching one realization per CRN pair."""

    def __init__(
        self,
        protocol: StatisticalRouteBenchProtocol,
        registry: StrategyRegistry,
        travel_provider: TravelTimeProvider,
    ) -> None:
        self.protocol = protocol
        self.registry = registry
        self.travel_provider = travel_provider
        self._scenario_by_pair: dict[str, RealizedStressScenario] = {}

    def __call__(
        self,
        pair: PilotPairExecutionPlan,
        role: ArmRole,
        attempt: int,
    ) -> ArmExecutionAttempt:
        arm = self.protocol.candidate if role == "candidate" else self.protocol.comparator
        started_at = _utc_now()
        started = perf_counter()
        try:
            scenario = self._scenario(pair)
            observation = self._run_arm(pair, role, attempt, arm, scenario, started_at, started)
        except MemoryError:
            observation = self._defect_attempt(
                pair,
                role,
                attempt,
                arm,
                started_at,
                started,
                "INFRASTRUCTURE_DEFECT",
                "PYTHON_MEMORY_ERROR",
            )
        except Exception as error:
            observation = self._defect_attempt(
                pair,
                role,
                attempt,
                arm,
                started_at,
                started,
                "HARNESS_DEFECT",
                f"{type(error).__name__}:{str(error)[:160]}",
            )
        return observation

    def _scenario(self, pair: PilotPairExecutionPlan) -> RealizedStressScenario:
        cached = self._scenario_by_pair.get(pair.randomness.plan_digest)
        if cached is not None:
            return cached
        regime = next(
            item
            for item in self.protocol.scenario_design.regimes
            if item.regime_id == pair.randomness.pair.regime_id
        )
        scenario = realize_stress_scenario(self.protocol, pair, regime)
        self._scenario_by_pair[pair.randomness.plan_digest] = scenario
        return scenario

    def _run_arm(
        self,
        pair: PilotPairExecutionPlan,
        role: ArmRole,
        attempt: int,
        arm: StatisticalRouteBenchArm,
        scenario: RealizedStressScenario,
        started_at: str,
        started: float,
    ) -> ArmExecutionAttempt:
        registered_version = str(getattr(self.registry.get(arm.strategy), "version", ""))
        if registered_version != arm.version:
            raise ValueError("registered strategy version drifted from frozen arm")
        runtime = {
            item.courier_id: _CourierRuntime(
                item.actual_location,
                item.reported_location,
                (
                    item.reported_location.latitude - item.actual_location.latitude,
                    item.reported_location.longitude - item.actual_location.longitude,
                ),
                0,
                item.service_risk,
                item.overtime_risk,
            )
            for item in scenario.couriers
        }
        risks: list[float] = []
        assigned = 0
        timeouts = 0
        failures = 0
        event_ids: list[str] = []
        parameter_configuration = tuple(
            (key, format(value, ".15g")) for key, value in arm.parameters
        )
        seconds_per_tick = 3600.0 / self.protocol.scenario_design.ticks_per_hour
        for request in scenario.requests:
            event_ids.append(request.request_id)
            candidates = tuple(
                CourierCandidate(
                    courier_id,
                    state.reported_location,
                    service_risk=state.service_risk,
                    overtime_risk=state.overtime_risk,
                )
                for courier_id, state in sorted(runtime.items())
                if state.available_tick <= request.tick
            )
            decision_started = perf_counter()
            try:
                decision = self.registry.solve(
                    arm.strategy,
                    DispatchProblem(
                        request.request_id,
                        request.pickup,
                        candidates,
                        pickup_ready_at_seconds=(request.tick + request.merchant_delay_ticks)
                        * seconds_per_tick,
                    ),
                    parameter_configuration,
                )
            except Exception:
                failures += 1
                risks.append(1.0)
                continue
            decision_millis = (perf_counter() - decision_started) * 1000.0
            if decision_millis > scenario.regime.decision_budget_millis:
                timeouts += 1
                risks.append(1.0)
                continue
            if decision.courier_id is None:
                risks.append(1.0)
                continue
            selected = runtime[decision.courier_id]
            assigned += 1
            risks.append(0.5 * selected.service_risk + 0.5 * selected.overtime_risk)
            travel = self.travel_provider.estimate(selected.actual_location, request.pickup)
            travel_ticks = ceil(
                travel.seconds
                * scenario.regime.traffic_multiplier
                * request.traffic_jitter
                / seconds_per_tick
            )
            selected.actual_location = request.pickup
            selected.reported_location = GeoPoint(
                max(
                    -90.0,
                    min(90.0, request.pickup.latitude + selected.reported_offset[0]),
                ),
                max(
                    -180.0,
                    min(180.0, request.pickup.longitude + selected.reported_offset[1]),
                ),
            )
            selected.available_tick = max(
                selected.available_tick,
                request.tick + request.merchant_delay_ticks,
            )
            selected.available_tick += travel_ticks

        elapsed_millis = (perf_counter() - started) * 1000.0
        if elapsed_millis > self.protocol.resource_envelope.arm_wall_timeout_seconds * 1000:
            return _scored_arm_failure(
                pair,
                role,
                attempt,
                arm,
                started_at,
                elapsed_millis,
                len(scenario.requests),
                tuple(event_ids),
                scenario,
                "TIMEOUT",
                "ARM_WALL_TIMEOUT",
            )
        deterministic = {
            "pair_plan_digest": pair.pair_plan_digest,
            "arm_role": role,
            "strategy": arm.strategy,
            "strategy_version": arm.version,
            "scenario_digest": scenario.scenario_digest,
            "request_count": len(scenario.requests),
            "assigned_count": assigned,
            "scenario_risk_index": fmean(risks),
            "strategy_failure_count": failures,
            "fallback_count": 0,
            "timeout_count": timeouts,
            "event_ids": event_ids,
        }
        stream_digests = tuple(
            (item.stream_name, item.realization_digest) for item in scenario.randomness.realizations
        )
        return ArmExecutionAttempt(
            pair_plan_digest=pair.pair_plan_digest,
            arm_role=role,
            strategy=arm.strategy,
            strategy_version=arm.version,
            attempt=attempt,
            outcome="COMPLETED",
            started_at_utc=started_at,
            completed_at_utc=_utc_now(),
            request_count=len(scenario.requests),
            assigned_count=assigned,
            scenario_risk_index=fmean(risks),
            assignment_rate=assigned / len(scenario.requests),
            runtime_millis=elapsed_millis,
            strategy_failure_count=failures,
            fallback_count=0,
            timeout_count=timeouts,
            event_ids=tuple(event_ids),
            scenario_manifest_digest=scenario.randomness.manifest_digest,
            stream_realization_digests=stream_digests,
            deterministic_result_digest=canonical_digest(deterministic),
        )

    @staticmethod
    def _defect_attempt(
        pair: PilotPairExecutionPlan,
        role: ArmRole,
        attempt: int,
        arm: StatisticalRouteBenchArm,
        started_at: str,
        started: float,
        outcome: ArmOutcome,
        failure_code: str,
    ) -> ArmExecutionAttempt:
        deterministic = {
            "pair_plan_digest": pair.pair_plan_digest,
            "arm_role": role,
            "strategy": arm.strategy,
            "attempt": attempt,
            "outcome": outcome,
            "failure_code": failure_code,
        }
        return ArmExecutionAttempt(
            pair_plan_digest=pair.pair_plan_digest,
            arm_role=role,
            strategy=arm.strategy,
            strategy_version=arm.version,
            attempt=attempt,
            outcome=outcome,
            started_at_utc=started_at,
            completed_at_utc=_utc_now(),
            request_count=None,
            assigned_count=None,
            scenario_risk_index=None,
            assignment_rate=None,
            runtime_millis=(perf_counter() - started) * 1000.0,
            strategy_failure_count=0,
            fallback_count=0,
            timeout_count=0,
            event_ids=(),
            scenario_manifest_digest=None,
            stream_realization_digests=(),
            deterministic_result_digest=canonical_digest(deterministic),
            failure_code=failure_code,
        )


def realize_stress_scenario(
    protocol: StatisticalRouteBenchProtocol,
    pair: PilotPairExecutionPlan,
    regime: StatisticalRouteBenchRegime,
) -> RealizedStressScenario:
    if regime.regime_id != pair.randomness.pair.regime_id:
        raise ValueError("stress regime escaped pair identity")
    demand_rng = random.Random(pair.randomness.stream("demand").seed)
    merchant_rng = random.Random(pair.randomness.stream("merchant").seed)
    courier_rng = random.Random(pair.randomness.stream("courier").seed)
    traffic_rng = random.Random(pair.randomness.stream("traffic").seed)
    design = protocol.scenario_design
    request_count = max(
        1,
        round(
            design.base_demand_rate_per_hour
            * (design.horizon_ticks / design.ticks_per_hour)
            * regime.demand_multiplier
        ),
    )
    burst_count = ceil(request_count / regime.demand_burst_size)
    burst_ticks = sorted(demand_rng.randrange(design.horizon_ticks) for _ in range(burst_count))
    requests: list[StressRequest] = []
    for index in range(request_count):
        burst_index = index // regime.demand_burst_size
        position = index % regime.demand_burst_size
        queue_delay = position // regime.merchant_queue_capacity
        merchant_jitter = (
            merchant_rng.randrange(regime.merchant_delay_ticks + 1)
            if regime.merchant_delay_ticks
            else 0
        )
        requests.append(
            StressRequest(
                request_id=(
                    f"{pair.randomness.pair.regime_id}-"
                    f"{pair.randomness.pair.replicate:04d}-{index:04d}"
                ),
                tick=burst_ticks[burst_index],
                pickup=GeoPoint(
                    31.2304 + demand_rng.uniform(-0.03, 0.03),
                    121.4737 + demand_rng.uniform(-0.03, 0.03),
                ),
                merchant_delay_ticks=regime.merchant_delay_ticks + merchant_jitter + queue_delay,
                traffic_jitter=traffic_rng.uniform(0.9, 1.1),
            )
        )
    courier_count = max(1, round(design.base_courier_count * regime.supply_multiplier))
    staleness_scale = regime.location_staleness_seconds / 300.0
    couriers = tuple(
        _stress_courier(courier_rng, index, staleness_scale) for index in range(courier_count)
    )
    requests_tuple = tuple(sorted(requests, key=lambda item: (item.tick, item.request_id)))
    stream_payloads = {
        "demand": [
            {
                "request_id": item.request_id,
                "tick": item.tick,
                "pickup": [item.pickup.latitude, item.pickup.longitude],
            }
            for item in requests_tuple
        ],
        "merchant": [[item.request_id, item.merchant_delay_ticks] for item in requests_tuple],
        "courier": [item.payload() for item in couriers],
        "traffic": [[item.request_id, item.traffic_jitter] for item in requests_tuple],
    }
    randomness = freeze_pair_randomness(pair.randomness, stream_payloads)
    return RealizedStressScenario(regime, randomness, requests_tuple, couriers)


def _stress_courier(
    rng: random.Random,
    index: int,
    staleness_scale: float,
) -> StressCourier:
    actual = GeoPoint(
        31.2304 + rng.uniform(-0.04, 0.04),
        121.4737 + rng.uniform(-0.04, 0.04),
    )
    reported = GeoPoint(
        actual.latitude + rng.uniform(-0.01, 0.01) * staleness_scale,
        actual.longitude + rng.uniform(-0.01, 0.01) * staleness_scale,
    )
    return StressCourier(
        courier_id=f"courier-{index:03d}",
        actual_location=actual,
        reported_location=reported,
        service_risk=rng.random(),
        overtime_risk=rng.random(),
    )


def _scored_arm_failure(
    pair: PilotPairExecutionPlan,
    role: ArmRole,
    attempt: int,
    arm: StatisticalRouteBenchArm,
    started_at: str,
    elapsed_millis: float,
    request_count: int,
    event_ids: tuple[str, ...],
    scenario: RealizedStressScenario,
    outcome: ArmOutcome,
    failure_code: str,
) -> ArmExecutionAttempt:
    deterministic = {
        "pair_plan_digest": pair.pair_plan_digest,
        "arm_role": role,
        "strategy": arm.strategy,
        "outcome": outcome,
        "request_count": request_count,
        "event_ids": event_ids,
    }
    return ArmExecutionAttempt(
        pair_plan_digest=pair.pair_plan_digest,
        arm_role=role,
        strategy=arm.strategy,
        strategy_version=arm.version,
        attempt=attempt,
        outcome=outcome,
        started_at_utc=started_at,
        completed_at_utc=_utc_now(),
        request_count=request_count,
        assigned_count=0,
        scenario_risk_index=1.0,
        assignment_rate=0.0,
        runtime_millis=elapsed_millis,
        strategy_failure_count=request_count if outcome == "STRATEGY_FAILURE" else 0,
        fallback_count=0,
        timeout_count=request_count if outcome == "TIMEOUT" else 0,
        event_ids=event_ids,
        scenario_manifest_digest=scenario.randomness.manifest_digest,
        stream_realization_digests=tuple(
            (item.stream_name, item.realization_digest) for item in scenario.randomness.realizations
        ),
        deterministic_result_digest=canonical_digest(deterministic),
        failure_code=failure_code,
    )


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


__all__ = [
    "FrozenLocalPilotArmExecutor",
    "RealizedStressScenario",
    "StressCourier",
    "StressRequest",
    "realize_stress_scenario",
]
