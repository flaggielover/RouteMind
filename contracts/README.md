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

Run `./scripts/compute-api.ps1 check` from the repository root. It checks every
schema, asserts positive and compatibility fixtures are accepted, and asserts
negative examples are rejected.
