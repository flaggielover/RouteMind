# P9 RouteBench and Research Lineage Core

## Goal

Provide a small, deterministic research boundary for comparing registered
dispatch strategies against the existing seeded Digital Twin kernel. The
boundary must record enough provenance to reproduce a reduced run and must keep
research claims separate from production business state.

## Manifest

`BenchmarkManifest` is immutable and records:

- manifest, code, scenario, and dataset-provenance identifiers;
- scenario seed, load profile, city state, and injected failure labels;
- canonical strategy names and key/value configuration;
- runtime and optional hardware metadata.

Metadata is represented as sorted tuples instead of an unbounded dictionary so
the canonical form is stable and the object is hashable. Values are strings;
large datasets remain under `ROUTEMIND_DATA_ROOT` and are referenced by a
provenance identifier/checksum.

## RouteBench execution

`RouteBenchRunner` executes each manifest strategy through a fresh
`ScenarioKernel`, records deterministic assignment metrics and replay digests,
and captures elapsed runtime as an observation rather than a reproducibility
claim. The run output digest covers the manifest identity, strategy versions,
decisions, transitions, and deterministic aggregate metrics; it deliberately
does not hash wall-clock duration.

## Research lineage

`ResearchLineage` stores typed nodes for `hypothesis`, `observation`, `result`,
and `conclusion`. Each node has a content-derived ID, parent IDs, optional
manifest ID, and canonical payload. Querying by hypothesis or manifest returns
the recorded nodes and preserves the distinction between empirical results and
conclusions. The store is process-local and serializable for an external
research artifact; it is not a durable business record.

## Validation

Unit tests cover manifest validation/canonicalization, multi-strategy baseline
comparison, deterministic output digests despite runtime variance, lineage
querying and parent links, and invalid or disconnected node references. Reduced
runs remain local; no live provider, production claim, or large dataset is
required.
