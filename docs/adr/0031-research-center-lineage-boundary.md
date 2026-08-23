# ADR-0031: Research Center Lineage Boundary

Date: 2026-08-24  
Status: Accepted

## Context

RouteMind already produces bounded What-if comparisons, manifests, replay
digests, output digests, and reference-data identities. Operators need a place
to inspect those artifacts and their lineage without accidentally presenting an
engineering observation as a scientific result.

## Decision

Web owns a read-only Research Center projection. It derives an experiment
manifest view, engineering observations, artifact references, and a compact
lineage chain from an existing recorded comparison. When no comparison is
attached it shows fixture/pending state and does not infer metrics. The panel
labels scientific claims and deep research campaigns as deferred.

## Consequences

- Every displayed observation remains linked to a recorded run and digest.
- Reference-data identity is shown when the durable decision ledger attaches it;
  otherwise the value remains unavailable.
- Round 3 research preparation remains a task-graph/documentation concern, not
  an automatic experiment campaign.
