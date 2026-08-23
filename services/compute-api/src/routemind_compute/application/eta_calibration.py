"""Data-backed ETA error metrics and explicit SLA risk labels."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from math import isfinite
from statistics import median
from typing import Literal

CalibrationStatus = Literal["AVAILABLE", "UNAVAILABLE"]
SlaRisk = Literal["ON_TRACK", "AT_RISK", "LIKELY_LATE"]


@dataclass(frozen=True, slots=True)
class EtaCalibrationSample:
    sample_id: str
    predicted_seconds: float
    actual_seconds: float
    interval_lower_seconds: float | None = None
    interval_upper_seconds: float | None = None

    def __post_init__(self) -> None:
        if not self.sample_id.strip():
            raise ValueError("calibration sample id must not be blank")
        values = (self.predicted_seconds, self.actual_seconds)
        if any(not isfinite(value) or value < 0 for value in values):
            raise ValueError("calibration durations must be finite and non-negative")
        bounds = (self.interval_lower_seconds, self.interval_upper_seconds)
        if any(value is not None and (not isfinite(value) or value < 0) for value in bounds):
            raise ValueError("calibration interval must be finite and non-negative")
        if (self.interval_lower_seconds is None or self.interval_upper_seconds is None) and any(
            value is not None for value in bounds
        ):
            raise ValueError("calibration interval requires both bounds")
        if (
            self.interval_lower_seconds is not None
            and self.interval_upper_seconds is not None
            and self.interval_lower_seconds > self.interval_upper_seconds
        ):
            raise ValueError("calibration interval lower bound must not exceed upper bound")


@dataclass(frozen=True, slots=True)
class EtaCalibrationResult:
    status: CalibrationStatus
    sample_count: int
    mae_seconds: float | None
    median_error_seconds: float | None
    p90_error_seconds: float | None
    interval_coverage: float | None
    digest: str


@dataclass(frozen=True, slots=True)
class SlaRiskResult:
    status: SlaRisk
    predicted_seconds: float
    sla_seconds: float
    margin_seconds: float
    customer_confidence: Literal["available", "unavailable"]


def calibrate(samples: tuple[EtaCalibrationSample, ...]) -> EtaCalibrationResult:
    if len({sample.sample_id for sample in samples}) != len(samples):
        raise ValueError("calibration sample ids must be unique")
    if not samples:
        return EtaCalibrationResult("UNAVAILABLE", 0, None, None, None, None, _digest(()))
    errors = tuple(abs(sample.predicted_seconds - sample.actual_seconds) for sample in samples)
    intervals = tuple(
        sample
        for sample in samples
        if sample.interval_lower_seconds is not None and sample.interval_upper_seconds is not None
    )
    coverage = None
    if intervals:
        covered = 0
        for sample in intervals:
            lower = sample.interval_lower_seconds
            upper = sample.interval_upper_seconds
            assert lower is not None and upper is not None
            covered += lower <= sample.actual_seconds <= upper
        coverage = covered / len(intervals)
    payload = tuple(
        (
            sample.sample_id,
            sample.predicted_seconds,
            sample.actual_seconds,
            sample.interval_lower_seconds,
            sample.interval_upper_seconds,
        )
        for sample in sorted(samples, key=lambda item: item.sample_id)
    )
    return EtaCalibrationResult(
        "AVAILABLE",
        len(samples),
        sum(errors) / len(errors),
        median(errors),
        _percentile(errors, 0.9),
        coverage,
        _digest(payload),
    )


def classify_sla_risk(
    predicted_seconds: float,
    sla_seconds: float,
    calibration: EtaCalibrationResult,
) -> SlaRiskResult:
    if not isfinite(predicted_seconds) or predicted_seconds < 0:
        raise ValueError("predicted ETA must be finite and non-negative")
    if not isfinite(sla_seconds) or sla_seconds <= 0:
        raise ValueError("SLA duration must be finite and positive")
    ratio = predicted_seconds / sla_seconds
    status: SlaRisk = "ON_TRACK" if ratio <= 0.9 else "AT_RISK" if ratio <= 1.0 else "LIKELY_LATE"
    return SlaRiskResult(
        status,
        predicted_seconds,
        sla_seconds,
        sla_seconds - predicted_seconds,
        "available" if calibration.status == "AVAILABLE" else "unavailable",
    )


def _percentile(values: tuple[float, ...], quantile: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * quantile
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def _digest(payload: object) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


__all__ = [
    "EtaCalibrationResult",
    "EtaCalibrationSample",
    "SlaRiskResult",
    "calibrate",
    "classify_sla_risk",
]
