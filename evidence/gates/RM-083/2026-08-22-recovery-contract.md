# RM-083 Recovery Artifact Contract Evidence

Date: 2026-08-22
Local revision before checkpoint: `e501a26`

## Scope

`scripts/recovery_contract.py` defines immutable recovery artifacts for
PostgreSQL, RabbitMQ, and Redis with explicit format, source revision, relative
payload path, SHA-256, byte size, and contiguous restore order. A package digest
is canonical and independent of filesystem timestamps. The rehearsal validator
only reads a package root and reports `ready` or bounded `blocked` reasons.
`RollbackManifest` records target revision, package digest, operator intent, and
an explicit `ack=required` confirmation marker without executing a state change.

## Executed gates

`python scripts/recovery_contract_test.py` — PASS (4 tests)

- complete three-service fixture rehearsal — PASS
- deterministic artifact ordering and package digest — PASS
- missing payload, size mismatch, and checksum mismatch — PASS
- incomplete services, path traversal, revision mismatch, and rollback ack
  validation — PASS

`./scripts/verify.ps1` — PASS

- task graph/control plane validation — PASS
- security/supply-chain gate and 3 self-tests — PASS
- recovery contract self-tests — PASS
- Compose configuration and PowerShell syntax — PASS

`./scripts/full-gate.ps1` — PASS

- Java: 34 tests — PASS
- Python: 56 tests, 96.05% coverage — PASS
- Web static checks, unit tests, and production build — PASS
- control, security, and recovery gates — PASS

## Behavioral evidence

- Recovery package services must be exactly PostgreSQL, RabbitMQ, and Redis.
- Artifact paths are normalized relative paths; traversal and absolute paths are rejected.
- Restore order must be contiguous and starts at 1.
- Rehearsal verifies declared size before checksum and reports stable service-scoped reasons.
- Rollback metadata is content-digestible and requires explicit acknowledgement metadata.

## Limits and deferred external validation

No production data, destructive volume command, external credential, or live
PostgreSQL/RabbitMQ/Redis restore is claimed by this gate. Docker/service-backed
restore rehearsal remains `deferred_external` until a controlled infrastructure
environment and retention policy are available.
