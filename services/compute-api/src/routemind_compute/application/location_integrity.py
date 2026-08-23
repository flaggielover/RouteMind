"""Deterministic courier-location integrity signals and privacy-bounded hotspots."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from math import isfinite
from typing import Literal

from routemind_compute.application.nearest import great_circle_distance_kilometres
from routemind_compute.domain.dispatch import GeoPoint

IntegrityStatus = Literal["HEALTHY", "DEGRADED", "SUSPECT", "STALE"]
SignalCode = Literal[
    "duplicate_sequence",
    "sequence_gap",
    "observed_time_regression",
    "impossible_speed",
    "stale_report",
    "offline_report",
    "ingestion_lag",
]


@dataclass(frozen=True, slots=True)
class LocationObservation:
    courier_id: str
    location: GeoPoint
    sequence: int
    observed_at: datetime
    ingested_at: datetime
    online: bool = True

    def __post_init__(self) -> None:
        if not self.courier_id.strip():
            raise ValueError("courier id must not be blank")
        if self.sequence < 1:
            raise ValueError("location sequence must be positive")
        if self.observed_at.tzinfo is None or self.ingested_at.tzinfo is None:
            raise ValueError("location timestamps must include timezone")


@dataclass(frozen=True, slots=True)
class IntegritySignal:
    code: SignalCode
    detail: str
    severity: Literal["info", "warning", "critical"]


@dataclass(frozen=True, slots=True)
class LocationIntegrityResult:
    courier_id: str
    status: IntegrityStatus
    sequence: int
    distance_kilometres: float
    speed_kilometres_per_hour: float | None
    staleness_seconds: float
    ingestion_lag_seconds: float
    sequence_gap: int
    signals: tuple[IntegritySignal, ...]

    @property
    def digest(self) -> str:
        payload = {
            "courier_id": self.courier_id,
            "status": self.status,
            "sequence": self.sequence,
            "distance_kilometres": round(self.distance_kilometres, 6),
            "speed_kilometres_per_hour": (
                round(self.speed_kilometres_per_hour, 6)
                if self.speed_kilometres_per_hour is not None
                else None
            ),
            "staleness_seconds": round(self.staleness_seconds, 3),
            "ingestion_lag_seconds": round(self.ingestion_lag_seconds, 3),
            "sequence_gap": self.sequence_gap,
            "signals": [(item.code, item.detail, item.severity) for item in self.signals],
        }
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()


@dataclass(frozen=True, slots=True)
class HotspotCell:
    """Aggregate cell with no courier identifiers or raw trajectory points."""

    cell_id: str
    latitude: float
    longitude: float
    observation_count: int
    unique_courier_count: int


def assess_location(
    current: LocationObservation,
    previous: LocationObservation | None = None,
    *,
    reference_time: datetime | None = None,
    max_speed_kilometres_per_hour: float = 130.0,
    stale_after_seconds: float = 120.0,
    max_ingestion_lag_seconds: float = 30.0,
) -> LocationIntegrityResult:
    """Classify one report without taking a disciplinary or dispatch action."""
    if not isfinite(max_speed_kilometres_per_hour) or max_speed_kilometres_per_hour <= 0:
        raise ValueError("maximum speed must be finite and positive")
    if not isfinite(stale_after_seconds) or stale_after_seconds <= 0:
        raise ValueError("stale threshold must be finite and positive")
    if not isfinite(max_ingestion_lag_seconds) or max_ingestion_lag_seconds < 0:
        raise ValueError("ingestion lag threshold must be finite and non-negative")
    reference = reference_time or current.ingested_at
    if reference.tzinfo is None:
        raise ValueError("reference timestamp must include timezone")
    staleness = max(0.0, (reference - current.observed_at).total_seconds())
    ingestion_lag = max(0.0, (current.ingested_at - current.observed_at).total_seconds())
    distance = 0.0
    speed: float | None = None
    sequence_gap = 0
    signals: list[IntegritySignal] = []
    if previous is not None:
        sequence_gap = current.sequence - previous.sequence - 1
        if current.sequence == previous.sequence:
            signals.append(IntegritySignal("duplicate_sequence", "sequence repeated", "info"))
        elif current.sequence < previous.sequence:
            signals.append(IntegritySignal("sequence_gap", "sequence moved backwards", "critical"))
        elif sequence_gap > 0:
            signals.append(
                IntegritySignal("sequence_gap", f"missing_sequences={sequence_gap}", "warning")
            )
        if current.sequence > previous.sequence:
            elapsed = (current.observed_at - previous.observed_at).total_seconds()
            if elapsed <= 0:
                signals.append(
                    IntegritySignal(
                        "observed_time_regression",
                        "event time did not advance",
                        "critical",
                    )
                )
            else:
                distance = great_circle_distance_kilometres(
                    previous.location.latitude,
                    previous.location.longitude,
                    current.location.latitude,
                    current.location.longitude,
                )
                speed = distance / elapsed * 3600.0
                if speed > max_speed_kilometres_per_hour:
                    signals.append(
                        IntegritySignal(
                            "impossible_speed",
                            f"speed_kmh={speed:.3f} exceeds={max_speed_kilometres_per_hour:.3f}",
                            "critical",
                        )
                    )
    if staleness > stale_after_seconds:
        signals.append(IntegritySignal("stale_report", f"age_seconds={staleness:.3f}", "warning"))
    if not current.online:
        signals.append(IntegritySignal("offline_report", "report marked offline", "warning"))
    if ingestion_lag > max_ingestion_lag_seconds:
        signals.append(
            IntegritySignal("ingestion_lag", f"lag_seconds={ingestion_lag:.3f}", "warning")
        )
    if any(signal.severity == "critical" for signal in signals):
        status: IntegrityStatus = "SUSPECT"
    elif any(signal.code == "stale_report" for signal in signals):
        status = "STALE"
    elif signals:
        status = "DEGRADED"
    else:
        status = "HEALTHY"
    return LocationIntegrityResult(
        courier_id=current.courier_id,
        status=status,
        sequence=current.sequence,
        distance_kilometres=distance,
        speed_kilometres_per_hour=speed,
        staleness_seconds=staleness,
        ingestion_lag_seconds=ingestion_lag,
        sequence_gap=max(0, sequence_gap),
        signals=tuple(signals),
    )


def build_hotspots(
    observations: tuple[LocationObservation, ...],
    *,
    cell_size_degrees: float = 0.01,
    minimum_unique_couriers: int = 3,
    maximum_observations: int = 10_000,
) -> tuple[HotspotCell, ...]:
    """Return only k-anonymous grid cells, bounded and free of courier IDs."""
    if not isfinite(cell_size_degrees) or cell_size_degrees <= 0:
        raise ValueError("cell size must be finite and positive")
    if minimum_unique_couriers < 2:
        raise ValueError("hotspot minimum must be at least two couriers")
    if len(observations) > maximum_observations:
        raise ValueError("hotspot observation batch exceeds bound")
    buckets: dict[tuple[int, int], tuple[int, set[str], float, float]] = {}
    for item in observations:
        key = (
            int(item.location.latitude // cell_size_degrees),
            int(item.location.longitude // cell_size_degrees),
        )
        count, couriers, lat_total, lon_total = buckets.get(key, (0, set(), 0.0, 0.0))
        buckets[key] = (
            count + 1,
            couriers | {item.courier_id},
            lat_total + item.location.latitude,
            lon_total + item.location.longitude,
        )
    cells: list[HotspotCell] = []
    for (lat_bucket, lon_bucket), (
        count,
        couriers,
        lat_total,
        lon_total,
    ) in sorted(buckets.items()):
        if len(couriers) < minimum_unique_couriers:
            continue
        cells.append(
            HotspotCell(
                cell_id=f"{lat_bucket}:{lon_bucket}:{cell_size_degrees:g}",
                latitude=lat_total / count,
                longitude=lon_total / count,
                observation_count=count,
                unique_courier_count=len(couriers),
            )
        )
    return tuple(cells)


__all__ = [
    "HotspotCell",
    "IntegritySignal",
    "LocationIntegrityResult",
    "LocationObservation",
    "assess_location",
    "build_hotspots",
]
