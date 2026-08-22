from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass, field
from math import ceil, isfinite
from time import perf_counter

from routemind_compute.application.registry import StrategyRegistry
from routemind_compute.application.travel import TravelTimeProvider
from routemind_compute.domain.dispatch import CourierCandidate, DispatchProblem, GeoPoint


@dataclass(frozen=True, slots=True)
class DemandEvent:
    request_id: str
    pickup: GeoPoint
    tick: int

    def __post_init__(self) -> None:
        if not self.request_id.strip():
            raise ValueError("request_id must not be blank")
        if self.tick < 0:
            raise ValueError("tick must be non-negative")


@dataclass(frozen=True, slots=True)
class CourierState:
    courier_id: str
    location: GeoPoint
    available_tick: int = 0

    def __post_init__(self) -> None:
        if not self.courier_id.strip():
            raise ValueError("courier_id must not be blank")
        if self.available_tick < 0:
            raise ValueError("available_tick must be non-negative")


@dataclass(frozen=True, slots=True)
class ScenarioManifest:
    scenario_id: str
    seed: int
    demands: tuple[DemandEvent, ...]
    couriers: tuple[CourierState, ...]
    delay_ticks: tuple[int, ...] = (0,)
    traffic_multiplier: float = 1.0

    def __post_init__(self) -> None:
        if not self.scenario_id.strip():
            raise ValueError("scenario_id must not be blank")
        if not self.demands:
            raise ValueError("scenario must contain at least one demand")
        if len({event.request_id for event in self.demands}) != len(self.demands):
            raise ValueError("demand request identifiers must be unique")
        if len({courier.courier_id for courier in self.couriers}) != len(self.couriers):
            raise ValueError("courier identifiers must be unique")
        if not self.couriers:
            raise ValueError("scenario must contain at least one courier")
        if not self.delay_ticks or any(delay < 0 for delay in self.delay_ticks):
            raise ValueError("delay_ticks must contain non-negative values")
        if not isfinite(self.traffic_multiplier) or self.traffic_multiplier <= 0:
            raise ValueError("traffic_multiplier must be finite and positive")


@dataclass(frozen=True, slots=True)
class StateTransition:
    request_id: str
    tick: int
    from_state: str
    to_state: str
    courier_id: str | None


@dataclass(frozen=True, slots=True)
class TwinClock:
    """Simulation time is advanced explicitly and never derived from wall time."""

    tick: int = 0
    ticks_per_hour: int = 60

    def __post_init__(self) -> None:
        if self.tick < 0:
            raise ValueError("clock tick must be non-negative")
        if self.ticks_per_hour <= 0:
            raise ValueError("clock ticks_per_hour must be positive")

    @property
    def simulated_time_seconds(self) -> float:
        return self.tick * 3600 / self.ticks_per_hour

    def advance_to(self, tick: int) -> TwinClock:
        if tick < self.tick:
            raise ValueError("clock cannot move backwards")
        return TwinClock(tick, self.ticks_per_hour)


@dataclass(frozen=True, slots=True)
class ScenarioDecision:
    request_id: str
    tick: int
    courier_id: str | None
    strategy: str
    strategy_version: str


@dataclass(frozen=True, slots=True)
class ScenarioRun:
    scenario_id: str
    seed: int
    decisions: tuple[ScenarioDecision, ...]
    transitions: tuple[StateTransition, ...]
    replay_digest: str
    simulated_end_tick: int = 0
    wall_clock_elapsed_seconds: float = field(default=0.0, compare=False)


class ScenarioKernel:
    def __init__(
        self,
        registry: StrategyRegistry,
        travel_provider: TravelTimeProvider,
        strategy: str = "nearest",
        ticks_per_hour: int = 60,
    ) -> None:
        if ticks_per_hour <= 0:
            raise ValueError("ticks_per_hour must be positive")
        self.registry = registry
        self.travel_provider = travel_provider
        self.strategy = strategy
        self.ticks_per_hour = ticks_per_hour

    def run(self, manifest: ScenarioManifest) -> ScenarioRun:
        wall_started = perf_counter()
        clock = TwinClock(0, self.ticks_per_hour)
        available = {courier.courier_id: courier for courier in manifest.couriers}
        rng = random.Random(manifest.seed)
        decisions: list[ScenarioDecision] = []
        transitions: list[StateTransition] = []
        for event in sorted(manifest.demands, key=lambda item: (item.tick, item.request_id)):
            clock = clock.advance_to(event.tick)
            candidates = tuple(
                CourierCandidate(courier_id, state.location)
                for courier_id, state in sorted(available.items())
                if state.available_tick <= event.tick
            )
            dispatch = self.registry.solve(
                self.strategy, DispatchProblem(event.request_id, event.pickup, candidates)
            )
            decisions.append(
                ScenarioDecision(
                    event.request_id,
                    event.tick,
                    dispatch.courier_id,
                    dispatch.strategy,
                    dispatch.strategy_version,
                )
            )
            transitions.append(
                StateTransition(
                    event.request_id,
                    event.tick,
                    "PENDING",
                    "ASSIGNED" if dispatch.courier_id else "UNASSIGNED",
                    dispatch.courier_id,
                )
            )
            if dispatch.courier_id:
                courier = available[dispatch.courier_id]
                travel = self.travel_provider.estimate(courier.location, event.pickup)
                traffic_seconds = travel.seconds * manifest.traffic_multiplier
                travel_ticks = ceil(traffic_seconds / (3600 / self.ticks_per_hour))
                delay = manifest.delay_ticks[rng.randrange(len(manifest.delay_ticks))]
                available[dispatch.courier_id] = CourierState(
                    dispatch.courier_id, event.pickup, event.tick + travel_ticks + delay
                )
        payload = {
            "scenario_id": manifest.scenario_id,
            "seed": manifest.seed,
            "simulated_end_tick": clock.tick,
            "decisions": [
                {
                    "request_id": decision.request_id,
                    "tick": decision.tick,
                    "courier_id": decision.courier_id,
                    "strategy": decision.strategy,
                    "strategy_version": decision.strategy_version,
                }
                for decision in decisions
            ],
            "transitions": [
                {
                    "request_id": transition.request_id,
                    "tick": transition.tick,
                    "from_state": transition.from_state,
                    "to_state": transition.to_state,
                    "courier_id": transition.courier_id,
                }
                for transition in transitions
            ],
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        return ScenarioRun(
            manifest.scenario_id,
            manifest.seed,
            tuple(decisions),
            tuple(transitions),
            digest,
            clock.tick,
            perf_counter() - wall_started,
        )
