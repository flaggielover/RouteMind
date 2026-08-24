from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from hashlib import sha256
from pathlib import Path
from typing import cast

import pytest

from routemind_compute.application.execution import canonical_digest
from routemind_compute.application.rads_robustness import (
    RadsRobustnessError,
    audit_rads_robustness_support,
    load_rads_robustness_plan,
)

ROOT = Path(__file__).resolve().parents[3]
PLAN = ROOT / "docs/research/r3/manifests/rads/r3-349-rads-robustness-v1.json"
AXES = (
    "seeds",
    "demand",
    "supply",
    "merchant_delay",
    "traffic",
    "location_noise",
    "location_staleness",
    "compute_constraints",
)
SUPPORT = (
    "seed_stream_identity",
    "demand_regime",
    "supply_regime",
    "merchant_delay_regime",
    "traffic_regime",
    "location_noise_regime",
    "location_staleness_regime",
    "compute_constraint_regime",
    "paired_stream_identity",
    "rads_strategy_identity",
    "rads_outcomes",
)


def _payload() -> dict[str, object]:
    value: object = json.loads(PLAN.read_text(encoding="utf-8"))
    return dict(cast(Mapping[str, object], value))


def _mapping(value: object) -> dict[str, object]:
    return dict(cast(Mapping[str, object], value))


def _write(tmp_path: Path, payload: dict[str, object]) -> Path:
    value = dict(payload)
    value["plan_digest"] = canonical_digest({k: v for k, v in value.items() if k != "plan_digest"})
    path = tmp_path / "rads-robustness.json"
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    return path


def test_plan_freezes_all_axes_cross_regime_rule_and_lineage() -> None:
    plan = load_rads_robustness_plan(PLAN)
    assert plan.study_id == "r3-349-rads-robustness-v1"
    assert plan.manifest_sha256 == sha256(PLAN.read_bytes()).hexdigest()
    rows = cast(list[dict[str, object]], plan.payload["robustness_axes"])
    assert tuple(row["axis"] for row in rows) == AXES
    assert cast(dict[str, object], plan.payload["analysis_plan"])["single_scenario_rule"] == (
        "NEVER_SUFFICIENT_FOR_BROAD_CLAIM"
    )


def test_current_source_audit_preserves_regimes_but_refuses_rads_claim() -> None:
    support = {field: True for field in SUPPORT}
    support["location_noise_regime"] = False
    support["rads_strategy_identity"] = False
    support["rads_outcomes"] = False
    audit = audit_rads_robustness_support(
        load_rads_robustness_plan(PLAN),
        support,
        {axis: 0 if axis == "location_noise" else 8 for axis in AXES},
    )
    assert audit.status == "INSUFFICIENT_DATA"
    assert dict(audit.axis_status)["demand"] == "SOURCE_REGIME_PRESENT_NO_RADS_OUTCOME"
    assert dict(audit.axis_status)["location_noise"] == "UNSUPPORTED_REGIME_NOT_PRESENT"
    assert audit.broad_claim_status == "PROHIBITED_NO_CROSS_REGIME_EVIDENCE"
    assert all(
        status == "NOT_REPORTED_NO_CROSS_REGIME_RADS_OUTCOMES" for _, status in audit.metric_status
    )


def test_complete_support_still_requires_minimum_pairs() -> None:
    support = {field: True for field in SUPPORT}
    plan = load_rads_robustness_plan(PLAN)
    underpowered = audit_rads_robustness_support(plan, support, {axis: 29 for axis in AXES})
    assert underpowered.status == "INSUFFICIENT_DATA"
    assert set(status for _, status in underpowered.axis_status) == {"INSUFFICIENT_PAIRS_FOR_AXIS"}
    ready = audit_rads_robustness_support(plan, support, {axis: 30 for axis in AXES})
    assert ready.status == "READY_FOR_CROSS_REGIME_ANALYSIS"
    assert ready.missing_fields == ()
    assert ready.broad_claim_status.startswith("ELIGIBLE_ONLY_AFTER")


def test_audit_rejects_support_pair_axes_and_count_shape() -> None:
    plan = load_rads_robustness_plan(PLAN)
    with pytest.raises(RadsRobustnessError, match="support fields"):
        audit_rads_robustness_support(plan, {"rads_outcomes": False}, {axis: 0 for axis in AXES})
    with pytest.raises(RadsRobustnessError, match="pair-count axes"):
        audit_rads_robustness_support(plan, {field: False for field in SUPPORT}, {"seeds": 0})
    with pytest.raises(RadsRobustnessError, match="non-negative integers"):
        audit_rads_robustness_support(
            plan, {field: False for field in SUPPORT}, {axis: -1 for axis in AXES}
        )


def test_loader_rejects_invalid_json_digest_and_shape(tmp_path: Path) -> None:
    invalid = tmp_path / "invalid.json"
    invalid.write_bytes(b"bad")
    with pytest.raises(RadsRobustnessError, match="UTF-8 JSON"):
        load_rads_robustness_plan(invalid)
    scalar = tmp_path / "scalar.json"
    scalar.write_text("[]", encoding="utf-8")
    with pytest.raises(RadsRobustnessError, match="JSON object"):
        load_rads_robustness_plan(scalar)
    payload = _payload()
    payload["question"] = "tampered"
    forged = tmp_path / "forged.json"
    forged.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(RadsRobustnessError, match="digest"):
        load_rads_robustness_plan(forged)


def test_loader_rejects_axis_analysis_support_lineage_and_execution_drift(tmp_path: Path) -> None:
    def reject(mutate: Callable[[dict[str, object]], None], match: str) -> None:
        payload = _payload()
        mutate(payload)
        with pytest.raises(RadsRobustnessError, match=match):
            load_rads_robustness_plan(_write(tmp_path, payload))

    reject(lambda p: p.update(robustness_axes=[]), "axes")
    reject(
        lambda p: p.update(
            analysis_plan={**_mapping(p["analysis_plan"]), "minimum_pairs_per_axis_level": 1}
        ),
        "analysis plan",
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
    reject(
        lambda p: p.update(
            source_lineage={**_mapping(p["source_lineage"]), "pilot_ledger": "0" * 64}
        ),
        "lineage",
    )
    reject(
        lambda p: p.update(
            execution_policy={**_mapping(p["execution_policy"]), "select_favorable_scenario": True}
        ),
        "read-only and complete",
    )
