"""Read-only held-out Digital Twin validation gate for R3-332."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256
from math import isfinite
from pathlib import Path
from typing import Literal

from routemind_compute.application.execution import canonical_digest
from routemind_compute.application.twin_calibration import (
    TwinCalibrationOutcome,
    TwinCalibrationPlan,
)
from routemind_compute.application.twin_fidelity_protocol import (
    TwinFidelityProtocol,
    assess_fidelity_support,
)
from routemind_compute.application.twin_split_contract import TwinSplitContract

_SCHEMA = "routemind-twin-held-out-validation-v1"
_CLAIM_BOUNDARY = "HELD_OUT_VALIDATION_DOES_NOT_ESTABLISH_EXTERNAL_VALIDITY"
_METRIC_IDS = (
    "assignment_rate",
    "scenario_risk_index",
    "dispatch_latency_seconds",
    "fallback_rate",
)
_OUTCOMES = (
    "VALIDATED_FOR_SCOPE",
    "PARTIALLY_VALIDATED",
    "FAILED_VALIDATION",
    "INSUFFICIENT_DATA",
)
_STATUS = Literal[
    "VALIDATED_FOR_SCOPE", "PARTIALLY_VALIDATED", "FAILED_VALIDATION", "INSUFFICIENT_DATA"
]


class TwinHeldOutValidationError(ValueError):
    """Raised when held-out validation lineage or policy is unsafe."""


@dataclass(frozen=True, slots=True)
class TwinHeldOutValidationPlan:
    payload: Mapping[str, object]
    plan_digest: str
    manifest_sha256: str

    @property
    def validation_id(self) -> str:
        return _text(self.payload, "validation_id")


@dataclass(frozen=True, slots=True)
class HeldOutMetricResult:
    metric_id: str
    status: str
    estimate: float | None
    uncertainty: tuple[float, float] | None


@dataclass(frozen=True, slots=True)
class TwinHeldOutValidationOutcome:
    outcome: _STATUS
    plan_digest: str
    split_contract_digest: str
    fidelity_protocol_digest: str
    calibration_status: str
    held_out_record_count: int
    metrics: tuple[HeldOutMetricResult, ...]
    reason: str
    claim_boundary: str = _CLAIM_BOUNDARY


def load_twin_held_out_validation_plan(path: Path | str) -> TwinHeldOutValidationPlan:
    """Load a content-addressed, one-shot validation plan without reading data."""

    plan_path = Path(path).expanduser().resolve()
    try:
        raw = plan_path.read_bytes()
        parsed = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise TwinHeldOutValidationError(
            "Twin held-out validation plan is not valid UTF-8 JSON"
        ) from exc
    if not isinstance(parsed, Mapping):
        raise TwinHeldOutValidationError("Twin held-out validation plan must be a JSON object")
    payload = dict(parsed)
    plan_digest = _text(payload, "plan_digest")
    unsigned = dict(payload)
    del unsigned["plan_digest"]
    if canonical_digest(unsigned) != plan_digest:
        raise TwinHeldOutValidationError(
            "Twin held-out validation plan digest does not match content"
        )
    _validate(payload)
    return TwinHeldOutValidationPlan(payload, plan_digest, sha256(raw).hexdigest())


def execute_twin_held_out_validation(
    plan: TwinHeldOutValidationPlan,
    split_contract: TwinSplitContract,
    fidelity_protocol: TwinFidelityProtocol,
    calibration_plan: TwinCalibrationPlan,
    calibration_outcome: TwinCalibrationOutcome,
) -> TwinHeldOutValidationOutcome:
    """Evaluate held-out support once; never retune or estimate without records."""

    _validate_lineage(
        plan, split_contract, fidelity_protocol, calibration_plan, calibration_outcome
    )
    split_values = _mapping(split_contract.payload, "splits")
    held_out = _mapping(split_values, "held_out")
    held_out_count = _integer(held_out, "record_count")
    support = assess_fidelity_support(fidelity_protocol, {})
    unavailable = (
        support.status == "INSUFFICIENT_DATA"
        and _text(held_out, "artifact_status") == "UNAVAILABLE_NO_OBSERVED_DATA"
        and held_out_count == 0
    )
    if unavailable:
        return TwinHeldOutValidationOutcome(
            outcome="INSUFFICIENT_DATA",
            plan_digest=plan.plan_digest,
            split_contract_digest=split_contract.contract_digest,
            fidelity_protocol_digest=fidelity_protocol.protocol_digest,
            calibration_status=calibration_outcome.status,
            held_out_record_count=held_out_count,
            metrics=tuple(
                HeldOutMetricResult(metric_id, "NOT_REPORTED_NO_DATA", None, None)
                for metric_id in _METRIC_IDS
            ),
            reason=_text(_mapping(plan.payload, "outcome_policy"), "reason"),
        )
    raise TwinHeldOutValidationError(
        "held-out records are required; validation cannot estimate from manifest counts"
    )


def _validate_lineage(
    plan: TwinHeldOutValidationPlan,
    split_contract: TwinSplitContract,
    fidelity_protocol: TwinFidelityProtocol,
    calibration_plan: TwinCalibrationPlan,
    calibration_outcome: TwinCalibrationOutcome,
) -> None:
    if _text(plan.payload, "source_calibration_plan_digest") != calibration_plan.plan_digest:
        raise TwinHeldOutValidationError("calibration plan digest does not match validation plan")
    if calibration_outcome.plan_digest != calibration_plan.plan_digest:
        raise TwinHeldOutValidationError("calibration outcome lineage does not match plan")
    if calibration_outcome.status != "INSUFFICIENT_DATA":
        raise TwinHeldOutValidationError("validation requires a frozen calibration outcome")
    if _text(plan.payload, "split_contract_digest") != split_contract.contract_digest:
        raise TwinHeldOutValidationError("split contract digest does not match validation plan")
    if _text(plan.payload, "fidelity_protocol_digest") != fidelity_protocol.protocol_digest:
        raise TwinHeldOutValidationError("fidelity protocol digest does not match validation plan")
    if split_contract.data_status != "INSUFFICIENT_DATA":
        raise TwinHeldOutValidationError("held-out records are required for validation")
    data_policy = _mapping(plan.payload, "data_policy")
    calibration_id, held_out_id = split_contract.split_ids
    if _text(data_policy, "calibration_split_id") != calibration_id:
        raise TwinHeldOutValidationError(
            "calibration split identity does not match validation plan"
        )
    if _text(data_policy, "held_out_split_id") != held_out_id:
        raise TwinHeldOutValidationError("held-out split identity does not match validation plan")
    if not _bool(data_policy, "held_out_read_only") or _bool(data_policy, "retune_on_held_out"):
        raise TwinHeldOutValidationError("held-out validation policy permits unsafe retuning")
    if tuple(metric.metric_id for metric in fidelity_protocol.metrics) != _METRIC_IDS:
        raise TwinHeldOutValidationError("fidelity metric identity/order drifted")


def _validate(value: Mapping[str, object]) -> None:
    required = {
        "schema_version",
        "task_id",
        "validation_id",
        "frozen_at_utc",
        "question",
        "source_calibration_plan_digest",
        "split_contract_digest",
        "fidelity_protocol_digest",
        "metric_ids",
        "uncertainty_policy",
        "data_policy",
        "outcome_policy",
        "claim_boundary",
        "plan_digest",
    }
    if set(value) != required:
        raise TwinHeldOutValidationError("Twin held-out validation plan fields mismatch")
    if _text(value, "schema_version") != _SCHEMA or _text(value, "task_id") != "R3-332":
        raise TwinHeldOutValidationError("Twin held-out validation plan identity is unsupported")
    if _text(value, "claim_boundary") != _CLAIM_BOUNDARY:
        raise TwinHeldOutValidationError("held-out validation claim boundary is missing")
    _text(value, "question")
    for key in (
        "source_calibration_plan_digest",
        "split_contract_digest",
        "fidelity_protocol_digest",
    ):
        _digest(value, key)
    metric_ids = tuple(_text_mapping(item, "metric id") for item in _sequence(value, "metric_ids"))
    if metric_ids != _METRIC_IDS:
        raise TwinHeldOutValidationError("held-out metric identity/order is not frozen")
    _validate_uncertainty(_mapping(value, "uncertainty_policy"))
    _validate_data_policy(_mapping(value, "data_policy"))
    _validate_outcome_policy(_mapping(value, "outcome_policy"))


def _validate_uncertainty(value: Mapping[str, object]) -> None:
    _exact(
        value,
        {"method", "confidence_level", "minimum_pairs", "report_when_missing"},
        "uncertainty_policy",
    )
    if _text(value, "method") != "paired_bootstrap_percentile_95":
        raise TwinHeldOutValidationError("held-out uncertainty method is unsupported")
    confidence = _number(value, "confidence_level")
    if confidence != 0.95:
        raise TwinHeldOutValidationError("held-out confidence level must remain 0.95")
    if _integer(value, "minimum_pairs") <= 0:
        raise TwinHeldOutValidationError("held-out minimum pairs must be positive")
    if _text(value, "report_when_missing") != "NOT_REPORTED_NO_DATA":
        raise TwinHeldOutValidationError("missing held-out uncertainty policy is unsupported")


def _validate_data_policy(value: Mapping[str, object]) -> None:
    _exact(
        value,
        {"calibration_split_id", "held_out_split_id", "held_out_read_only", "retune_on_held_out"},
        "data_policy",
    )
    calibration_id = _text(value, "calibration_split_id")
    held_out_id = _text(value, "held_out_split_id")
    if calibration_id == held_out_id:
        raise TwinHeldOutValidationError("calibration and held-out split IDs must be distinct")
    if not _bool(value, "held_out_read_only") or _bool(value, "retune_on_held_out"):
        raise TwinHeldOutValidationError("held-out policy permits retuning")


def _validate_outcome_policy(value: Mapping[str, object]) -> None:
    _exact(value, {"allowed_outcomes", "status_when_missing", "reason"}, "outcome_policy")
    outcomes = tuple(
        _text_mapping(item, "outcome") for item in _sequence(value, "allowed_outcomes")
    )
    if outcomes != _OUTCOMES:
        raise TwinHeldOutValidationError("held-out outcomes are not the frozen four-state policy")
    if _text(value, "status_when_missing") != "INSUFFICIENT_DATA":
        raise TwinHeldOutValidationError("missing held-out data must produce INSUFFICIENT_DATA")
    _text(value, "reason")


def _exact(value: Mapping[str, object], allowed: set[str], label: str) -> None:
    if set(value) != allowed:
        raise TwinHeldOutValidationError(f"{label} fields mismatch")


def _mapping(value: Mapping[str, object], key: str) -> Mapping[str, object]:
    return _mapping_value(value.get(key), key)


def _mapping_value(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise TwinHeldOutValidationError(f"{label} must be an object")
    return value


def _sequence(value: Mapping[str, object], key: str) -> Sequence[object]:
    selected = value.get(key)
    if not isinstance(selected, Sequence) or isinstance(selected, (str, bytes, bytearray)):
        raise TwinHeldOutValidationError(f"{key} must be an array")
    return selected


def _text(value: Mapping[str, object], key: str) -> str:
    selected = value.get(key)
    if not isinstance(selected, str) or not selected.strip() or len(selected) > 1024:
        raise TwinHeldOutValidationError(f"{key} must be non-empty text")
    return selected


def _text_mapping(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TwinHeldOutValidationError(f"{label} must be non-empty text")
    return value


def _digest(value: Mapping[str, object], key: str) -> str:
    selected = _text(value, key)
    if len(selected) != 64 or any(char not in "0123456789abcdef" for char in selected):
        raise TwinHeldOutValidationError(f"{key} must be a SHA-256 digest")
    return selected


def _integer(value: Mapping[str, object], key: str) -> int:
    selected = value.get(key)
    if isinstance(selected, bool) or not isinstance(selected, int):
        raise TwinHeldOutValidationError(f"{key} must be an integer")
    return selected


def _number(value: Mapping[str, object], key: str) -> float:
    selected = value.get(key)
    if (
        isinstance(selected, bool)
        or not isinstance(selected, (int, float))
        or not isfinite(float(selected))
    ):
        raise TwinHeldOutValidationError(f"{key} must be a finite number")
    return float(selected)


def _bool(value: Mapping[str, object], key: str) -> bool:
    selected = value.get(key)
    if not isinstance(selected, bool):
        raise TwinHeldOutValidationError(f"{key} must be boolean")
    return selected


__all__ = [
    "HeldOutMetricResult",
    "TwinHeldOutValidationError",
    "TwinHeldOutValidationOutcome",
    "TwinHeldOutValidationPlan",
    "execute_twin_held_out_validation",
    "load_twin_held_out_validation_plan",
]
