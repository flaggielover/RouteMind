from __future__ import annotations

from collections.abc import Sequence

import pytest
from fastapi.testclient import TestClient
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import SpanKind

from routemind_compute.api.app import create_app
from routemind_compute.api.runtime import create_runtime
from routemind_compute.application.nearest import NearestStrategy
from routemind_compute.application.registry import StrategyRegistry
from routemind_compute.application.telemetry import (
    TENANT_KEY_HEADER,
    TelemetrySettings,
    TenantTelemetryAttribution,
)
from routemind_compute.application.tracing import (
    TraceSettings,
    TracingRuntime,
    span_trace_id,
    span_traceparent,
)
from routemind_compute.application.travel import (
    DeterministicLocalTravelProvider,
    TracedTravelTimeProvider,
)
from routemind_compute.domain.dispatch import CourierCandidate, DispatchProblem, GeoPoint

TRACE_ID = "11111111111111111111111111111111"
PARENT_SPAN_ID = "2222222222222222"


def _runtime() -> tuple[TracingRuntime, InMemorySpanExporter]:
    exporter = InMemorySpanExporter()
    runtime = TracingRuntime(TraceSettings(service_name="test-compute"), span_exporter=exporter)
    return runtime, exporter


def _problem() -> DispatchProblem:
    return DispatchProblem(
        request_id="trace-decision-1",
        pickup=GeoPoint(31.2304, 121.4737),
        candidates=(CourierCandidate("courier-1", GeoPoint(31.2305, 121.4738)),),
    )


def test_w3c_and_legacy_context_create_real_parent_child_relationships() -> None:
    runtime, exporter = _runtime()
    with runtime.start_span(
        "http-parented",
        kind=SpanKind.SERVER,
        carrier={"traceparent": f"00-{TRACE_ID}-{PARENT_SPAN_ID}-01"},
    ) as span:
        assert span_trace_id(span) == TRACE_ID
        assert span_traceparent(span).startswith(f"00-{TRACE_ID}-")
    with runtime.start_span("legacy-parented", carrier={"X-Trace-Id": TRACE_ID}) as span:
        assert span_trace_id(span) == TRACE_ID

    spans = exporter.get_finished_spans()
    assert spans[0].parent is not None and f"{spans[0].parent.span_id:016x}" == PARENT_SPAN_ID
    assert spans[1].parent is not None and spans[1].parent.is_remote


def test_http_span_preserves_trace_and_business_identifiers() -> None:
    tracing, exporter = _runtime()
    client = TestClient(create_app(create_runtime(tracing)))

    response = client.get(
        "/healthz",
        headers={
            "traceparent": f"00-{TRACE_ID}-{PARENT_SPAN_ID}-01",
            "X-Request-Id": "request-http-1",
            "X-Correlation-Id": "correlation-http-1",
        },
    )

    assert response.status_code == 200
    assert response.headers["X-Trace-Id"] == TRACE_ID
    assert response.headers["traceparent"].startswith(f"00-{TRACE_ID}-")
    http_span = next(span for span in exporter.get_finished_spans() if span.name == "GET /healthz")
    assert http_span.kind is SpanKind.SERVER
    http_attributes = http_span.attributes
    assert http_attributes is not None
    assert http_attributes["routemind.request_id"] == "request-http-1"
    assert http_attributes["routemind.correlation_id"] == "correlation-http-1"
    assert http_attributes["http.response.status_code"] == 200


def test_solver_decision_and_travel_boundaries_share_current_trace() -> None:
    runtime, exporter = _runtime()
    registry = StrategyRegistry((NearestStrategy(),), tracer=runtime.tracer)
    travel = TracedTravelTimeProvider(DeterministicLocalTravelProvider(), tracer=runtime.tracer)

    with runtime.start_span("workflow-root"):
        decision = registry.solve("nearest", _problem())
        estimate = travel.estimate(GeoPoint(31.23, 121.47), GeoPoint(31.24, 121.48))
        matrix = travel.matrix((GeoPoint(31.23, 121.47),), (GeoPoint(31.24, 121.48),))

    assert decision.courier_id == "courier-1"
    assert estimate.seconds > 0
    assert matrix.metadata["rows"] == 1
    spans = {span.name: span for span in exporter.get_finished_spans()}
    solver_attributes = spans["routemind.solver.solve"].attributes
    verification_attributes = spans["routemind.decision.verify"].attributes
    estimate_attributes = spans["routemind.travel.estimate"].attributes
    matrix_attributes = spans["routemind.travel.matrix"].attributes
    assert solver_attributes is not None
    assert verification_attributes is not None
    assert estimate_attributes is not None
    assert matrix_attributes is not None
    assert solver_attributes["routemind.request_id"] == "trace-decision-1"
    assert verification_attributes["routemind.decision.valid"] is True
    assert estimate_attributes["routemind.travel.fallback_used"] is False
    assert matrix_attributes["routemind.travel.origins"] == 1
    contexts = tuple(span.context for span in spans.values())
    assert all(context is not None for context in contexts)
    assert len({context.trace_id for context in contexts if context is not None}) == 1


def test_disabled_sdk_and_invalid_carrier_do_not_fake_exported_context() -> None:
    exporter = InMemorySpanExporter()
    runtime = TracingRuntime(
        TraceSettings(service_name="disabled", sdk_enabled=False), span_exporter=exporter
    )
    with runtime.start_span("disabled", carrier={"traceparent": "invalid"}) as span:
        assert span.is_recording() is False
    assert exporter.get_finished_spans() == ()


def test_message_context_injection_and_simulation_experiment_spans_are_correlated() -> None:
    tracing, exporter = _runtime()
    telemetry = TenantTelemetryAttribution(TelemetrySettings(max_active_tenant_keys=2))
    client = TestClient(create_app(create_runtime(tracing, telemetry)))
    tenant_key = "rtk_0123456789abcdef01234567"

    response = client.post(
        "/api/v1/twin/control",
        headers={
            "traceparent": f"00-{TRACE_ID}-{PARENT_SPAN_ID}-01",
            TENANT_KEY_HEADER: tenant_key,
        },
        json={"command_id": "trace-simulation", "action": "reset"},
    )
    assert response.status_code == 200
    response = client.post(
        "/api/v1/experiments/routebench",
        headers={
            "traceparent": f"00-{TRACE_ID}-{PARENT_SPAN_ID}-01",
            TENANT_KEY_HEADER: tenant_key,
        },
        json={
            "manifest_id": "trace-manifest",
            "code_version": "git:test",
            "scenario_id": "trace-scenario",
            "seed": 7,
            "load_profile": "tiny",
            "city_state": "fixture",
            "dataset_provenance": "fixture:test",
            "strategies": ["nearest"],
            "demands": [
                {
                    "request_id": "trace-demand",
                    "pickup": {"latitude": 31.2304, "longitude": 121.4737},
                    "tick": 0,
                }
            ],
            "couriers": [
                {
                    "courier_id": "trace-courier",
                    "location": {"latitude": 31.231, "longitude": 121.474},
                }
            ],
        },
    )
    assert response.status_code == 200

    spans = exporter.get_finished_spans()
    names = {span.name for span in spans}
    assert "routemind.simulation.control" in names
    assert "routemind.experiment.routebench" in names
    workflow_spans = [
        span
        for span in spans
        if span.name.startswith(("routemind.simulation", "routemind.experiment"))
    ]
    assert all(
        span.context is not None and f"{span.context.trace_id:032x}" == TRACE_ID
        for span in workflow_spans
    )
    assert all(
        span.attributes is not None and span.attributes["routemind.tenant_key"] == tenant_key
        for span in workflow_spans
    )

    carrier: dict[str, str] = {}
    with tracing.start_span("message-producer"):
        tracing.inject(carrier)
    assert carrier["traceparent"].startswith("00-")
    with tracing.start_span("message-worker", carrier=carrier):
        pass
    message_spans = {span.name: span for span in exporter.get_finished_spans()}
    worker_parent = message_spans["message-worker"].parent
    producer_context = message_spans["message-producer"].context
    assert worker_parent is not None and producer_context is not None
    assert worker_parent.trace_id == producer_context.trace_id
    assert worker_parent.span_id == producer_context.span_id
    assert worker_parent.is_remote is True


class FailingExporter(SpanExporter):
    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        return SpanExportResult.FAILURE

    def shutdown(self) -> None:
        return None


def test_exporter_failure_does_not_change_http_business_outcome() -> None:
    runtime = TracingRuntime(
        TraceSettings(service_name="failing-exporter"), span_exporter=FailingExporter()
    )
    client = TestClient(create_app(create_runtime(runtime)))

    response = client.get("/api/v1/system")

    assert response.status_code == 200
    assert response.json()["durable_state_owner"] is False


def test_batch_export_settings_are_bounded_and_fail_closed() -> None:
    with pytest.raises(ValueError, match="fit within"):
        TraceSettings(max_queue_size=8, max_export_batch_size=9)
