from __future__ import annotations

import json
from collections.abc import Mapping
from hashlib import sha256
from pathlib import Path
from typing import cast

import pytest

from routemind_compute.application.execution import canonical_digest
from routemind_compute.application.twin_calibration import (
    execute_bounded_twin_calibration,
    load_twin_calibration_plan,
)
from routemind_compute.application.twin_fidelity_protocol import load_twin_fidelity_protocol
from routemind_compute.application.twin_held_out_validation import (
    TwinHeldOutValidationOutcome,
    execute_twin_held_out_validation,
    load_twin_held_out_validation_plan,
)
from routemind_compute.application.twin_split_contract import load_twin_split_contract
from routemind_compute.application.twin_what_if_validity import (
    TwinWhatIfValidityError,
    TwinWhatIfValidityPlan,
    assess_twin_what_if_validity,
    load_twin_what_if_validity_plan,
)

ROOT = Path(__file__).resolve().parents[3]
PLAN = ROOT / "docs" / "research" / "r3" / "manifests" / "twin" / "r3-335-what-if-validity-v1.json"
CALIBRATION = (
    ROOT / "docs" / "research" / "r3" / "manifests" / "twin" / "r3-331-calibration-plan-v1.json"
)
VALIDATION = (
    ROOT / "docs" / "research" / "r3" / "manifests" / "twin" / "r3-332-held-out-validation-v1.json"
)
SPLIT = (
    ROOT / "docs" / "research" / "r3" / "manifests" / "twin" / "r3-330-twin-split-contract-v1.json"
)
PROTOCOL = (
    ROOT / "docs" / "research" / "r3" / "manifests" / "twin" / "r3-333-fidelity-protocol-v1.json"
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
    path = tmp_path / "what-if.json"
    path.write_text(json.dumps(unsigned, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _loaded() -> tuple[TwinWhatIfValidityPlan, TwinHeldOutValidationOutcome]:
    plan = load_twin_what_if_validity_plan(PLAN)
    calibration = load_twin_calibration_plan(CALIBRATION)
    validation_plan = load_twin_held_out_validation_plan(VALIDATION)
    split = load_twin_split_contract(SPLIT)
    protocol = load_twin_fidelity_protocol(PROTOCOL)
    calibration_outcome = execute_bounded_twin_calibration(calibration, split, protocol)
    validation_outcome = execute_twin_held_out_validation(
        validation_plan, split, protocol, calibration, calibration_outcome
    )
    return plan, validation_outcome


def test_validity_boundaries_produce_no_claim_when_held_out_is_missing() -> None:
    plan, validation_outcome = _loaded()
    outcome = assess_twin_what_if_validity(plan, validation_outcome)
    assert plan.boundary_id == "r3-335-what-if-validity-v1"
    assert outcome.status == "NO_VALIDITY_CLAIM"
    assert outcome.allowed_scope == ()
    assert [mode.mode_id for mode in outcome.modes] == [
        "counterfactual_replay",
        "simulation_comparison",
        "causal_inference",
    ]
    assert all(mode.status == "BOUNDARY_ONLY" for mode in outcome.modes)
    assert all(mode.prohibited_claims for mode in outcome.modes)
    assert outcome.reason == "NO_VALIDITY_CLAIM"


def test_supported_outcome_remains_scope_only() -> None:
    plan, validation_outcome = _loaded()
    supported = TwinHeldOutValidationOutcome(
        "VALIDATED_FOR_SCOPE",
        validation_outcome.plan_digest,
        validation_outcome.split_contract_digest,
        validation_outcome.fidelity_protocol_digest,
        validation_outcome.calibration_status,
        100,
        validation_outcome.metrics,
        validation_outcome.reason,
    )
    outcome = assess_twin_what_if_validity(plan, supported)
    assert outcome.status == "SCOPE_ONLY"
    assert outcome.allowed_scope == ("observed_held_out_scope_only",)
    assert all(mode.status == "SCOPE_ONLY" for mode in outcome.modes)


def test_plan_rejects_digest_json_identity_and_boundary(tmp_path: Path) -> None:
    payload = _payload()
    payload["question"] = "changed"
    forged = tmp_path / "forged.json"
    forged.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(TwinWhatIfValidityError, match="digest"):
        load_twin_what_if_validity_plan(forged)

    scalar = tmp_path / "scalar.json"
    scalar.write_text("[]", encoding="utf-8")
    with pytest.raises(TwinWhatIfValidityError, match="JSON object"):
        load_twin_what_if_validity_plan(scalar)

    invalid = tmp_path / "invalid.json"
    invalid.write_bytes(b"not-json")
    with pytest.raises(TwinWhatIfValidityError, match="UTF-8 JSON"):
        load_twin_what_if_validity_plan(invalid)

    payload = _payload()
    del payload["question"]
    with pytest.raises(TwinWhatIfValidityError, match="fields mismatch"):
        load_twin_what_if_validity_plan(_write(tmp_path, payload))

    payload = _payload()
    payload["task_id"] = "R3-334"
    with pytest.raises(TwinWhatIfValidityError, match="identity"):
        load_twin_what_if_validity_plan(_write(tmp_path, payload))

    payload = _payload()
    payload["claim_boundary"] = "other"
    with pytest.raises(TwinWhatIfValidityError, match="claim boundary"):
        load_twin_what_if_validity_plan(_write(tmp_path, payload))


def test_plan_rejects_mode_and_scope_policy_drift(tmp_path: Path) -> None:
    payload = _payload()
    payload["mode_policies"] = []
    with pytest.raises(TwinWhatIfValidityError, match="three"):
        load_twin_what_if_validity_plan(_write(tmp_path, payload))

    payload = _payload()
    modes = [_mapping(item) for item in cast(list[object], payload["mode_policies"])]
    modes[0]["mode_id"] = "other"
    payload["mode_policies"] = modes
    with pytest.raises(TwinWhatIfValidityError, match="mode identity"):
        load_twin_what_if_validity_plan(_write(tmp_path, payload))

    payload = _payload()
    modes = [_mapping(item) for item in cast(list[object], payload["mode_policies"])]
    modes[0]["prohibited_claims"] = []
    payload["mode_policies"] = modes
    with pytest.raises(TwinWhatIfValidityError, match="prohibited claims"):
        load_twin_what_if_validity_plan(_write(tmp_path, payload))

    payload = _payload()
    scope = _mapping(payload["scope_policy"])
    scope["external_validity"] = "ALLOWED"
    payload["scope_policy"] = scope
    with pytest.raises(TwinWhatIfValidityError, match="external-validity"):
        load_twin_what_if_validity_plan(_write(tmp_path, payload))

    payload = _payload()
    scope = _mapping(payload["scope_policy"])
    scope["when_supported"] = "CLAIM"
    payload["scope_policy"] = scope
    with pytest.raises(TwinWhatIfValidityError, match="scope-only"):
        load_twin_what_if_validity_plan(_write(tmp_path, payload))


def test_plan_rejects_nested_types_and_lineage(tmp_path: Path) -> None:
    payload = _payload()
    payload["mode_policies"] = "invalid"
    with pytest.raises(TwinWhatIfValidityError, match="array"):
        load_twin_what_if_validity_plan(_write(tmp_path, payload))

    payload = _payload()
    scope = _mapping(payload["scope_policy"])
    scope["unexpected"] = True
    payload["scope_policy"] = scope
    with pytest.raises(TwinWhatIfValidityError, match="fields mismatch"):
        load_twin_what_if_validity_plan(_write(tmp_path, payload))

    payload = _payload()
    mode_objects = cast(list[object], payload["mode_policies"])
    payload["mode_policies"] = ["invalid", mode_objects[1], mode_objects[2]]
    with pytest.raises(TwinWhatIfValidityError, match="object"):
        load_twin_what_if_validity_plan(_write(tmp_path, payload))

    payload = _payload()
    payload["question"] = ""
    with pytest.raises(TwinWhatIfValidityError, match="non-empty text"):
        load_twin_what_if_validity_plan(_write(tmp_path, payload))

    payload = _payload()
    modes = [_mapping(item) for item in cast(list[object], payload["mode_policies"])]
    modes[0]["prohibited_claims"] = [1]
    payload["mode_policies"] = modes
    with pytest.raises(TwinWhatIfValidityError, match="prohibited claim"):
        load_twin_what_if_validity_plan(_write(tmp_path, payload))

    payload = _payload()
    payload["source_validation_plan_digest"] = "g" * 64
    with pytest.raises(TwinWhatIfValidityError, match="SHA-256"):
        load_twin_what_if_validity_plan(_write(tmp_path, payload))

    payload = _payload()
    scope = _mapping(payload["scope_policy"])
    scope["when_insufficient_data"] = "CLAIM"
    payload["scope_policy"] = scope
    with pytest.raises(TwinWhatIfValidityError, match="insufficient data"):
        load_twin_what_if_validity_plan(_write(tmp_path, payload))

    plan, validation_outcome = _loaded()
    altered = TwinHeldOutValidationOutcome(
        validation_outcome.outcome,
        "a" * 64,
        validation_outcome.split_contract_digest,
        validation_outcome.fidelity_protocol_digest,
        validation_outcome.calibration_status,
        validation_outcome.held_out_record_count,
        validation_outcome.metrics,
        validation_outcome.reason,
    )
    with pytest.raises(TwinWhatIfValidityError, match="validation plan digest"):
        assess_twin_what_if_validity(plan, altered)


def test_plan_file_digest_is_stable() -> None:
    first = load_twin_what_if_validity_plan(PLAN)
    second = load_twin_what_if_validity_plan(PLAN)
    assert first.manifest_sha256 == second.manifest_sha256
    assert first.manifest_sha256 == sha256(PLAN.read_bytes()).hexdigest()
