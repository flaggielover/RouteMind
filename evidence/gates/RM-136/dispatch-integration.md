# RM-136 Advanced Dispatch Integration

- Date: 2026-08-23 (Asia/Shanghai)
- Design: `docs/superpowers/specs/2026-08-23-rm-136-dispatch-integration-design.md`
- Checkpoint: `1d172ec`
- Gate decision: PASS; fully validated after GitHub Actions run `32609222189`

## Boundary and behavior

The Python live dispatch response now carries the frozen `v1` contract version,
SHA-256 input/output digests, and explicit travel fallback metadata. It remains
stateless and does not write business state.

Java exposes `POST /api/v1/orders/{orderId}/dispatch-assignment`. The command
validates the versioned decision envelope, digest shape, selected courier UUID,
and expected order version. In one PostgreSQL transaction it transitions the
authoritative order to `ASSIGNED`, writes `dispatch_assignment_audits`, and
enqueues a detailed `dispatch.assignment.applied` Outbox event containing the
strategy, input/output digests, trace, and fallback reason.

The audit idempotency key is durable. An identical retry returns the applied
result with `replayed=true`; key reuse with a changed decision returns
`idempotency_key_reused`; a stale expected order version returns
`stale_version` before any audit or event is committed.

## Executable evidence

1. `./scripts/full-gate.ps1` -> PASS: control-plane/security/repository gates,
   Java 61 tests, Python 142 tests at 95.88% coverage with 5 schemas and 15
   fixtures, Web 49 unit tests and production build.
2. `./scripts/web.ps1 -Action e2e` -> PASS: 23 passed, 1 existing
   desktop-only skip across 24 Playwright desktop/mobile/axe smoke tests.
3. Java golden-path test asserts the detailed Outbox payload, durable audit,
   duplicate replay, idempotency-key reuse conflict, and stale-version
   rejection. Flyway applies migration V10 for the audit table.
4. Python dispatch API test asserts `contract_version=v1`, 64-character input
   and output digests, and `fallback_used=false` for deterministic local travel.

## Acceptance mapping

- Versioned compute contract and durable assignment boundary: PASS locally.
- Strategy/input/output/trace/fallback audit linkage: PASS locally.
- Duplicate and stale decision safety: PASS locally.

5. GitHub Actions run `32609222189` -> PASS: Control plane and Compose, Java,
   Python/contract, Web/browser smoke, and bounded resilience jobs all green.
