# R3-311 Solomon VRPTW evidence

## Preregistration checkpoint

- Manifest: `docs/research/r3/manifests/solomon/solomon-stratified-six-v1.json`
- Frozen: `2026-08-24T06:17:53Z`, before any material solver execution.
- Base revision: `741c8ef93a40f0b82bb0ea375aab292e58ca4505`.
- Selection: lexicographically first member from each of C1, C2, R1, R2,
  RC1, and RC2; all six source hashes were rechecked under
  `ROUTEMIND_DATA_ROOT`.
- Bound: six runs, ten solver seconds each, one thread, zero external cost.
- Output acceptance: only complete incumbents accepted by the R3-314 independent
  verifier; R3-317 preserves timeout, resource-limit, infeasible, and failure
  outcomes.

## Pre-experiment statistical disposition

The frozen H1-A1 gate cannot be met by this bounded six-instance design. Even
6/6 successes produce a two-sided 95% Wilson lower bound of
`0.6096657120978346`, below `0.95`. This limitation was recorded as
`NR-R3-006` before execution. The campaign may provide descriptive public-
benchmark engineering evidence, but its statistical and claim dispositions are
precommitted to `S-FAIL` and `C-NO-CLAIM` for H1-A1.

## Material results

Not executed at this preregistration checkpoint.
