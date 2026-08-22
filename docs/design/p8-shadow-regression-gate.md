# P8 Strategy Shadow Mode and Regression Gate

## Goal

Evaluate a candidate dispatch strategy against the same immutable inputs as the
active strategy without allowing the candidate to affect operational authority.
The resulting shadow run must be reproducible, failure-tolerant, and suitable
for an explicit regression decision. This task provides `promote` or `hold`
evidence; staged traffic release and automatic rollback remain later controls.

## Authority and isolation

`ShadowModeEvaluator` resolves the active strategy first for every independent
`DispatchProblem`. Its decision is recorded as the sole authoritative result.
The candidate is then evaluated against the same frozen problem. Candidate
exceptions are converted into bounded failure observations and never replace,
cancel, or mutate the active result. Active strategy failures remain hard
errors because Shadow Mode must not conceal a broken operational path.

Problems are identified by unique request IDs and canonicalized by request ID.
The run is process-local and read-only: it writes no Java business state,
Outbox message, assignment, or Redis projection.

## Provenance and metrics

`ShadowManifest` records a manifest ID, code/scenario identity, seed, active and
candidate strategy names, regression policy, and bounded configuration metadata.
Decision snapshots retain strategy/version, assignment, score, and rationale.
Observed registry latency may be exposed separately, but deterministic digests
exclude wall-clock timing.

`ShadowMetrics` records sample count, active and candidate assignment rates,
candidate failure rate, and decision disagreement rate. Candidate failures count
as unassigned and disagreeing observations, so unavailable candidates cannot
appear healthy through denominator changes.

## Regression decision

`RegressionPolicy` defines:

- minimum sample count;
- maximum candidate failure rate;
- maximum assignment-rate drop relative to active;
- maximum decision disagreement rate.

`RegressionGate` returns `promote` only when every threshold passes. Otherwise it
returns `hold` with stable reason codes and the run/manifest digests. The gate is
a deterministic policy check, not a statistical significance or production
performance claim.

## Validation

Tests cover candidate isolation, active failure propagation, candidate failure
capture, canonical input ordering, duplicate request rejection, deterministic
digests, metric denominators, threshold boundaries, and explicit promote/hold
reasons. Full repository regression must pass before RM-081 can be marked passed.
