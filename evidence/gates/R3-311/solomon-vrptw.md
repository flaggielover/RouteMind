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

Campaign `r3-311-20260824T065444Z-8a0a4ea5c098` executed all six frozen
instances using remote-green implementation revision
`8a0a4ea5c098347b2224ec8ef9b2b8aef66564e5` (Actions run `32699067563`).
Full artifacts are below
`experiments/r3/R3-311/r3-311-20260824T065444Z-8a0a4ea5c098` in
`ROUTEMIND_DATA_ROOT`; the committed compact ledger is
`docs/research/r3/results/solomon/solomon-stratified-six-results-v1.json`.

- Selection/exclusion: 6 selected, 6 executed, 6 retained, 0 excluded.
- Outcomes: 4 `TIMEOUT_WITH_FEASIBLE`, 2 `TIMEOUT_NO_FEASIBLE`.
- Independent verification: every incumbent was verified; 4/4 were complete
  and valid. R101 and RC101 produced no incumbent, so no feasibility output was
  available to verify or compare.
- Primary result: 4/6 = `0.6666666666666666`; two-sided Wilson 95% interval
  `[0.299993315138392, 0.9032285888942195]`. The frozen lower-bound gate failed.
- Hierarchical reference comparison: C101 and C201 match the cited distance at
  two decimals with the same vehicle count; R201 is `5.349058185679953%` and
  RC201 `10.305343511450381%` above reference distance with the same vehicle
  count. No scalar gap applies to the two no-incumbent outcomes.
- Artifact integrity: all seven JSON artifacts matched their sidecars; campaign
  summary SHA-256 is
  `e5fc0c512f906ffd5370fbb77ac4fe942ae63d796b7930321ed61111545e89ee`.

Final gates: `E-PASS / X-PASS / S-FAIL / C-NO-CLAIM`. X-PASS means the frozen
campaign executed with complete retention and verification semantics; it does
not convert the failed hypothesis or descriptive reference gaps into a claim.

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
