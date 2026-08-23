"""Composable, honest ETA baseline with explicit lineage metadata."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from math import isfinite

from routemind_compute.application.travel import TravelTimeProvider
from routemind_compute.domain.dispatch import GeoPoint


@dataclass(frozen=True, slots=True)
class EtaComponent:
    name: str
    seconds: float | None
    source: str
    available: bool

    def __post_init__(self) -> None:
        if not self.name.strip() or not self.source.strip():
            raise ValueError("ETA component identity must not be blank")
        if self.seconds is not None and (not isfinite(self.seconds) or self.seconds < 0):
            raise ValueError("ETA component seconds must be finite and non-negative")
        if self.available != (self.seconds is not None):
            raise ValueError("ETA component availability must match seconds")


@dataclass(frozen=True, slots=True)
class EtaPrediction:
    order_id: str
    courier_id: str
    prediction_time: datetime
    horizon_seconds: float
    predicted_delivery_at: datetime | None
    model: str
    model_version: str
    components: tuple[EtaComponent, ...]
    input_digest: str
    actual_delivered_at: datetime | None = None

    def __post_init__(self) -> None:
        if not self.order_id.strip() or not self.courier_id.strip():
            raise ValueError("ETA identities must not be blank")
        if self.prediction_time.tzinfo is None:
            raise ValueError("ETA prediction time must include timezone")
        if not isfinite(self.horizon_seconds) or self.horizon_seconds <= 0:
            raise ValueError("ETA horizon must be finite and positive")
        if not self.model.strip() or not self.model_version.strip():
            raise ValueError("ETA model identity must not be blank")
        if len(self.input_digest) != 64:
            raise ValueError("ETA input digest must be SHA-256")

    @property
    def total_seconds(self) -> float | None:
        values = tuple(item.seconds for item in self.components if item.available)
        if len(values) != len(self.components):
            return None
        return sum(value for value in values if value is not None)

    @property
    def actual_duration_seconds(self) -> float | None:
        if self.actual_delivered_at is None:
            return None
        return max(0.0, (self.actual_delivered_at - self.prediction_time).total_seconds())

    @property
    def outcome_available(self) -> bool:
        return self.actual_delivered_at is not None


class EtaBaseline:
    """Compute an ETA from explicit components; never claims calibration."""

    model = "deterministic-baseline"
    model_version = "1.0.0"

    def __init__(self, travel_provider: TravelTimeProvider) -> None:
        self.travel_provider = travel_provider

    def predict(
        self,
        *,
        order_id: str,
        courier_id: str,
        prediction_time: datetime,
        horizon_seconds: float,
        courier_location: GeoPoint,
        pickup_location: GeoPoint,
        delivery_location: GeoPoint,
        courier_available_at: datetime,
        pickup_ready_at: datetime,
        preparation_seconds: float | None,
        pickup_seconds: float,
        delivery_seconds: float,
        actual_delivered_at: datetime | None = None,
    ) -> EtaPrediction:
        values = {
            "order_id": order_id,
            "courier_id": courier_id,
            "prediction_time": prediction_time.isoformat(),
            "horizon_seconds": horizon_seconds,
            "courier_location": (courier_location.latitude, courier_location.longitude),
            "pickup_location": (pickup_location.latitude, pickup_location.longitude),
            "delivery_location": (delivery_location.latitude, delivery_location.longitude),
            "courier_available_at": courier_available_at.isoformat(),
            "pickup_ready_at": pickup_ready_at.isoformat(),
            "preparation_seconds": preparation_seconds,
            "pickup_seconds": pickup_seconds,
            "delivery_seconds": delivery_seconds,
        }
        input_digest = hashlib.sha256(
            json.dumps(values, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        dispatch_wait = max(
            0.0,
            (courier_available_at - prediction_time).total_seconds(),
            (pickup_ready_at - prediction_time).total_seconds(),
        )
        travel_to_pickup = self.travel_provider.estimate(courier_location, pickup_location).seconds
        travel_to_delivery = self.travel_provider.estimate(
            pickup_location, delivery_location
        ).seconds
        components = (
            EtaComponent("dispatch", dispatch_wait, "courier availability", True),
            EtaComponent(
                "travel",
                travel_to_pickup + travel_to_delivery,
                "travel provider",
                True,
            ),
            EtaComponent(
                "preparation",
                preparation_seconds,
                "merchant preparation",
                preparation_seconds is not None,
            ),
            EtaComponent("pickup", pickup_seconds, "pickup service", True),
            EtaComponent("delivery", delivery_seconds, "delivery service", True),
        )
        total = sum(item.seconds for item in components if item.seconds is not None)
        predicted = (
            prediction_time + timedelta(seconds=total) if preparation_seconds is not None else None
        )
        return EtaPrediction(
            order_id,
            courier_id,
            prediction_time,
            horizon_seconds,
            predicted,
            self.model,
            self.model_version,
            components,
            input_digest,
            actual_delivered_at,
        )


__all__ = ["EtaBaseline", "EtaComponent", "EtaPrediction"]
