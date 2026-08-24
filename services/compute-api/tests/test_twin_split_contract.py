from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from hashlib import sha256
from pathlib import Path
from typing import cast

import pytest

from routemind_compute.application.execution import canonical_digest
from routemind_compute.application.twin_split_contract import (
    TwinSplitContractError,
    load_twin_split_contract,
)

ROOT = Path(__file__).resolve().parents[3]
CONTRACT = (
    ROOT / "docs" / "research" / "r3" / "manifests" / "twin" / "r3-330-twin-split-contract-v1.json"
)


def _payload() -> dict[str, object]:
    parsed: object = json.loads(CONTRACT.read_text(encoding="utf-8"))
    if not isinstance(parsed, Mapping):
        raise AssertionError("fixture must be an object")
    return cast(dict[str, object], parsed)


def _mapping(value: object) -> dict[str, object]:
    return dict(cast(Mapping[str, object], value))


def _mappings(value: object) -> list[dict[str, object]]:
    return [_mapping(item) for item in cast(Sequence[object], value)]


def _write(tmp_path: Path, payload: dict[str, object]) -> Path:
    unsigned = dict(payload)
    unsigned["contract_digest"] = canonical_digest(
        {key: value for key, value in unsigned.items() if key != "contract_digest"}
    )
    path = tmp_path / "contract.json"
    path.write_text(json.dumps(unsigned, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def test_twin_split_contract_validates_disjoint_no_data_design() -> None:
    contract = load_twin_split_contract(CONTRACT)
    assert contract.contract_id == "r3-330-twin-split-contract-v1"
    assert contract.data_status == "INSUFFICIENT_DATA"
    assert contract.split_ids == (
        "r3-330-calibration-observed-v1",
        "r3-330-held-out-observed-v1",
    )
    assert len(contract.contract_digest) == 64
    assert len(contract.manifest_sha256) == 64


def test_twin_split_contract_rejects_forged_digest(tmp_path: Path) -> None:
    payload = _payload()
    payload["scope"] = "changed"
    path = tmp_path / "forged.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(TwinSplitContractError, match="digest"):
        load_twin_split_contract(path)


def test_twin_split_contract_rejects_held_out_fit_and_shared_identity(tmp_path: Path) -> None:
    payload = _payload()
    protocol = _mapping(payload["protocol"])
    protocol["fit_may_read_held_out"] = True
    payload["protocol"] = protocol
    with pytest.raises(TwinSplitContractError, match="held-out"):
        load_twin_split_contract(_write(tmp_path, payload))

    payload = _payload()
    splits = _mapping(payload["splits"])
    calibration = _mapping(splits["calibration"])
    held_out = _mapping(splits["held_out"])
    held_out["split_id"] = calibration["split_id"]
    held_out["identity_digest"] = canonical_digest(
        {key: value for key, value in held_out.items() if key != "identity_digest"}
    )
    splits["held_out"] = held_out
    payload["splits"] = splits
    with pytest.raises(TwinSplitContractError, match="disjoint"):
        load_twin_split_contract(_write(tmp_path, payload))


def test_twin_split_contract_rejects_claimed_data_without_checksum(tmp_path: Path) -> None:
    payload = _payload()
    splits = _mapping(payload["splits"])
    calibration = _mapping(splits["calibration"])
    calibration["artifact_status"] = "AVAILABLE"
    calibration["record_count"] = 1
    calibration["artifact_sha256"] = None
    calibration["identity_digest"] = canonical_digest(
        {key: value for key, value in calibration.items() if key != "identity_digest"}
    )
    splits["calibration"] = calibration
    payload["splits"] = splits
    with pytest.raises(TwinSplitContractError, match="SHA-256"):
        load_twin_split_contract(_write(tmp_path, payload))


def test_twin_split_contract_requires_all_no_data_leakage_checks(tmp_path: Path) -> None:
    payload = _payload()
    checks = _mappings(payload["leakage_checks"])
    checks[0]["status"] = "PASS"
    payload["leakage_checks"] = checks
    with pytest.raises(TwinSplitContractError, match="NOT_RUN_NO_DATA"):
        load_twin_split_contract(_write(tmp_path, payload))

    payload = _payload()
    payload["leakage_checks"] = checks[:4]
    with pytest.raises(TwinSplitContractError, match="five leakage"):
        load_twin_split_contract(_write(tmp_path, payload))


def test_twin_split_contract_rejects_non_insufficient_data_and_invalid_json(tmp_path: Path) -> None:
    payload = _payload()
    availability = _mapping(payload["data_availability"])
    availability["status"] = "AVAILABLE"
    payload["data_availability"] = availability
    with pytest.raises(TwinSplitContractError, match="INSUFFICIENT_DATA"):
        load_twin_split_contract(_write(tmp_path, payload))

    invalid = tmp_path / "invalid.json"
    invalid.write_bytes(b"not-json")
    with pytest.raises(TwinSplitContractError, match="UTF-8 JSON"):
        load_twin_split_contract(invalid)


def test_twin_split_contract_file_digest_is_stable() -> None:
    first = load_twin_split_contract(CONTRACT)
    second = load_twin_split_contract(CONTRACT)
    assert first.manifest_sha256 == second.manifest_sha256
    assert first.manifest_sha256 == sha256(CONTRACT.read_bytes()).hexdigest()


def test_twin_split_contract_rejects_shape_identity_and_claim_boundaries(tmp_path: Path) -> None:
    path = tmp_path / "scalar.json"
    path.write_text("[]", encoding="utf-8")
    with pytest.raises(TwinSplitContractError, match="JSON object"):
        load_twin_split_contract(path)

    payload = _payload()
    del payload["scope"]
    with pytest.raises(TwinSplitContractError, match="fields mismatch"):
        load_twin_split_contract(_write(tmp_path, payload))

    payload = _payload()
    payload["schema_version"] = "other"
    with pytest.raises(TwinSplitContractError, match="identity"):
        load_twin_split_contract(_write(tmp_path, payload))

    payload = _payload()
    payload["claim_boundary"] = "other"
    with pytest.raises(TwinSplitContractError, match="claim boundary"):
        load_twin_split_contract(_write(tmp_path, payload))


def test_twin_split_contract_rejects_availability_and_protocol_bounds(tmp_path: Path) -> None:
    payload = _payload()
    availability = _mapping(payload["data_availability"])
    availability["observed_record_count"] = 1
    payload["data_availability"] = availability
    with pytest.raises(TwinSplitContractError, match="count zero"):
        load_twin_split_contract(_write(tmp_path, payload))

    payload = _payload()
    availability = _mapping(payload["data_availability"])
    availability["required_minimum_records"] = 0
    payload["data_availability"] = availability
    with pytest.raises(TwinSplitContractError, match="positive"):
        load_twin_split_contract(_write(tmp_path, payload))

    payload = _payload()
    protocol = _mapping(payload["protocol"])
    protocol["validation_requires_observed_outcomes"] = False
    payload["protocol"] = protocol
    with pytest.raises(TwinSplitContractError, match="observed outcomes"):
        load_twin_split_contract(_write(tmp_path, payload))


def test_twin_split_contract_rejects_axes_and_split_shapes(tmp_path: Path) -> None:
    payload = _payload()
    rationale = _mapping(payload["split_rationale"])
    rationale["primary_axis"] = "other"
    payload["split_rationale"] = rationale
    with pytest.raises(TwinSplitContractError, match="primary axis"):
        load_twin_split_contract(_write(tmp_path, payload))

    payload = _payload()
    rationale = _mapping(payload["split_rationale"])
    rationale["secondary_axis"] = "other"
    payload["split_rationale"] = rationale
    with pytest.raises(TwinSplitContractError, match="secondary axis"):
        load_twin_split_contract(_write(tmp_path, payload))

    payload = _payload()
    rationale = _mapping(payload["split_rationale"])
    rationale["secondary_axis"] = rationale["primary_axis"]
    payload["split_rationale"] = rationale
    with pytest.raises(TwinSplitContractError, match="distinct"):
        load_twin_split_contract(_write(tmp_path, payload))

    payload = _payload()
    splits = _mapping(payload["splits"])
    del splits["held_out"]
    payload["splits"] = splits
    with pytest.raises(TwinSplitContractError, match="identities"):
        load_twin_split_contract(_write(tmp_path, payload))


def test_twin_split_contract_rejects_artifact_and_identity_drift(tmp_path: Path) -> None:
    payload = _payload()
    splits = _mapping(payload["splits"])
    calibration = _mapping(splits["calibration"])
    calibration["artifact_status"] = "AVAILABLE"
    calibration["artifact_sha256"] = "a" * 64
    calibration["record_count"] = 1
    calibration["identity_digest"] = canonical_digest(
        {key: value for key, value in calibration.items() if key != "identity_digest"}
    )
    held_out = _mapping(splits["held_out"])
    held_out["artifact_status"] = "AVAILABLE"
    held_out["artifact_sha256"] = "a" * 64
    held_out["record_count"] = 1
    held_out["identity_digest"] = canonical_digest(
        {key: value for key, value in held_out.items() if key != "identity_digest"}
    )
    splits["calibration"] = calibration
    splits["held_out"] = held_out
    payload["splits"] = splits
    with pytest.raises(TwinSplitContractError, match="share a checksum"):
        load_twin_split_contract(_write(tmp_path, payload))

    payload = _payload()
    splits = _mapping(payload["splits"])
    calibration = _mapping(splits["calibration"])
    calibration["artifact_status"] = "OTHER"
    calibration["identity_digest"] = canonical_digest(
        {key: value for key, value in calibration.items() if key != "identity_digest"}
    )
    splits["calibration"] = calibration
    payload["splits"] = splits
    with pytest.raises(TwinSplitContractError, match="status"):
        load_twin_split_contract(_write(tmp_path, payload))

    payload = _payload()
    splits = _mapping(payload["splits"])
    calibration = _mapping(splits["calibration"])
    calibration["identity_digest"] = "b" * 64
    splits["calibration"] = calibration
    payload["splits"] = splits
    with pytest.raises(TwinSplitContractError, match="identity digest"):
        load_twin_split_contract(_write(tmp_path, payload))

    payload = _payload()
    splits = _mapping(payload["splits"])
    calibration = _mapping(splits["calibration"])
    calibration["record_count"] = 1
    calibration["identity_digest"] = canonical_digest(
        {key: value for key, value in calibration.items() if key != "identity_digest"}
    )
    splits["calibration"] = calibration
    payload["splits"] = splits
    with pytest.raises(TwinSplitContractError, match="cannot claim"):
        load_twin_split_contract(_write(tmp_path, payload))

    payload = _payload()
    splits = _mapping(payload["splits"])
    calibration = _mapping(splits["calibration"])
    calibration["identity_digest"] = "bad"
    splits["calibration"] = calibration
    payload["splits"] = splits
    with pytest.raises(TwinSplitContractError, match="must be SHA-256"):
        load_twin_split_contract(_write(tmp_path, payload))

    payload = _payload()
    splits = _mapping(payload["splits"])
    calibration = _mapping(splits["calibration"])
    calibration["unexpected"] = True
    splits["calibration"] = calibration
    payload["splits"] = splits
    with pytest.raises(TwinSplitContractError, match="fields mismatch"):
        load_twin_split_contract(_write(tmp_path, payload))


def test_twin_split_contract_rejects_leakage_and_type_boundaries(tmp_path: Path) -> None:
    payload = _payload()
    checks = _mappings(payload["leakage_checks"])
    checks[1]["check_id"] = checks[0]["check_id"]
    payload["leakage_checks"] = checks
    with pytest.raises(TwinSplitContractError, match="identities"):
        load_twin_split_contract(_write(tmp_path, payload))

    payload = _payload()
    checks = _mappings(payload["leakage_checks"])
    checks[0]["method"] = ""
    payload["leakage_checks"] = checks
    with pytest.raises(TwinSplitContractError, match="method"):
        load_twin_split_contract(_write(tmp_path, payload))

    payload = _payload()
    payload["leakage_checks"] = "invalid"
    with pytest.raises(TwinSplitContractError, match="array"):
        load_twin_split_contract(_write(tmp_path, payload))

    payload = _payload()
    payload["splits"] = "invalid"
    with pytest.raises(TwinSplitContractError, match="object"):
        load_twin_split_contract(_write(tmp_path, payload))

    payload = _payload()
    splits = _mapping(payload["splits"])
    calibration = _mapping(splits["calibration"])
    calibration["record_count"] = "zero"
    calibration["identity_digest"] = canonical_digest(
        {key: value for key, value in calibration.items() if key != "identity_digest"}
    )
    splits["calibration"] = calibration
    payload["splits"] = splits
    with pytest.raises(TwinSplitContractError, match="integer"):
        load_twin_split_contract(_write(tmp_path, payload))

    payload = _payload()
    protocol = _mapping(payload["protocol"])
    protocol["fit_may_read_held_out"] = "no"
    payload["protocol"] = protocol
    with pytest.raises(TwinSplitContractError, match="boolean"):
        load_twin_split_contract(_write(tmp_path, payload))
