"""Immutable historical-event compatibility adapters for replay consumers."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal

ClockDomain = Literal["WALL", "SIMULATED", "REPLAY"]
PayloadTransform = Callable[[Mapping[str, Any]], Mapping[str, Any]]
_VERSION = re.compile(r"^(?:v)?(?P<major>\d+)(?:\.\d+)?$")


class EventUpcastError(ValueError):
    """Base error with an auditable code for compatibility failures."""

    def __init__(
        self,
        message: str,
        *,
        code: str,
        event_type: str,
        schema_version: int,
        target_version: int | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.event_type = event_type
        self.schema_version = schema_version
        self.target_version = target_version


class UnsupportedEventTypeError(EventUpcastError):
    """The replay consumer has no current read-model contract for an event."""


class UnsupportedEventVersionError(EventUpcastError):
    """The event is newer than the read model or has an invalid version."""


class MissingUpcasterError(EventUpcastError):
    """A version transition has no registered, explicit compatibility step."""


class InvalidUpcasterError(EventUpcastError):
    """A registered transition returned a non-serializable or invalid payload."""


@dataclass(frozen=True, slots=True)
class HistoricalEvent:
    """An immutable event envelope read from a historical archive or stream."""

    event_id: str
    event_type: str
    schema_version: int
    event_time: datetime
    clock_domain: ClockDomain
    payload: Mapping[str, Any]
    trace_id: str | None = None
    reference_data_id: str | None = None
    replay_digest: str | None = None

    def __post_init__(self) -> None:
        if not self.event_id.strip() or not self.event_type.strip():
            raise ValueError("event identity must not be blank")
        if self.schema_version < 1:
            raise ValueError("schema_version must be positive")
        if self.clock_domain not in {"WALL", "SIMULATED", "REPLAY"}:
            raise ValueError("unsupported clock domain")
        if self.event_time.tzinfo is None or self.event_time.utcoffset() is None:
            raise ValueError("event_time must be timezone-aware")
        if not isinstance(self.payload, Mapping):
            raise ValueError("payload must be a mapping")
        if self.trace_id is not None and not self.trace_id.strip():
            raise ValueError("trace_id must not be blank when present")
        if self.reference_data_id is not None and not self.reference_data_id.strip():
            raise ValueError("reference_data_id must not be blank when present")
        if self.replay_digest is not None and not re.fullmatch(r"[0-9a-f]{64}", self.replay_digest):
            raise ValueError("replay_digest must be a lowercase sha256 digest")
        try:
            json.dumps(self.payload, sort_keys=True, separators=(",", ":"))
        except (TypeError, ValueError) as exc:
            raise ValueError("payload must be JSON serializable") from exc

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> HistoricalEvent:
        """Parse the stable archive shape without mutating the source mapping."""

        event_time = value.get("event_time")
        if isinstance(event_time, str):
            event_time = datetime.fromisoformat(event_time.replace("Z", "+00:00"))
        if not isinstance(event_time, datetime):
            raise ValueError("event_time must be an ISO datetime")
        raw_version = value.get("schema_version")
        schema_version = parse_schema_version(raw_version)
        payload = value.get("payload")
        if not isinstance(payload, Mapping):
            raise ValueError("payload must be a mapping")
        return cls(
            event_id=str(value.get("event_id", "")),
            event_type=str(value.get("event_type", "")),
            schema_version=schema_version,
            event_time=event_time,
            clock_domain=value.get("clock_domain", ""),
            payload=dict(payload),
            trace_id=_optional_string(value.get("trace_id")),
            reference_data_id=_optional_string(value.get("reference_data_id")),
            replay_digest=_optional_string(value.get("replay_digest")),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "schema_version": f"v{self.schema_version}",
            "event_time": _format_time(self.event_time),
            "clock_domain": self.clock_domain,
            "trace_id": self.trace_id,
            "reference_data_id": self.reference_data_id,
            "replay_digest": self.replay_digest,
            "payload": dict(self.payload),
        }

    @property
    def event_digest(self) -> str:
        return _digest(self.as_dict())


@dataclass(frozen=True, slots=True)
class UpcastedHistoricalEvent:
    """Current read-model projection plus immutable replay provenance."""

    event: HistoricalEvent
    original_schema_version: int
    upcast_path: tuple[int, ...]
    source_event_digest: str

    def as_read_model(self) -> dict[str, Any]:
        result = self.event.as_dict()
        result.update(
            {
                "original_schema_version": f"v{self.original_schema_version}",
                "upcast_path": tuple(f"v{version}" for version in self.upcast_path),
                "source_event_digest": self.source_event_digest,
                "read_model_digest": _digest(result),
            }
        )
        return result


class EventUpcasterRegistry:
    """Explicit, additive version transitions for replay read models."""

    def __init__(self, current_versions: Mapping[str, int]) -> None:
        self._current_versions = dict(current_versions)
        if not self._current_versions or any(
            not event_type.strip() or version < 1
            for event_type, version in self._current_versions.items()
        ):
            raise ValueError("current_versions must contain positive versions and names")
        self._transforms: dict[tuple[str, int], tuple[int, PayloadTransform]] = {}

    def register(
        self,
        event_type: str,
        from_version: int,
        to_version: int,
        transform: PayloadTransform,
    ) -> None:
        if event_type not in self._current_versions:
            raise ValueError(f"event type is not declared: {event_type}")
        if to_version != from_version + 1 or from_version < 1:
            raise ValueError("upcaster versions must advance exactly one step")
        key = (event_type, from_version)
        if key in self._transforms:
            raise ValueError(f"upcaster already registered: {event_type} v{from_version}")
        self._transforms[key] = (to_version, transform)

    def upcast(self, event: HistoricalEvent) -> UpcastedHistoricalEvent:
        target = self._current_versions.get(event.event_type)
        if target is None:
            raise UnsupportedEventTypeError(
                f"no current read model for {event.event_type}",
                code="unsupported_event_type",
                event_type=event.event_type,
                schema_version=event.schema_version,
            )
        if event.schema_version > target:
            raise UnsupportedEventVersionError(
                f"event {event.event_type} v{event.schema_version} is newer than v{target}",
                code="unsupported_event_version",
                event_type=event.event_type,
                schema_version=event.schema_version,
                target_version=target,
            )
        source_digest = event.event_digest
        payload: Mapping[str, Any] = dict(event.payload)
        version = event.schema_version
        path: list[int] = []
        while version < target:
            transition = self._transforms.get((event.event_type, version))
            if transition is None:
                raise MissingUpcasterError(
                    f"missing upcaster for {event.event_type} v{version}->v{version + 1}",
                    code="missing_upcaster",
                    event_type=event.event_type,
                    schema_version=version,
                    target_version=target,
                )
            next_version, transform = transition
            try:
                transformed = transform(dict(payload))
                if not isinstance(transformed, Mapping):
                    raise TypeError("transform must return a mapping")
                json.dumps(transformed, sort_keys=True, separators=(",", ":"))
            except (TypeError, ValueError) as exc:
                raise InvalidUpcasterError(
                    f"invalid payload from {event.event_type} v{version}->v{next_version}",
                    code="invalid_upcaster_output",
                    event_type=event.event_type,
                    schema_version=version,
                    target_version=target,
                ) from exc
            payload = dict(transformed)
            path.append(next_version)
            version = next_version
        current = HistoricalEvent(
            event_id=event.event_id,
            event_type=event.event_type,
            schema_version=target,
            event_time=event.event_time,
            clock_domain=event.clock_domain,
            payload=payload,
            trace_id=event.trace_id,
            reference_data_id=event.reference_data_id,
            replay_digest=event.replay_digest,
        )
        return UpcastedHistoricalEvent(current, event.schema_version, tuple(path), source_digest)

    def upcast_many(
        self, events: tuple[HistoricalEvent, ...]
    ) -> tuple[UpcastedHistoricalEvent, ...]:
        return tuple(self.upcast(event) for event in events)


def default_event_upcaster_registry() -> EventUpcasterRegistry:
    """Return the bounded compatibility set used by replay API consumers."""

    registry = EventUpcasterRegistry(
        {
            "simulation.started": 1,
            "simulation.paused": 1,
            "simulation.resumed": 1,
            "order.assigned": 2,
            "order.unassigned": 2,
            "dispatch.assignment.applied": 2,
        }
    )
    registry.register("order.assigned", 1, 2, _assignment_v1_to_v2)
    registry.register("order.unassigned", 1, 2, _assignment_v1_to_v2)
    registry.register("dispatch.assignment.applied", 1, 2, _assignment_v1_to_v2)
    return registry


def parse_schema_version(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise ValueError("schema_version must be a positive version")
    match = _VERSION.fullmatch(str(value))
    if match is None:
        raise ValueError("schema_version must look like v1 or 1.0")
    version = int(match.group("major"))
    if version < 1:
        raise ValueError("schema_version must be positive")
    return version


def _assignment_v1_to_v2(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    result = dict(payload)
    if "selected_courier_id" not in result and "courier_id" in result:
        result["selected_courier_id"] = result["courier_id"]
    if "selected_courier_id" not in result:
        raise ValueError("historical assignment has no courier identity")
    result.setdefault("selection_source", "historical-upcast")
    return result


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def _format_time(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _digest(value: Mapping[str, Any]) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


__all__ = [
    "EventUpcastError",
    "EventUpcasterRegistry",
    "HistoricalEvent",
    "InvalidUpcasterError",
    "MissingUpcasterError",
    "UnsupportedEventTypeError",
    "UnsupportedEventVersionError",
    "UpcastedHistoricalEvent",
    "default_event_upcaster_registry",
    "parse_schema_version",
]
