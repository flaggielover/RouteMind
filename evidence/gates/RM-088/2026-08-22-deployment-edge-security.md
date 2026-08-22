# RM-088 Deployment and Edge-Security Adapter Evidence

- Date: 2026-08-22 (Asia/Shanghai)
- Revision: `42f7279` implementation checkpoint
- Worktree: clean after the implementation checkpoint

## Contract

The Java security domain now provides a provider-neutral deployment adapter
boundary. `DeploymentAdapterRequest` binds release-manifest, staged-decision,
authorization-policy, and rate/input-policy digests to an explicit environment
and operation. Edge identity, TLS, WAF, distributed limiter, and secret-manager
values are references or identities only; no secret value is accepted by the
contract. `DeploymentEdgeAdapter` produces stable operation IDs and reason
codes without mutating business state or calling a provider.

Local `preflight` and `plan` return `READY` and remain read-only. `apply` and
`rollback` return `BLOCKED` for missing or mutable references, unverified edge
controls, missing provider capabilities, or a missing external gate. They return
`ACCEPTED_EXTERNAL` only when all checks are verified, explicitly indicating
that execution belongs to an external operator or CI gate.

## Commands and results

1. `./scripts/business-api.ps1 -Action test` -> 49 Java tests passed.
2. `./scripts/verify.ps1` -> control, security, recovery, release, staged-release,
   Compose, Java, Python, schema, and Web repository gates passed. Python passed
   56 tests at 96.05% statement/branch coverage.
3. Focused `DeploymentEdgeAdapterTests` -> 5 tests passed for stable digests,
   read-only operations, immutable-reference validation, external apply/rollback,
   and fail-closed verification gates.

## Boundary and deferred external validation

The adapter does not deploy artifacts, mutate traffic, store credentials, write
PostgreSQL, or replace transactional business state. Provider API behavior,
actual TLS/WAF/limiter enforcement, identity rotation, deployment health, and
production rollback remain external gates.

## GitHub Actions

- Design checkpoint run: `32559357972` (all five jobs passed).
- Implementation run: `32559680696` (all five jobs passed: control plane and
  Compose, Java business runtime, Python compute and contracts, Role-aware web
  application, and bounded degradation and resilience).
