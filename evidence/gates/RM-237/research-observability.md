# RM-237 Research Observability Evidence

Date: 2026-08-29
Status: PASS / FUTURE_DATA_READY

## Scope

RM-237 is a standalone research-enabling checkpoint. It covers only future
policy observations, Java durable dispatch-ledger metadata, Python alignment,
deterministic replay linkage, `ROUTEMIND_DATA_ROOT` export, schema/provenance,
privacy controls, focused tests, and evidence synchronization.

It does not modify or reinterpret frozen R3-325 artifacts or verdicts, backfill
tick logs, create empirical records, alter Round 4 external claims, weaken a
Human Gate, call an external API, or create a paid resource.

## Implemented boundary

- Python contract: `routemind-policy-observation-v1` with explicit semantic
  classes, switch invariants, consequence statuses, replay digest, metrics,
  redaction, and deterministic JSONL manifest.
- Java boundary: `DispatchObservationMetadata` is optional-compatible on the
  assignment command and is persisted with the durable dispatch ledger and
  redacted Outbox/response provenance.
- Contract: `contracts/observability/rm-237-policy-observation-v1.schema.json`
  with synthetic valid/invalid examples.
- Reports: `research/observability/RESEARCH_OBSERVABILITY_READINESS.md` and
  `research/observability/FIRST_EMPIRICAL_DATASET_SPEC.md`.

## Validation record

- `./scripts/compute-api.ps1 check` passed: Ruff, format, strict mypy, 7
  schemas/20 fixtures, Google contract checks, and 950 Python tests; coverage
  is 95.10%.
- The compute determinism gate reported stable scenario-kernel digest
  `4ac8221571aa4f619f9518f2742f9e9db9d1e621d983aa08670be818f729b520` on both
  runs. Observation replay digests exclude wall timestamps.
- `./scripts/business-api.ps1 test` passed: 124 Java tests, zero failures;
  Flyway applied and validated migration V18 for the durable ledger extension.
- `./scripts/verify.ps1` and `./scripts/resume.ps1` passed the control-plane,
  dependency, evidence, mirror, security, and repository gates. No eligible
  external action was created; the existing R4-422 Human Gate remains the
  active external boundary.
- The tracked implementation is committed and pushed as RM-237 checkpoint
  `37bf50711057da9fa4f34f09af56838d951dc1ca`. GitHub Actions CI run
  `33230961979` passed all five required jobs. `.codex-tmp/` remains an
  untouched local untracked directory.

## Boundary and provenance

Python owns tick-level policy observations, switch metrics, replay linkage, and
the `ROUTEMIND_DATA_ROOT` JSONL projection. Java owns the optional-compatible
metadata accepted on dispatch commands, idempotency fingerprint, transactional
Outbox provenance, and durable ledger columns. The artifact schema is
`routemind-policy-observation-v1`; its manifest carries format, relative path,
record count, SHA-256, and the observational-only claim boundary.

Instrumentation is observational and semantics-preserving: no solver,
assignment, lease, order, retry, provider, or Human Gate decision is changed.
No empirical record was fabricated, no historical tick log was backfilled, and
no AWS, Google, HERE, or other external API was called.

No observed empirical dataset is claimed. All current examples are synthetic.
