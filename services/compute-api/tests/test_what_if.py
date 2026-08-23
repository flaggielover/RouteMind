from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from routemind_compute.api.app import app
from routemind_compute.application.nearest import NearestStrategy
from routemind_compute.application.registry import StrategyRegistry
from routemind_compute.application.simulation import CourierState, DemandEvent, ScenarioManifest
from routemind_compute.application.travel import DeterministicLocalTravelProvider
from routemind_compute.application.what_if import WhatIfRunner, WhatIfVariant
from routemind_compute.domain.dispatch import GeoPoint

client = TestClient(app)


def manifest() -> ScenarioManifest:
    return ScenarioManifest(
        "what-if-fixture",
        7,
        (
            DemandEvent("request-1", GeoPoint(31.2304, 121.4737), 0),
            DemandEvent("request-2", GeoPoint(31.2305, 121.4738), 1),
        ),
        (
            CourierState("courier-1", GeoPoint(31.22, 121.48)),
            CourierState("courier-2", GeoPoint(31.24, 121.46)),
        ),
        delay_ticks=(0, 1),
    )


def runner() -> WhatIfRunner:
    return WhatIfRunner(
        StrategyRegistry((NearestStrategy(),)),
        DeterministicLocalTravelProvider(),
    )


def test_variants_are_deterministic_and_record_all_dimensions() -> None:
    variants = (
        WhatIfVariant(
            "busy",
            "Traffic and preparation stress",
            demand_multiplier=2.0,
            supply_delta=-1,
            preparation_delay_ticks=2,
            traffic_multiplier=1.5,
            risk_multiplier=2.0,
        ),
        WhatIfVariant(
            "light",
            "Lower demand and faster traffic",
            demand_multiplier=0.5,
            supply_delta=1,
            traffic_multiplier=0.8,
            risk_multiplier=0.5,
        ),
    )
    first = runner().run("recorded-v1", "nearest", manifest(), variants)
    second = runner().run("recorded-v1", "nearest", manifest(), variants)

    assert first.comparison_digest == second.comparison_digest
    assert [item.variant_id for item in first.results] == ["baseline", "busy", "light"]
    assert first.results[0].request_count == 2
    assert first.results[1].request_count == 4
    assert first.results[2].request_count == 1
    assert first.results[1].risk_index > first.results[0].risk_index
    assert first.results[1].manifest_digest != first.results[0].manifest_digest
    assert all(len(item.replay_digest) == 64 for item in first.results)
    assert all(item.observed_runtime_millis >= 0 for item in first.results)


def test_variant_and_runner_bounds_are_explicit() -> None:
    with pytest.raises(ValueError, match="identity"):
        WhatIfVariant(" ", "label")
    with pytest.raises(ValueError, match="demand_multiplier"):
        WhatIfVariant("bad", "label", demand_multiplier=3)
    with pytest.raises(ValueError, match="supply_delta"):
        WhatIfVariant("bad", "label", supply_delta=33)
    with pytest.raises(ValueError, match="preparation"):
        WhatIfVariant("bad", "label", preparation_delay_ticks=61)
    with pytest.raises(ValueError, match="traffic_multiplier"):
        WhatIfVariant("bad", "label", traffic_multiplier=4)
    with pytest.raises(ValueError, match="strategy"):
        WhatIfVariant("bad", "label", strategy=" ")
    with pytest.raises(ValueError, match="risk_multiplier"):
        WhatIfVariant("bad", "label", risk_multiplier=0)

    value = WhatIfVariant("variant", "Variant")
    for recorded_id, variants, message in (
        (" ", (value,), "recorded_run_id"),
        ("recorded", (), "1 to 4"),
        ("recorded", (value, value), "unique"),
        ("recorded", tuple(WhatIfVariant(str(i), "v") for i in range(5)), "1 to 4"),
        ("recorded", (WhatIfVariant("baseline", "reserved"),), "reserved"),
    ):
        with pytest.raises(ValueError, match=message):
            runner().run(recorded_id, "nearest", manifest(), variants)

    with pytest.raises(KeyError, match="unknown"):
        runner().run("recorded", "missing", manifest(), (value,))
    with pytest.raises(KeyError, match="unknown"):
        runner().run(
            "recorded",
            "nearest",
            manifest(),
            (WhatIfVariant("v", "v", strategy="missing"),),
        )
    with pytest.raises(ValueError, match="at least one courier"):
        runner().run("recorded", "nearest", manifest(), (WhatIfVariant("v", "v", supply_delta=-2),))


def api_payload() -> dict[str, object]:
    return {
        "recorded_run_id": "recorded-v1",
        "baseline_strategy": "nearest",
        "manifest_id": "what-if-manifest",
        "code_version": "git:test",
        "scenario_id": "what-if-fixture",
        "seed": 7,
        "load_profile": "reduced",
        "city_state": "shanghai-local",
        "dataset_provenance": "fixture:what-if-v1",
        "strategies": ["nearest"],
        "demands": [
            {
                "request_id": "request-1",
                "pickup": {"latitude": 31.2304, "longitude": 121.4737},
                "tick": 0,
            },
            {
                "request_id": "request-2",
                "pickup": {"latitude": 31.2305, "longitude": 121.4738},
                "tick": 1,
            },
        ],
        "couriers": [
            {
                "courier_id": "courier-1",
                "location": {"latitude": 31.22, "longitude": 121.48},
            },
            {
                "courier_id": "courier-2",
                "location": {"latitude": 31.24, "longitude": 121.46},
            },
        ],
        "variants": [
            {
                "variant_id": "stress",
                "label": "Stress test",
                "demand_multiplier": 1.5,
                "supply_delta": -1,
                "preparation_delay_ticks": 2,
                "traffic_multiplier": 1.4,
                "strategy": "nearest",
                "risk_multiplier": 1.5,
            }
        ],
    }


def test_what_if_http_returns_metrics_and_rejects_unknown_strategy() -> None:
    response = client.post("/api/v1/experiments/what-if", json=api_payload())

    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "what-if"
    assert body["claim_label"] == "scenario comparison; not a causal production claim"
    assert body["recorded_run_id"] == "recorded-v1"
    assert len(body["comparison_digest"]) == 64
    assert [item["variant_id"] for item in body["results"]] == ["baseline", "stress"]
    assert body["results"][1]["manifest_digest"] != body["results"][0]["manifest_digest"]

    invalid = api_payload()
    invalid["baseline_strategy"] = "missing"
    rejected = client.post("/api/v1/experiments/what-if", json=invalid)
    assert rejected.status_code == 400
