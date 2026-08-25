from __future__ import annotations

import logging
import re
from time import perf_counter
from uuid import uuid4

from opentelemetry.trace import SpanKind, Status, StatusCode
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from routemind_compute.application.telemetry import TenantTelemetryAttribution
from routemind_compute.application.tracing import (
    TracingRuntime,
    span_trace_id,
    span_traceparent,
)

LOGGER = logging.getLogger("routemind.http")
SAFE_IDENTIFIER = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
REQUEST_COUNT = Counter(
    "routemind_http_requests_total",
    "Completed HTTP requests handled by RouteMind compute-api.",
    ("service", "method", "status"),
)
REQUEST_LATENCY = Histogram(
    "routemind_http_request_duration_seconds",
    "HTTP request duration in seconds.",
    ("service", "method"),
)


def _normalize(candidate: str | None, fallback: str) -> str:
    return candidate if candidate and SAFE_IDENTIFIER.fullmatch(candidate) else fallback


def request_context(request: Request) -> tuple[str, str | None]:
    request_id = _normalize(request.headers.get("X-Request-Id"), str(uuid4()))
    candidate = request.headers.get("X-Trace-Id")
    trace_id = _normalize(candidate, "") or None
    return request_id, trace_id


class RequestObservabilityMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app: ASGIApp,
        tracing: TracingRuntime,
        telemetry: TenantTelemetryAttribution,
    ) -> None:
        super().__init__(app)
        self.tracing = tracing
        self.telemetry = telemetry

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id, legacy_trace_id = request_context(request)
        tenant_key = self.telemetry.resolve(request.headers)
        started = perf_counter()
        attributes = {
            "http.request.method": request.method,
            "url.path": request.url.path,
            "server.address": request.url.hostname or "unknown",
            "routemind.request_id": request_id,
            "routemind.tenant_key": tenant_key,
        }
        if legacy_trace_id is not None:
            attributes["routemind.legacy_trace_id"] = legacy_trace_id
        correlation_id = request.headers.get("X-Correlation-Id")
        if correlation_id is not None and SAFE_IDENTIFIER.fullmatch(correlation_id):
            attributes["routemind.correlation_id"] = correlation_id
        with self.tracing.start_span(
            f"{request.method} {request.url.path}",
            kind=SpanKind.SERVER,
            attributes=attributes,
            carrier=request.headers,
        ) as span:
            otel_trace_id = span_trace_id(span)
            trace_id = legacy_trace_id or otel_trace_id
            request.state.request_id = request_id
            request.state.trace_id = trace_id
            request.state.tenant_key = tenant_key
            response = await call_next(request)
            duration = perf_counter() - started
            path = request.url.path
            status = str(response.status_code)
            span.set_attribute("http.response.status_code", response.status_code)
            if response.status_code >= 500:
                span.set_status(Status(StatusCode.ERROR))
            REQUEST_COUNT.labels("compute-api", request.method, status).inc()
            REQUEST_LATENCY.labels("compute-api", request.method).observe(duration)
            self.telemetry.record_http(tenant_key)
            response.headers["X-Request-Id"] = request_id
            response.headers["X-Trace-Id"] = trace_id
            response.headers["traceparent"] = span_traceparent(span)
            LOGGER.info(
                "http_request_completed",
                extra={
                    "event": "http_request_completed",
                    "request_id": request_id,
                    "trace_id": trace_id,
                    "otel_trace_id": otel_trace_id,
                    "method": request.method,
                    "path": path,
                    "status": response.status_code,
                    "duration_ms": round(duration * 1000, 3),
                },
            )
            return response


def metrics_response() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
