from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from hashlib import sha256
from pathlib import Path
from typing import cast

import pytest

from routemind_compute.application.execution import canonical_digest
from routemind_compute.application.switchback_design import (
    SwitchbackDesignError,
    load_switchback_design,
)

ROOT = Path(__file__).resolve().parents[3]
DESIGN = (
    ROOT / "docs" / "research" / "r3" / "manifests" / "switchback" / "r3-352-switchback-v1.json"
)


def _payload() -> dict[str, object]:
    parsed: object = json.loads(DESIGN.read_text(encoding="utf-8"))
    if not isinstance(parsed, Mapping):
        raise AssertionError("fixture must be an object")
    return cast(dict[str, object], parsed)


def _write(tmp_path: Path, payload: dict[str, object]) -> Path:
    unsigned = dict(payload)
    unsigned["design_digest"] = canonical_digest(
        {key: value for key, value in unsigned.items() if key != "design_digest"}
    )
    path = tmp_path / "design.json"
    path.write_text(json.dumps(unsigned, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _mapping(value: object) -> dict[str, object]:
    return dict(cast(Mapping[str, object], value))


def _mappings(value: object) -> list[dict[str, object]]:
    selected = cast(Sequence[object], value)
    return [_mapping(item) for item in selected]


def test_switchback_manifest_validates_preregistered_simulation_design() -> None:
    design = load_switchback_design(DESIGN)
    assert design.design_id == "r3-352-simulation-switchback-v1"
    assert design.period_count == 6
    assert design.zone_count == 3
    assert len(design.design_digest) == 64
    assert len(design.manifest_sha256) == 64


def test_switchback_manifest_rejects_forged_digest(tmp_path: Path) -> None:
    payload = _payload()
    payload["scope"] = "changed"
    path = tmp_path / "forged.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(SwitchbackDesignError, match="digest"):
        load_switchback_design(path)


def test_switchback_manifest_rejects_naive_per_order_assignment(tmp_path: Path) -> None:
    payload = _payload()
    assignment = _mapping(payload["assignment"])
    assignment["per_order_randomization_allowed"] = True
    payload["assignment"] = assignment
    with pytest.raises(SwitchbackDesignError, match="per-order"):
        load_switchback_design(_write(tmp_path, payload))


def test_switchback_manifest_rejects_non_alternating_or_short_periods(tmp_path: Path) -> None:
    payload = _payload()
    periods = _mappings(payload["periods"])
    periods[1]["arm"] = "candidate"
    payload["periods"] = periods
    with pytest.raises(SwitchbackDesignError, match="alternate"):
        load_switchback_design(_write(tmp_path, payload))

    payload = _payload()
    payload["periods"] = _mappings(payload["periods"])[:3]
    with pytest.raises(SwitchbackDesignError, match="four periods"):
        load_switchback_design(_write(tmp_path, payload))


def test_switchback_manifest_rejects_missing_interference_and_causal_metrics(
    tmp_path: Path,
) -> None:
    payload = _payload()
    payload["interference_risks"] = _mappings(payload["interference_risks"])[:1]
    with pytest.raises(SwitchbackDesignError, match="interference"):
        load_switchback_design(_write(tmp_path, payload))

    payload = _payload()
    metrics = _mapping(payload["metrics"])
    metrics["primary"] = ["causal_effect"]
    payload["metrics"] = metrics
    with pytest.raises(SwitchbackDesignError, match="metrics"):
        load_switchback_design(_write(tmp_path, payload))


def test_switchback_manifest_rejects_real_world_phase_and_invalid_json(tmp_path: Path) -> None:
    payload = _payload()
    payload["phase"] = "live"
    with pytest.raises(SwitchbackDesignError, match="simulation-only"):
        load_switchback_design(_write(tmp_path, payload))
    invalid = tmp_path / "invalid.json"
    invalid.write_bytes(b"not-json")
    with pytest.raises(SwitchbackDesignError, match="UTF-8 JSON"):
        load_switchback_design(invalid)


def test_switchback_manifest_file_digest_is_stable() -> None:
    first = load_switchback_design(DESIGN)
    second = load_switchback_design(DESIGN)
    assert first.manifest_sha256 == second.manifest_sha256
    assert first.manifest_sha256 == sha256(DESIGN.read_bytes()).hexdigest()
