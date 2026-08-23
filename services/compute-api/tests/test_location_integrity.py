from datetime import UTC, datetime, timedelta

import pytest

from routemind_compute.application.location_integrity import (
    LocationObservation,
    assess_location,
    build_hotspots,
)
from routemind_compute.domain.dispatch import GeoPoint

BASE = datetime(2026, 8, 24, 0, 0, tzinfo=UTC)


def observation(
    courier_id: str,
    sequence: int,
    latitude: float = 31.2,
    longitude: float = 121.4,
    *,
    observed_at: datetime = BASE,
    ingested_at: datetime | None = None,
    online: bool = True,
) -> LocationObservation:
    return LocationObservation(
        courier_id,
        GeoPoint(latitude, longitude),
        sequence,
        observed_at,
        ingested_at or observed_at,
        online,
    )


def test_integrity_distinguishes_healthy_gap_stale_and_impossible_speed() -> None:
    healthy = assess_location(observation("c-1", 1), reference_time=BASE)
    gap = assess_location(
        observation("c-1", 3, observed_at=BASE + timedelta(seconds=10)),
        observation("c-1", 1),
        reference_time=BASE + timedelta(seconds=10),
    )
    suspect = assess_location(
        observation("c-1", 2, latitude=32.2, observed_at=BASE + timedelta(seconds=1)),
        observation("c-1", 1),
        reference_time=BASE + timedelta(seconds=1),
    )
    stale = assess_location(
        observation("c-1", 4, observed_at=BASE),
        reference_time=BASE + timedelta(seconds=121),
    )

    assert healthy.status == "HEALTHY"
    assert gap.status == "DEGRADED"
    assert gap.sequence_gap == 1
    assert any(signal.code == "sequence_gap" for signal in gap.signals)
    assert suspect.status == "SUSPECT"
    assert any(signal.code == "impossible_speed" for signal in suspect.signals)
    assert stale.status == "STALE"


def test_duplicate_and_offline_reports_are_explicit_without_discipline() -> None:
    result = assess_location(
        observation("c-1", 2, online=False),
        observation("c-1", 2),
        reference_time=BASE,
    )

    assert result.status == "DEGRADED"
    assert {signal.code for signal in result.signals} == {
        "duplicate_sequence",
        "offline_report",
    }


def test_hotspots_are_k_anonymous_and_bounded() -> None:
    points = tuple(observation(f"c-{index}", 1, 31.2, 121.4) for index in range(3))
    cells = build_hotspots(points, minimum_unique_couriers=3)

    assert len(cells) == 1
    assert cells[0].unique_courier_count == 3
    assert cells[0].observation_count == 3
    assert not hasattr(cells[0], "courier_ids")
    with pytest.raises(ValueError, match="at least two"):
        build_hotspots(points, minimum_unique_couriers=1)
    with pytest.raises(ValueError, match="cell size"):
        build_hotspots(points, cell_size_degrees=0)
    with pytest.raises(ValueError, match="exceeds bound"):
        build_hotspots(points, maximum_observations=2)


def test_integrity_validates_time_thresholds_and_digests() -> None:
    with pytest.raises(ValueError, match="courier id"):
        LocationObservation(" ", GeoPoint(0, 0), 1, BASE, BASE)
    with pytest.raises(ValueError, match="positive"):
        LocationObservation("c-1", GeoPoint(0, 0), 0, BASE, BASE)
    with pytest.raises(ValueError, match="timezone"):
        LocationObservation("c-1", GeoPoint(0, 0), 1, datetime(2026, 8, 24), BASE)
    current = observation("c-1", 1, ingested_at=BASE + timedelta(seconds=31))
    with pytest.raises(ValueError, match="timezone"):
        assess_location(current, reference_time=datetime(2026, 8, 24))
    with pytest.raises(ValueError, match="maximum speed"):
        assess_location(current, max_speed_kilometres_per_hour=0)
    with pytest.raises(ValueError, match="stale threshold"):
        assess_location(current, stale_after_seconds=0)
    with pytest.raises(ValueError, match="ingestion lag"):
        assess_location(current, max_ingestion_lag_seconds=-1)
    lagged = assess_location(current, reference_time=BASE + timedelta(seconds=31))
    assert lagged.status == "DEGRADED"
    assert any(signal.code == "ingestion_lag" for signal in lagged.signals)
    backwards = assess_location(
        observation("c-1", 1, observed_at=BASE + timedelta(seconds=1)),
        observation("c-1", 2),
        reference_time=BASE + timedelta(seconds=1),
    )
    regression = assess_location(
        observation("c-1", 2),
        observation("c-1", 1),
        reference_time=BASE,
    )
    assert backwards.status == "SUSPECT"
    assert regression.status == "SUSPECT"
    assert {signal.code for signal in regression.signals} == {"observed_time_regression"}
    assert len(lagged.digest) == 64
