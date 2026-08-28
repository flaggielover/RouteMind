from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from routemind_compute.application import google_routes
from routemind_compute.application.google_routes import (
    GoogleRoutesError,
    GoogleRoutesPolicy,
    GoogleRoutesProvider,
    GoogleRoutesResponse,
)
from routemind_compute.application.travel import (
    DeterministicLocalTravelProvider,
    FallbackTravelTimeProvider,
)
from routemind_compute.domain.dispatch import GeoPoint

ORIGIN = GeoPoint(35.681236, 139.767125)
DESTINATION = GeoPoint(35.689592, 139.700413)


class FakeTransport:
    def __init__(self, responses: Sequence[GoogleRoutesResponse | Exception]) -> None:
        self.responses = list(responses)
        self.calls: list[dict[str, object]] = []

    def __call__(self, **kwargs: object) -> GoogleRoutesResponse:
        self.calls.append(kwargs)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def _provider(transport: FakeTransport, **overrides: object) -> GoogleRoutesProvider:
    policy_kwargs: dict[str, Any] = {"rate_limit_per_second": 0, **overrides}
    policy = GoogleRoutesPolicy(**policy_kwargs)
    return GoogleRoutesProvider(transport, policy=policy)


def _point_response() -> GoogleRoutesResponse:
    return GoogleRoutesResponse(
        200,
        {"routes": [{"distanceMeters": 4200, "duration": "600s", "staticDuration": "720s"}]},
        "provider-request-1",
    )


def test_point_route_serializes_minimal_request_and_normalizes_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ROUTEMIND_GOOGLE_ROUTES_API_KEY", "unit-test-key")
    transport = FakeTransport([_point_response()])
    provider = _provider(transport)

    result = provider.estimate(
        ORIGIN, DESTINATION, departure_time="2026-08-28T04:00:00Z", request_id="opaque-1"
    )

    assert result.provider == "google-routes"
    assert result.seconds == 600
    assert result.distance_kilometres == pytest.approx(4.2)
    assert result.traffic_seconds == 600
    assert result.request_id == "opaque-1"
    assert dict(result.provenance)["operation"] == "ComputeRoutes"
    call = transport.calls[0]
    body = call["body"]
    assert isinstance(body, Mapping)
    assert body["travelMode"] == "DRIVE"
    assert "departureTime" in body
    assert "tenant_id" not in str(body)
    assert "X-Goog-Api-Key" in call["headers"]  # type: ignore[operator]


def test_matrix_success_and_partial_failure_are_cell_explicit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ROUTEMIND_GOOGLE_ROUTES_API_KEY", "unit-test-key")
    response = GoogleRoutesResponse(
        200,
        [
            {
                "originIndex": 0,
                "destinationIndex": 0,
                "distanceMeters": 1000,
                "duration": "100s",
                "condition": "ROUTE_EXISTS",
            },
            {"originIndex": 0, "destinationIndex": 1, "condition": "ROUTE_NOT_FOUND"},
        ],
    )
    provider = _provider(FakeTransport([response]))

    matrix = provider.matrix((ORIGIN,), (DESTINATION, ORIGIN), request_id="opaque-matrix")

    assert matrix.provider == "google-routes"
    assert matrix.values[0][0].seconds == 100
    assert matrix.values[0][0].distance_kilometres == 1
    assert matrix.values[0][1].status == "ERROR"
    assert matrix.values[0][1].error_class == "ROUTE_NOT_FOUND"
    assert matrix.values[0][1].request_id == "opaque-matrix"


def test_missing_credentials_and_http_classes_are_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ROUTEMIND_GOOGLE_ROUTES_API_KEY", raising=False)
    with pytest.raises(GoogleRoutesError, match="credential") as missing:
        _provider(FakeTransport([_point_response()])).estimate(ORIGIN, DESTINATION)
    assert missing.value.classification == "missing_credentials"

    monkeypatch.setenv("ROUTEMIND_GOOGLE_ROUTES_API_KEY", "unit-test-key")
    for status, classification in (
        (401, "auth_or_entitlement"),
        (403, "auth_or_entitlement"),
        (429, "rate_limited"),
        (503, "provider_5xx"),
    ):
        with pytest.raises(GoogleRoutesError) as error:
            _provider(FakeTransport([GoogleRoutesResponse(status, {})]), max_retries=0).estimate(
                ORIGIN, DESTINATION
            )
        assert error.value.classification == classification


def test_retry_is_bounded_and_budget_counts_each_provider_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ROUTEMIND_GOOGLE_ROUTES_API_KEY", "unit-test-key")
    transport = FakeTransport([GoogleRoutesResponse(503, {}), _point_response()])
    provider = _provider(transport, max_retries=1, retry_backoff_seconds=0)

    result = provider.estimate(ORIGIN, DESTINATION)

    assert result.status == "OK"
    assert provider.budget_snapshot["point_requests"] == 2
    assert len(transport.calls) == 2


def test_budget_limits_matrix_elements_and_point_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ROUTEMIND_GOOGLE_ROUTES_API_KEY", "unit-test-key")
    provider = _provider(
        FakeTransport([GoogleRoutesResponse(200, [])]),
        max_matrix_requests=1,
        max_matrix_elements=1,
    )
    with pytest.raises(GoogleRoutesError, match="element"):
        provider.matrix((ORIGIN,), (DESTINATION, ORIGIN))

    point_provider = _provider(FakeTransport([_point_response()]), max_point_requests=1)
    point_provider.estimate(ORIGIN, DESTINATION)
    with pytest.raises(GoogleRoutesError, match="point"):
        point_provider.estimate(ORIGIN, DESTINATION)


def test_circuit_breaker_and_fallback_are_explicit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ROUTEMIND_GOOGLE_ROUTES_API_KEY", "unit-test-key")
    transport = FakeTransport([GoogleRoutesResponse(503, {})] * 3)
    provider = _provider(transport, max_retries=0, circuit_failure_threshold=2)
    for _ in range(2):
        with pytest.raises(GoogleRoutesError):
            provider.estimate(ORIGIN, DESTINATION)
    with pytest.raises(GoogleRoutesError) as open_error:
        provider.estimate(ORIGIN, DESTINATION)
    assert open_error.value.classification == "circuit_open"

    monkeypatch.delenv("ROUTEMIND_GOOGLE_ROUTES_API_KEY", raising=False)
    fallback = FallbackTravelTimeProvider(provider, DeterministicLocalTravelProvider())
    result = fallback.estimate(ORIGIN, DESTINATION)
    assert result.fallback_used is True
    assert result.provider == "deterministic-local"
    assert result.fallback_reason == "missing_credentials"


def test_matrix_budget_is_one_logical_request_and_body_has_no_business_identifiers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ROUTEMIND_GOOGLE_ROUTES_API_KEY", "unit-test-key")
    transport = FakeTransport([GoogleRoutesResponse(200, [])])
    provider = _provider(transport)
    provider.matrix((ORIGIN, DESTINATION), (ORIGIN, DESTINATION))

    assert provider.budget_snapshot["matrix_requests"] == 1
    assert provider.budget_snapshot["matrix_elements"] == 4
    body = transport.calls[0]["body"]
    assert isinstance(body, Mapping)
    serialized = str(body)
    for forbidden in (
        "tenant",
        "customer",
        "courier",
        "merchant",
        "order",
        "phone",
        "email",
        "name",
    ):
        assert forbidden not in serialized.lower()


def test_policy_and_request_boundaries_reject_invalid_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    invalid = (
        {"timeout_seconds": 0},
        {"max_retries": -1},
        {"retry_backoff_seconds": -1},
        {"max_point_requests": 0},
        {"max_duration_seconds": -1},
        {"max_spend_usd": 0},
        {"rate_limit_per_second": -1},
    )
    for kwargs in invalid:
        with pytest.raises(ValueError):
            GoogleRoutesPolicy(**kwargs)
    with pytest.raises(ValueError, match="environment"):
        GoogleRoutesProvider(FakeTransport([]), api_key_env=" ")
    monkeypatch.setenv("ROUTEMIND_GOOGLE_ROUTES_API_KEY", "unit-test-key")
    provider = _provider(FakeTransport([GoogleRoutesResponse(200, [])]))
    assert provider.matrix((), (DESTINATION,)).values == ()
    with pytest.raises(ValueError, match="departure"):
        provider.estimate(ORIGIN, DESTINATION, departure_time=" ")
    with pytest.raises(ValueError, match="departure"):
        provider.matrix((ORIGIN,), (DESTINATION,), departure_time=" ")


def test_transport_malformed_and_unknown_responses_are_classified(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ROUTEMIND_GOOGLE_ROUTES_API_KEY", "unit-test-key")
    for response in (
        GoogleRoutesResponse(200, None),
        GoogleRoutesResponse(200, {"routes": []}),
        GoogleRoutesResponse(200, {"routes": [{"distanceMeters": "bad", "duration": "x"}]}),
    ):
        with pytest.raises(GoogleRoutesError) as error:
            _provider(FakeTransport([response])).estimate(ORIGIN, DESTINATION)
        assert error.value.classification == "malformed_response"
    with pytest.raises(GoogleRoutesError) as transport_error:
        _provider(FakeTransport([RuntimeError("hidden")]), max_retries=0).estimate(
            ORIGIN, DESTINATION
        )
    assert transport_error.value.classification == "transport_error"
    with pytest.raises(GoogleRoutesError) as client_error:
        _provider(FakeTransport([GoogleRoutesResponse(400, {})]), max_retries=0).estimate(
            ORIGIN, DESTINATION
        )
    assert client_error.value.classification == "provider_4xx"


def test_matrix_mapping_payload_and_missing_cells_are_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ROUTEMIND_GOOGLE_ROUTES_API_KEY", "unit-test-key")
    response = GoogleRoutesResponse(
        200,
        {
            "entries": [
                {"originIndex": "bad", "destinationIndex": 0},
                {"originIndex": 0, "destinationIndex": 9},
                {
                    "originIndex": 0,
                    "destinationIndex": 0,
                    "distanceMeters": 1,
                    "duration": 1,
                    "status": "OK",
                },
            ]
        },
    )
    matrix = _provider(FakeTransport([response])).matrix((ORIGIN,), (DESTINATION,))
    assert matrix.values[0][0].seconds == 1
    missing = _provider(FakeTransport([GoogleRoutesResponse(200, {"entries": []})])).matrix(
        (ORIGIN,), (DESTINATION,)
    )
    assert missing.values[0][0].error_class == "MISSING_MATRIX_CELL"
    with pytest.raises(GoogleRoutesError, match="malformed"):
        _provider(FakeTransport([GoogleRoutesResponse(200, {"entries": {}})])).matrix(
            (ORIGIN,), (DESTINATION,)
        )
    assert google_routes._safe_classification(" ") == "UNKNOWN"


def test_budget_clock_rate_wait_and_circuit_reset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ROUTEMIND_GOOGLE_ROUTES_API_KEY", "unit-test-key")
    now = [0.0]
    sleeps: list[float] = []

    def clock() -> float:
        return now[0]

    def sleeper(delay: float) -> None:
        sleeps.append(delay)
        now[0] += delay

    transport = FakeTransport([GoogleRoutesResponse(503, {}), GoogleRoutesResponse(503, {})])
    provider = GoogleRoutesProvider(
        transport,
        policy=GoogleRoutesPolicy(
            rate_limit_per_second=2,
            max_retries=0,
            circuit_failure_threshold=1,
            circuit_reset_seconds=1,
            max_duration_seconds=10,
        ),
        clock=clock,
        sleeper=sleeper,
    )
    with pytest.raises(GoogleRoutesError):
        provider.estimate(ORIGIN, DESTINATION)
    with pytest.raises(GoogleRoutesError, match="circuit"):
        provider.estimate(ORIGIN, DESTINATION)
    now[0] += 1
    with pytest.raises(GoogleRoutesError):
        provider.estimate(ORIGIN, DESTINATION)
    rate_provider = GoogleRoutesProvider(
        FakeTransport([_point_response(), _point_response()]),
        policy=GoogleRoutesPolicy(rate_limit_per_second=2),
        clock=clock,
        sleeper=sleeper,
    )
    rate_provider.estimate(ORIGIN, DESTINATION)
    rate_provider.estimate(ORIGIN, DESTINATION)
    assert sleeps

    expired_now = [0.0]
    expired = GoogleRoutesProvider(
        FakeTransport([_point_response()]),
        policy=GoogleRoutesPolicy(rate_limit_per_second=0, max_duration_seconds=1),
        clock=lambda: expired_now[0],
    )
    expired_now[0] = 2.0
    with pytest.raises(GoogleRoutesError, match="time budget"):
        expired.estimate(ORIGIN, DESTINATION)
