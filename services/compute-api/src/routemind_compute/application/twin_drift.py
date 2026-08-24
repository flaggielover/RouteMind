"""Regime-separated Digital Twin drift reporting for R3-334."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Literal

from routemind_compute.application.execution import canonical_digest
from routemind_compute.application.twin_held_out_validation import (
    TwinHeldOutValidationOutcome,
)
from routemind_compute.application.twin_split_contract import TwinSplitContract

_SCHEMA = "routemind-twin-drift-report-v1"
_CLAIM_BOUNDARY = "DRIFT_REPORT_DOES_NOT_ESTABLISH_STABILITY_OR_EXTERNAL_VALIDITY"
_AXES = ("time", "zone", "demand", "traffic")
_STATUS = Literal["INSUFFICIENT_DATA"]


class TwinDriftError(ValueError):
    """Raised when the frozen drift report plan or lineage is unsafe."""


@dataclass(frozen=True, slots=True)
class TwinDriftPlan:
    payload: Mapping[str, object]
    plan_digest: str
    manifest_sha256: str

    @property
    def drift_id(self) -> str:
        return _text(self.payload, "drift_id")


@dataclass(frozen=True, slots=True)
class DriftRegimeResult:
    axis: str
    status: str
    record_count: int
    parameter_drift_status: str
    fidelity_degradation_status: str


@dataclass(frozen=True, slots=True)
class TwinDriftOutcome:
    status: _STATUS
    plan_digest: str
    split_contract_digest: str
    validation_plan_digest: str
    parameter_drift_status: str
    fidelity_degradation_status: str
    regimes: tuple[DriftRegimeResult, ...]
    reason: str
    claim_boundary: str = _CLAIM_BOUNDARY


def load_twin_drift_plan(path: Path | str) -> TwinDriftPlan:
    """Load a content-addressed drift plan without reading observed records."""

    plan_path = Path(path).expanduser().resolve()
    try:
        raw = plan_path.read_bytes()
        parsed = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise TwinDriftError("Twin drift plan is not valid UTF-8 JSON") from exc
    if not isinstance(parsed, Mapping):
        raise TwinDriftError("Twin drift plan must be a JSON object")
    payload = dict(parsed)
    plan_digest = _text(payload, "plan_digest")
    unsigned = dict(payload)
    del unsigned["plan_digest"]
    if canonical_digest(unsigned) != plan_digest:
        raise TwinDriftError("Twin drift plan digest does not match content")
    _validate(payload)
    return TwinDriftPlan(payload, plan_digest, sha256(raw).hexdigest())


def execute_twin_drift_report(
    plan: TwinDriftPlan,
    split_contract: TwinSplitContract,
    validation_outcome: TwinHeldOutValidationOutcome,
) -> TwinDriftOutcome:
    """Separate parameter/fidelity drift and return no-data results when unsupported."""

    _validate_lineage(plan, split_contract, validation_outcome)
    split_values = _mapping(split_contract.payload, "splits")
    calibration = _mapping(split_values, "calibration")
    held_out = _mapping(split_values, "held_out")
    calibration_count = _integer(calibration, "record_count")
    held_out_count = _integer(held_out, "record_count")
    if (
        calibration_count == 0
        and held_out_count == 0
        and _text(calibration, "artifact_status") == "UNAVAILABLE_NO_OBSERVED_DATA"
        and _text(held_out, "artifact_status") == "UNAVAILABLE_NO_OBSERVED_DATA"
    ):
        regimes = tuple(
            DriftRegimeResult(
                axis, "NOT_ANALYZED_NO_DATA", 0, "NOT_ANALYZED_NO_DATA", "NOT_ANALYZED_NO_DATA"
            )
            for axis in _AXES
        )
        reason = _text(_mapping(plan.payload, "data_policy"), "reason")
        return TwinDriftOutcome(
            status="INSUFFICIENT_DATA",
            plan_digest=plan.plan_digest,
            split_contract_digest=split_contract.contract_digest,
            validation_plan_digest=validation_outcome.plan_digest,
            parameter_drift_status="NOT_ANALYZED_NO_DATA",
            fidelity_degradation_status="NOT_ANALYZED_NO_DATA",
            regimes=regimes,
            reason=reason,
        )
    raise TwinDriftError("drift records are required; manifest counts cannot produce a report")


def _validate_lineage(
    plan: TwinDriftPlan,
    split_contract: TwinSplitContract,
    validation_outcome: TwinHeldOutValidationOutcome,
) -> None:
    if _text(plan.payload, "split_contract_digest") != split_contract.contract_digest:
        raise TwinDriftError("split contract digest does not match drift plan")
    if _text(plan.payload, "source_validation_plan_digest") != validation_outcome.plan_digest:
        raise TwinDriftError("validation plan digest does not match drift plan")
    if validation_outcome.outcome != "INSUFFICIENT_DATA":
        raise TwinDriftError("drift report requires an explicit held-out outcome")
    data_policy = _mapping(plan.payload, "data_policy")
    calibration_id, held_out_id = split_contract.split_ids
    if _text(data_policy, "calibration_split_id") != calibration_id:
        raise TwinDriftError("calibration split identity does not match drift plan")
    if _text(data_policy, "held_out_split_id") != held_out_id:
        raise TwinDriftError("held-out split identity does not match drift plan")
    if not _bool(data_policy, "no_synthetic_data") or _bool(
        data_policy, "recalibration_is_solution"
    ):
        raise TwinDriftError(
            "drift policy permits synthetic data or solved auto-calibration wording"
        )


def _validate(value: Mapping[str, object]) -> None:
    required = {
        "schema_version",
        "task_id",
        "drift_id",
        "frozen_at_utc",
        "question",
        "source_validation_plan_digest",
        "split_contract_digest",
        "regime_axes",
        "parameter_drift_policy",
        "fidelity_degradation_policy",
        "data_policy",
        "claim_boundary",
        "plan_digest",
    }
    if set(value) != required:
        raise TwinDriftError("Twin drift plan fields mismatch")
    if _text(value, "schema_version") != _SCHEMA or _text(value, "task_id") != "R3-334":
        raise TwinDriftError("Twin drift plan identity is unsupported")
    if _text(value, "claim_boundary") != _CLAIM_BOUNDARY:
        raise TwinDriftError("Twin drift claim boundary is missing")
    _text(value, "question")
    _digest(value, "source_validation_plan_digest")
    _digest(value, "split_contract_digest")
    axes = tuple(_text_mapping(item, "regime axis") for item in _sequence(value, "regime_axes"))
    if axes != _AXES:
        raise TwinDriftError("drift regime axes/order are not frozen")
    _validate_parameter_policy(_mapping(value, "parameter_drift_policy"))
    _validate_fidelity_policy(_mapping(value, "fidelity_degradation_policy"))
    _validate_data_policy(_mapping(value, "data_policy"))


def _validate_parameter_policy(value: Mapping[str, object]) -> None:
    _exact(
        value,
        {"metrics", "require_before_after_checksums", "missing_status"},
        "parameter_drift_policy",
    )
    metrics = tuple(_text_mapping(item, "parameter metric") for item in _sequence(value, "metrics"))
    if metrics != ("parameter_l1_delta", "parameter_relative_delta"):
        raise TwinDriftError("parameter drift metrics are not frozen")
    if not _bool(value, "require_before_after_checksums"):
        raise TwinDriftError("parameter drift requires before/after checksums")
    if _text(value, "missing_status") != "NOT_ANALYZED_NO_DATA":
        raise TwinDriftError("missing parameter drift must remain explicit")


def _validate_fidelity_policy(value: Mapping[str, object]) -> None:
    _exact(value, {"metrics", "baseline", "missing_status"}, "fidelity_degradation_policy")
    metrics = tuple(_text_mapping(item, "fidelity metric") for item in _sequence(value, "metrics"))
    if metrics != (
        "assignment_rate",
        "scenario_risk_index",
        "dispatch_latency_seconds",
        "fallback_rate",
    ):
        raise TwinDriftError("fidelity degradation metrics are not frozen")
    if _text(value, "baseline") != "R3-333_FROZEN_PROTOCOL":
        raise TwinDriftError("fidelity degradation baseline is unsupported")
    if _text(value, "missing_status") != "NOT_ANALYZED_NO_DATA":
        raise TwinDriftError("missing fidelity degradation must remain explicit")


def _validate_data_policy(value: Mapping[str, object]) -> None:
    _exact(
        value,
        {
            "calibration_split_id",
            "held_out_split_id",
            "no_synthetic_data",
            "recalibration_is_solution",
            "reason",
        },
        "data_policy",
    )
    calibration_id = _text(value, "calibration_split_id")
    held_out_id = _text(value, "held_out_split_id")
    if calibration_id == held_out_id:
        raise TwinDriftError("calibration and held-out split IDs must be distinct")
    if not _bool(value, "no_synthetic_data") or _bool(value, "recalibration_is_solution"):
        raise TwinDriftError("drift data policy permits unsafe claims")
    _text(value, "reason")


def _exact(value: Mapping[str, object], allowed: set[str], label: str) -> None:
    if set(value) != allowed:
        raise TwinDriftError(f"{label} fields mismatch")


def _mapping(value: Mapping[str, object], key: str) -> Mapping[str, object]:
    return _mapping_value(value.get(key), key)


def _mapping_value(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise TwinDriftError(f"{label} must be an object")
    return value


def _sequence(value: Mapping[str, object], key: str) -> Sequence[object]:
    selected = value.get(key)
    if not isinstance(selected, Sequence) or isinstance(selected, (str, bytes, bytearray)):
        raise TwinDriftError(f"{key} must be an array")
    return selected


def _text(value: Mapping[str, object], key: str) -> str:
    selected = value.get(key)
    if not isinstance(selected, str) or not selected.strip() or len(selected) > 1024:
        raise TwinDriftError(f"{key} must be non-empty text")
    return selected


def _text_mapping(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TwinDriftError(f"{label} must be non-empty text")
    return value


def _digest(value: Mapping[str, object], key: str) -> str:
    selected = _text(value, key)
    if len(selected) != 64 or any(char not in "0123456789abcdef" for char in selected):
        raise TwinDriftError(f"{key} must be a SHA-256 digest")
    return selected


def _integer(value: Mapping[str, object], key: str) -> int:
    selected = value.get(key)
    if isinstance(selected, bool) or not isinstance(selected, int):
        raise TwinDriftError(f"{key} must be an integer")
    return selected


def _bool(value: Mapping[str, object], key: str) -> bool:
    selected = value.get(key)
    if not isinstance(selected, bool):
        raise TwinDriftError(f"{key} must be boolean")
    return selected


__all__ = [
    "DriftRegimeResult",
    "TwinDriftError",
    "TwinDriftOutcome",
    "TwinDriftPlan",
    "execute_twin_drift_report",
    "load_twin_drift_plan",
]
