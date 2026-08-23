"""Central semantic metric definitions over reproducible analytical marts."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

import duckdb

MetricConsumer = Literal["web", "report", "agent"]
MetricValueType = Literal["count", "ratio"]
MetricStatus = Literal["available", "unavailable"]

_CONSUMERS: tuple[MetricConsumer, ...] = ("web", "report", "agent")
_ALLOWED_VIEWS = {
    "fact_event",
    "fact_order",
    "fact_decision",
    "fact_solver_run",
    "fact_simulation_run",
}


class MetricError(ValueError):
    """Base error for semantic metric contract violations."""


class UnknownMetricError(MetricError):
    """Raised when a caller asks for a metric outside the registry."""


class MetricStoreUnavailableError(MetricError):
    """Raised when the analytical mart is not available for reading."""


@dataclass(frozen=True)
class MetricDefinition:
    """A versioned executable definition shared by every metric consumer."""

    name: str
    display_name: str
    description: str
    unit: str
    value_type: MetricValueType
    source_view: str
    source_fields: tuple[str, ...]
    aggregation: str
    numerator: str
    denominator: str | None
    time_semantics: str
    unavailable_when: str
    consumers: tuple[MetricConsumer, ...] = _CONSUMERS
    numerator_sql: str = field(repr=False, compare=False, default="count(*)")
    denominator_sql: str | None = field(repr=False, compare=False, default=None)

    def __post_init__(self) -> None:
        if self.source_view not in _ALLOWED_VIEWS:
            raise MetricError(f"metric source view is not allowed: {self.source_view}")
        if not self.name or not self.source_fields:
            raise MetricError("metric name and source fields are required")
        if self.value_type == "ratio" and self.denominator_sql is None:
            raise MetricError(f"ratio metric requires denominator SQL: {self.name}")
        if self.value_type == "count" and self.denominator_sql is not None:
            raise MetricError(f"count metric cannot define denominator SQL: {self.name}")
        if set(self.consumers) != set(_CONSUMERS):
            raise MetricError(f"metric must serve every semantic consumer: {self.name}")
        for expression in (self.numerator_sql, self.denominator_sql):
            if expression is not None and ";" in expression:
                raise MetricError(
                    f"metric SQL expression contains a statement delimiter: {self.name}"
                )

    @property
    def definition_digest(self) -> str:
        encoded = json.dumps(
            self._definition_payload(), sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode()
        return hashlib.sha256(encoded).hexdigest()

    def contract(self) -> dict[str, Any]:
        """Return the public contract without exposing executable SQL."""

        payload = self._public_payload()
        payload["definition_digest"] = self.definition_digest
        return payload

    def _public_payload(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "unit": self.unit,
            "value_type": self.value_type,
            "source_view": self.source_view,
            "source_fields": self.source_fields,
            "aggregation": self.aggregation,
            "numerator": self.numerator,
            "denominator": self.denominator,
            "time_semantics": self.time_semantics,
            "unavailable_when": self.unavailable_when,
            "consumers": self.consumers,
        }

    def _definition_payload(self) -> dict[str, Any]:
        payload = self._public_payload()
        payload["numerator_sql"] = self.numerator_sql
        payload["denominator_sql"] = self.denominator_sql
        return payload


@dataclass(frozen=True)
class MetricResult:
    name: str
    value: float | None
    numerator: float
    denominator: float | None
    status: MetricStatus
    unavailable_reason: str | None
    window_start: datetime
    window_end: datetime
    definition_digest: str


_DEFINITIONS: tuple[MetricDefinition, ...] = (
    MetricDefinition(
        name="archived_event_count",
        display_name="Archived events",
        description="Immutable analytical records observed in the selected event-time window.",
        unit="event",
        value_type="count",
        source_view="fact_event",
        source_fields=("event_time", "record_id"),
        aggregation="COUNT of records in the UTC event-time window",
        numerator="all unique archived records",
        denominator=None,
        time_semantics="event_time >= start and event_time < end, normalized to UTC",
        unavailable_when="never; an empty window returns zero",
    ),
    MetricDefinition(
        name="order_count",
        display_name="Orders",
        description="Order records observed in the selected event-time window.",
        unit="order",
        value_type="count",
        source_view="fact_order",
        source_fields=("event_time", "record_id"),
        aggregation="COUNT of order records in the UTC event-time window",
        numerator="all order records",
        denominator=None,
        time_semantics="event_time >= start and event_time < end, normalized to UTC",
        unavailable_when="never; an empty window returns zero",
    ),
    MetricDefinition(
        name="dispatch_decision_count",
        display_name="Dispatch decisions",
        description="Durably archived dispatch decision observations in the time window.",
        unit="decision",
        value_type="count",
        source_view="fact_decision",
        source_fields=("event_time", "decision_id"),
        aggregation="COUNT of dispatch decision records in the UTC event-time window",
        numerator="all dispatch decision records",
        denominator=None,
        time_semantics="event_time >= start and event_time < end, normalized to UTC",
        unavailable_when="never; an empty window returns zero",
    ),
    MetricDefinition(
        name="dispatch_assignment_rate",
        display_name="Dispatch assignment rate",
        description="Share of dispatch decisions that selected a non-empty courier identifier.",
        unit="ratio",
        value_type="ratio",
        source_view="fact_decision",
        source_fields=("event_time", "payload.selected_courier"),
        aggregation="assigned decisions divided by all dispatch decisions",
        numerator="decisions with a non-empty payload.selected_courier",
        denominator="all dispatch decision records",
        time_semantics="event_time >= start and event_time < end, normalized to UTC",
        unavailable_when="no dispatch decisions exist in the window",
        numerator_sql=(
            "count(*) FILTER (WHERE nullif(trim(json_extract_string("
            "payload_json, '$.selected_courier')), '') IS NOT NULL)"
        ),
        denominator_sql="count(*)",
    ),
    MetricDefinition(
        name="dispatch_fallback_rate",
        display_name="Dispatch fallback rate",
        description="Share of decisions with an explicit fallback flag that used fallback.",
        unit="ratio",
        value_type="ratio",
        source_view="fact_decision",
        source_fields=("event_time", "payload.fallback_used"),
        aggregation="fallback=true decisions divided by decisions with a valid boolean flag",
        numerator="decisions where payload.fallback_used parses as true",
        denominator="decisions where payload.fallback_used parses as a boolean",
        time_semantics="event_time >= start and event_time < end, normalized to UTC",
        unavailable_when="no decision has a valid boolean payload.fallback_used value",
        numerator_sql=(
            "count(*) FILTER (WHERE try_cast(json_extract_string("
            "payload_json, '$.fallback_used') AS BOOLEAN) IS TRUE)"
        ),
        denominator_sql=(
            "count(*) FILTER (WHERE try_cast(json_extract_string("
            "payload_json, '$.fallback_used') AS BOOLEAN) IS NOT NULL)"
        ),
    ),
    MetricDefinition(
        name="solver_success_rate",
        display_name="Solver success rate",
        description="Share of solver runs with a recognized status that completed successfully.",
        unit="ratio",
        value_type="ratio",
        source_view="fact_solver_run",
        source_fields=("event_time", "payload.status"),
        aggregation="successful runs divided by runs with a recognized terminal status",
        numerator="runs where lowercase payload.status is success or succeeded",
        denominator="runs where lowercase payload.status is success, succeeded, failed, or error",
        time_semantics="event_time >= start and event_time < end, normalized to UTC",
        unavailable_when="no solver run has a recognized terminal status",
        numerator_sql=(
            "count(*) FILTER (WHERE lower(json_extract_string(payload_json, '$.status')) "
            "IN ('success', 'succeeded'))"
        ),
        denominator_sql=(
            "count(*) FILTER (WHERE lower(json_extract_string(payload_json, '$.status')) "
            "IN ('success', 'succeeded', 'failed', 'error'))"
        ),
    ),
    MetricDefinition(
        name="simulation_completion_rate",
        display_name="Simulation completion rate",
        description="Share of simulation runs with a recognized status that completed.",
        unit="ratio",
        value_type="ratio",
        source_view="fact_simulation_run",
        source_fields=("event_time", "payload.status"),
        aggregation="completed runs divided by runs with a recognized terminal status",
        numerator="runs where lowercase payload.status is completed",
        denominator="runs where lowercase payload.status is completed, failed, or cancelled",
        time_semantics="event_time >= start and event_time < end, normalized to UTC",
        unavailable_when="no simulation run has a recognized terminal status",
        numerator_sql=(
            "count(*) FILTER (WHERE lower(json_extract_string(payload_json, '$.status')) "
            "= 'completed')"
        ),
        denominator_sql=(
            "count(*) FILTER (WHERE lower(json_extract_string(payload_json, '$.status')) "
            "IN ('completed', 'failed', 'cancelled'))"
        ),
    ),
)

_REGISTRY = {definition.name: definition for definition in _DEFINITIONS}
if len(_REGISTRY) != len(_DEFINITIONS):
    raise RuntimeError("semantic metric names must be unique")


def metric_catalog(consumer: MetricConsumer | None = None) -> tuple[MetricDefinition, ...]:
    if consumer is not None and consumer not in _CONSUMERS:
        raise MetricError(f"unsupported metric consumer: {consumer}")
    return tuple(
        definition
        for definition in _DEFINITIONS
        if consumer is None or consumer in definition.consumers
    )


def metric_definition(name: str) -> MetricDefinition:
    try:
        return _REGISTRY[name]
    except KeyError as exc:
        raise UnknownMetricError(f"unknown semantic metric: {name}") from exc


class SemanticMetricEngine:
    """Evaluate registry-owned queries against a read-only DuckDB mart."""

    def __init__(self, database_path: Path | str) -> None:
        self.database_path = Path(database_path).expanduser().resolve()

    def evaluate(
        self, names: tuple[str, ...], start: datetime, end: datetime
    ) -> tuple[MetricResult, ...]:
        if not names:
            raise MetricError("at least one metric name is required")
        window_start, window_end = _validated_window(start, end)
        definitions = tuple(metric_definition(name) for name in names)
        if not self.database_path.is_file():
            raise MetricStoreUnavailableError(f"analytical mart missing: {self.database_path}")

        with duckdb.connect(str(self.database_path), read_only=True) as connection:
            return tuple(
                self._evaluate_definition(connection, definition, window_start, window_end)
                for definition in definitions
            )

    @staticmethod
    def _evaluate_definition(
        connection: duckdb.DuckDBPyConnection,
        definition: MetricDefinition,
        start: datetime,
        end: datetime,
    ) -> MetricResult:
        denominator_expression = definition.denominator_sql or "NULL"
        query = (
            f"SELECT ({definition.numerator_sql})::DOUBLE, "
            f"({denominator_expression})::DOUBLE FROM {definition.source_view} "
            "WHERE event_time >= ? AND event_time < ?"
        )
        row = connection.execute(query, [start, end]).fetchone()
        if row is None:
            raise MetricStoreUnavailableError(f"metric query returned no row: {definition.name}")
        numerator = float(row[0] or 0.0)
        denominator = float(row[1]) if row[1] is not None else None
        if definition.value_type == "ratio" and (denominator is None or denominator == 0):
            return MetricResult(
                name=definition.name,
                value=None,
                numerator=numerator,
                denominator=denominator or 0.0,
                status="unavailable",
                unavailable_reason="no_eligible_records",
                window_start=start,
                window_end=end,
                definition_digest=definition.definition_digest,
            )
        value = numerator if denominator is None else numerator / denominator
        return MetricResult(
            name=definition.name,
            value=value,
            numerator=numerator,
            denominator=denominator,
            status="available",
            unavailable_reason=None,
            window_start=start,
            window_end=end,
            definition_digest=definition.definition_digest,
        )


def _validated_window(start: datetime, end: datetime) -> tuple[datetime, datetime]:
    for field_name, value in (("start", start), ("end", end)):
        if value.tzinfo is None or value.utcoffset() is None:
            raise MetricError(f"metric window {field_name} must be timezone-aware")
    normalized_start = start.astimezone(UTC)
    normalized_end = end.astimezone(UTC)
    if normalized_start >= normalized_end:
        raise MetricError("metric window start must be before end")
    return normalized_start, normalized_end


__all__ = [
    "MetricConsumer",
    "MetricDefinition",
    "MetricError",
    "MetricResult",
    "MetricStoreUnavailableError",
    "SemanticMetricEngine",
    "UnknownMetricError",
    "metric_catalog",
    "metric_definition",
]
