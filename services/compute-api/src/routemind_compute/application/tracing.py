"""Provider-neutral OpenTelemetry runtime with optional OTLP export."""

from __future__ import annotations

import os
import re
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass

from opentelemetry import trace
from opentelemetry.context import Context
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    SimpleSpanProcessor,
    SpanExporter,
)
from opentelemetry.sdk.trace.sampling import ALWAYS_OFF
from opentelemetry.trace import (
    Span,
    SpanContext,
    SpanKind,
    TraceFlags,
    Tracer,
    TraceState,
    get_current_span,
    set_span_in_context,
)
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

type TraceAttribute = str | bool | int | float
type TraceAttributes = Mapping[str, TraceAttribute]
_TRACE_ID = re.compile(r"^[0-9a-f]{32}$")


@dataclass(frozen=True)
class TraceSettings:
    service_name: str = "routemind-compute-api"
    sdk_enabled: bool = True
    otlp_export_enabled: bool = False

    @classmethod
    def from_environment(cls) -> TraceSettings:
        return cls(
            service_name=os.getenv("OTEL_SERVICE_NAME", "routemind-compute-api"),
            sdk_enabled=not _truthy(os.getenv("OTEL_SDK_DISABLED", "false")),
            otlp_export_enabled=_truthy(os.getenv("ROUTEMIND_OTLP_EXPORT_ENABLED", "false")),
        )


class TracingRuntime:
    """Own a tracer provider without requiring a process-global SDK."""

    def __init__(
        self,
        settings: TraceSettings | None = None,
        *,
        span_exporter: SpanExporter | None = None,
    ) -> None:
        self.settings = settings or TraceSettings.from_environment()
        resource = Resource.create(
            {
                "service.name": self.settings.service_name,
                "service.namespace": "routemind",
            }
        )
        if self.settings.sdk_enabled:
            provider = TracerProvider(resource=resource)
        else:
            provider = TracerProvider(resource=resource, sampler=ALWAYS_OFF)
        if span_exporter is not None:
            provider.add_span_processor(SimpleSpanProcessor(span_exporter))
        elif self.settings.otlp_export_enabled:
            provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
        self.provider = provider
        self.tracer = provider.get_tracer("routemind.compute", "v1")
        self.propagator = TraceContextTextMapPropagator()

    def extract(self, carrier: Mapping[str, str]) -> Context:
        normalized = {key.lower(): value for key, value in carrier.items()}
        extracted = self.propagator.extract(normalized)
        if get_current_span(extracted).get_span_context().is_valid:
            return extracted
        legacy_trace_id = normalized.get("x-trace-id", "")
        if not _TRACE_ID.fullmatch(legacy_trace_id):
            return Context()
        span_id = int(legacy_trace_id[-16:], 16) or 1
        remote = SpanContext(
            trace_id=int(legacy_trace_id, 16),
            span_id=span_id,
            is_remote=True,
            trace_flags=TraceFlags(TraceFlags.SAMPLED),
            trace_state=TraceState(),
        )
        return set_span_in_context(trace.NonRecordingSpan(remote), Context())

    @contextmanager
    def start_span(
        self,
        name: str,
        *,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: TraceAttributes | None = None,
        carrier: Mapping[str, str] | None = None,
    ) -> Iterator[Span]:
        parent = self.extract(carrier) if carrier is not None else None
        with self.tracer.start_as_current_span(
            name,
            context=parent,
            kind=kind,
            attributes=attributes,
            record_exception=True,
            set_status_on_exception=True,
        ) as span:
            yield span

    def force_flush(self) -> bool:
        return bool(self.provider.force_flush())


def span_trace_id(span: Span) -> str:
    return f"{span.get_span_context().trace_id:032x}"


def span_traceparent(span: Span) -> str:
    context = span.get_span_context()
    flags = "01" if context.trace_flags.sampled else "00"
    return f"00-{context.trace_id:032x}-{context.span_id:016x}-{flags}"


def _truthy(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


__all__ = [
    "TraceSettings",
    "Tracer",
    "TracingRuntime",
    "span_trace_id",
    "span_traceparent",
]
