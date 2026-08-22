# RM-102 Idempotent Java Order Command API

- Date: 2026-08-22 (Asia/Shanghai)
- Revision: implementation checkpoint recorded by the accompanying commit
- Boundary: Java durable order state, transactional Outbox, and durable command idempotency

## Contract

Java exposes `POST /api/v1/orders` for create and
`POST /api/v1/orders/{orderId}/transitions` for lifecycle commands. Both require
`Idempotency-Key` and `X-Actor`; transitions also require a target and expected
aggregate version. Create and transition persist the order, Outbox event, and a
request fingerprint/response record in one transaction.

Repeated delivery with the same key and fingerprint returns the original order
response with `replayed: true`. A changed request under an existing key returns
`409 idempotency_key_reused`. Stale versions and invalid state transitions return
stable conflict codes. The command boundary rejects unsupported actor roles
before mutating durable state. External token parsing and identity verification
remain the edge/security adapter boundary recorded in ADR 0002.

## Commands and results

1. `./scripts/business-api.ps1 -Action test` -> PASS; 53 Java tests passed,
   including HTTP create/transition replay, key conflict, missing key,
   unauthorized actor, and stale-version cases.
2. `./scripts/full-gate.ps1` -> PASS; control, security, Compose, Java, Python,
   contract, Web static/unit/build, and resilience gates passed.
3. `python scripts/validate_control_plane.py` -> PASS.

## Durable behavior

- Flyway V7 creates `routemind.order_command_idempotency` with a safe key length,
  SHA-256 request hash, operation, order response, and creation timestamp.
- Existing Java `OrderCommandService` keeps order mutation and Outbox insertion
  under `@Transactional`; idempotency records participate in the same unit of
  work.
- No browser, Python, Redis, or RabbitMQ path owns order writes.

## Evidence limits

The role actor is a bounded domain authorization input, not a JWT verification
claim. Production identity/token validation, distributed rate limiting, and
concurrent multi-instance idempotency stress remain external or later gates.
