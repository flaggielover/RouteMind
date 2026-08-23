# ADR 0013: Detect-Only Continuous Reconciliation

## Context

RouteMind keeps durable business truth in PostgreSQL and rebuildable courier GEO
state in Redis. Transactional constraints protect individual writes, but they do
not prove that leases, assignment audits, decision records, terminal orders, and
hot projections remain mutually consistent after partial failure or operational
intervention. Treating an unavailable dependency as healthy would also hide the
exact failure mode that reconciliation is intended to expose.

## Decision

Run reconciliation inside the Java business runtime because the checked
invariants are consistency-sensitive and Java owns their durable state. Each run
is explicitly `DETECT_ONLY` and classifies every independent check as `PASS`,
`FAIL`, or `UNAVAILABLE`. The aggregate result is `HEALTHY`, `DRIFT_DETECTED`, or
`DEGRADED`; detected drift takes precedence over unavailable checks.

The initial invariant set covers:

- assigned orders and committed lease cardinality, lease/order state agreement,
  committed lease audit linkage, and expired provisional leases;
- terminal orders that retain an active lease;
- assignment audits whose complete decision-ledger reference is absent or does
  not agree;
- durable courier-location membership versus the rebuildable Redis GEO
  projection;
- successful append of the reconciliation evidence itself.

Runs execute on a bounded configurable fixed delay and can also be invoked
manually through the reliability API. Every successful run is appended to
`routemind.reconciliation_runs` with a SHA-256 report digest and the complete
bounded JSON report. The latest report remains queryable after process restart.
Failure of an individual query, Redis inspection, or evidence append is returned
as unavailable rather than converted to a pass.

## Consequences

Operators gain an inspectable last-check time, exact violation identity, bounded
evidence, and explicit dependency degradation without granting the scanner write
authority over business records. PostgreSQL remains durable truth and Redis
remains rebuildable hot state. A future repair policy must be separately designed,
authorized, idempotent, and evidenced; this implementation cannot silently repair.

The scan is intentionally bounded to 100 returned violations per check. It is a
continuous integrity detector, not a complete data export or a substitute for
database constraints. Production interval, alert routing, retention, and repair
automation require environment-specific evidence and are not claimed here.

## Validation

`./scripts/business-api.ps1 -Action test` covers healthy, drift, unavailable,
projection mismatch, evidence-write, report-readback, and no-repair behavior.
`./scripts/full-gate.ps1` and `./scripts/verify.ps1` preserve repository-wide
architecture, contract, security, compute, and Web gates.
