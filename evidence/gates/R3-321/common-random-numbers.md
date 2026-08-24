# R3-321 common-random-number stream ownership evidence

Date: 2026-08-24 (Asia/Shanghai)

## Scope

R3-321 implements the random-stream ownership and reuse contract frozen by
`r3-320-statistical-routebench-v1`. It does not execute the eight-regime pilot or
confirmatory campaign and does not estimate a strategy effect.

## Ownership design

- Pair identity is exactly protocol, phase, regime, and replicate. Pilot
  replicates are 0-7; confirmatory identities are 1000-1199 at the frozen maximum.
- Demand, merchant, courier, and traffic have distinct logical owners. Strategy
  arms never own environmental randomness.
- Each 63-bit seed is the first 16 hex digits of
  `SHA256(protocol_id|phase|regime_id|replicate|stream_name)`, masked to 63 bits.
  The arm identity is intentionally absent.
- A stream plan is content-addressed. Each owner materializes its payload once;
  the paired manifest binds its canonical content digest. Candidate and
  comparator bindings reference the same four realization digests.
- Execution order alternates by replicate parity, but order never changes the
  pair or stream identities. Different phases, regimes, and replicates cannot
  reuse a stream digest.
- The explicit disposition is
  `VARIANCE_CONTROL_NOT_OBSERVATION_INDEPENDENCE`: CRN reduces paired variance
  and does not make pairs, requests, regimes, or shared-resource outcomes
  statistically independent.

`routebench-crn` is registered as `DETERMINISM_CRITICAL`. Missing/extra streams,
out-of-range identities, owner drift, invalid digests, arm-specific payloads,
non-canonical data, and mismatched realizations fail closed.

The locked `pilot/normal/0` seed tuple is
`(4816923383674551721, 1496333979318861507, 9107451314426469478,
8847950333973352481)`. The corresponding plan digest is
`9c4b643fff5b8db5bad9be038ab9498088c35a6dde460606ba844bc9a85d71d2`;
tests also prove that repeated materialization and input-map reordering preserve
the manifest and realization digests.

## Validation

- 21 directed CRN tests passed. Isolated branch-aware coverage for the new module
  is 96.12%, above the 95% gate.
- The full Python suite passed 565/565 at 95.76% total coverage. Ruff formatting
  and lint, mypy, 6 schemas / 18 contract fixtures, determinism, archive, mart,
  and semantic-metric gates passed.
- The complete repository gate passed Java 80/80 and Web 92/92 plus the
  production build and repository controls.
- R3-320 closure revision `6d7a2f1` passed all five GitHub Actions jobs in run
  `32713474028`, so this implementation began from a remote-green prerequisite.

Implementation revision `00475b8` passed all five GitHub Actions jobs in run
`32714350193`, including frozen Python/contracts and browser smoke.

Final disposition: `E-PASS / X-NOT-REQUIRED / S-NOT-APPLICABLE /
C-NOT-APPLICABLE`. No pilot observations or strategy-effect claims exist.
