# RM-163 Shadow Mode Productization

## Implemented contract

- `POST /api/v1/shadow/evaluate` exposes the existing compute-owned Shadow
  evaluator and deterministic RegressionGate without granting candidate
  decisions operational authority.
- Responses include active/candidate strategy identities, ordered observations,
  assignment/disagreement/failure metrics, quality delta, promote/hold action,
  stable reason codes, manifest/run digests, trace context, and an explicit
  `candidate_authority: none` marker.
- Active strategy failures remain surfaced as unavailable errors; candidate
  failures are bounded into an observation and counted by the existing gate.

## Local evidence

- Compute check: 111 tests passed at 95.41% total statement/branch coverage;
  Ruff, format, mypy, and contract validation passed.
- Full available gate: Java 60 tests, Python 111 tests, Web 38 unit tests/build,
  and 5 schemas/15 fixtures passed.
- Focused API tests cover hold reasons at disagreement thresholds, digest
  emission, ordered observations, no-candidate-authority signaling, same
  strategy rejection, and unknown candidate handling.

## Gate decision

Local L2 shadow contract, L4 product-facing evaluation, and L5 isolation
evidence is complete. Remote Actions validation is required before RM-163 is
marked passed.
