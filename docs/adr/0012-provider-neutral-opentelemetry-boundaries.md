# ADR 0012: Provider-Neutral OpenTelemetry Boundaries

## Context

RouteMind already returned bounded request and legacy trace identifiers, emitted
Prometheus metrics, and stored trace/correlation identity in durable events. It
did not yet create real parent-child spans across the important Java and Python
execution boundaries. A tracing backend is not available in every local or CI
environment and must not become a correctness dependency.

## Decision

Use W3C Trace Context and OpenTelemetry-compatible runtime libraries inside the
existing Java and Python deployables. Java uses Spring Boot's Micrometer tracing
bridge over OpenTelemetry; Python owns an application-scoped OpenTelemetry SDK
provider. Both continue valid incoming `traceparent` context and return a W3C
header plus the compatible `X-Trace-Id` response header.

Trace the useful boundaries only:

- Java HTTP server, JPA adapter, Rabbit outbox publish, and durable dispatch
  decision recording;
- Python HTTP server, travel estimate/matrix, solver execution, and independent
  decision verification.

Preserve event, aggregate/order, correlation, request, and decision identifiers
as trace attributes or message headers. They are not metric labels. OTLP export
is disabled by default and enabled only through environment configuration. Span
creation and propagation remain locally testable with in-memory observation or
span exporters, so no collector or vendor account is needed for the gate.

## Consequences

Operators can correlate a request with the durable event and dispatch decision
path without moving business authority out of PostgreSQL or Java. Python agents
and solvers remain analytical execution boundaries and cannot use tracing as a
correctness mechanism. Disabling export does not disable local propagation.
Exporter or collector failure cannot alter a business transition or decision.

The first implementation does not deploy a collector, choose a tracing vendor,
define retention, or claim production sampling performance. Those require an
environment-specific deployment and evidence.

## Validation

`./scripts/business-api.ps1 -Action test` verifies the Java context, observation,
and message-header contracts. `./scripts/compute-api.ps1 -Action check` verifies
W3C and legacy parents with an in-memory exporter and checks all Python tracing
boundaries. `./scripts/resilience.ps1` retains the bounded degradation gate.
