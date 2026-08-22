# RM-081 Strategy Shadow Mode and Regression Gate Evidence

Date: 2026-08-22
Local revision before checkpoint: `c71241c`

## Scope

The Python compute boundary now evaluates a candidate strategy against the same
immutable dispatch inputs while retaining the active decision as sole
operational authority. Candidate exceptions become bounded shadow failures and
cannot mutate business state, assignments, Outbox messages, or Redis
projections. `RegressionGate` emits deterministic `promote` or `hold` decisions
using minimum sample, candidate failure, assignment-rate drop, and disagreement
thresholds.

## Executed gates

`./scripts/compute-api.ps1 check` — PASS

- Ruff lint and format checks — PASS
- strict mypy — PASS
- 4 API schemas and 12 contract fixtures — PASS
- 56 Python tests — PASS
- total statement/branch coverage: 96.05% — PASS
- `application/shadow.py` coverage: 99% — PASS

`./scripts/full-gate.ps1` — PASS

- control-plane, Compose, and PowerShell gates — PASS
- Java: 34 tests — PASS
- Python: 56 tests, 96.05% coverage — PASS
- Web static checks, unit tests, and production build — PASS

## Reduced shadow samples

Policy: 2 minimum samples, zero failure/drop/disagreement tolerance. Two
canonicalized requests were evaluated in reversed input order to verify stable
ordering and digest behavior.

Same-as-active candidate:

- manifest digest: `8600985ecb2f9d84520e97b64c248204d477d37d289d0f057cf10ee769f8c070`
- run digest: `3ca4791e723e13846caa12bf423b707add3014287a4b039b3a41c912d0923018`
- metrics: sample `2`, active assignment `1.0`, candidate assignment `1.0`,
  failure `0.0`, disagreement `0.0`
- assessment: `promote`

Failing candidate:

- manifest digest: `fa8d305e94e313226484d00044c6722153a69d0071282329e402b75b6ca2543a`
- run digest: `6a6533bf04dd3c1eff45c24078f9ac322fb8e561b8f987522ec2584ca8014b89`
- metrics: sample `2`, active assignment `1.0`, candidate assignment `0.0`,
  failure `1.0`, disagreement `1.0`
- assessment: `hold`
- reasons: `candidate_failure_rate_exceeded`,
  `assignment_rate_drop_exceeded`, `disagreement_rate_exceeded`

## Behavioral evidence

- Active strategy failures propagate as hard errors and are not hidden by shadow handling.
- Candidate failures retain a bounded type-based reason without leaking exception text or request data.
- Request inputs are sorted by request ID and duplicate IDs are rejected.
- Deterministic output digests omit wall-clock latency; observed payloads retain latency separately.
- Threshold equality passes; only strictly exceeded limits produce hold reasons.

## Limits

This gate is process-local and read-only. It does not claim staged traffic,
automatic rollback, statistical significance, production latency, or live
strategy promotion. Those require subsequent deployment and operational gates.
