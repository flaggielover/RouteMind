from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from hashlib import sha256
from pathlib import Path
from typing import cast

import pytest

from routemind_compute.application.execution import canonical_digest
from routemind_compute.application.rads_stability_map import (
    RadsStabilityMapError,
    audit_rads_stability_map_support,
    load_rads_stability_map_plan,
)

ROOT = Path(__file__).resolve().parents[3]
PLAN = ROOT / "docs/research/r3/manifests/rads/r3-343-stability-map-v1.json"
SUPPORT = (
    "tick_state_observations",
    "strategy_selections",
    "switch_events",
    "service_outcomes",
    "route_cost_outcomes",
    "instability_observations",
    "regime_identity",
    "pairing_unit",
)


def _payload() -> dict[str, object]:
    value: object = json.loads(PLAN.read_text(encoding="utf-8"))
    return dict(cast(Mapping[str, object], value))


def _mapping(value: object) -> dict[str, object]:
    return dict(cast(Mapping[str, object], value))


def _write(tmp_path: Path, payload: dict[str, object]) -> Path:
    value = dict(payload)
    value["plan_digest"] = canonical_digest({k: v for k, v in value.items() if k != "plan_digest"})
    path = tmp_path / "stability-map.json"
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    return path


def test_plan_freezes_empirical_axes_coverage_and_uncertainty() -> None:
    plan = load_rads_stability_map_plan(PLAN)
    assert plan.map_id == "r3-343-empirical-stability-map-v1"
    assert plan.manifest_sha256 == sha256(PLAN.read_bytes()).hexdigest()
    rows = cast(list[dict[str, object]], plan.payload["state_axes"])
    assert tuple(row["axis"] for row in rows) == (
        "relative_advantage",
        "dwell_ticks",
        "pressure_ticks",
        "regime_id",
        "strategy_pair",
    )


def test_audit_refuses_map_without_tick_trajectories() -> None:
    audit = audit_rads_stability_map_support(
        load_rads_stability_map_plan(PLAN), {field: False for field in SUPPORT}
    )
    assert audit.status == "INSUFFICIENT_DATA"
    assert audit.missing_fields == SUPPORT
    assert audit.coverage_status == "NO_ELIGIBLE_CELLS"
    assert audit.uncertainty_status == "NOT_ESTIMATED_NO_CELL_SUPPORT"
    assert all(status == "NOT_MAPPED_NO_TICK_LOGS" for _, status in audit.axis_status)
    assert audit.interpretation == "EMPIRICAL_ONLY_NOT_THEORETICAL"


def test_audit_is_ready_only_with_complete_support() -> None:
    audit = audit_rads_stability_map_support(
        load_rads_stability_map_plan(PLAN), {field: True for field in SUPPORT}
    )
    assert audit.status == "READY_FOR_MAPPING"
    assert audit.available_fields == SUPPORT
    assert audit.missing_fields == ()
    assert all(status == "READY_FOR_EMPIRICAL_MAPPING" for _, status in audit.metric_status)


def test_loader_rejects_invalid_json_digest_and_shape(tmp_path: Path) -> None:
    invalid = tmp_path / "invalid.json"
    invalid.write_bytes(b"bad")
    with pytest.raises(RadsStabilityMapError, match="UTF-8 JSON"):
        load_rads_stability_map_plan(invalid)
    scalar = tmp_path / "scalar.json"
    scalar.write_text("[]", encoding="utf-8")
    with pytest.raises(RadsStabilityMapError, match="JSON object"):
        load_rads_stability_map_plan(scalar)
    payload = _payload()
    payload["question"] = "tampered"
    forged = tmp_path / "forged.json"
    forged.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(RadsStabilityMapError, match="digest"):
        load_rads_stability_map_plan(forged)


def test_loader_rejects_axis_coverage_uncertainty_and_support_drift(tmp_path: Path) -> None:
    def reject(mutate: Callable[[dict[str, object]], None], match: str) -> None:
        payload = _payload()
        mutate(payload)
        with pytest.raises(RadsStabilityMapError, match=match):
            load_rads_stability_map_plan(_write(tmp_path, payload))

    reject(lambda p: p.update(task_id="R3-342"), "identity")
    reject(lambda p: p.update(state_axes=[]), "axes")
    reject(
        lambda p: p.update(
            coverage_policy={
                **_mapping(p["coverage_policy"]),
                "minimum_cell_observations": 1,
            }
        ),
        "coverage policy",
    )
    reject(
        lambda p: p.update(
            uncertainty_policy={
                **_mapping(p["uncertainty_policy"]),
                "bootstrap_resamples": 10,
            }
        ),
        "uncertainty policy",
    )
    reject(
        lambda p: p.update(
            support_requirements={
                **_mapping(p["support_requirements"]),
                "synthetic_substitution": True,
            }
        ),
        "fail-closed",
    )


def test_loader_rejects_lineage_theoretical_claim_and_support_shape(tmp_path: Path) -> None:
    payload = _payload()
    payload["source_lineage"] = {
        **_mapping(payload["source_lineage"]),
        "pilot_ledger": "0" * 64,
    }
    with pytest.raises(RadsStabilityMapError, match="lineage"):
        load_rads_stability_map_plan(_write(tmp_path, payload))
    payload = _payload()
    payload["execution_policy"] = {
        **_mapping(payload["execution_policy"]),
        "theoretical_stability_claim": True,
    }
    with pytest.raises(RadsStabilityMapError, match="empirical/read-only"):
        load_rads_stability_map_plan(_write(tmp_path, payload))
    with pytest.raises(RadsStabilityMapError, match="support fields"):
        audit_rads_stability_map_support(
            load_rads_stability_map_plan(PLAN), {"tick_state_observations": False}
        )
