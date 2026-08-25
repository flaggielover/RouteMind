from __future__ import annotations

import json
import logging
import os
import sys
from typing import Any

from opentelemetry import _logs, metrics, trace
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

TENANT_KEY = "rtk_aaaaaaaaaaaaaaaaaaaaaaaa"


def main() -> int:
    resource = Resource.create(
        {
            "service.name": "routemind-external-validation-probe",
            "service.namespace": "routemind",
            "deployment.environment.name": "vultr-nrt-external-validation",
            "routemind.tenant_key": TENANT_KEY,
        }
    )

    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(tracer_provider)

    metric_reader = PeriodicExportingMetricReader(
        OTLPMetricExporter(), export_interval_millis=1000
    )
    meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
    metrics.set_meter_provider(meter_provider)

    logger_provider = LoggerProvider(resource=resource)
    logger_provider.add_log_record_processor(BatchLogRecordProcessor(OTLPLogExporter()))
    _logs.set_logger_provider(logger_provider)
    handler = LoggingHandler(level=logging.INFO, logger_provider=logger_provider)
    logger = logging.getLogger("routemind.external_validation")
    logger.handlers = [handler]
    logger.setLevel(logging.INFO)
    logger.propagate = False

    tracer = trace.get_tracer("routemind.external_validation", "1.0.0")
    meter = metrics.get_meter("routemind.external_validation", "1.0.0")
    records = meter.create_counter(
        "routemind_validation_connectivity_records_total",
        unit="{logical_export_record}",
    )

    with tracer.start_as_current_span("routemind.validation.otlp-connectivity") as span:
        trace_id = format(span.get_span_context().trace_id, "032x")
        span.set_attribute("routemind.validation.kind", "otlp-connectivity")
        span.set_attribute("routemind.tenant_key", TENANT_KEY)
        span.set_attribute("routemind.synthetic_qualification", True)
        records.add(
            1,
            {
                "service": "external-validation-probe",
                "signal": "trace",
                "operation": "otlp-connectivity",
                "tenant_key": TENANT_KEY,
            },
        )
        logger.info(
            "RouteMind OTLP connectivity qualification log",
            extra={
                "routemind.validation.kind": "otlp-connectivity",
                "routemind.tenant_key": TENANT_KEY,
                "routemind.synthetic_qualification": True,
            },
        )

    records.add(
        1,
        {
            "service": "external-validation-probe",
            "signal": "metric",
            "operation": "otlp-connectivity",
            "tenant_key": TENANT_KEY,
        },
    )
    trace_flush = tracer_provider.force_flush(timeout_millis=20_000)
    metric_flush = meter_provider.force_flush(timeout_millis=20_000)
    log_flush = logger_provider.force_flush(timeout_millis=20_000)
    payload: dict[str, Any] = {
        "valid": True,
        "classification": "OTLP_CONNECTIVITY_PROBE_ONLY",
        "actualRouteMindWorkload": False,
        "traceId": trace_id,
        "signals": ["traces", "metrics", "logs"],
        "tenantKey": TENANT_KEY,
        "flush": {
            "traces": bool(trace_flush),
            "metrics": bool(metric_flush),
            "logs": bool(log_flush),
        },
        "probeId": os.environ.get("ROUTEMIND_PROBE_ID", "qualification"),
    }
    print(json.dumps(payload, sort_keys=True, separators=(",", ":")))
    logger_provider.shutdown()
    meter_provider.shutdown()
    tracer_provider.shutdown()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # pragma: no cover - target runtime diagnostic
        print(f"R4 telemetry probe failed: {type(exc).__name__}", file=sys.stderr)
        raise
