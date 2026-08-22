from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from math import isfinite
from typing import Literal

from routemind_compute.application.travel import DynamicTravelContext, TravelUpdate

PerturbationKind = Literal["traffic", "supply", "merchant_delay", "dependency_failure"]
PerturbationSource = Literal["simulated", "live"]
PerturbationScope = Literal["global", "zone", "edge", "merchant", "courier_pool", "dependency"]


@dataclass(frozen=True, slots=True)
class ScenarioPerturbation:
    perturbation_id: str
    kind: PerturbationKind
    effective_from_seconds: float
    target: str
    end_at_seconds: float | None = None
    scope: PerturbationScope = "global"
    traffic_multiplier: float = 1.0
    delay_seconds: float = 0.0
    supply_delta: int = 0
    failure_mode: str = ""
    source: PerturbationSource = "simulated"

    def __post_init__(self) -> None:
        if not self.perturbation_id.strip():
            raise ValueError("perturbation id must not be blank")
        if self.kind not in {"traffic", "supply", "merchant_delay", "dependency_failure"}:
            raise ValueError("perturbation kind is not supported")
        if self.scope not in {"global", "zone", "edge", "merchant", "courier_pool", "dependency"}:
            raise ValueError("perturbation scope is not supported")
        if self.source not in {"simulated", "live"}:
            raise ValueError("perturbation source must be simulated or live")
        if not self.target.strip():
            raise ValueError("perturbation target must not be blank")
        if not isfinite(self.effective_from_seconds) or self.effective_from_seconds < 0:
            raise ValueError("perturbation effective time must be finite and non-negative")
        if self.end_at_seconds is not None and (
            not isfinite(self.end_at_seconds) or self.end_at_seconds <= self.effective_from_seconds
        ):
            raise ValueError("perturbation end time must be after effective time")
        if not isfinite(self.traffic_multiplier) or self.traffic_multiplier <= 0:
            raise ValueError("perturbation traffic multiplier must be finite and positive")
        if not isfinite(self.delay_seconds) or self.delay_seconds < 0:
            raise ValueError("perturbation delay must be finite and non-negative")
        if self.kind == "supply" and (
            not isinstance(self.supply_delta, int)
            or isinstance(self.supply_delta, bool)
            or self.supply_delta == 0
        ):
            raise ValueError("perturbation supply delta must be a non-zero integer")
        if self.kind == "dependency_failure" and not self.failure_mode.strip():
            raise ValueError("dependency failure mode must not be blank")
        expected_scope = {
            "traffic": {"global", "zone", "edge"},
            "supply": {"courier_pool"},
            "merchant_delay": {"merchant"},
            "dependency_failure": {"dependency"},
        }[self.kind]
        if self.scope not in expected_scope:
            raise ValueError(f"{self.kind} perturbation scope is invalid")

    @property
    def active_event(self) -> dict[str, object]:
        return {
            "perturbation_id": self.perturbation_id,
            "kind": self.kind,
            "effective_from_seconds": self.effective_from_seconds,
            "end_at_seconds": self.end_at_seconds,
            "target": self.target,
            "scope": self.scope,
            "traffic_multiplier": self.traffic_multiplier,
            "delay_seconds": self.delay_seconds,
            "supply_delta": self.supply_delta,
            "failure_mode": self.failure_mode,
            "source": self.source,
        }


@dataclass(frozen=True, slots=True)
class PerturbationMetrics:
    active_event_count: int
    traffic_multiplier: float
    incident_delay_seconds: float
    courier_supply: int
    supply_delta: int
    merchant_delay_seconds: float
    merchant_delay_by_target: tuple[tuple[str, float], ...]
    failed_dependencies: tuple[str, ...]
    simulated_failure_count: int
    live_failure_count: int


@dataclass(frozen=True, slots=True)
class PerturbationSnapshot:
    scenario_id: str
    observed_at_seconds: float
    active_events: tuple[ScenarioPerturbation, ...]
    metrics: PerturbationMetrics
    travel_context: DynamicTravelContext


@dataclass(frozen=True, slots=True)
class PerturbationRun:
    scenario_id: str
    seed: int
    base_courier_supply: int
    perturbations: tuple[ScenarioPerturbation, ...]
    replay_digest: str

    def state_at(self, simulated_time_seconds: float) -> PerturbationSnapshot:
        if not isfinite(simulated_time_seconds) or simulated_time_seconds < 0:
            raise ValueError("perturbation time must be finite and non-negative")
        active = tuple(
            perturbation
            for perturbation in self.perturbations
            if perturbation.effective_from_seconds <= simulated_time_seconds
            and (
                perturbation.end_at_seconds is None
                or simulated_time_seconds < perturbation.end_at_seconds
            )
        )
        traffic_multiplier = 1.0
        incident_delay_seconds = 0.0
        supply_delta = 0
        merchant_delay: dict[str, float] = {}
        failed_dependencies: set[str] = set()
        simulated_failure_count = 0
        live_failure_count = 0
        traffic_updates: list[TravelUpdate] = []
        for revision, event in enumerate(active):
            if event.kind == "traffic":
                traffic_multiplier *= event.traffic_multiplier
                if event.scope == "global":
                    update_multiplier = event.traffic_multiplier
                    zone_multipliers: tuple[tuple[str, float], ...] = ()
                    edge_delays: tuple[tuple[str, float], ...] = ()
                elif event.scope == "zone":
                    update_multiplier = 1.0
                    zone_multipliers = ((event.target, event.traffic_multiplier),)
                    edge_delays = ()
                else:
                    update_multiplier = 1.0
                    zone_multipliers = ()
                    edge_delays = ((event.target, event.delay_seconds),)
                incident_delay_seconds += (
                    event.delay_seconds if event.scope in {"global", "zone"} else 0.0
                )
                traffic_updates.append(
                    TravelUpdate(
                        f"perturbation:{event.perturbation_id}",
                        revision,
                        event.effective_from_seconds,
                        traffic_multiplier=update_multiplier,
                        zone_multipliers=zone_multipliers,
                        edge_delays_seconds=edge_delays,
                        incident_delay_seconds=(
                            event.delay_seconds if event.scope in {"global", "zone"} else 0.0
                        ),
                        source=event.source,
                    )
                )
            elif event.kind == "supply":
                supply_delta += event.supply_delta
            elif event.kind == "merchant_delay":
                merchant_delay[event.target] = (
                    merchant_delay.get(event.target, 0.0) + event.delay_seconds
                )
            else:
                failed_dependencies.add(event.target)
                if event.source == "simulated":
                    simulated_failure_count += 1
                else:
                    live_failure_count += 1
        metrics = PerturbationMetrics(
            len(active),
            traffic_multiplier,
            incident_delay_seconds,
            max(0, self.base_courier_supply + supply_delta),
            supply_delta,
            sum(merchant_delay.values()),
            tuple(sorted(merchant_delay.items())),
            tuple(sorted(failed_dependencies)),
            simulated_failure_count,
            live_failure_count,
        )
        travel_context = DynamicTravelContext(
            simulated_time_seconds=simulated_time_seconds,
            traffic_context="scenario-perturbation" if traffic_updates else "baseline",
            incident_ids=tuple(event.target for event in active if event.kind == "traffic"),
            updates=tuple(traffic_updates),
        )
        return PerturbationSnapshot(
            self.scenario_id,
            simulated_time_seconds,
            active,
            metrics,
            travel_context,
        )


@dataclass(frozen=True, slots=True)
class PerturbationScenario:
    scenario_id: str
    base_courier_supply: int
    perturbations: tuple[ScenarioPerturbation, ...] = ()
    seed: int = 0

    def __post_init__(self) -> None:
        if not self.scenario_id.strip():
            raise ValueError("perturbation scenario id must not be blank")
        if (
            not isinstance(self.base_courier_supply, int)
            or isinstance(self.base_courier_supply, bool)
            or self.base_courier_supply < 0
        ):
            raise ValueError("base courier supply must be a non-negative integer")
        ids = [perturbation.perturbation_id for perturbation in self.perturbations]
        if len(ids) != len(set(ids)):
            raise ValueError("perturbation identifiers must be unique")
        object.__setattr__(
            self,
            "perturbations",
            tuple(
                sorted(
                    self.perturbations,
                    key=lambda event: (event.effective_from_seconds, event.perturbation_id),
                )
            ),
        )

    def run(self) -> PerturbationRun:
        payload = {
            "scenario_id": self.scenario_id,
            "base_courier_supply": self.base_courier_supply,
            "seed": self.seed,
            "perturbations": [event.active_event for event in self.perturbations],
        }
        digest = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        return PerturbationRun(
            self.scenario_id,
            self.seed,
            self.base_courier_supply,
            self.perturbations,
            digest,
        )
