# RouteMind Round 3 Negative Results

This is an append-only scientific review ledger. Failed hypotheses, null results,
unstable effects, sensitivity, benchmark failures, Twin non-fidelity, and
unsupported claims remain here even when engineering gates are green.

## Pre-experiment baseline limitations

- `NR-R3-001`: Existing RouteBench/RADS evidence uses internal deterministic
  scenarios and cannot establish external validity or strategy superiority.
- `NR-R3-002`: The current VRPTW planner is a bounded deterministic insertion
  baseline. No public-benchmark gap or scale claim exists yet.
- `NR-R3-003`: No immutable observed calibration/held-out dataset has yet passed
  the R3-330 contract. Current Twin capability cannot claim external fidelity.
- `NR-R3-004`: Current deterministic decision logs have not yet demonstrated
  logged propensities or action-support overlap. OPE identifiability is unresolved.
- `NR-R3-005`: No Round 3 novelty claim has passed prior-art or independent
  reproduction review. The supported-claims set is empty.
- `NR-R3-006`: Before R3-311 material execution, the bounded six-family Solomon
  design was found incapable of meeting H1-A1. Even 6/6 verified complete
  solutions yield a two-sided 95% Wilson lower bound of `0.6096657120978346`,
  below the frozen `0.95` gate. R3-311 may still produce descriptive engineering
  evidence, but this manifest is precommitted to `S-FAIL` and `C-NO-CLAIM` for
  H1-A1; the threshold will not be changed after results.
- `NR-R3-007`: R3-311 campaign
  `r3-311-20260824T065444Z-8a0a4ea5c098` retained all six frozen Solomon
  instances. Four produced independently verified complete incumbents; R101 and
  RC101 timed out without an incumbent. The verified completion rate was 4/6
  with Wilson 95% interval `[0.299993315138392, 0.9032285888942195]`, so H1-A1
  failed as precommitted. Same-vehicle distance gaps were 0% for C101/C201,
  5.3491% for R201, and 10.3053% for RC201. This is `S-FAIL` and
  `C-NO-CLAIM`; no instance was excluded and no threshold was revised.

No material Round 3 experiment had executed through the R3-311 preregistration
checkpoint. Future entries record manifest IDs, code commits, datasets, seeds,
statistical outcomes, sensitivity, and final claim disposition without rewriting
earlier entries.
