from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from hashlib import sha256
from pathlib import Path
from typing import cast

import pytest

from routemind_compute.application.execution import canonical_digest
from routemind_compute.application.rads_h_plan import (
    RadsHPlanError,
    load_rads_h_plan,
)

ROOT = Path(__file__).resolve().parents[3]
PLAN = (
    ROOT / "docs" / "research" / "r3" / "manifests" / "rads" / "r3-341-rads-h-formalization-v1.json"
)


def _payload() -> dict[str, object]:
    parsed: object = json.loads(PLAN.read_text(encoding="utf-8"))
    if not isinstance(parsed, Mapping):
        raise AssertionError("fixture must be an object")
    return cast(dict[str, object], parsed)


def _mapping(value: object) -> dict[str, object]:
    return dict(cast(Mapping[str, object], value))


def _write(tmp_path: Path, payload: dict[str, object]) -> Path:
    unsigned = dict(payload)
    unsigned["baseline_digest"] = canonical_digest(
        {key: value for key, value in unsigned.items() if key != "baseline_digest"}
    )
    path = tmp_path / "rads-h.json"
    path.write_text(json.dumps(unsigned, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def test_plan_freezes_hysteresis_semantics_and_lineage() -> None:
    plan = load_rads_h_plan(PLAN)
    assert plan.mechanism_id == "RADS-H-v1"
    assert (
        plan.baseline_digest == "4b846bc8b971df269c1c6439b325ab61b7803a83812ced39b352f519acb929c5"
    )
    assert plan.manifest_sha256 == sha256(PLAN.read_bytes()).hexdigest()
    parameters = _mapping(plan.payload["parameters"])
    assert parameters["enter_threshold"] == 0.05
    assert parameters["exit_threshold"] == 0.02
    assert parameters["persistence_ticks"] == 2
    assert parameters["minimum_dwell_ticks"] == 3
    assert parameters["switching_cost"] == 0.01
    assert _mapping(plan.payload["regime"])["required"] is True


def test_plan_rejects_json_identity_and_shape(tmp_path: Path) -> None:
    payload = _payload()
    payload["question"] = "changed"
    forged = tmp_path / "forged.json"
    forged.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(RadsHPlanError, match="digest"):
        load_rads_h_plan(forged)

    scalar = tmp_path / "scalar.json"
    scalar.write_text("[]", encoding="utf-8")
    with pytest.raises(RadsHPlanError, match="JSON object"):
        load_rads_h_plan(scalar)

    invalid = tmp_path / "invalid.json"
    invalid.write_bytes(b"not-json")
    with pytest.raises(RadsHPlanError, match="UTF-8 JSON"):
        load_rads_h_plan(invalid)

    payload = _payload()
    del payload["question"]
    with pytest.raises(RadsHPlanError, match="fields mismatch"):
        load_rads_h_plan(_write(tmp_path, payload))

    payload = _payload()
    payload["task_id"] = "R3-340"
    with pytest.raises(RadsHPlanError, match="identity"):
        load_rads_h_plan(_write(tmp_path, payload))


def test_plan_rejects_parameter_state_transition_and_regime_drift(tmp_path: Path) -> None:
    payload = _payload()
    parameters = _mapping(payload["parameters"])
    parameters["enter_threshold"] = 0.02
    payload["parameters"] = parameters
    with pytest.raises(RadsHPlanError, match="threshold band"):
        load_rads_h_plan(_write(tmp_path, payload))

    payload = _payload()
    state = _mapping(payload["state"])
    state["fields"] = ["active_strategy"]
    payload["state"] = state
    with pytest.raises(RadsHPlanError, match="state fields"):
        load_rads_h_plan(_write(tmp_path, payload))

    payload = _payload()
    transition = _mapping(payload["transition"])
    transition["exit"] = "other"
    payload["transition"] = transition
    with pytest.raises(RadsHPlanError, match="transition semantics"):
        load_rads_h_plan(_write(tmp_path, payload))

    payload = _payload()
    regime = _mapping(payload["regime"])
    regime["required"] = False
    payload["regime"] = regime
    with pytest.raises(RadsHPlanError, match="regime identity"):
        load_rads_h_plan(_write(tmp_path, payload))

    payload = _payload()
    cooldown = _mapping(payload["cooldown_comparison"])
    cooldown["separation"] = "other"
    payload["cooldown_comparison"] = cooldown
    with pytest.raises(RadsHPlanError, match="remain separate"):
        load_rads_h_plan(_write(tmp_path, payload))

    payload = _payload()
    limitations = list(cast(list[object], payload["limitations"]))
    limitations[0] = ""
    payload["limitations"] = limitations
    with pytest.raises(RadsHPlanError, match="limitations"):
        load_rads_h_plan(_write(tmp_path, payload))


def test_plan_rejects_source_identity_and_nested_types(tmp_path: Path) -> None:
    payload = _payload()
    sources = list(cast(list[object], payload["source_artifacts"]))
    source = _mapping(sources[0])
    source["sha256"] = "invalid"
    sources[0] = source
    payload["source_artifacts"] = sources
    with pytest.raises(RadsHPlanError, match="SHA-256"):
        load_rads_h_plan(_write(tmp_path, payload))

    payload = _payload()
    payload["source_artifacts"] = "invalid"
    with pytest.raises(RadsHPlanError, match="array"):
        load_rads_h_plan(_write(tmp_path, payload))

    payload = _payload()
    sources = list(cast(list[object], payload["source_artifacts"]))
    source = _mapping(sources[0])
    source["path"] = "other.py"
    sources[0] = source
    payload["source_artifacts"] = sources
    with pytest.raises(RadsHPlanError, match="identity"):
        load_rads_h_plan(_write(tmp_path, payload))

    payload = _payload()
    payload["parameters"] = "invalid"
    with pytest.raises(RadsHPlanError, match="object"):
        load_rads_h_plan(_write(tmp_path, payload))


def test_plan_rejects_remaining_fail_closed_branches(tmp_path: Path) -> None:
    def reject(mutate: Callable[[dict[str, object]], None], match: str) -> None:
        payload = _payload()
        mutate(payload)
        with pytest.raises(RadsHPlanError, match=match):
            load_rads_h_plan(_write(tmp_path, payload))

    reject(
        lambda payload: payload.update(mechanism_id="other"),
        "mechanism identity",
    )
    reject(
        lambda payload: payload.update(baseline_reference="other"),
        "baseline reference",
    )
    reject(
        lambda payload: payload.update(claim_boundary="other"),
        "claim boundary",
    )
    reject(
        lambda payload: payload.update(
            parameters={**_mapping(payload["parameters"]), "persistence_ticks": 1}
        ),
        "persistence or dwell",
    )
    reject(
        lambda payload: payload.update(
            parameters={**_mapping(payload["parameters"]), "switching_cost": 0.02}
        ),
        "switching cost",
    )
    reject(
        lambda payload: payload.update(
            state={**_mapping(payload["state"]), "reset_rules": ["switch"]}
        ),
        "reset rules",
    )
    reject(
        lambda payload: payload.update(
            regime={
                **_mapping(payload["regime"]),
                "change_behavior": "other",
            }
        ),
        "regime change behavior",
    )
    reject(
        lambda payload: payload.update(
            cooldown_comparison={
                **_mapping(payload["cooldown_comparison"]),
                "cooldown_only": "other",
            }
        ),
        "cooldown comparator",
    )
    reject(
        lambda payload: payload.update(
            cooldown_comparison={
                **_mapping(payload["cooldown_comparison"]),
                "rads_h": "other",
            }
        ),
        "RADS-H comparator",
    )

    def incomplete_sources(payload: dict[str, object]) -> None:
        payload["source_artifacts"] = cast(list[object], payload["source_artifacts"])[:-1]

    reject(incomplete_sources, "source artifact list")

    def reversed_sources(payload: dict[str, object]) -> None:
        payload["source_artifacts"] = list(
            reversed(cast(list[object], payload["source_artifacts"]))
        )

    reject(reversed_sources, "source artifact order")
    reject(
        lambda payload: payload.update(state={**_mapping(payload["state"]), "fields": "invalid"}),
        "array",
    )
    reject(
        lambda payload: payload.update(state={**_mapping(payload["state"]), "fields": [None]}),
        "state field must be non-empty text",
    )
    reject(
        lambda payload: payload.update(
            parameters={**_mapping(payload["parameters"]), "enter_threshold": "invalid"}
        ),
        "finite number",
    )
    reject(
        lambda payload: payload.update(
            parameters={**_mapping(payload["parameters"]), "persistence_ticks": True}
        ),
        "integer",
    )
    reject(
        lambda payload: payload.update(regime={**_mapping(payload["regime"]), "required": "true"}),
        "boolean",
    )
    reject(
        lambda payload: payload.update(state={**_mapping(payload["state"]), "unexpected": True}),
        "state fields mismatch",
    )
    reject(
        lambda payload: payload.update(question=""),
        "question must be non-empty text",
    )


def test_plan_file_digest_is_stable() -> None:
    first = load_rads_h_plan(PLAN)
    second = load_rads_h_plan(PLAN)
    assert first.baseline_digest == second.baseline_digest
    assert first.manifest_sha256 == second.manifest_sha256
