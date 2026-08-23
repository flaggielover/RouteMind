from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from routemind_compute.api.app import app
from routemind_compute.application.event_upcasting import (
    EventUpcasterRegistry,
    EventUpcastError,
    HistoricalEvent,
    InvalidUpcasterError,
    MissingUpcasterError,
    UnsupportedEventTypeError,
    UnsupportedEventVersionError,
    default_event_upcaster_registry,
    parse_schema_version,
)

client = TestClient(app)
_TIME = datetime(2026, 8, 24, 12, 0, tzinfo=UTC)


def _event(**overrides: object) -> HistoricalEvent:
    values: dict[str, object] = {
        "event_id": "evt-1",
        "event_type": "order.assigned",
        "schema_version": 1,
        "event_time": _TIME,
        "clock_domain": "REPLAY",
        "payload": {"request_id": "req-1", "courier_id": "courier-1"},
        "trace_id": "trace-1",
        "reference_data_id": "travel:deterministic-local:v1",
        "replay_digest": "a" * 64,
    }
    values.update(overrides)
    return HistoricalEvent(**values)  # type: ignore[arg-type]


def test_assignment_v1_upcasts_without_changing_provenance() -> None:
    source = _event()
    projected = default_event_upcaster_registry().upcast(source)

    assert projected.original_schema_version == 1
    assert projected.upcast_path == (2,)
    assert projected.event.schema_version == 2
    assert projected.event.payload["selected_courier_id"] == "courier-1"
    assert projected.event.clock_domain == source.clock_domain
    assert projected.event.event_time == source.event_time
    assert projected.event.trace_id == source.trace_id
    assert projected.event.reference_data_id == source.reference_data_id
    assert projected.event.replay_digest == source.replay_digest
    assert projected.source_event_digest == source.event_digest
    assert source.schema_version == 1
    assert "selected_courier_id" not in source.payload


def test_current_events_are_identity_projections() -> None:
    source = _event(schema_version=2, payload={"selected_courier_id": "courier-1"})
    projected = default_event_upcaster_registry().upcast(source)
    assert projected.upcast_path == ()
    assert projected.event.as_dict() == source.as_dict()


def test_unknown_versions_and_types_fail_with_auditable_codes() -> None:
    registry = default_event_upcaster_registry()
    with pytest.raises(UnsupportedEventVersionError) as newer:
        registry.upcast(_event(schema_version=3))
    assert newer.value.code == "unsupported_event_version"
    with pytest.raises(UnsupportedEventTypeError) as unknown:
        registry.upcast(_event(event_type="future.event"))
    assert unknown.value.code == "unsupported_event_type"


def test_missing_transition_fails_closed() -> None:
    registry = EventUpcasterRegistry({"order.assigned": 2})
    with pytest.raises(MissingUpcasterError) as missing:
        registry.upcast(_event())
    assert missing.value.code == "missing_upcaster"


def test_schema_version_parser_accepts_contract_forms() -> None:
    assert parse_schema_version("v1") == 1
    assert parse_schema_version("1.0") == 1
    with pytest.raises(ValueError, match="positive"):
        parse_schema_version("v0")


def test_replay_upcast_api_returns_projection_and_trace() -> None:
    response = client.post(
        "/api/v1/replay/upcast",
        headers={"X-Trace-Id": "b" * 32},
        json={
            "events": [
                {
                    "event_id": "evt-api",
                    "event_type": "order.assigned",
                    "schema_version": "v1",
                    "event_time": _TIME.isoformat(),
                    "clock_domain": "REPLAY",
                    "payload": {"courier_id": "courier-api"},
                    "trace_id": "trace-api",
                    "reference_data_id": "travel:deterministic-local:v1",
                    "replay_digest": "c" * 64,
                }
            ]
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "replay-compatibility"
    assert body["trace_id"] == "b" * 32
    assert body["events"][0]["schema_version"] == "v2"
    assert body["events"][0]["payload"]["selected_courier_id"] == "courier-api"
    assert body["events"][0]["clock_domain"] == "REPLAY"


def test_replay_upcast_api_rejects_unknown_version() -> None:
    response = client.post(
        "/api/v1/replay/upcast",
        json={
            "events": [
                {
                    "event_id": "evt-new",
                    "event_type": "order.assigned",
                    "schema_version": 3,
                    "event_time": _TIME.isoformat(),
                    "clock_domain": "REPLAY",
                    "payload": {"selected_courier_id": "courier-api"},
                }
            ]
        },
    )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "unsupported_event_version"


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("event_id", " ", "identity"),
        ("schema_version", 0, "positive"),
        ("clock_domain", "UNKNOWN", "clock"),
        ("event_time", datetime(2026, 8, 24, 12), "timezone"),
        ("payload", ("not", "a", "mapping"), "mapping"),
        ("trace_id", " ", "trace_id"),
        ("reference_data_id", " ", "reference_data_id"),
        ("replay_digest", "z" * 64, "replay_digest"),
        ("payload", {"bad": object()}, "JSON"),
    ],
)
def test_historical_event_rejects_invalid_contract_fields(
    field: str, value: object, message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        _event(**{field: value})


@pytest.mark.parametrize(
    "value",
    [
        {"event_time": "not-a-time", "schema_version": 1, "payload": {}},
        {"event_time": _TIME, "schema_version": "nope", "payload": {}},
        {"event_time": _TIME, "schema_version": 1, "payload": []},
    ],
)
def test_historical_event_mapping_parser_rejects_malformed_input(value: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        HistoricalEvent.from_mapping(value)


def test_registry_registration_and_transform_failures_are_explicit() -> None:
    with pytest.raises(ValueError, match="positive"):
        EventUpcasterRegistry({})
    with pytest.raises(ValueError, match="positive"):
        EventUpcasterRegistry({"event": 0})
    registry = EventUpcasterRegistry({"event": 2})
    with pytest.raises(ValueError, match="declared"):
        registry.register("missing", 1, 2, lambda payload: payload)
    with pytest.raises(ValueError, match="exactly one"):
        registry.register("event", 1, 3, lambda payload: payload)
    registry.register(
        "event",
        1,
        2,
        lambda payload: "not a mapping",  # type: ignore[arg-type,return-value]
    )
    with pytest.raises(ValueError, match="already registered"):
        registry.register("event", 1, 2, lambda payload: payload)
    with pytest.raises(InvalidUpcasterError, match="invalid payload") as invalid:
        registry.upcast(_event(event_type="event"))
    assert invalid.value.code == "invalid_upcaster_output"


def test_assignment_upcaster_requires_courier_identity() -> None:
    with pytest.raises(EventUpcastError, match="invalid payload") as invalid:
        default_event_upcaster_registry().upcast(_event(payload={"request_id": "req-1"}))
    assert invalid.value.code == "invalid_upcaster_output"
