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

## Implementation validation checkpoint

- The compute dependency lock pins `ortools==9.15.6755`; its transitive
  protobuf constraint resolves to `6.33.6` and passed the full contract suite.
- `solomon_evaluation.py` validates the frozen protocol and source hashes,
  applies the conservative scale-1000 model, isolates public-instance runs at
  the CLI process boundary, independently recomputes double-precision routes,
  and maps the official RoutingSearchStatus values into the R3-317 contract.
- The installed API has no top-level RoutingModel random seed or worker-count
  fields. Runs record `SEED_API_NOT_AVAILABLE`, set nested SAT seed 0/workers 1,
  and do not claim bitwise runtime determinism.
- Directed validation: 14 synthetic tests cover protocol drift, a real OR-Tools
  solve, independent acceptance, outcome mapping, hierarchical references,
  immutable artifacts, checksum rejection, Wilson bounds, and CLI dispatch.
- Full local validation: Java `80/80`; Python `352/352` at `95.31%`; Web
  `92/92` plus production build; 6 schemas and 18 fixtures; control-plane,
  security, determinism, archive, mart, and semantic gates passed.

No selected C101/C201/R101/R201/RC101/RC201 solver run was executed during
implementation validation. Material execution remains gated on a committed,
remote-green implementation revision.
