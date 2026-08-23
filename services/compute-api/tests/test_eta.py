from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from routemind_compute.application.eta import EtaBaseline, EtaComponent
from routemind_compute.application.travel import DeterministicLocalTravelProvider
from routemind_compute.domain.dispatch import GeoPoint

BASE = datetime(2026, 8, 24, 1, 0, tzinfo=UTC)


def baseline() -> EtaBaseline:
    return EtaBaseline(DeterministicLocalTravelProvider())


def kwargs() -> dict[str, Any]:
    return {
        "order_id": "order-1",
        "courier_id": "courier-1",
        "prediction_time": BASE,
        "horizon_seconds": 3600,
        "courier_location": GeoPoint(31.2, 121.4),
        "pickup_location": GeoPoint(31.21, 121.41),
        "delivery_location": GeoPoint(31.22, 121.42),
        "courier_available_at": BASE,
        "pickup_ready_at": BASE + timedelta(seconds=60),
        "preparation_seconds": 120.0,
        "pickup_seconds": 30.0,
        "delivery_seconds": 20.0,
    }


def test_eta_composes_five_components_and_records_outcome_lineage() -> None:
    prediction = baseline().predict(**kwargs(), actual_delivered_at=BASE + timedelta(seconds=900))

    assert [item.name for item in prediction.components] == [
        "dispatch",
        "travel",
        "preparation",
        "pickup",
        "delivery",
    ]
    assert prediction.predicted_delivery_at is not None
    assert prediction.outcome_available is True
    assert prediction.actual_duration_seconds == 900
    assert len(prediction.input_digest) == 64


def test_eta_marks_unavailable_preparation_without_inventing_estimate() -> None:
    payload = kwargs()
    payload["preparation_seconds"] = None
    prediction = baseline().predict(**payload)

    assert prediction.predicted_delivery_at is None
    assert prediction.total_seconds is None
    preparation = prediction.components[2]
    assert preparation.available is False
    assert preparation.seconds is None


def test_eta_components_validate_identity_availability_and_thresholds() -> None:
    with pytest.raises(ValueError, match="identity"):
        EtaComponent(" ", 1, "source", True)
    with pytest.raises(ValueError, match="availability"):
        EtaComponent("travel", None, "source", True)
    with pytest.raises(ValueError, match="horizon"):
        baseline().predict(**{**kwargs(), "horizon_seconds": 0})
