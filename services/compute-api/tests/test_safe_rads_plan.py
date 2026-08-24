from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from hashlib import sha256
from pathlib import Path
from typing import cast

import pytest

from routemind_compute.application.execution import canonical_digest
from routemind_compute.application.safe_rads_plan import (
    SafeRadsPlanError,
    load_safe_rads_plan,
)

ROOT = Path(__file__).resolve().parents[3]
PLAN = (
    ROOT
    / "docs"
    / "research"
    / "r3"
    / "manifests"
    / "rads"
    / "r3-344-safe-rads-formalization-v1.json"
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
    unsigned["plan_digest"] = canonical_digest(
        {key: value for key, value in unsigned.items() if key != "plan_digest"}
    )
    path = tmp_path / "safe-rads.json"
    path.write_text(json.dumps(unsigned, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def test_plan_freezes_constraint_semantics_and_lineage() -> None:
    plan = load_safe_rads_plan(PLAN)
    assert plan.mechanism_id == "Safe-RADS-v1"
    assert plan.plan_digest == ("82fed4dc95bec7ccbfa10ead770d63e2de6f47bb081d0b5d05672382462f6644")
    assert plan.manifest_sha256 == sha256(PLAN.read_bytes()).hexdigest()
    assert _mapping(plan.payload["primary_constraint"])["epsilon"] == 0.05
    assert _mapping(plan.payload["fallback"])["penalty_only_allowed"] is False


def test_plan_rejects_json_shape_and_digest(tmp_path: Path) -> None:
    invalid = tmp_path / "invalid.json"
    invalid.write_bytes(b"not-json")
    with pytest.raises(SafeRadsPlanError, match="UTF-8 JSON"):
        load_safe_rads_plan(invalid)
    scalar = tmp_path / "scalar.json"
    scalar.write_text("[]", encoding="utf-8")
    with pytest.raises(SafeRadsPlanError, match="JSON object"):
        load_safe_rads_plan(scalar)
    payload = _payload()
    payload["question"] = "tampered"
    forged = tmp_path / "forged.json"
    forged.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(SafeRadsPlanError, match="digest"):
        load_safe_rads_plan(forged)


def test_plan_rejects_identity_semantics_and_constraint_drift(tmp_path: Path) -> None:
    def reject(mutate: Callable[[dict[str, object]], None], match: str) -> None:
        payload = _payload()
        mutate(payload)
        with pytest.raises(SafeRadsPlanError, match=match):
            load_safe_rads_plan(_write(tmp_path, payload))

    reject(lambda p: p.update(task_id="R3-340"), "identity")
    reject(lambda p: p.update(mechanism_id="other"), "identifier")
    reject(lambda p: p.update(baseline_reference="other"), "baseline")
    reject(lambda p: p.update(claim_boundary="other"), "claim boundary")
    reject(
        lambda p: p.update(semantics={**_mapping(p["semantics"]), "penalty": "safety guarantee"}),
        "semantic distinction",
    )
    reject(
        lambda p: p.update(
            primary_constraint={**_mapping(p["primary_constraint"]), "epsilon": 0.1}
        ),
        "epsilon or bound",
    )
    reject(
        lambda p: p.update(
            primary_constraint={**_mapping(p["primary_constraint"]), "metric": "risk"}
        ),
        "primary metric",
    )


def test_plan_rejects_uncertainty_efficiency_and_fallback_drift(tmp_path: Path) -> None:
    def reject(mutate: Callable[[dict[str, object]], None], match: str) -> None:
        payload = _payload()
        mutate(payload)
        with pytest.raises(SafeRadsPlanError, match=match):
            load_safe_rads_plan(_write(tmp_path, payload))

    reject(
        lambda p: p.update(
            uncertainty={**_mapping(p["uncertainty"]), "calibration_required": False}
        ),
        "calibration",
    )
    reject(
        lambda p: p.update(uncertainty={**_mapping(p["uncertainty"]), "minimum_observations": 10}),
        "thresholds",
    )
    reject(
        lambda p: p.update(
            efficiency_cost={**_mapping(p["efficiency_cost"]), "relative_bound": 0.05}
        ),
        "efficiency bound",
    )
    reject(
        lambda p: p.update(fallback={**_mapping(p["fallback"]), "penalty_only_allowed": True}),
        "penalty-only",
    )
    reject(
        lambda p: p.update(fallback={**_mapping(p["fallback"]), "on_hard_violation": "ignore"}),
        "hard-violation",
    )
    reject(
        lambda p: p.update(
            fallback={**_mapping(p["fallback"]), "on_uncertainty_failure": "continue"}
        ),
        "uncertainty fallback",
    )


def test_plan_rejects_authority_execution_lineage_and_nested_types(tmp_path: Path) -> None:
    def reject(mutate: Callable[[dict[str, object]], None], match: str) -> None:
        payload = _payload()
        mutate(payload)
        with pytest.raises(SafeRadsPlanError, match=match):
            load_safe_rads_plan(_write(tmp_path, payload))

    reject(
        lambda p: p.update(
            validation_authority={
                **_mapping(p["validation_authority"]),
                "durable_enforcer": "Python",
            }
        ),
        "durable authority",
    )
    reject(
        lambda p: p.update(
            execution_policy={
                **_mapping(p["execution_policy"]),
                "material_run_authorized": True,
            }
        ),
        "preregistration-only",
    )
    reject(
        lambda p: p.update(
            source_lineage={
                **_mapping(p["source_lineage"]),
                "rads_source": "0" * 64,
            }
        ),
        "lineage",
    )
    reject(lambda p: p.update(semantics="invalid"), "object")
    reject(lambda p: p.update(limitations="invalid"), "array")
    reject(
        lambda p: p.update(uncertainty={**_mapping(p["uncertainty"]), "confidence_level": "high"}),
        "finite number",
    )
    reject(
        lambda p: p.update(
            uncertainty={**_mapping(p["uncertainty"]), "minimum_observations": True}
        ),
        "integer",
    )
    reject(
        lambda p: p.update(
            execution_policy={**_mapping(p["execution_policy"]), "resource_envelope": ""}
        ),
        "non-empty text",
    )


def test_plan_rejects_extra_fields_and_empty_limitations(tmp_path: Path) -> None:
    payload = _payload()
    payload["unexpected"] = True
    with pytest.raises(SafeRadsPlanError, match="fields mismatch"):
        load_safe_rads_plan(_write(tmp_path, payload))
    payload = _payload()
    payload["limitations"] = []
    with pytest.raises(SafeRadsPlanError, match="limitations"):
        load_safe_rads_plan(_write(tmp_path, payload))
