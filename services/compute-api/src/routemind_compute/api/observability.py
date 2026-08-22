from __future__ import annotations

import logging
import re
from time import perf_counter
from uuid import uuid4

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

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


def request_context(request: Request) -> tuple[str, str]:
    request_id = _normalize(request.headers.get("X-Request-Id"), str(uuid4()))
    trace_id = _normalize(request.headers.get("X-Trace-Id"), uuid4().hex)
    return request_id, trace_id


class RequestObservabilityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id, trace_id = request_context(request)
        started = perf_counter()
        request.state.request_id = request_id
        request.state.trace_id = trace_id
        response = await call_next(request)
        duration = perf_counter() - started
        path = request.url.path
        status = str(response.status_code)
        REQUEST_COUNT.labels("compute-api", request.method, status).inc()
        REQUEST_LATENCY.labels("compute-api", request.method).observe(duration)
        response.headers["X-Request-Id"] = request_id
        response.headers["X-Trace-Id"] = trace_id
        LOGGER.info(
            "http_request_completed",
            extra={
                "event": "http_request_completed",
                "request_id": request_id,
                "trace_id": trace_id,
                "method": request.method,
                "path": path,
                "status": response.status_code,
                "duration_ms": round(duration * 1000, 3),
            },
        )
        return response


def metrics_response() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
