# ADR 0026: Immutable Reference-Data Identity Contract

## Decision

Reference data is identified by a typed, immutable key:
`{kind}:{name}:{version}` for travel, zone, strategy, or analytical data. The
identity carries a lowercase SHA-256 content digest, producer, and optional
superseded identity. A local `ReferenceDataCatalog` accepts an identical
re-registration but rejects content mutation; a new version must explicitly
name an existing identity it supersedes.

Compute manifests link the identity directly. Scenario/replay manifests and
RouteBench benchmark manifests carry `reference_data_id`; external artifact
resolution exposes the same identity in its verified metadata. Analytical
records and DuckDB facts retain their existing `reference_data_id`, while the
Java dispatch ledger remains the durable decision authority with its existing
reference-data column.

## Boundaries

- The catalog is an in-process contract and does not become a database or
  network service.
- New versions are additive; no update operation rewrites a prior identity.
- Content hashes verify payload identity, while the typed key identifies the
  semantic kind and producer version.
- Missing external payloads remain an explicit artifact-resolution failure.

## Consequences

Decision, archive, mart, and replay consumers can join on a stable identity and
detect accidental rewrites. Providers remain swappable because travel and zone
identities are provider-neutral, and local deterministic fixtures continue to
work without paid services.
