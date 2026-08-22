# RM-105 Realtime Event Stream and Cursor Contract

- Date: 2026-08-22 (Asia/Shanghai)
- Revision: implementation checkpoint recorded by the accompanying commit
- Boundary: versioned event-stream item contract consumed by future SSE adapters

## Contract

`contracts/events/v1/event-stream-item.schema.json` defines a v1 SSE item with
a decimal cursor, the immutable event envelope, replay provenance, and explicit
stale-state metadata. Supported event types cover `order`, `dispatch`,
`courier`, `exception`, and `simulation` updates.

## Cursor and reconnect rules

- The cursor is the SSE `id` and `Last-Event-ID` token, encoded as an unsigned
  decimal string without leading zeroes.
- Producers allocate cursors strictly monotonically. A reconnect resumes
  exclusively after the supplied cursor (`cursor > Last-Event-ID`) and retains
  the original event ID, correlation ID, causation ID, and trace ID.
- `replay=true` marks reconnect-delivered history. `stale=true` requires a
  non-empty `staleReason`; consumers stop applying updates and refresh their
  authoritative snapshot when stale or when a cursor gap is detected.
- The initial event at a workflow root may have `causationId: null`; redelivery
  never changes event identity.

## Executable evidence

1. `./scripts/compute-api.ps1 -Action check` -> PASS; 5 schemas and 15 contract
   fixtures validated, plus 59 Python tests and 96.13% coverage.
2. `python scripts/validate_control_plane.py` -> PASS.
3. `git diff --check` -> PASS.

## Evidence limits

This task defines the provider-neutral contract and semantics. Java SSE
transport, durable publication, reconnect serving, and browser consumption are
the follow-on RM-106+ tasks and are not claimed here.
