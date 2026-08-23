"""Descriptive ETA delay accounting with explicit completeness boundaries."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from math import isclose, isfinite
from typing import Literal

DelayClockDomain = Literal["wall", "simulated"]
DelayStatus = Literal["RECONCILED", "UNRECONCILED", "INCOMPLETE", "CLOCK_DOMAIN_MISMATCH"]

ETA_COMPONENT_NAMES = ("dispatch", "travel", "preparation", "pickup", "delivery")


@dataclass(frozen=True, slots=True)
class DelayAccountingComponent:
    name: str
    seconds: float | None
    clock_domain: DelayClockDomain | None

    def __post_init__(self) -> None:
        if self.name not in ETA_COMPONENT_NAMES:
            raise ValueError(f"unknown ETA delay component: {self.name}")
        if self.seconds is not None and (not isfinite(self.seconds) or self.seconds < 0):
            raise ValueError("delay component seconds must be finite and non-negative")
        if self.seconds is None and self.clock_domain is not None:
            raise ValueError("missing delay component must not declare a clock domain")
        if self.seconds is not None and self.clock_domain is None:
            raise ValueError("available delay component requires a clock domain")


@dataclass(frozen=True, slots=True)
class DelayAccountingRecord:
    record_id: str
    observed_duration_seconds: float
    clock_domain: DelayClockDomain
    components: tuple[DelayAccountingComponent, ...]

    def __post_init__(self) -> None:
        if not self.record_id.strip():
            raise ValueError("delay accounting record id must not be blank")
        if not isfinite(self.observed_duration_seconds) or self.observed_duration_seconds < 0:
            raise ValueError("observed duration must be finite and non-negative")
        names = tuple(component.name for component in self.components)
        if len(set(names)) != len(names):
            raise ValueError("delay component names must be unique")


@dataclass(frozen=True, slots=True)
class DelayAccountingResult:
    record_id: str
    status: DelayStatus
    observed_duration_seconds: float
    accounted_duration_seconds: float
    residual_seconds: float | None
    components: tuple[DelayAccountingComponent, ...]
    missing_components: tuple[str, ...]
    mismatched_components: tuple[str, ...]
    digest: str


@dataclass(frozen=True, slots=True)
class DelayAccountingAggregate:
    record_count: int
    observed_duration_seconds: float
    accounted_duration_seconds: float
    residual_seconds: float | None
    reconciled_count: int
    incomplete_count: int
    clock_domain_mismatch_count: int
    digest: str


def account_record(record: DelayAccountingRecord) -> DelayAccountingResult:
    by_name = {component.name: component for component in record.components}
    normalized = tuple(
        by_name.get(name, DelayAccountingComponent(name, None, None))
        for name in ETA_COMPONENT_NAMES
    )
    missing = tuple(component.name for component in normalized if component.seconds is None)
    mismatched = tuple(
        component.name
        for component in normalized
        if component.seconds is not None and component.clock_domain != record.clock_domain
    )
    accounted = sum(component.seconds or 0.0 for component in normalized)
    residual = record.observed_duration_seconds - accounted
    if mismatched:
        status: DelayStatus = "CLOCK_DOMAIN_MISMATCH"
        reported_residual: float | None = None
    elif missing:
        status = "INCOMPLETE"
        reported_residual = residual
    elif isclose(residual, 0.0, abs_tol=1e-6):
        status = "RECONCILED"
        reported_residual = 0.0
    else:
        status = "UNRECONCILED"
        reported_residual = residual
    payload = {
        "record_id": record.record_id,
        "observed_duration_seconds": record.observed_duration_seconds,
        "clock_domain": record.clock_domain,
        "components": tuple(
            (component.name, component.seconds, component.clock_domain) for component in normalized
        ),
        "status": status,
        "residual_seconds": reported_residual,
    }
    return DelayAccountingResult(
        record.record_id,
        status,
        record.observed_duration_seconds,
        accounted,
        reported_residual,
        normalized,
        missing,
        mismatched,
        _digest(payload),
    )


def account_records(
    records: tuple[DelayAccountingRecord, ...],
) -> tuple[tuple[DelayAccountingResult, ...], DelayAccountingAggregate]:
    if len({record.record_id for record in records}) != len(records):
        raise ValueError("delay accounting record ids must be unique")
    results = tuple(account_record(record) for record in records)
    observed = sum(result.observed_duration_seconds for result in results)
    accounted = sum(result.accounted_duration_seconds for result in results)
    residuals = tuple(result.residual_seconds for result in results)
    aggregate_residual = (
        observed - accounted if all(value is not None for value in residuals) else None
    )
    aggregate = DelayAccountingAggregate(
        record_count=len(results),
        observed_duration_seconds=observed,
        accounted_duration_seconds=accounted,
        residual_seconds=aggregate_residual,
        reconciled_count=sum(result.status == "RECONCILED" for result in results),
        incomplete_count=sum(result.status == "INCOMPLETE" for result in results),
        clock_domain_mismatch_count=sum(
            result.status == "CLOCK_DOMAIN_MISMATCH" for result in results
        ),
        digest=_digest(tuple(result.digest for result in results)),
    )
    return results, aggregate


def _digest(payload: object) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


__all__ = [
    "DelayAccountingAggregate",
    "DelayAccountingComponent",
    "DelayAccountingRecord",
    "DelayAccountingResult",
    "DelayClockDomain",
    "DelayStatus",
    "account_record",
    "account_records",
]
