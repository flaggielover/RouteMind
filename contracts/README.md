# RouteMind Contracts

Contracts are independently versioned integration assets. Directory versions are
major versions and do not mirror service release versions.

- `api/v1`: JSON payloads crossing HTTP/runtime boundaries.
- `events/v1`: durable event envelope payloads.
- `examples`: positive and negative executable examples.
- `compatibility/v1`: permanent payloads every compatible v1 schema must accept.

## Compatibility policy

Within a published major version, fields may not be removed, renamed, change
type, become required, or receive narrower validation. Enum values are open to
documented additions only when all consumers are verified tolerant. A change
that can reject a previously valid compatibility fixture requires a new major
directory and an explicit producer/consumer migration plan.

Event identity fields and meanings are immutable after publication. Event IDs
identify one logical event across redelivery; correlation IDs join one workflow;
causation IDs identify the direct predecessor and are null only at a workflow
root; W3C-compatible trace IDs join telemetry. Payload models are not internal
database or domain entities.

The v1 event-stream item uses a decimal cursor as the SSE `id` and
`Last-Event-ID` resume token. Producers assign cursors strictly monotonically;
reconnect replay is exclusive (`cursor > Last-Event-ID`) and keeps the original
event identity. `replay` identifies a reconnect replay, while `stale: true` is
only valid with a non-empty `staleReason` when a cursor gap or retention boundary
prevents a complete stream. Consumers must stop applying updates and refresh
their snapshot when an item is stale. Supported event types cover order,
dispatch, courier, exception, and simulation updates.

Run `./scripts/compute-api.ps1 check` from the repository root. It checks every
schema, asserts positive and compatibility fixtures are accepted, and asserts
negative examples are rejected.
