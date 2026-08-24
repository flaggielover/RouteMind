"""Preregistered Digital Twin fidelity metrics and support gates for R3-333."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256
from math import isfinite
from pathlib import Path
from typing import Literal

from routemind_compute.application.execution import canonical_digest

_SCHEMA = "routemind-twin-fidelity-protocol-v1"
_CLAIM_BOUNDARY = "FIDELITY_PROTOCOL_DOES_NOT_ESTABLISH_TWIN_VALIDITY"
_METRIC_IDS = (
    "assignment_rate",
    "scenario_risk_index",
    "dispatch_latency_seconds",
    "fallback_rate",
)
_STATUS = Literal["READY_FOR_VALIDATION", "INSUFFICIENT_DATA"]


class TwinFidelityProtocolError(ValueError):
    """Raised when a preregistered fidelity protocol is invalid."""


@dataclass(frozen=True, slots=True)
class TwinFidelityMetric:
    metric_id: str
    source_variable: str
    aggregation: str
    unit: str
    direction: str
    absolute_threshold: float
    minimum_calibration_records: int
    minimum_held_out_records: int
    improvement_test: str
    improvement_alpha: float
    improvement_effect: float


@dataclass(frozen=True, slots=True)
class TwinFidelityProtocol:
    payload: Mapping[str, object]
    protocol_digest: str
    manifest_sha256: str
    metrics: tuple[TwinFidelityMetric, ...]

    @property
    def protocol_id(self) -> str:
        return _text(self.payload, "protocol_id")


@dataclass(frozen=True, slots=True)
class FidelitySupportResult:
    status: _STATUS
    metric_counts: tuple[tuple[str, int], ...]
    missing_metrics: tuple[str, ...]
    claim_boundary: str = _CLAIM_BOUNDARY


def load_twin_fidelity_protocol(path: Path | str) -> TwinFidelityProtocol:
    """Load and validate the frozen metric protocol without evaluating outcomes."""

    protocol_path = Path(path).expanduser().resolve()
    try:
        raw = protocol_path.read_bytes()
        parsed = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise TwinFidelityProtocolError("Twin fidelity protocol is not valid UTF-8 JSON") from exc
    if not isinstance(parsed, Mapping):
        raise TwinFidelityProtocolError("Twin fidelity protocol must be a JSON object")
    payload = dict(parsed)
    protocol_digest = _text(payload, "protocol_digest")
    unsigned = dict(payload)
    del unsigned["protocol_digest"]
    if canonical_digest(unsigned) != protocol_digest:
        raise TwinFidelityProtocolError("Twin fidelity protocol digest does not match content")
    metrics = _validate(payload)
    return TwinFidelityProtocol(payload, protocol_digest, sha256(raw).hexdigest(), metrics)


def assess_fidelity_support(
    protocol: TwinFidelityProtocol, held_out_counts: Mapping[str, int]
) -> FidelitySupportResult:
    """Return support status; no metric or effect is computed here."""

    counts: list[tuple[str, int]] = []
    missing: list[str] = []
    for metric in protocol.metrics:
        count = held_out_counts.get(metric.metric_id, 0)
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise TwinFidelityProtocolError(f"held-out count is invalid: {metric.metric_id}")
        counts.append((metric.metric_id, count))
        if count < metric.minimum_held_out_records:
            missing.append(metric.metric_id)
    return FidelitySupportResult(
        "INSUFFICIENT_DATA" if missing else "READY_FOR_VALIDATION",
        tuple(counts),
        tuple(missing),
    )


def _validate(value: Mapping[str, object]) -> tuple[TwinFidelityMetric, ...]:
    required = {
        "schema_version",
        "task_id",
        "protocol_id",
        "frozen_at_utc",
        "question",
        "metrics",
        "support_policy",
        "improvement_policy",
        "claim_boundary",
        "protocol_digest",
    }
    if set(value) != required:
        raise TwinFidelityProtocolError("Twin fidelity protocol fields mismatch")
    if _text(value, "schema_version") != _SCHEMA or _text(value, "task_id") != "R3-333":
        raise TwinFidelityProtocolError("Twin fidelity protocol identity is unsupported")
    if _text(value, "claim_boundary") != _CLAIM_BOUNDARY:
        raise TwinFidelityProtocolError("Twin fidelity claim boundary is missing")
    _require_text(value, "question")
    support = _mapping(value, "support_policy")
    _exact(
        support,
        {"minimum_calibration_records", "minimum_held_out_records", "status_when_missing"},
        "support_policy",
    )
    if (
        _integer(support, "minimum_calibration_records") <= 0
        or _integer(support, "minimum_held_out_records") <= 0
    ):
        raise TwinFidelityProtocolError("minimum support counts must be positive")
    if _text(support, "status_when_missing") != "INSUFFICIENT_DATA":
        raise TwinFidelityProtocolError("missing support must produce INSUFFICIENT_DATA")
    improvement = _mapping(value, "improvement_policy")
    _exact(
        improvement,
        {"comparison", "confidence_level", "rule", "required_before_validation"},
        "improvement_policy",
    )
    if _text(improvement, "comparison") != "naive_uncalibrated_baseline":
        raise TwinFidelityProtocolError("improvement baseline is unsupported")
    confidence = _number(improvement, "confidence_level")
    if not 0 < confidence < 1:
        raise TwinFidelityProtocolError("improvement confidence must be between zero and one")
    if not _bool(improvement, "required_before_validation"):
        raise TwinFidelityProtocolError("improvement test must be fixed before validation")
    _require_text(improvement, "rule")
    metrics = _sequence(value, "metrics")
    if len(metrics) != len(_METRIC_IDS):
        raise TwinFidelityProtocolError("exactly four variable-appropriate metrics are required")
    parsed = tuple(_metric(_mapping_value(item, "metric"), support, confidence) for item in metrics)
    if tuple(metric.metric_id for metric in parsed) != _METRIC_IDS:
        raise TwinFidelityProtocolError("metric identity/order is not the frozen protocol")
    return parsed


def _metric(
    value: Mapping[str, object], support: Mapping[str, object], confidence: float
) -> TwinFidelityMetric:
    required = {
        "metric_id",
        "source_variable",
        "aggregation",
        "unit",
        "direction",
        "absolute_threshold",
        "minimum_calibration_records",
        "minimum_held_out_records",
        "improvement_test",
        "improvement_alpha",
        "improvement_effect",
    }
    if set(value) != required:
        raise TwinFidelityProtocolError("fidelity metric fields mismatch")
    metric_id = _text(value, "metric_id")
    if metric_id not in _METRIC_IDS:
        raise TwinFidelityProtocolError("fidelity metric identity is unsupported")
    for key in ("source_variable", "aggregation", "unit", "direction", "improvement_test"):
        _require_text(value, key)
    threshold = _number(value, "absolute_threshold")
    alpha = _number(value, "improvement_alpha")
    effect = _number(value, "improvement_effect")
    if threshold < 0 or not 0 < alpha < 1 or effect < 0:
        raise TwinFidelityProtocolError("fidelity metric thresholds are invalid")
    calibration = _integer(value, "minimum_calibration_records")
    held_out = _integer(value, "minimum_held_out_records")
    if calibration != _integer(support, "minimum_calibration_records") or held_out != _integer(
        support, "minimum_held_out_records"
    ):
        raise TwinFidelityProtocolError("metric support counts drift from support policy")
    if alpha != round(1 - confidence, 10):
        raise TwinFidelityProtocolError("metric improvement alpha drifts from confidence policy")
    return TwinFidelityMetric(
        metric_id,
        _text(value, "source_variable"),
        _text(value, "aggregation"),
        _text(value, "unit"),
        _text(value, "direction"),
        threshold,
        calibration,
        held_out,
        _text(value, "improvement_test"),
        alpha,
        effect,
    )


def _exact(value: Mapping[str, object], allowed: set[str], label: str) -> None:
    if set(value) != allowed:
        raise TwinFidelityProtocolError(f"{label} fields mismatch")


def _mapping(value: Mapping[str, object], key: str) -> Mapping[str, object]:
    return _mapping_value(value.get(key), key)


def _mapping_value(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise TwinFidelityProtocolError(f"{label} must be an object")
    return value


def _sequence(value: Mapping[str, object], key: str) -> Sequence[object]:
    selected = value.get(key)
    if not isinstance(selected, Sequence) or isinstance(selected, (str, bytes, bytearray)):
        raise TwinFidelityProtocolError(f"{key} must be an array")
    return selected


def _text(value: Mapping[str, object], key: str) -> str:
    selected = value.get(key)
    if not isinstance(selected, str) or not selected.strip() or len(selected) > 1024:
        raise TwinFidelityProtocolError(f"{key} must be non-empty text")
    return selected


def _require_text(value: Mapping[str, object], key: str) -> None:
    _text(value, key)


def _number(value: Mapping[str, object], key: str) -> float:
    selected = value.get(key)
    if (
        isinstance(selected, bool)
        or not isinstance(selected, (int, float))
        or not isfinite(float(selected))
    ):
        raise TwinFidelityProtocolError(f"{key} must be a finite number")
    return float(selected)


def _integer(value: Mapping[str, object], key: str) -> int:
    selected = value.get(key)
    if isinstance(selected, bool) or not isinstance(selected, int):
        raise TwinFidelityProtocolError(f"{key} must be an integer")
    return selected


def _bool(value: Mapping[str, object], key: str) -> bool:
    selected = value.get(key)
    if not isinstance(selected, bool):
        raise TwinFidelityProtocolError(f"{key} must be boolean")
    return selected


__all__ = [
    "FidelitySupportResult",
    "TwinFidelityMetric",
    "TwinFidelityProtocol",
    "TwinFidelityProtocolError",
    "assess_fidelity_support",
    "load_twin_fidelity_protocol",
]
