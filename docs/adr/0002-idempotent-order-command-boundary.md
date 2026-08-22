# ADR 0002: Idempotent Java Order Command Boundary

- Status: accepted
- Date: 2026-08-22
- Scope: Round 2 RM-102 order command API

## Decision

Expose Java-owned order create and lifecycle commands under `/api/v1/orders`.
Every command requires an `Idempotency-Key` and `X-Actor`. The Java domain
validates actor role against the requested lifecycle transition, and the
aggregate version is checked before a transition is applied. A command request
fingerprint and its order response (`orderId`, status, version) are persisted in
`routemind.order_command_idempotency` in the same transaction as the order and
transactional Outbox write.

Repeated delivery with the same key and fingerprint returns the stored response
with `replayed: true`. Reusing a key with a different operation or fingerprint
returns a stable conflict. Stale versions and invalid lifecycle transitions are
conflicts; missing or unknown actors are rejected. External identity verification
and token parsing remain an edge/security adapter concern from RM-086, while the
domain boundary remains fail-closed for unsupported actor roles.

## Alternatives considered

1. In-memory idempotency cache: rejected because restart or multi-instance
   delivery would lose the command result.
2. Reusing Inbox event deduplication: rejected because command keys and inbound
   event IDs have different producers, fingerprints, and response semantics.
3. Browser-side writes: rejected because Java owns durable transactions and
   Outbox consistency.
