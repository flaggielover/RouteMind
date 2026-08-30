from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

SERVICE_ROOT = Path(__file__).resolve().parents[1] / "services" / "compute-api"
sys.path.insert(0, str(SERVICE_ROOT / "src"))

CATALOG_PATH = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "product"
    / "scenarios"
    / "product-readiness-scenarios-v1.json"
)
EXPECTED_IDS = (
    "NORMAL_BASELINE",
    "DINNER_RUSH",
    "COURIER_SHORTAGE",
    "MERCHANT_DELAY",
    "TRAFFIC_DEGRADATION",
    "ROUTING_PROVIDER_FAILURE",
    "DISPATCH_PRESSURE",
    "RECOVERY",
)


class _FailingTravelProvider:
    name = "injected-routing-failure"

    def estimate(self, origin: Any, destination: Any, **_: object) -> Any:
        raise RuntimeError("injected routing provider failure")

    def matrix(self, origins: object, destinations: object, **_: object) -> Any:
        raise RuntimeError("injected routing provider failure")


def load_catalog(path: Path = CATALOG_PATH) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise ValueError("scenario catalog schema_version must be 1")
    if payload.get("catalog_id") != "product-readiness-scenarios-v1":
        raise ValueError("scenario catalog identity is not recognized")
    records = payload.get("scenarios")
    if not isinstance(records, list) or tuple(item.get("id") for item in records) != EXPECTED_IDS:
        raise ValueError("scenario catalog must contain the frozen scenario IDs in order")
    for record in records:
        if not isinstance(record, dict):
            raise TypeError("scenario catalog entries must be objects")
        if record.get("provider_mode") not in {"local", "fallback"}:
            raise ValueError(f"unsupported provider mode for {record.get('id')}")
        if not isinstance(record.get("demand_count"), int) or record["demand_count"] < 1:
            raise ValueError(f"invalid demand_count for {record.get('id')}")
        if len(record.get("demand_ticks", ())) != record["demand_count"]:
            raise ValueError(f"demand_ticks does not match demand_count for {record.get('id')}")
        if not isinstance(record.get("courier_count"), int) or record["courier_count"] < 1:
            raise ValueError(f"invalid courier_count for {record.get('id')}")
    return payload


def _coordinate(scenario_id: str, seed: int, index: int) -> Any:
    from routemind_compute.domain.dispatch import GeoPoint

    digest = hashlib.sha256(f"{scenario_id}:{seed}:{index}".encode()).digest()
    return GeoPoint(31.20 + digest[0] / 2550, 121.40 + digest[1] / 2550)


def build_manifest(record: dict[str, Any], seed: int) -> Any:
    from routemind_compute.application.simulation import (
        CourierState,
        DemandEvent,
        ScenarioManifest,
    )
    from routemind_compute.domain.dispatch import GeoPoint

    scenario_id = str(record["id"])
    center = _coordinate(scenario_id, seed, 0)
    demands = tuple(
        DemandEvent(
            f"scenario:{scenario_id}:request-{index + 1}",
            _coordinate(scenario_id, seed, index + 1),
            int(tick),
            zone="product-readiness",
            merchant_id=f"merchant:{scenario_id}",
            order_profile="delayed-preparation" if scenario_id == "MERCHANT_DELAY" else "standard",
        )
        for index, tick in enumerate(record["demand_ticks"])
    )
    couriers = tuple(
        CourierState(
            f"scenario:{scenario_id}:courier-{index + 1}",
            GeoPoint(center.latitude + index * 0.002, center.longitude + index * 0.002),
        )
        for index in range(record["courier_count"])
    )
    return ScenarioManifest(
        scenario_id,
        seed,
        demands,
        couriers,
        delay_ticks=tuple(record["delay_ticks"]),
        traffic_multiplier=float(record["traffic_multiplier"]),
        reference_data_id="product-readiness:deterministic-local:v1",
    )


def _provider(record: dict[str, Any]) -> Any:
    from routemind_compute.application.travel import DeterministicLocalTravelProvider

    local = DeterministicLocalTravelProvider()
    if record["provider_mode"] == "fallback":
        from routemind_compute.application.travel import FallbackTravelTimeProvider

        return FallbackTravelTimeProvider(_FailingTravelProvider(), local, timeout_seconds=0.1)
    return local


def run_scenario(record: dict[str, Any], seed: int, strategy: str = "nearest") -> dict[str, Any]:
    from routemind_compute.application.registry import default_registry
    from routemind_compute.application.simulation import ScenarioKernel

    manifest = build_manifest(record, seed)
    kernel = ScenarioKernel(default_registry(), _provider(record), strategy=strategy)
    first = kernel.run(manifest)
    second = kernel.run(manifest)
    if first.replay_digest != second.replay_digest:
        raise AssertionError(f"non-deterministic replay digest for {manifest.scenario_id}")
    result = {
        "catalog_id": "product-readiness-scenarios-v1",
        "scenario_id": manifest.scenario_id,
        "seed": manifest.seed,
        "configuration": {
            "demand_count": len(manifest.demands),
            "courier_count": len(manifest.couriers),
            "delay_ticks": manifest.delay_ticks,
            "traffic_multiplier": manifest.traffic_multiplier,
            "provider_mode": record["provider_mode"],
        },
        "source": "SIMULATION",
        "claim_label": "deterministic scenario observation; not a causal production claim",
        "replay_digest": first.replay_digest,
        "replay_verified": True,
        "decision_count": len(first.decisions),
        "assigned_count": sum(decision.courier_id is not None for decision in first.decisions),
        "unassigned_count": sum(decision.courier_id is None for decision in first.decisions),
        "simulated_end_tick": first.simulated_end_tick,
        "strategy": strategy,
        "strategy_version": first.decisions[0].strategy_version if first.decisions else "1.0.0",
        "fallback_states": dict(
            sorted(
                (state, sum(item.fallback_state == state for item in first.observations))
                for state in {item.fallback_state for item in first.observations}
            )
        ),
        "observation_metrics": {},
    }
    from routemind_compute.application.research_observability import PolicyTrace

    trace = PolicyTrace()
    trace.extend(first.observations)
    result["observation_metrics"] = trace.metrics().as_dict()
    if record.get("recovery_replay"):
        result["recovery_replay_verified"] = result["replay_verified"]
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run RouteMind's finite deterministic product scenarios"
    )
    parser.add_argument("--list", action="store_true", help="list the frozen scenario catalog")
    parser.add_argument("--scenario", choices=EXPECTED_IDS, help="run one scenario")
    parser.add_argument("--seed", type=int, default=20260830)
    parser.add_argument("--strategy", default="nearest", help="explicit strategy name")
    parser.add_argument(
        "--compare",
        help="comma-separated strategy names for an independent fixed-strategy comparison",
    )
    args = parser.parse_args(argv)
    catalog = load_catalog()
    if args.list:
        print(json.dumps(catalog, sort_keys=True, separators=(",", ":")))
        return 0
    records = [
        record
        for record in catalog["scenarios"]
        if args.scenario is None or record["id"] == args.scenario
    ]
    if args.compare:
        from routemind_compute.application.registry import default_registry
        from routemind_compute.application.simulation import compare_strategies

        output = []
        for record in records:
            manifest = build_manifest(record, args.seed)
            comparison = compare_strategies(
                default_registry(),
                _provider(record),
                manifest,
                tuple(item.strip() for item in args.compare.split(",")),
            )
            output.append(
                {
                    "scenario_id": comparison.scenario_id,
                    "seed": comparison.seed,
                    "source": "SIMULATION",
                    "claim_label": "fixed-strategy comparison; not a causal production claim",
                    "strategies": [
                        {
                            "strategy": run.decisions[0].strategy
                            if run.decisions
                            else args.strategy,
                            "strategy_version": run.decisions[0].strategy_version
                            if run.decisions
                            else "1.0.0",
                            "assigned_count": sum(
                                item.courier_id is not None for item in run.decisions
                            ),
                            "decision_count": len(run.decisions),
                            "replay_digest": run.replay_digest,
                            "latency_millis": run.wall_clock_elapsed_seconds * 1000,
                            "feasible": all(item.courier_id is not None for item in run.decisions),
                            "fallback_states": sorted(
                                {item.fallback_state for item in run.observations}
                            ),
                            "selection_mode": sorted(
                                {item.selection_mode for item in run.observations}
                            ),
                            "provenance": sorted(
                                {key for item in run.observations for key, _ in item.provenance}
                            ),
                        }
                        for run in comparison.results
                    ],
                    "incompatible": [
                        {"strategy": name, "reason": reason}
                        for name, reason in comparison.incompatible
                    ],
                }
            )
        print(
            json.dumps(
                output[0] if args.scenario else output, sort_keys=True, separators=(",", ":")
            )
        )
        return 0
    results = [run_scenario(record, args.seed, args.strategy) for record in records]
    print(
        json.dumps(
            results[0] if args.scenario else results,
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
