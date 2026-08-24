from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from hashlib import sha256
from pathlib import Path
from typing import cast

import pytest

from routemind_compute.application.execution import canonical_digest
from routemind_compute.application.twin_calibration import (
    TwinCalibrationError,
    TwinCalibrationPlan,
    execute_bounded_twin_calibration,
    load_twin_calibration_plan,
)
from routemind_compute.application.twin_fidelity_protocol import (
    TwinFidelityProtocol,
    load_twin_fidelity_protocol,
)
from routemind_compute.application.twin_split_contract import (
    TwinSplitContract,
    load_twin_split_contract,
)

ROOT = Path(__file__).resolve().parents[3]
PLAN = ROOT / "docs" / "research" / "r3" / "manifests" / "twin" / "r3-331-calibration-plan-v1.json"
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


def _mappings(value: object) -> list[dict[str, object]]:
    return [_mapping(item) for item in cast(Sequence[object], value)]


def _write(tmp_path: Path, payload: dict[str, object]) -> Path:
    unsigned = dict(payload)
    unsigned["plan_digest"] = canonical_digest(
        {key: value for key, value in unsigned.items() if key != "plan_digest"}
    )
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(unsigned, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _loaded() -> tuple[TwinCalibrationPlan, TwinSplitContract, TwinFidelityProtocol]:
    return (
        load_twin_calibration_plan(PLAN),
        load_twin_split_contract(SPLIT),
        load_twin_fidelity_protocol(PROTOCOL),
    )


def test_bounded_calibration_returns_frozen_insufficient_data_without_fit() -> None:
    plan, split, protocol = _loaded()
    assert plan.plan_id == "r3-331-bounded-twin-calibration-v1"
    outcome = execute_bounded_twin_calibration(plan, split, protocol)
    assert outcome.status == "INSUFFICIENT_DATA"
    assert outcome.calibration_record_count == 0
    assert outcome.held_out_record_count == 0
    assert outcome.missing_targets == plan.target_ids
    assert outcome.parameter_before_sha256 is None
    assert outcome.parameter_after_sha256 is None
    assert outcome.artifact_sha256 is None
    assert outcome.reason.startswith("No immutable")
    assert outcome.claim_boundary == "CALIBRATION_FIT_DOES_NOT_ESTABLISH_TWIN_VALIDITY"


def test_plan_identity_digest_and_json_errors(tmp_path: Path) -> None:
    payload = _payload()
    payload["question"] = "changed"
    forged = tmp_path / "forged.json"
    forged.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(TwinCalibrationError, match="digest"):
        load_twin_calibration_plan(forged)

    scalar = tmp_path / "scalar.json"
    scalar.write_text("[]", encoding="utf-8")
    with pytest.raises(TwinCalibrationError, match="JSON object"):
        load_twin_calibration_plan(scalar)

    invalid = tmp_path / "invalid.json"
    invalid.write_bytes(b"not-json")
    with pytest.raises(TwinCalibrationError, match="UTF-8 JSON"):
        load_twin_calibration_plan(invalid)


def test_plan_rejects_root_shape_identity_and_claim_boundary(tmp_path: Path) -> None:
    payload = _payload()
    del payload["question"]
    with pytest.raises(TwinCalibrationError, match="fields mismatch"):
        load_twin_calibration_plan(_write(tmp_path, payload))

    payload = _payload()
    payload["task_id"] = "R3-330"
    with pytest.raises(TwinCalibrationError, match="identity"):
        load_twin_calibration_plan(_write(tmp_path, payload))

    payload = _payload()
    payload["claim_boundary"] = "other"
    with pytest.raises(TwinCalibrationError, match="claim boundary"):
        load_twin_calibration_plan(_write(tmp_path, payload))


def test_plan_rejects_target_and_objective_drift(tmp_path: Path) -> None:
    payload = _payload()
    targets = _mappings(payload["targets"])
    targets[0]["unexpected"] = True
    payload["targets"] = targets
    with pytest.raises(TwinCalibrationError, match="target fields"):
        load_twin_calibration_plan(_write(tmp_path, payload))

    payload = _payload()
    targets = _mappings(payload["targets"])
    targets[0] = cast(dict[str, object], "invalid")
    payload["targets"] = targets
    with pytest.raises(TwinCalibrationError, match="object"):
        load_twin_calibration_plan(_write(tmp_path, payload))

    payload = _payload()
    targets = _mappings(payload["targets"])
    targets[0] = cast(dict[str, object], {"target_id": "assignment_rate"})
    payload["targets"] = targets
    with pytest.raises(TwinCalibrationError, match="target fields"):
        load_twin_calibration_plan(_write(tmp_path, payload))

    payload = _payload()
    payload["targets"] = _mappings(payload["targets"])[:3]
    with pytest.raises(TwinCalibrationError, match="exactly four"):
        load_twin_calibration_plan(_write(tmp_path, payload))

    payload = _payload()
    targets = _mappings(payload["targets"])
    targets.reverse()
    payload["targets"] = targets
    with pytest.raises(TwinCalibrationError, match="identity/order"):
        load_twin_calibration_plan(_write(tmp_path, payload))

    payload = _payload()
    objective = _mapping(payload["objective"])
    objective["name"] = "other"
    payload["objective"] = objective
    with pytest.raises(TwinCalibrationError, match="objective"):
        load_twin_calibration_plan(_write(tmp_path, payload))

    payload = _payload()
    objective = _mapping(payload["objective"])
    objective["metric_ids"] = ["assignment_rate"]
    payload["objective"] = objective
    with pytest.raises(TwinCalibrationError, match="metrics drift"):
        load_twin_calibration_plan(_write(tmp_path, payload))

    payload = _payload()
    objective = _mapping(payload["objective"])
    objective["lower_is_better"] = False
    payload["objective"] = objective
    with pytest.raises(TwinCalibrationError, match="minimize"):
        load_twin_calibration_plan(_write(tmp_path, payload))

    payload = _payload()
    targets = _mappings(payload["targets"])
    targets[0]["parameter_names"] = [""]
    payload["targets"] = targets
    with pytest.raises(TwinCalibrationError, match="parameter names"):
        load_twin_calibration_plan(_write(tmp_path, payload))

    payload = _payload()
    targets = _mappings(payload["targets"])
    targets[0]["parameter_names"] = "invalid"
    payload["targets"] = targets
    with pytest.raises(TwinCalibrationError, match="array"):
        load_twin_calibration_plan(_write(tmp_path, payload))

    payload = _payload()
    objective = _mapping(payload["objective"])
    objective["metric_ids"] = [1]
    payload["objective"] = objective
    with pytest.raises(TwinCalibrationError, match="objective metric"):
        load_twin_calibration_plan(_write(tmp_path, payload))

    payload = _payload()
    objective = _mapping(payload["objective"])
    objective["lower_is_better"] = "yes"
    payload["objective"] = objective
    with pytest.raises(TwinCalibrationError, match="boolean"):
        load_twin_calibration_plan(_write(tmp_path, payload))


def test_plan_rejects_bounds_and_search_drift(tmp_path: Path) -> None:
    payload = _payload()
    bounds = _mapping(payload["parameter_bounds"])
    del bounds["risk_scale"]
    payload["parameter_bounds"] = bounds
    with pytest.raises(TwinCalibrationError, match="all bounded"):
        load_twin_calibration_plan(_write(tmp_path, payload))

    payload = _payload()
    bounds = _mapping(payload["parameter_bounds"])
    bounds["risk_scale"] = [1.0]
    payload["parameter_bounds"] = bounds
    with pytest.raises(TwinCalibrationError, match="two finite"):
        load_twin_calibration_plan(_write(tmp_path, payload))

    payload = _payload()
    bounds = _mapping(payload["parameter_bounds"])
    bounds["risk_scale"] = [2.0, 1.0]
    payload["parameter_bounds"] = bounds
    with pytest.raises(TwinCalibrationError, match="ordered"):
        load_twin_calibration_plan(_write(tmp_path, payload))

    payload = _payload()
    search = _mapping(payload["search"])
    search["method"] = "random"
    payload["search"] = search
    with pytest.raises(TwinCalibrationError, match="search method"):
        load_twin_calibration_plan(_write(tmp_path, payload))

    payload = _payload()
    search = _mapping(payload["search"])
    search["seed"] = 0
    payload["search"] = search
    with pytest.raises(TwinCalibrationError, match="seed"):
        load_twin_calibration_plan(_write(tmp_path, payload))

    payload = _payload()
    search = _mapping(payload["search"])
    search["tolerance"] = 0.0
    payload["search"] = search
    with pytest.raises(TwinCalibrationError, match="tolerance"):
        load_twin_calibration_plan(_write(tmp_path, payload))

    payload = _payload()
    bounds = _mapping(payload["parameter_bounds"])
    bounds["risk_scale"] = [None, 2.0]
    payload["parameter_bounds"] = bounds
    with pytest.raises(TwinCalibrationError, match="two finite"):
        load_twin_calibration_plan(_write(tmp_path, payload))

    payload = _payload()
    search = _mapping(payload["search"])
    search["seed"] = "331"
    payload["search"] = search
    with pytest.raises(TwinCalibrationError, match="integer"):
        load_twin_calibration_plan(_write(tmp_path, payload))


def test_plan_rejects_initialization_regularization_and_policy_drift(tmp_path: Path) -> None:
    payload = _payload()
    initialization = _mapping(payload["initialization"])
    initialization["method"] = "random"
    payload["initialization"] = initialization
    with pytest.raises(TwinCalibrationError, match="initialization"):
        load_twin_calibration_plan(_write(tmp_path, payload))

    payload = _payload()
    initialization = _mapping(payload["initialization"])
    parameters = _mapping(initialization["parameters"])
    parameters["risk_scale"] = 3.0
    initialization["parameters"] = parameters
    payload["initialization"] = initialization
    with pytest.raises(TwinCalibrationError, match="bounds"):
        load_twin_calibration_plan(_write(tmp_path, payload))

    payload = _payload()
    regularization = _mapping(payload["regularization"])
    regularization["lambda"] = -1.0
    payload["regularization"] = regularization
    with pytest.raises(TwinCalibrationError, match="non-negative"):
        load_twin_calibration_plan(_write(tmp_path, payload))

    payload = _payload()
    policy = _mapping(payload["data_policy"])
    policy["held_out_split_id"] = policy["calibration_split_id"]
    payload["data_policy"] = policy
    with pytest.raises(TwinCalibrationError, match="distinct"):
        load_twin_calibration_plan(_write(tmp_path, payload))

    payload = _payload()
    policy = _mapping(payload["artifact_policy"])
    policy["artifact_required"] = False
    payload["artifact_policy"] = policy
    with pytest.raises(TwinCalibrationError, match="checksums"):
        load_twin_calibration_plan(_write(tmp_path, payload))

    payload = _payload()
    missing = _mapping(payload["missing_data_policy"])
    missing["no_fit_performed"] = False
    payload["missing_data_policy"] = missing
    with pytest.raises(TwinCalibrationError, match="no-fit"):
        load_twin_calibration_plan(_write(tmp_path, payload))

    payload = _payload()
    initialization = _mapping(payload["initialization"])
    parameters = _mapping(initialization["parameters"])
    del parameters["risk_scale"]
    initialization["parameters"] = parameters
    payload["initialization"] = initialization
    with pytest.raises(TwinCalibrationError, match="initialization parameters"):
        load_twin_calibration_plan(_write(tmp_path, payload))

    payload = _payload()
    initialization = _mapping(payload["initialization"])
    parameters = _mapping(initialization["parameters"])
    parameters["risk_scale"] = "one"
    initialization["parameters"] = parameters
    payload["initialization"] = initialization
    with pytest.raises(TwinCalibrationError, match="finite number"):
        load_twin_calibration_plan(_write(tmp_path, payload))

    payload = _payload()
    artifact = _mapping(payload["artifact_policy"])
    artifact["checksum_algorithm"] = "md5"
    payload["artifact_policy"] = artifact
    with pytest.raises(TwinCalibrationError, match="SHA-256"):
        load_twin_calibration_plan(_write(tmp_path, payload))

    payload = _payload()
    payload["question"] = ""
    with pytest.raises(TwinCalibrationError, match="non-empty text"):
        load_twin_calibration_plan(_write(tmp_path, payload))


def test_executor_rejects_lineage_drift(tmp_path: Path) -> None:
    plan, split, protocol = _loaded()
    payload = _payload()
    data_policy = _mapping(payload["data_policy"])
    data_policy["calibration_split_id"] = "other"
    payload["data_policy"] = data_policy
    drifted = load_twin_calibration_plan(_write(tmp_path, payload))
    with pytest.raises(TwinCalibrationError, match="calibration split identity"):
        execute_bounded_twin_calibration(drifted, split, protocol)

    payload = _payload()
    data_policy = _mapping(payload["data_policy"])
    data_policy["fit_may_read_held_out"] = True
    payload["data_policy"] = data_policy
    with pytest.raises(TwinCalibrationError, match="unsafe reads"):
        load_twin_calibration_plan(_write(tmp_path, payload))

    unsafe_policy = _mapping(plan.payload["data_policy"])
    unsafe_policy["fit_may_read_held_out"] = True
    unsafe_plan = TwinCalibrationPlan(
        {**plan.payload, "data_policy": unsafe_policy},
        plan.plan_digest,
        plan.manifest_sha256,
    )
    with pytest.raises(TwinCalibrationError, match="permits held-out"):
        execute_bounded_twin_calibration(unsafe_plan, split, protocol)

    held_out_policy = _mapping(plan.payload["data_policy"])
    held_out_policy["held_out_split_id"] = "other"
    held_out_plan = TwinCalibrationPlan(
        {**plan.payload, "data_policy": held_out_policy},
        plan.plan_digest,
        plan.manifest_sha256,
    )
    with pytest.raises(TwinCalibrationError, match="held-out split identity"):
        execute_bounded_twin_calibration(held_out_plan, split, protocol)

    split_payload = dict(split.payload)
    split_payload["claim_boundary"] = "other"
    bad_claim = TwinSplitContract(split_payload, split.contract_digest, split.manifest_sha256)
    with pytest.raises(TwinCalibrationError, match="claim boundary"):
        execute_bounded_twin_calibration(plan, bad_claim, protocol)


def test_executor_rejects_protocol_and_non_no_data_branches() -> None:
    plan, split, protocol = _loaded()
    altered_protocol = type(protocol)(
        protocol.payload,
        protocol.protocol_digest,
        protocol.manifest_sha256,
        tuple(reversed(protocol.metrics)),
    )
    with pytest.raises(TwinCalibrationError, match="fidelity protocol"):
        execute_bounded_twin_calibration(plan, split, altered_protocol)

    split_payload = dict(split.payload)
    split_payload["data_availability"] = {
        **_mapping(split_payload["data_availability"]),
        "status": "AVAILABLE",
    }
    available = TwinSplitContract(split_payload, split.contract_digest, split.manifest_sha256)
    with pytest.raises(TwinCalibrationError, match="only supports"):
        execute_bounded_twin_calibration(plan, available, protocol)

    split_payload = dict(split.payload)
    split_values = _mapping(split_payload["splits"])
    calibration = _mapping(split_values["calibration"])
    calibration["artifact_status"] = "AVAILABLE"
    calibration["record_count"] = 1
    split_values["calibration"] = calibration
    split_payload["splits"] = split_values
    available = TwinSplitContract(split_payload, split.contract_digest, split.manifest_sha256)
    with pytest.raises(TwinCalibrationError, match="required"):
        execute_bounded_twin_calibration(plan, available, protocol)


def test_plan_file_digest_is_stable() -> None:
    first = load_twin_calibration_plan(PLAN)
    second = load_twin_calibration_plan(PLAN)
    assert first.manifest_sha256 == second.manifest_sha256
    assert first.manifest_sha256 == sha256(PLAN.read_bytes()).hexdigest()
