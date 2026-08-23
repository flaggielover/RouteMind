from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from math import isfinite
from time import perf_counter

from routemind_compute.application.registry import StrategyRegistry
from routemind_compute.application.simulation import (
    CourierState,
    DemandEvent,
    ScenarioKernel,
    ScenarioManifest,
)
from routemind_compute.application.travel import TravelTimeProvider


def _canonical_json(payload: object) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _digest(payload: object) -> str:
    return sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class WhatIfVariant:
    variant_id: str
    label: str
    demand_multiplier: float = 1.0
    supply_delta: int = 0
    preparation_delay_ticks: int = 0
    traffic_multiplier: float = 1.0
    strategy: str = "nearest"
    risk_multiplier: float = 1.0

    def __post_init__(self) -> None:
        if not self.variant_id.strip() or not self.label.strip():
            raise ValueError("what-if variant identity must not be blank")
        if not isfinite(self.demand_multiplier) or not 0.5 <= self.demand_multiplier <= 2.0:
            raise ValueError("demand_multiplier must be between 0.5 and 2")
        if not -32 <= self.supply_delta <= 32:
            raise ValueError("supply_delta must be between -32 and 32")
        if not 0 <= self.preparation_delay_ticks <= 60:
            raise ValueError("preparation_delay_ticks must be between 0 and 60")
        if not isfinite(self.traffic_multiplier) or not 0.5 <= self.traffic_multiplier <= 3.0:
            raise ValueError("traffic_multiplier must be between 0.5 and 3")
        if not self.strategy.strip():
            raise ValueError("strategy must not be blank")
        if not isfinite(self.risk_multiplier) or not 0.1 <= self.risk_multiplier <= 5.0:
            raise ValueError("risk_multiplier must be between 0.1 and 5")

    def canonical_payload(self) -> dict[str, object]:
        return {
            "variant_id": self.variant_id,
            "label": self.label,
            "demand_multiplier": self.demand_multiplier,
            "supply_delta": self.supply_delta,
            "preparation_delay_ticks": self.preparation_delay_ticks,
            "traffic_multiplier": self.traffic_multiplier,
            "strategy": self.strategy,
            "risk_multiplier": self.risk_multiplier,
        }


@dataclass(frozen=True, slots=True)
class WhatIfMetric:
    variant_id: str
    label: str
    strategy: str
    strategy_version: str
    request_count: int
    assigned_count: int
    assignment_rate: float
    simulated_end_tick: int
    simulated_duration_seconds: float
    risk_index: float
    replay_digest: str
    manifest_digest: str
    output_digest: str
    observed_runtime_millis: float

    def canonical_payload(self) -> dict[str, object]:
        return {
            "variant_id": self.variant_id,
            "label": self.label,
            "strategy": self.strategy,
            "strategy_version": self.strategy_version,
            "request_count": self.request_count,
            "assigned_count": self.assigned_count,
            "assignment_rate": self.assignment_rate,
            "simulated_end_tick": self.simulated_end_tick,
            "simulated_duration_seconds": self.simulated_duration_seconds,
            "risk_index": self.risk_index,
            "replay_digest": self.replay_digest,
            "manifest_digest": self.manifest_digest,
            "output_digest": self.output_digest,
        }


@dataclass(frozen=True, slots=True)
class WhatIfComparison:
    recorded_run_id: str
    scenario_id: str
    seed: int
    comparison_digest: str
    results: tuple[WhatIfMetric, ...]

    def canonical_payload(self) -> dict[str, object]:
        return {
            "recorded_run_id": self.recorded_run_id,
            "scenario_id": self.scenario_id,
            "seed": self.seed,
            "results": [result.canonical_payload() for result in self.results],
        }


class WhatIfRunner:
    """Run bounded scenario variants through the existing compute-owned kernel."""

    max_variants = 4
    max_demands = 64
    max_couriers = 64

    def __init__(self, registry: StrategyRegistry, travel_provider: TravelTimeProvider) -> None:
        self.registry = registry
        self.travel_provider = travel_provider

    def run(
        self,
        recorded_run_id: str,
        baseline_strategy: str,
        manifest: ScenarioManifest,
        variants: tuple[WhatIfVariant, ...],
    ) -> WhatIfComparison:
        if not recorded_run_id.strip():
            raise ValueError("recorded_run_id must not be blank")
        if not variants or len(variants) > self.max_variants:
            raise ValueError(f"what-if variants must contain 1 to {self.max_variants} items")
        if len({variant.variant_id for variant in variants}) != len(variants):
            raise ValueError("what-if variant ids must be unique")
        if any(variant.variant_id == "baseline" for variant in variants):
            raise ValueError("variant id baseline is reserved")
        self._ensure_strategy(baseline_strategy)
        for variant in variants:
            self._ensure_strategy(variant.strategy)

        baseline = WhatIfVariant("baseline", "Recorded baseline", strategy=baseline_strategy)
        all_variants = (baseline, *variants)
        results = tuple(self._run_variant(manifest, variant) for variant in all_variants)
        comparison = WhatIfComparison(
            recorded_run_id,
            manifest.scenario_id,
            manifest.seed,
            "",
            results,
        )
        return WhatIfComparison(
            comparison.recorded_run_id,
            comparison.scenario_id,
            comparison.seed,
            _digest(comparison.canonical_payload()),
            comparison.results,
        )

    def _run_variant(self, base: ScenarioManifest, variant: WhatIfVariant) -> WhatIfMetric:
        started = perf_counter()
        derived = self._derive_manifest(base, variant)
        run = ScenarioKernel(
            self.registry,
            self.travel_provider,
            strategy=variant.strategy,
        ).run(derived)
        request_count = len(run.decisions)
        assigned_count = sum(item.courier_id is not None for item in run.decisions)
        assignment_rate = assigned_count / request_count if request_count else 0.0
        risk_index = self._risk_index(derived, variant, assignment_rate)
        metric_payload = {
            "variant": variant.canonical_payload(),
            "manifest": self._manifest_payload(derived),
            "run": {
                "replay_digest": run.replay_digest,
                "decisions": [
                    {
                        "request_id": item.request_id,
                        "tick": item.tick,
                        "courier_id": item.courier_id,
                    }
                    for item in run.decisions
                ],
                "transitions": [
                    {
                        "request_id": item.request_id,
                        "tick": item.tick,
                        "to_state": item.to_state,
                        "courier_id": item.courier_id,
                    }
                    for item in run.transitions
                ],
            },
        }
        return WhatIfMetric(
            variant.variant_id,
            variant.label,
            variant.strategy,
            str(getattr(self.registry.get(variant.strategy), "version", "1.0.0")),
            request_count,
            assigned_count,
            assignment_rate,
            run.simulated_end_tick,
            run.simulated_end_tick * 60.0,
            risk_index,
            run.replay_digest,
            _digest(self._manifest_payload(derived)),
            _digest(metric_payload),
            (perf_counter() - started) * 1000,
        )

    def _derive_manifest(self, base: ScenarioManifest, variant: WhatIfVariant) -> ScenarioManifest:
        demands = tuple(sorted(base.demands, key=lambda item: (item.tick, item.request_id)))
        target_count = max(
            1, min(self.max_demands, round(len(demands) * variant.demand_multiplier))
        )
        derived_demands: list[DemandEvent] = []
        for index in range(target_count):
            source = demands[index % len(demands)]
            cycle = index // len(demands)
            request_id = source.request_id if cycle == 0 else f"{source.request_id}:what-if-{cycle}"
            derived_demands.append(
                DemandEvent(
                    request_id,
                    source.pickup,
                    source.tick + cycle,
                    source.zone,
                    source.merchant_id,
                    source.order_profile,
                )
            )

        couriers = list(sorted(base.couriers, key=lambda item: item.courier_id))
        if variant.supply_delta < 0:
            if len(couriers) + variant.supply_delta < 1:
                raise ValueError("supply variant must leave at least one courier")
            del couriers[len(couriers) + variant.supply_delta :]
        elif variant.supply_delta > 0:
            template = couriers[-1]
            for index in range(variant.supply_delta):
                couriers.append(
                    CourierState(
                        f"{template.courier_id}:what-if-{index + 1}",
                        template.location,
                        template.available_tick,
                    )
                )

        delay_ticks = tuple(
            sorted({delay + variant.preparation_delay_ticks for delay in base.delay_ticks})
        )
        return ScenarioManifest(
            f"{base.scenario_id}:what-if:{variant.variant_id}",
            base.seed,
            tuple(derived_demands),
            tuple(couriers),
            delay_ticks,
            variant.traffic_multiplier,
        )

    @staticmethod
    def _risk_index(
        manifest: ScenarioManifest, variant: WhatIfVariant, assignment_rate: float
    ) -> float:
        supply = max(1, len(manifest.couriers))
        demand_pressure = max(0.0, len(manifest.demands) / supply - 1.0)
        risk = (
            max(0.0, 1.0 - assignment_rate) * 100.0
            + demand_pressure * 20.0
            + max(0.0, manifest.traffic_multiplier - 1.0) * 15.0
            + variant.preparation_delay_ticks * 0.5
        ) * variant.risk_multiplier
        return round(risk, 4)

    def _ensure_strategy(self, strategy: str) -> None:
        if strategy not in self.registry.names():
            raise KeyError(f"unknown dispatch strategy: {strategy}")

    @staticmethod
    def _manifest_payload(manifest: ScenarioManifest) -> dict[str, object]:
        return {
            "scenario_id": manifest.scenario_id,
            "seed": manifest.seed,
            "traffic_multiplier": manifest.traffic_multiplier,
            "delay_ticks": manifest.delay_ticks,
            "demands": [
                {
                    "request_id": item.request_id,
                    "latitude": item.pickup.latitude,
                    "longitude": item.pickup.longitude,
                    "tick": item.tick,
                }
                for item in manifest.demands
            ],
            "couriers": [
                {
                    "courier_id": item.courier_id,
                    "latitude": item.location.latitude,
                    "longitude": item.location.longitude,
                    "available_tick": item.available_tick,
                }
                for item in manifest.couriers
            ],
        }
