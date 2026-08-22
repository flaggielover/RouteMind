# RM-087 Request Rate-Limit and Input Protection Evidence

- Date: 2026-08-22 (Asia/Shanghai)
- Revision: `24831c09460b4d8ec0f9f2d1421836ddc4a53600`
- Worktree: clean after the implementation checkpoint

## Contract

The Java domain security package now includes immutable `RequestPolicy`,
`RequestDescriptor`, `UsageSnapshot`, and explicit admission decisions.
`RequestAdmissionPolicy` is a pure read-only evaluator: invalid UTF-8,
control characters, missing command idempotency keys, body/field limits, and
invalid measurements reject before rate-limit evaluation. Usage at or above
the configured request plus burst budget throttles with deterministic
window-based retry-after seconds; safe input is allowed. Policy digests are
content-derived and raw bodies/secrets are not part of evidence.

## Commands and results

1. `./mvnw.cmd -q -Dtest=RequestAdmissionPolicyTests test` with repository JDK
   17 -> 5 tests passed.
2. `./scripts/full-gate.ps1` -> Java 44 tests passed; Python 56 tests passed at
   96.05% statement/branch coverage; 4 schemas and 12 fixtures passed; Web
   formatting, lint, typecheck, unit, and production build passed; control,
   security, recovery, release-preflight, and staged-release self-tests passed.

The tests cover allow/throttle boundaries, deterministic retry-after, malformed
and oversized input precedence, command idempotency, stable policy digests, and
invalid construction inputs.

## Boundary

The evaluator does not store or mutate counters, authorize business commands,
write PostgreSQL, or replace Outbox/idempotency semantics. Atomic distributed
counters, WAF/bot mitigation, production quotas, credential reputation, and
load validation remain external gates.

## GitHub Actions

- Run: `32559165335`
- Commit: `df616fe55e1e51a1ec5481412b6ba3aaa8e6a232`
- Result: all five jobs passed: control plane and Compose, Java business
  runtime, Python compute and contracts, Web application, and bounded
  degradation/resilience.
