"""Bounded, manifest-bound Digital Twin calibration execution for R3-331."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256
from math import isfinite
from pathlib import Path
from typing import Literal

from routemind_compute.application.execution import canonical_digest
from routemind_compute.application.twin_fidelity_protocol import (
    TwinFidelityProtocol,
)
from routemind_compute.application.twin_split_contract import TwinSplitContract

_SCHEMA = "routemind-twin-calibration-v1"
_CLAIM_BOUNDARY = "CALIBRATION_FIT_DOES_NOT_ESTABLISH_TWIN_VALIDITY"
_TARGET_IDS = (
    "assignment_rate",
    "scenario_risk_index",
    "dispatch_latency_seconds",
    "fallback_rate",
)
_PARAMETER_NAMES = (
    "assignment_bias",
    "risk_scale",
    "latency_bias_seconds",
    "fallback_bias",
)
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_STATUS = Literal["INSUFFICIENT_DATA"]


class TwinCalibrationError(ValueError):
    """Raised when a bounded calibration plan or lineage is unsafe."""


@dataclass(frozen=True, slots=True)
class TwinCalibrationPlan:
    payload: Mapping[str, object]
    plan_digest: str
    manifest_sha256: str

    @property
    def plan_id(self) -> str:
        return _text(self.payload, "plan_id")

    @property
    def target_ids(self) -> tuple[str, ...]:
        return tuple(
            _text(_mapping_value(item, "target"), "target_id")
            for item in _sequence(self.payload, "targets")
        )


@dataclass(frozen=True, slots=True)
class TwinCalibrationOutcome:
    status: _STATUS
    plan_digest: str
    split_contract_digest: str
    fidelity_protocol_digest: str
    calibration_record_count: int
    held_out_record_count: int
    missing_targets: tuple[str, ...]
    parameter_before_sha256: str | None
    parameter_after_sha256: str | None
    artifact_sha256: str | None
    reason: str
    claim_boundary: str = _CLAIM_BOUNDARY


def load_twin_calibration_plan(path: Path | str) -> TwinCalibrationPlan:
    """Load a content-addressed calibration plan without reading data."""

    plan_path = Path(path).expanduser().resolve()
    try:
        raw = plan_path.read_bytes()
        parsed = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise TwinCalibrationError("Twin calibration plan is not valid UTF-8 JSON") from exc
    if not isinstance(parsed, Mapping):
        raise TwinCalibrationError("Twin calibration plan must be a JSON object")
    payload = dict(parsed)
    plan_digest = _text(payload, "plan_digest")
    unsigned = dict(payload)
    del unsigned["plan_digest"]
    if canonical_digest(unsigned) != plan_digest:
        raise TwinCalibrationError("Twin calibration plan digest does not match content")
    _validate(payload)
    return TwinCalibrationPlan(payload, plan_digest, sha256(raw).hexdigest())


def execute_bounded_twin_calibration(
    plan: TwinCalibrationPlan,
    split_contract: TwinSplitContract,
    fidelity_protocol: TwinFidelityProtocol,
) -> TwinCalibrationOutcome:
    """Execute only the no-data-safe calibration branch for the current corpus.

    The function deliberately refuses to infer parameters from manifest counts. A
    future data-backed implementation must supply a new, reviewed execution
    path and retain this lineage contract.
    """

    _validate_lineage(plan, split_contract, fidelity_protocol)
    split_values = _mapping(split_contract.payload, "splits")
    calibration = _mapping(split_values, "calibration")
    held_out = _mapping(split_values, "held_out")
    calibration_count = _integer(calibration, "record_count")
    held_out_count = _integer(held_out, "record_count")
    unavailable = (
        split_contract.data_status == "INSUFFICIENT_DATA"
        and _text(calibration, "artifact_status") == "UNAVAILABLE_NO_OBSERVED_DATA"
        and calibration_count == 0
    )
    if unavailable:
        missing = tuple(plan.target_ids)
        return TwinCalibrationOutcome(
            status="INSUFFICIENT_DATA",
            plan_digest=plan.plan_digest,
            split_contract_digest=split_contract.contract_digest,
            fidelity_protocol_digest=fidelity_protocol.protocol_digest,
            calibration_record_count=calibration_count,
            held_out_record_count=held_out_count,
            missing_targets=missing,
            parameter_before_sha256=None,
            parameter_after_sha256=None,
            artifact_sha256=None,
            reason=_text(_mapping(split_contract.payload, "data_availability"), "reason"),
        )
    raise TwinCalibrationError(
        "calibration records are required; manifest counts cannot produce a fit"
    )


def _validate_lineage(
    plan: TwinCalibrationPlan,
    split_contract: TwinSplitContract,
    fidelity_protocol: TwinFidelityProtocol,
) -> None:
    data_policy = _mapping(plan.payload, "data_policy")
    calibration_id, held_out_id = split_contract.split_ids
    if _text(data_policy, "calibration_split_id") != calibration_id:
        raise TwinCalibrationError("calibration split identity does not match plan")
    if _text(data_policy, "held_out_split_id") != held_out_id:
        raise TwinCalibrationError("held-out split identity does not match plan")
    if _bool(data_policy, "fit_may_read_held_out"):
        raise TwinCalibrationError("calibration plan permits held-out reads")
    if fidelity_protocol.metrics and tuple(
        metric.metric_id for metric in fidelity_protocol.metrics
    ) != (plan.target_ids):
        raise TwinCalibrationError("calibration targets drift from fidelity protocol")
    if split_contract.data_status != "INSUFFICIENT_DATA":
        raise TwinCalibrationError("calibration runner only supports the declared no-data branch")
    if _text(split_contract.payload, "claim_boundary") != (
        "TWIN_FIDELITY_NOT_ESTABLISHED_WITHOUT_HELD_OUT_OBSERVATIONS"
    ):
        raise TwinCalibrationError("split claim boundary is missing")


def _validate(value: Mapping[str, object]) -> None:
    required = {
        "schema_version",
        "task_id",
        "plan_id",
        "frozen_at_utc",
        "question",
        "targets",
        "objective",
        "parameter_bounds",
        "search",
        "initialization",
        "regularization",
        "data_policy",
        "artifact_policy",
        "missing_data_policy",
        "claim_boundary",
        "plan_digest",
    }
    if set(value) != required:
        raise TwinCalibrationError("Twin calibration plan fields mismatch")
    if _text(value, "schema_version") != _SCHEMA or _text(value, "task_id") != "R3-331":
        raise TwinCalibrationError("Twin calibration plan identity is unsupported")
    if _text(value, "claim_boundary") != _CLAIM_BOUNDARY:
        raise TwinCalibrationError("Twin calibration claim boundary is missing")
    _text(value, "question")
    _validate_targets(_sequence(value, "targets"))
    _validate_objective(_mapping(value, "objective"))
    _validate_bounds(_mapping(value, "parameter_bounds"))
    _validate_search(_mapping(value, "search"))
    _validate_initialization(_mapping(value, "initialization"), _mapping(value, "parameter_bounds"))
    _validate_regularization(_mapping(value, "regularization"))
    _validate_data_policy(_mapping(value, "data_policy"))
    _validate_artifact_policy(_mapping(value, "artifact_policy"))
    _validate_missing_data_policy(_mapping(value, "missing_data_policy"))


def _validate_targets(value: Sequence[object]) -> None:
    if len(value) != len(_TARGET_IDS):
        raise TwinCalibrationError("exactly four calibration targets are required")
    parsed: list[str] = []
    for item in value:
        target = _mapping_value(item, "target")
        _exact(target, {"target_id", "source_variable", "parameter_names"}, "target")
        target_id = _text(target, "target_id")
        parsed.append(target_id)
        _text(target, "source_variable")
        names = _sequence(target, "parameter_names")
        if not names or any(not isinstance(name, str) or not name.strip() for name in names):
            raise TwinCalibrationError("target parameter names must be non-empty text")
    if tuple(parsed) != _TARGET_IDS:
        raise TwinCalibrationError("calibration target identity/order is not frozen")


def _validate_objective(value: Mapping[str, object]) -> None:
    _exact(value, {"name", "metric_ids", "loss", "lower_is_better"}, "objective")
    if _text(value, "name") != "weighted_mean_absolute_error_on_calibration_split":
        raise TwinCalibrationError("calibration objective is unsupported")
    if tuple(
        _text_mapping(item, "objective metric") for item in _sequence(value, "metric_ids")
    ) != (_TARGET_IDS):
        raise TwinCalibrationError("calibration objective metrics drift")
    if _text(value, "loss") != "mean_absolute_error" or not _bool(value, "lower_is_better"):
        raise TwinCalibrationError("calibration objective must minimize absolute error")


def _validate_bounds(value: Mapping[str, object]) -> None:
    if set(value) != set(_PARAMETER_NAMES):
        raise TwinCalibrationError("all bounded calibration parameters are required")
    for name in _PARAMETER_NAMES:
        bounds = _sequence(value, name)
        lower, upper = _finite_pair(bounds)
        if lower >= upper:
            raise TwinCalibrationError("parameter bounds must be ordered")


def _validate_search(value: Mapping[str, object]) -> None:
    _exact(value, {"method", "seed", "max_iterations", "tolerance", "max_no_improvement"}, "search")
    if _text(value, "method") != "bounded_coordinate_descent":
        raise TwinCalibrationError("calibration search method is unsupported")
    _positive_integer(value, "seed")
    _positive_integer(value, "max_iterations")
    _positive_integer(value, "max_no_improvement")
    _positive_number(value, "tolerance")


def _validate_initialization(value: Mapping[str, object], bounds: Mapping[str, object]) -> None:
    _exact(value, {"method", "parameters"}, "initialization")
    if _text(value, "method") != "frozen_baseline_parameters":
        raise TwinCalibrationError("calibration initialization is unsupported")
    parameters = _mapping(value, "parameters")
    if set(parameters) != set(_PARAMETER_NAMES):
        raise TwinCalibrationError("initialization parameters drift")
    for name in _PARAMETER_NAMES:
        selected = _number(parameters, name)
        lower, upper = _finite_pair(_sequence(bounds, name))
        if not lower <= selected <= upper:
            raise TwinCalibrationError("initialization must lie within parameter bounds")


def _validate_regularization(value: Mapping[str, object]) -> None:
    _exact(value, {"method", "lambda"}, "regularization")
    if _text(value, "method") != "l2" or _number(value, "lambda") < 0:
        raise TwinCalibrationError("regularization must be non-negative L2")


def _validate_data_policy(value: Mapping[str, object]) -> None:
    _exact(
        value,
        {
            "calibration_split_id",
            "held_out_split_id",
            "fit_may_read_held_out",
            "calibration_data_required",
        },
        "data_policy",
    )
    calibration_id = _text(value, "calibration_split_id")
    held_out_id = _text(value, "held_out_split_id")
    if calibration_id == held_out_id:
        raise TwinCalibrationError("calibration and held-out split IDs must be distinct")
    if _bool(value, "fit_may_read_held_out") or not _bool(value, "calibration_data_required"):
        raise TwinCalibrationError("calibration data policy permits unsafe reads")


def _validate_artifact_policy(value: Mapping[str, object]) -> None:
    _exact(
        value,
        {
            "checksum_algorithm",
            "before_parameters_required",
            "after_parameters_required",
            "artifact_required",
        },
        "artifact_policy",
    )
    if _text(value, "checksum_algorithm") != "sha256":
        raise TwinCalibrationError("calibration artifacts require SHA-256")
    for key in ("before_parameters_required", "after_parameters_required", "artifact_required"):
        if not _bool(value, key):
            raise TwinCalibrationError("calibration artifact checksums are mandatory")


def _validate_missing_data_policy(value: Mapping[str, object]) -> None:
    _exact(value, {"status", "reason", "no_fit_performed"}, "missing_data_policy")
    if _text(value, "status") != "INSUFFICIENT_DATA" or not _bool(value, "no_fit_performed"):
        raise TwinCalibrationError("missing data must produce a no-fit INSUFFICIENT_DATA outcome")
    _text(value, "reason")


def _exact(value: Mapping[str, object], allowed: set[str], label: str) -> None:
    if set(value) != allowed:
        raise TwinCalibrationError(f"{label} fields mismatch")


def _mapping(value: Mapping[str, object], key: str) -> Mapping[str, object]:
    return _mapping_value(value.get(key), key)


def _mapping_value(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise TwinCalibrationError(f"{label} must be an object")
    return value


def _sequence(value: Mapping[str, object], key: str) -> Sequence[object]:
    selected = value.get(key)
    if not isinstance(selected, Sequence) or isinstance(selected, (str, bytes, bytearray)):
        raise TwinCalibrationError(f"{key} must be an array")
    return selected


def _text(value: Mapping[str, object], key: str) -> str:
    selected = value.get(key)
    if not isinstance(selected, str) or not selected.strip() or len(selected) > 1024:
        raise TwinCalibrationError(f"{key} must be non-empty text")
    return selected


def _text_mapping(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TwinCalibrationError(f"{label} must be non-empty text")
    return value


def _integer(value: Mapping[str, object], key: str) -> int:
    selected = value.get(key)
    if isinstance(selected, bool) or not isinstance(selected, int):
        raise TwinCalibrationError(f"{key} must be an integer")
    return selected


def _positive_integer(value: Mapping[str, object], key: str) -> int:
    selected = _integer(value, key)
    if selected <= 0:
        raise TwinCalibrationError(f"{key} must be positive")
    return selected


def _number(value: Mapping[str, object], key: str) -> float:
    selected = value.get(key)
    if (
        isinstance(selected, bool)
        or not isinstance(selected, (int, float))
        or not isfinite(float(selected))
    ):
        raise TwinCalibrationError(f"{key} must be a finite number")
    return float(selected)


def _positive_number(value: Mapping[str, object], key: str) -> float:
    selected = _number(value, key)
    if selected <= 0:
        raise TwinCalibrationError(f"{key} must be positive")
    return selected


def _finite_pair(value: Sequence[object]) -> tuple[float, float]:
    if len(value) != 2:
        raise TwinCalibrationError("parameter bounds must contain two finite numbers")
    first, second = value
    if (
        isinstance(first, bool)
        or not isinstance(first, (int, float))
        or not isfinite(float(first))
        or isinstance(second, bool)
        or not isinstance(second, (int, float))
        or not isfinite(float(second))
    ):
        raise TwinCalibrationError("parameter bounds must contain two finite numbers")
    return float(first), float(second)


def _bool(value: Mapping[str, object], key: str) -> bool:
    selected = value.get(key)
    if not isinstance(selected, bool):
        raise TwinCalibrationError(f"{key} must be boolean")
    return selected


__all__ = [
    "TwinCalibrationError",
    "TwinCalibrationOutcome",
    "TwinCalibrationPlan",
    "execute_bounded_twin_calibration",
    "load_twin_calibration_plan",
]
