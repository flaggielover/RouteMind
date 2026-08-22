# ADR 0002: Request Observability and Bounded Degradation Boundary

## Context

RouteMind has durable event identity (`correlationId`, `causationId`, and
`traceId`) inside business events, but inbound HTTP requests did not expose a
stable context or a shared metrics surface. The compute runtime already had a
deterministic travel-time fallback and the business runtime already preserved
courier writes when Redis projection failed; those guarantees were not grouped
under an executable resilience gate.

## Decision

Keep observability inside the existing Java and Python deployables. Each runtime
accepts or generates bounded `X-Request-Id` and `X-Trace-Id` values, returns them
on the response, and logs a completion record with method, path, status, and
duration. Java exposes a Micrometer Prometheus registry-backed `/metrics`
endpoint; Python exposes a Prometheus endpoint backed by request counters and a
latency histogram. A focused
PowerShell gate runs deterministic dependency-fault tests in both runtimes.

## Alternatives

- A new telemetry service would add an operational dependency before deployment
  or scaling requires one.
- An external tracing vendor would require credentials and would not prove local
  failure behavior.
- Unstructured ad-hoc logs would not provide stable correlation or scrapeable
  SLIs.

## Consequences

Requests and event processing can be joined through stable context identifiers,
and operators can scrape the same metric family from each runtime. Metrics are
local process telemetry, not durable business truth. The first resilience gate
proves bounded local fallback and projection degradation; broker restart, load,
and production collector validation remain follow-up scope.

## Validation

`./scripts/full-gate.ps1` validates the static and unit layers. `./scripts/resilience.ps1`
runs the Java request/metrics checks and Python travel-provider fault injection.
The CI `resilience` job runs the focused gate on every push and pull request.
