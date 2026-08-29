# Research Observability Readiness

Date: 2026-08-29
Checkpoint: RM-237
Status: OBSERVABILITY_READY

This is an engineering readiness result for future observed-data collection. It
is not a scientific pass, novelty result, production validation, or
reinterpretation of any historical campaign.

## What is observable

- Each future Python dispatch or Digital Twin decision can emit a versioned
  policy observation with run, scenario, decision, request, tick, previous and
  selected policy, reason, policy version, fallback state, configuration digest,
  seed, state features, semantic classes, and provenance.
- The trace records no-switch decisions, switches across any policy names,
  dwell ticks, transition matrices, occupancy, switch rate, and short-window
  reversals. Raw transition timing remains available; no arbitrary chatter
  threshold is asserted.
- Java remains the durable authority. The dispatch decision ledger stores the
  same observation metadata transactionally with the existing decision and
  includes it in idempotency and outbox provenance.
- A deterministic JSONL exporter writes below `ROUTEMIND_DATA_ROOT` and emits
  a content digest manifest. Secret-like keys are redacted before writing.

## Measurement boundary

The observation contract preserves a vector of consequence components instead
of inventing one scalar switch cost:

- `MEASURED`: only values supplied by the caller from an authoritative runtime
  measurement, such as an explicitly recorded decision latency.
- `DERIVED`: values computed from recorded observations, such as switch rate,
  dwell ticks, occupancy, and transition counts.
- `UNAVAILABLE`: route delta, SLA delta, customer/merchant/courier impact, and
  other consequences when the current execution does not provide them.
- `NOT_APPLICABLE`: a component outside the run's declared scope.

Unavailable values are never replaced with zero. Post-switch outcomes are
labelled observational association and are not causal switch costs.

## Replay and lineage

The replay digest excludes wall-clock timestamps and includes the observation
sequence alongside the existing scenario decisions and transitions. A future
run can therefore link code/configuration digest -> run/seed -> decision ->
policy switch -> state/transition -> exported artifact without a second replay
system.

## Export and privacy

Raw observations are external artifacts under `ROUTEMIND_DATA_ROOT`; Git holds
only schemas, synthetic examples, manifests, and summaries. Sender, recipient,
credentials, tokens, payment data, and unnecessary personal identifiers are
forbidden. Exported rows are deterministic JSONL with schema version
`routemind-policy-observation-v1` and a SHA-256 manifest.

## What remains unobservable

The current package does not create empirical records, backfill historical
tick logs, measure real-world policy frequency or realized operational cost,
calibrate the Digital Twin, or identify a causal effect. Those require a
separately authorized observed-data run and, where applicable, a separate
external or Human Gate.

## Reopening trigger

Future science may be considered only after an observed dataset passes the
quality checks in `FIRST_EMPIRICAL_DATASET_SPEC.md`, exact decision sequences
are replayable, a simple baseline explanation has been attempted, and at least
one reproducible unexplained anomaly is present. Data volume alone is not a
trigger.

## Historical claim boundary

R3-325 artifacts and verdict `E-PASS / X-PASS / S-FAIL / C-NO-CLAIM` remain
frozen and are not inputs to a retroactive repair. RM-237 does not alter any
Round 4 external-action boundary, Human Gate, production claim, or prior
scientific result.
