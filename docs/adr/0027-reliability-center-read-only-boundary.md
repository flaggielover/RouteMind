# ADR 0027: Reliability Center Read-Only Boundary

## Decision

The Operations route exposes a Reliability Center projection composed from the
captured operations snapshot, service-health checks, and realtime stream state.
It renders a bounded timeline, invariant matrix, dependency records, trace
links, and recovery evidence. Statuses distinguish `healthy`, `degraded`,
`unavailable`, and `fixture`; fixture or missing telemetry is never promoted to
healthy.

Continuous Java reconciliation remains the owner of durable invariant scans.
When its latest detect-only report is not attached to the Web snapshot, the
matrix shows reconciliation as unavailable rather than inferring health from
UI state. Trace IDs are shown only when present in the attached ledger/request
evidence. Dependency endpoints and check times remain inspectable.

## Boundaries

- The panel is read-only and introduces no repair, restart, retry loop, or
  autonomous remediation.
- Stream stale/degraded state is evidence of a bounded failure mode, not proof
  of an outage beyond the captured interval.
- Recovery entries describe available refresh/stream evidence and explicitly
  label absent telemetry.
- Demo and replay sources are labeled fixtures; they are useful for inspection
  but do not claim live dependency health.

## Consequences

Operators can compare dependency health, freshness, invariants, and recovery
signals in one surface while preserving Java durable truth and the existing
failure-degradation semantics.
