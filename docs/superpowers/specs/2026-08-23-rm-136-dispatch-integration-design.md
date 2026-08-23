# RM-136 Durable Dispatch Integration

Date: 2026-08-23

## Goal

Connect an advanced, versioned Python dispatch decision to the Java order
authority without allowing the compute runtime to mutate durable state. The
boundary must retain enough provenance to explain which strategy produced an
assignment, which input and output were applied, which trace carried it, and
whether a bounded fallback was used.

## Boundary

Python responses expose a stable `contract_version` plus SHA-256 input/output
digests and explicit fallback metadata. The existing stateless strategy
registry remains the only decision producer. Java accepts a decision through a
dedicated order command. It validates the contract, order version, selected
courier UUID, idempotency key, and digest shape before transitioning the order
to `ASSIGNED`.

The Java command writes a durable dispatch audit and a detailed
`dispatch.assignment.applied` Outbox event in the same transaction as the order
transition. PostgreSQL therefore remains the source of truth, while RabbitMQ
publication remains retriable through the existing Outbox relay.

## Duplicate and stale behavior

The assignment idempotency key is unique in the dispatch audit table. A repeat
with the same request fingerprint returns the original applied result and marks
the response as replayed. Reusing the key for a different decision is a
conflict. A decision whose expected order version no longer matches is rejected
before any audit or event is committed.

## Failure and verification

Tests cover the Python envelope digests and fallback metadata, Java golden-path
assignment with the detailed Outbox payload, duplicate replay, key reuse,
stale-version rejection, malformed contract rejection, and rollback behavior.
The implementation must pass the existing full gate and the five-job GitHub
Actions workflow before RM-136 is marked passed.
