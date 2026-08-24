"""Fail-closed calibration/held-out split contract for R3-330."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from routemind_compute.application.execution import canonical_digest

_SCHEMA = "routemind-twin-split-contract-v1"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_CLAIM_BOUNDARY = "TWIN_FIDELITY_NOT_ESTABLISHED_WITHOUT_HELD_OUT_OBSERVATIONS"
_SPLITS = ("calibration", "held_out")
_LEAKAGE_CHECKS = ("event_identity", "temporal", "scenario", "geographic", "source_manifest")


class TwinSplitContractError(ValueError):
    """Raised when the R3-330 split contract is unsafe or inconsistent."""


@dataclass(frozen=True, slots=True)
class TwinSplitContract:
    payload: Mapping[str, object]
    contract_digest: str
    manifest_sha256: str

    @property
    def contract_id(self) -> str:
        return _text(self.payload, "contract_id")

    @property
    def data_status(self) -> str:
        return _text(_mapping(self.payload, "data_availability"), "status")

    @property
    def split_ids(self) -> tuple[str, str]:
        splits = _mapping(self.payload, "splits")
        return (
            _text(_mapping(splits, "calibration"), "split_id"),
            _text(_mapping(splits, "held_out"), "split_id"),
        )


def load_twin_split_contract(path: Path | str) -> TwinSplitContract:
    """Load a content-addressed split contract without reading or mutating data."""

    contract_path = Path(path).expanduser().resolve()
    try:
        raw = contract_path.read_bytes()
        parsed = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise TwinSplitContractError("Twin split contract is not valid UTF-8 JSON") from exc
    if not isinstance(parsed, Mapping):
        raise TwinSplitContractError("Twin split contract must be a JSON object")
    payload = dict(parsed)
    contract_digest = _text(payload, "contract_digest")
    unsigned = dict(payload)
    del unsigned["contract_digest"]
    if canonical_digest(unsigned) != contract_digest:
        raise TwinSplitContractError("Twin split contract digest does not match content")
    _validate(payload)
    return TwinSplitContract(payload, contract_digest, sha256(raw).hexdigest())


def _validate(value: Mapping[str, object]) -> None:
    required = {
        "schema_version",
        "task_id",
        "contract_id",
        "frozen_at_utc",
        "scope",
        "data_availability",
        "split_rationale",
        "splits",
        "leakage_checks",
        "protocol",
        "claim_boundary",
        "contract_digest",
    }
    if set(value) != required:
        raise TwinSplitContractError("Twin split contract fields mismatch")
    if _text(value, "schema_version") != _SCHEMA or _text(value, "task_id") != "R3-330":
        raise TwinSplitContractError("Twin split contract identity is unsupported")
    if _text(value, "claim_boundary") != _CLAIM_BOUNDARY:
        raise TwinSplitContractError("Twin split claim boundary is missing")
    availability = _mapping(value, "data_availability")
    _exact(
        availability,
        {
            "status",
            "observed_record_count",
            "required_minimum_records",
            "reason",
            "unlock_condition",
        },
        "data_availability",
    )
    if _text(availability, "status") != "INSUFFICIENT_DATA":
        raise TwinSplitContractError("R3-330 fixture must explicitly report INSUFFICIENT_DATA")
    if _integer(availability, "observed_record_count") != 0:
        raise TwinSplitContractError("unavailable observed data must have record count zero")
    if _integer(availability, "required_minimum_records") <= 0:
        raise TwinSplitContractError("required minimum record count must be positive")
    _require_text(availability, "reason")
    _require_text(availability, "unlock_condition")
    _validate_rationale(_mapping(value, "split_rationale"))
    _validate_splits(_mapping(value, "splits"))
    _validate_leakage(_sequence(value, "leakage_checks"))
    protocol = _mapping(value, "protocol")
    _exact(
        protocol,
        {
            "calibration_use",
            "held_out_use",
            "fit_may_read_held_out",
            "validation_requires_observed_outcomes",
        },
        "protocol",
    )
    if _bool(protocol, "fit_may_read_held_out"):
        raise TwinSplitContractError("calibration fit must not read held-out data")
    if not _bool(protocol, "validation_requires_observed_outcomes"):
        raise TwinSplitContractError("validation must require observed outcomes")
    _require_text(protocol, "calibration_use")
    _require_text(protocol, "held_out_use")


def _validate_rationale(value: Mapping[str, object]) -> None:
    _exact(value, {"primary_axis", "secondary_axis", "ordering", "reason"}, "split_rationale")
    if _text(value, "primary_axis") not in {"temporal", "scenario", "geographic"}:
        raise TwinSplitContractError("split primary axis is unsupported")
    if _text(value, "secondary_axis") not in {"temporal", "scenario", "geographic"}:
        raise TwinSplitContractError("split secondary axis is unsupported")
    if _text(value, "primary_axis") == _text(value, "secondary_axis"):
        raise TwinSplitContractError("split axes must be distinct")
    for key in ("ordering", "reason"):
        _require_text(value, key)


def _validate_splits(value: Mapping[str, object]) -> None:
    if set(value) != set(_SPLITS):
        raise TwinSplitContractError("calibration and held_out split identities are required")
    normalized: dict[str, Mapping[str, object]] = {}
    for name in _SPLITS:
        split = _mapping(value, name)
        _exact(
            split,
            {
                "split_id",
                "selection",
                "partition_key",
                "artifact_status",
                "artifact_sha256",
                "record_count",
                "identity_digest",
            },
            name,
        )
        _require_text(split, "split_id")
        for key in ("selection", "partition_key"):
            _require_text(split, key)
        status = _text(split, "artifact_status")
        checksum = split.get("artifact_sha256")
        if status == "UNAVAILABLE_NO_OBSERVED_DATA":
            if checksum is not None or _integer(split, "record_count") != 0:
                raise TwinSplitContractError("unavailable split cannot claim records or a checksum")
        elif status == "AVAILABLE":
            if (
                not isinstance(checksum, str)
                or not _SHA256.fullmatch(checksum)
                or _integer(split, "record_count") <= 0
            ):
                raise TwinSplitContractError("available split requires records and SHA-256")
        else:
            raise TwinSplitContractError("split artifact status is unsupported")
        identity = _text(split, "identity_digest")
        if not _SHA256.fullmatch(identity):
            raise TwinSplitContractError("split identity digest must be SHA-256")
        unsigned = dict(split)
        del unsigned["identity_digest"]
        if canonical_digest(unsigned) != identity:
            raise TwinSplitContractError(f"{name} split identity digest does not match")
        normalized[name] = split
    if _text(normalized["calibration"], "split_id") == _text(normalized["held_out"], "split_id"):
        raise TwinSplitContractError("calibration and held-out identities must be disjoint")
    checksums = [split.get("artifact_sha256") for split in normalized.values()]
    if checksums[0] is not None and checksums[0] == checksums[1]:
        raise TwinSplitContractError("calibration and held-out artifacts must not share a checksum")


def _validate_leakage(value: Sequence[object]) -> None:
    if len(value) != len(_LEAKAGE_CHECKS):
        raise TwinSplitContractError("all five leakage checks are required")
    seen: set[str] = set()
    for item in value:
        check = _mapping_value(item, "leakage check")
        _exact(check, {"check_id", "method", "expected", "status"}, "leakage check")
        check_id = _text(check, "check_id")
        if check_id in seen or check_id not in _LEAKAGE_CHECKS:
            raise TwinSplitContractError("leakage check identities are invalid")
        seen.add(check_id)
        for key in ("method", "expected", "status"):
            _require_text(check, key)
        if _text(check, "status") != "NOT_RUN_NO_DATA":
            raise TwinSplitContractError("no-data leakage checks must remain NOT_RUN_NO_DATA")


def _exact(value: Mapping[str, object], allowed: set[str], label: str) -> None:
    if set(value) != allowed:
        raise TwinSplitContractError(f"{label} fields mismatch")


def _mapping(value: Mapping[str, object], key: str) -> Mapping[str, object]:
    return _mapping_value(value.get(key), key)


def _mapping_value(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise TwinSplitContractError(f"{label} must be an object")
    return value


def _sequence(value: Mapping[str, object], key: str) -> Sequence[object]:
    selected = value.get(key)
    if not isinstance(selected, Sequence) or isinstance(selected, (str, bytes, bytearray)):
        raise TwinSplitContractError(f"{key} must be an array")
    return selected


def _text(value: Mapping[str, object], key: str) -> str:
    selected = value.get(key)
    if not isinstance(selected, str) or not selected.strip() or len(selected) > 1024:
        raise TwinSplitContractError(f"{key} must be non-empty text")
    return selected


def _require_text(value: Mapping[str, object], key: str) -> None:
    _text(value, key)


def _integer(value: Mapping[str, object], key: str) -> int:
    selected = value.get(key)
    if isinstance(selected, bool) or not isinstance(selected, int):
        raise TwinSplitContractError(f"{key} must be an integer")
    return selected


def _bool(value: Mapping[str, object], key: str) -> bool:
    selected = value.get(key)
    if not isinstance(selected, bool):
        raise TwinSplitContractError(f"{key} must be boolean")
    return selected


__all__ = ["TwinSplitContract", "TwinSplitContractError", "load_twin_split_contract"]
