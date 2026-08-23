# Observability and Resilience Runbook

## Signals

Every Java and Python HTTP response carries `X-Request-Id`, `X-Trace-Id`, and a
W3C `traceparent` header. W3C context is continued as a real parent-child trace;
`X-Trace-Id` remains a compatibility input/output for existing clients.
Callers may supply identifiers matching `[A-Za-z0-9._:-]{1,128}`; invalid or
missing values are replaced at the service boundary. Event envelopes continue
to carry the existing correlation, causation, and 32-character trace fields.

Metrics endpoints:

- Java: `GET /metrics` on `BUSINESS_API_PORT` (default `18080`)
- Python: `GET /metrics` on `COMPUTE_API_PORT` (default `18081`)

Useful SLIs are request count by service/method/status, request latency,
health status, outbox retry/dead-letter counts, inbox retry/dead-letter counts,
and dispatch fallback usage. Metric names and labels must remain bounded; do not
label metrics with request IDs, user identifiers, or arbitrary exception text.

Tracing is provider-neutral and exports nothing by default. Set
`ROUTEMIND_OTLP_EXPORT_ENABLED=true` to enable the standard OTLP exporter and use
the standard `OTEL_EXPORTER_OTLP_*` variables for collector endpoint, protocol,
headers, and timeout. `OTEL_SERVICE_NAME` overrides the Python service name;
`ROUTEMIND_TRACE_SAMPLE_PROBABILITY` controls Java sampling. `OTEL_SDK_DISABLED`
can disable Python recording while retaining the bounded runtime contract.
Never commit collector credentials or headers.

Java spans cover HTTP, JPA adapters, Rabbit publishing, and durable dispatch
decision recording. Python spans cover HTTP, travel provider calls, solver
execution, and decision verification. Request, correlation, event, order, and
decision identifiers belong on traces or message envelopes, not metric labels.

## Local checks

```powershell
./scripts/full-gate.ps1
./scripts/resilience.ps1
./scripts/business-api.ps1 -Action test
./scripts/compute-api.ps1 -Action check
```

The resilience gate injects a travel-provider timeout/failure and asserts the
deterministic local provider is used with an explicit fallback marker. Java
application tests assert request-context propagation and Prometheus exposure;
the Python API tests also send a fixed 100-request local burst and assert every
response is healthy with a corresponding bounded metric series. The existing
courier service test asserts durable persistence when the Redis projection
throws.

## Incident triage

1. Capture the request and trace identifiers from the failing response or log.
2. Check `/actuator/health` and `/healthz` before restarting anything.
3. Compare request latency and status counters with outbox/inbox retry and
   dead-letter records in PostgreSQL.
4. If Redis is degraded, keep durable courier writes enabled and treat nearby
   search/projection as degraded; rebuild the projection after recovery.
5. If a travel provider times out, keep the deterministic local fallback and
   record the provider/fallback metadata. Do not promote fallback output to a
   live-provider claim.
6. For broker or database incidents, use the existing Outbox/Inbox runbooks and
   preserve the trace identifiers in the investigation record.

## Scope and escalation

This runbook documents local and CI evidence. It does not claim a production
collector, trace retention, alerting policy, load threshold, or vendor-specific
trace backend.
RM-080 follow-up work should add seeded load/failure injection, dashboards,
alert thresholds, and rollback drills without making telemetry a new source of
business truth.
