"""Provider-neutral, zero-default-live-call adapter for Google Routes API."""

from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from math import isfinite
from typing import Protocol
from uuid import uuid4

from routemind_compute.application.travel import (
    DynamicTravelContext,
    TravelTime,
    TravelTimeMatrix,
)
from routemind_compute.domain.dispatch import GeoPoint

POINT_ENDPOINT = "https://routes.googleapis.com/directions/v2:computeRoutes"
MATRIX_ENDPOINT = "https://routes.googleapis.com/distanceMatrix/v2:computeRouteMatrix"


class GoogleRoutesTransport(Protocol):
    def __call__(
        self,
        *,
        operation: str,
        endpoint: str,
        headers: Mapping[str, str],
        body: Mapping[str, object],
        timeout_seconds: float,
    ) -> GoogleRoutesResponse: ...


@dataclass(frozen=True, slots=True)
class GoogleRoutesResponse:
    status_code: int
    payload: object
    provider_request_id: str | None = None


@dataclass(frozen=True, slots=True)
class GoogleRoutesPolicy:
    timeout_seconds: float = 2.0
    max_retries: int = 2
    retry_backoff_seconds: float = 0.05
    max_point_requests: int = 20
    max_matrix_requests: int = 5
    max_matrix_elements: int = 100
    max_duration_seconds: float = 1800.0
    max_spend_usd: float = 1.0
    estimated_point_cost_usd: float = 0.0
    estimated_matrix_element_cost_usd: float = 0.0
    rate_limit_per_second: float = 5.0
    circuit_failure_threshold: int = 3
    circuit_reset_seconds: float = 30.0

    def __post_init__(self) -> None:
        if not isfinite(self.timeout_seconds) or self.timeout_seconds <= 0:
            raise ValueError("Google timeout must be finite and positive")
        if (
            not isinstance(self.max_retries, int)
            or isinstance(self.max_retries, bool)
            or self.max_retries < 0
        ):
            raise ValueError("Google retries must be a non-negative integer")
        if not isfinite(self.retry_backoff_seconds) or self.retry_backoff_seconds < 0:
            raise ValueError("Google retry backoff must be finite and non-negative")
        for name in (
            "max_point_requests",
            "max_matrix_requests",
            "max_matrix_elements",
            "circuit_failure_threshold",
        ):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                raise ValueError(f"{name} must be a positive integer")
        for name in (
            "max_duration_seconds",
            "max_spend_usd",
            "estimated_point_cost_usd",
            "estimated_matrix_element_cost_usd",
            "circuit_reset_seconds",
        ):
            value = getattr(self, name)
            if not isfinite(value) or value < 0:
                raise ValueError(f"{name} must be finite and non-negative")
        if self.max_spend_usd <= 0 or self.max_duration_seconds <= 0:
            raise ValueError("Google budget ceilings must be positive")
        if not isfinite(self.rate_limit_per_second) or self.rate_limit_per_second < 0:
            raise ValueError("Google rate limit must be finite and non-negative")


class GoogleRoutesError(RuntimeError):
    """Stable, non-sensitive provider failure classification."""

    def __init__(
        self,
        classification: str,
        message: str = "Google Routes request failed",
        *,
        status_code: int | None = None,
        retryable: bool = False,
    ) -> None:
        super().__init__(
            message
            if message != "Google Routes request failed"
            else f"Google Routes request failed: {classification}"
        )
        self.classification = classification
        self.status_code = status_code
        self.retryable = retryable


class _Budget:
    def __init__(self, policy: GoogleRoutesPolicy, clock: Callable[[], float]) -> None:
        self.policy = policy
        self.clock = clock
        self.started_at = clock()
        self.point_requests = 0
        self.matrix_requests = 0
        self.matrix_elements = 0
        self.spend_usd = 0.0
        self._lock = threading.Lock()

    def consume(self, operation: str, elements: int) -> None:
        with self._lock:
            if self.clock() - self.started_at >= self.policy.max_duration_seconds:
                raise GoogleRoutesError("budget_exceeded", "Google validation time budget exceeded")
            if operation == "ComputeRoutes":
                if self.point_requests >= self.policy.max_point_requests:
                    raise GoogleRoutesError("point_request_budget_exceeded")
                cost = self.policy.estimated_point_cost_usd
            else:
                if self.matrix_requests >= self.policy.max_matrix_requests:
                    raise GoogleRoutesError("matrix_request_budget_exceeded")
                if self.matrix_elements + elements > self.policy.max_matrix_elements:
                    raise GoogleRoutesError("matrix_element_budget_exceeded")
                cost = elements * self.policy.estimated_matrix_element_cost_usd
            if self.spend_usd + cost > self.policy.max_spend_usd:
                raise GoogleRoutesError("spend_budget_exceeded")
            if operation == "ComputeRoutes":
                self.point_requests += 1
            else:
                self.matrix_requests += 1
                self.matrix_elements += elements
            self.spend_usd += cost

    def snapshot(self) -> dict[str, float | int]:
        with self._lock:
            return {
                "point_requests": self.point_requests,
                "matrix_requests": self.matrix_requests,
                "matrix_elements": self.matrix_elements,
                "estimated_spend_usd": round(self.spend_usd, 8),
                "elapsed_seconds": round(self.clock() - self.started_at, 6),
            }


class _RateLimiter:
    def __init__(
        self, rate_per_second: float, clock: Callable[[], float], sleeper: Callable[[float], None]
    ) -> None:
        self.interval = 1.0 / rate_per_second if rate_per_second > 0 else 0.0
        self.clock = clock
        self.sleeper = sleeper
        self.next_allowed = 0.0
        self._lock = threading.Lock()

    def wait(self) -> None:
        if self.interval == 0:
            return
        with self._lock:
            now = self.clock()
            delay = max(0.0, self.next_allowed - now)
            if delay:
                self.sleeper(delay)
                now = self.clock()
            self.next_allowed = max(now, self.next_allowed) + self.interval


class _Circuit:
    def __init__(self, policy: GoogleRoutesPolicy, clock: Callable[[], float]) -> None:
        self.policy = policy
        self.clock = clock
        self.failures = 0
        self.opened_at: float | None = None
        self._lock = threading.Lock()

    def check(self) -> None:
        with self._lock:
            if self.opened_at is None:
                return
            if self.clock() - self.opened_at >= self.policy.circuit_reset_seconds:
                self.failures = 0
                self.opened_at = None
                return
            raise GoogleRoutesError("circuit_open")

    def success(self) -> None:
        with self._lock:
            self.failures = 0
            self.opened_at = None

    def failure(self, error: GoogleRoutesError) -> None:
        if not error.retryable:
            return
        with self._lock:
            self.failures += 1
            if self.failures >= self.policy.circuit_failure_threshold:
                self.opened_at = self.clock()


class GoogleRoutesProvider:
    """Google adapter; callers must supply a transport, preventing accidental live I/O."""

    name = "google-routes"

    def __init__(
        self,
        transport: GoogleRoutesTransport,
        *,
        api_key_env: str = "ROUTEMIND_GOOGLE_ROUTES_API_KEY",
        policy: GoogleRoutesPolicy | None = None,
        clock: Callable[[], float] = time.monotonic,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        if not api_key_env.strip():
            raise ValueError("Google API key environment name must not be blank")
        self.transport = transport
        self.api_key_env = api_key_env
        self.policy = policy or GoogleRoutesPolicy()
        self._clock = clock
        self._budget = _Budget(self.policy, clock)
        self._rate_limiter = _RateLimiter(self.policy.rate_limit_per_second, clock, sleeper)
        self._circuit = _Circuit(self.policy, clock)
        self._sleeper = sleeper

    @property
    def budget_snapshot(self) -> dict[str, float | int]:
        return self._budget.snapshot()

    def estimate(
        self,
        origin: GeoPoint,
        destination: GeoPoint,
        context: DynamicTravelContext | None = None,
        *,
        departure_time: str | None = None,
        request_id: str | None = None,
    ) -> TravelTime:
        effective_context = context or DynamicTravelContext()
        request_id = request_id or f"rm-google-{uuid4().hex}"
        body = _route_body(origin, destination, departure_time)
        response = self._perform("ComputeRoutes", POINT_ENDPOINT, body)
        result = _parse_point(response, request_id, body, effective_context)
        self._circuit.success()
        return result

    def matrix(
        self,
        origins: Sequence[GeoPoint],
        destinations: Sequence[GeoPoint],
        context: DynamicTravelContext | None = None,
        *,
        departure_time: str | None = None,
        request_id: str | None = None,
    ) -> TravelTimeMatrix:
        effective_context = context or DynamicTravelContext()
        if not origins or not destinations:
            return TravelTimeMatrix((), self.name, effective_context)
        request_id = request_id or f"rm-google-{uuid4().hex}"
        body = _matrix_body(origins, destinations, departure_time)
        response = self._perform(
            "ComputeRouteMatrix", MATRIX_ENDPOINT, body, elements=len(origins) * len(destinations)
        )
        result = _parse_matrix(
            response, len(origins), len(destinations), request_id, body, effective_context
        )
        self._circuit.success()
        return result

    def _perform(
        self,
        operation: str,
        endpoint: str,
        body: Mapping[str, object],
        *,
        elements: int = 1,
    ) -> GoogleRoutesResponse:
        api_key = os.environ.get(self.api_key_env)
        if not api_key:
            raise GoogleRoutesError(
                "missing_credentials", "Google Routes credential is not configured"
            )
        self._circuit.check()
        for attempt in range(self.policy.max_retries + 1):
            self._budget.consume(operation, elements)
            self._rate_limiter.wait()
            error: GoogleRoutesError | None = None
            try:
                response = self.transport(
                    operation=operation,
                    endpoint=endpoint,
                    headers=_headers(api_key, operation),
                    body=body,
                    timeout_seconds=self.policy.timeout_seconds,
                )
            except TimeoutError:
                error = GoogleRoutesError("timeout", retryable=True)
            except Exception:  # transport boundary must classify without exposing payloads
                error = GoogleRoutesError("transport_error", retryable=True)
            else:
                error = _response_error(response)
                if error is None:
                    return response
            if error is None:
                raise GoogleRoutesError("unknown_provider_error")
            self._circuit.failure(error)
            if not error.retryable or attempt >= self.policy.max_retries:
                raise error
            self._sleeper(self.policy.retry_backoff_seconds * (2**attempt))
        raise GoogleRoutesError("unreachable")


def _headers(api_key: str, operation: str) -> dict[str, str]:
    field_mask = (
        "routes.distanceMeters,routes.duration,routes.staticDuration"
        if operation == "ComputeRoutes"
        else "originIndex,destinationIndex,distanceMeters,duration,staticDuration,condition,status"
    )
    return {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": field_mask,
    }


def _route_body(
    origin: GeoPoint, destination: GeoPoint, departure_time: str | None
) -> dict[str, object]:
    body: dict[str, object] = {
        "origin": {
            "location": {"latLng": {"latitude": origin.latitude, "longitude": origin.longitude}}
        },
        "destination": {
            "location": {
                "latLng": {"latitude": destination.latitude, "longitude": destination.longitude}
            }
        },
        "travelMode": "DRIVE",
        "routingPreference": "TRAFFIC_AWARE_OPTIMAL",
    }
    if departure_time is not None:
        if not departure_time.strip():
            raise ValueError("departure time must not be blank")
        body["departureTime"] = departure_time
    return body


def _matrix_body(
    origins: Sequence[GeoPoint], destinations: Sequence[GeoPoint], departure_time: str | None
) -> dict[str, object]:
    body: dict[str, object] = {
        "origins": [
            {
                "waypoint": {
                    "location": {
                        "latLng": {"latitude": point.latitude, "longitude": point.longitude}
                    }
                }
            }
            for point in origins
        ],
        "destinations": [
            {
                "waypoint": {
                    "location": {
                        "latLng": {"latitude": point.latitude, "longitude": point.longitude}
                    }
                }
            }
            for point in destinations
        ],
        "travelMode": "DRIVE",
        "routingPreference": "TRAFFIC_AWARE_OPTIMAL",
    }
    if departure_time is not None:
        if not departure_time.strip():
            raise ValueError("departure time must not be blank")
        body["departureTime"] = departure_time
    return body


def _response_error(response: GoogleRoutesResponse) -> GoogleRoutesError | None:
    status = response.status_code
    if 200 <= status < 300:
        return None
    if status in {408, 429}:
        return GoogleRoutesError(
            "rate_limited" if status == 429 else "timeout", status_code=status, retryable=True
        )
    if status in {401, 403}:
        return GoogleRoutesError("auth_or_entitlement", status_code=status)
    if 500 <= status < 600:
        return GoogleRoutesError("provider_5xx", status_code=status, retryable=True)
    return GoogleRoutesError("provider_4xx", status_code=status)


def _parse_point(
    response: GoogleRoutesResponse,
    request_id: str,
    body: Mapping[str, object],
    context: DynamicTravelContext,
) -> TravelTime:
    if not isinstance(response.payload, Mapping):
        raise GoogleRoutesError("malformed_response")
    routes = response.payload.get("routes")
    if not isinstance(routes, list) or not routes or not isinstance(routes[0], Mapping):
        raise GoogleRoutesError("malformed_response")
    route = routes[0]
    distance = _number(route.get("distanceMeters"))
    seconds = _duration_seconds(route.get("duration"))
    if distance is None or seconds is None:
        raise GoogleRoutesError("malformed_response")
    return TravelTime(
        seconds,
        GoogleRoutesProvider.name,
        context=context,
        distance_kilometres=distance / 1000,
        traffic_seconds=seconds,
        request_id=request_id,
        provenance=_provenance("ComputeRoutes", response, request_id, body),
    )


def _parse_matrix(
    response: GoogleRoutesResponse,
    rows: int,
    columns: int,
    request_id: str,
    body: Mapping[str, object],
    context: DynamicTravelContext,
) -> TravelTimeMatrix:
    entries = response.payload
    if isinstance(entries, Mapping):
        entries = entries.get("entries", entries.get("matrix"))
    if not isinstance(entries, list):
        raise GoogleRoutesError("malformed_response")
    cells: dict[tuple[int, int], TravelTime] = {}
    for entry in entries:
        if not isinstance(entry, Mapping):
            continue
        row = _integer(entry.get("originIndex"))
        column = _integer(entry.get("destinationIndex"))
        if row is None or column is None or not (0 <= row < rows and 0 <= column < columns):
            continue
        status = str(entry.get("condition", entry.get("status", "ROUTE_EXISTS"))).upper()
        distance = _number(entry.get("distanceMeters"))
        seconds = _duration_seconds(entry.get("duration"))
        if status not in {"ROUTE_EXISTS", "OK", "SUCCESS"} or distance is None or seconds is None:
            cells[(row, column)] = _matrix_failure(status, request_id, response, body, context)
            continue
        cells[(row, column)] = TravelTime(
            seconds,
            GoogleRoutesProvider.name,
            context=context,
            distance_kilometres=distance / 1000,
            traffic_seconds=seconds,
            request_id=request_id,
            provenance=_provenance("ComputeRouteMatrix", response, request_id, body),
        )
    default_failure = _matrix_failure("MISSING_MATRIX_CELL", request_id, response, body, context)
    values = tuple(
        tuple(cells.get((row, column), default_failure) for column in range(columns))
        for row in range(rows)
    )
    return TravelTimeMatrix(values, GoogleRoutesProvider.name, context)


def _matrix_failure(
    classification: str,
    request_id: str,
    response: GoogleRoutesResponse,
    body: Mapping[str, object],
    context: DynamicTravelContext,
) -> TravelTime:
    return TravelTime(
        0.0,
        GoogleRoutesProvider.name,
        context=context,
        request_id=request_id,
        status="ERROR",
        error_class=_safe_classification(classification),
        provenance=_provenance("ComputeRouteMatrix", response, request_id, body),
    )


def _provenance(
    operation: str, response: GoogleRoutesResponse, request_id: str, body: Mapping[str, object]
) -> tuple[tuple[str, str], ...]:
    return (
        ("provider", "google-maps-routes"),
        ("operation", operation),
        ("request_id", request_id),
        ("request_digest", _body_digest(body)),
        ("response_status", str(response.status_code)),
        ("provider_request_id", response.provider_request_id or "none"),
    )


def _body_digest(body: Mapping[str, object]) -> str:
    encoded = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    return hashlib.sha256(encoded).hexdigest()


def _number(value: object) -> float | None:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not isfinite(float(value))
        or float(value) < 0
    ):
        return None
    return float(value)


def _integer(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def _duration_seconds(value: object) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value) if isfinite(float(value)) and float(value) >= 0 else None
    if not isinstance(value, str) or not value.endswith("s"):
        return None
    try:
        seconds = float(value[:-1])
    except ValueError:
        return None
    return seconds if isfinite(seconds) and seconds >= 0 else None


def _optional_duration(value: object) -> float | None:
    return None if value is None else _duration_seconds(value)


def _safe_classification(value: str) -> str:
    normalized = "".join(char if char.isalnum() else "_" for char in value.upper()).strip("_")
    return normalized[:64] or "UNKNOWN"
