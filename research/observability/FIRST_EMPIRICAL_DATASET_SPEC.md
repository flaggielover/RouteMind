# First Empirical Dispatch Dataset Specification

Date: 2026-08-29
Checkpoint: RM-237
Purpose: define the smallest future observational dataset that can support
anomaly discovery without fabricating evidence.

## Minimum record

Every decision row must contain the fields in
`contracts/observability/rm-237-policy-observation-v1.schema.json`:

- schema version, run ID, decision ID, request ID, and optional scenario ID;
- wall timestamp or simulation tick with an explicit clock domain;
- previous policy, selected policy, switch indicator, reason, selection mode,
  and policy version;
- configuration digest, deterministic seed when applicable, fallback state,
  state features, semantic classes, and provenance references;
- consequence components with `MEASURED`, `DERIVED`, `UNAVAILABLE`, or
  `NOT_APPLICABLE` status.

The minimum useful anomaly-discovery unit is one complete, quality-passing run
with the full decision sequence. A run with zero switches is valid evidence;
the collection plan should seek policy variation across runs and retain both
switching and non-switching regimes when they occur. No arbitrary large record
count is required by this specification. Confirmatory sample size is
`TBD_BY_HYPOTHESIS`.

## Optional fields

Additional fields may be added only when already authoritative and classified:
assignment changes, route recomputation, queue/SLA outcomes, solver runtime,
tail-risk estimates, provider/travel provenance, and pseudonymous entity keys.
Each addition requires a schema version and lineage update.

## Forbidden fields

Do not export credentials, API keys, authorization headers, raw provider
tokens, payment data, message bodies, or unnecessary customer, courier, or
merchant PII. Use opaque internal research identifiers only when linkage is
scientifically necessary; do not persist raw names, addresses, phones, or
emails.

## Quality and time semantics

Before analysis, verify unique IDs, monotonic tick ordering per run, valid
policy transitions, `switch_count <= decision_count`, digest format, complete
provenance, and absence of forbidden fields. Missing outcomes remain missing
with an explicit unavailable status; they are not imputed as zero. Wall time,
simulated time, and replay time are never mixed. All exports include the code,
configuration, schema, and source-run digests.

## Format and lineage

The default format is deterministic JSONL plus a SHA-256 manifest under the
directory selected by `ROUTEMIND_DATA_ROOT`. A future Parquet projection may be
created only with equivalent fields and a linked manifest. The expected lineage
is code version -> configuration -> run -> decision -> switch -> outcome ->
exported artifact -> analysis.

## Collection and science boundary

This document does not authorize a live run, external API call, paid resource,
or scientific campaign. A future campaign requires a separate approved run
contract, privacy review, and evidence bundle. Reopening is justified only by
quality-passing observed evidence plus a reproducible anomaly that survives a
simple baseline explanation; collection volume alone is insufficient.
