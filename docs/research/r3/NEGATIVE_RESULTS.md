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
- `NR-R3-008`: R3-315 campaign
  `r3-315-20260824T073439Z-1bae0447b562` proved the optimum of all six frozen
  eight-customer conservative integer models, and every independently verified
  RoutingModel candidate matched that hierarchical objective. This does not
  prove optimality for the Euclidean-double source models or original
  100-customer instances, does not use an independent solver distribution, and
  does not establish broad quality, superiority, or external validity. The task
  therefore closes `S-NOT-APPLICABLE / C-NO-CLAIM` despite its engineering and
  experiment gates passing.
- `NR-R3-009`: R3-316 retained all 42 frozen R3-311/R3-312/R3-315 records.
  Thirty-five of 36 source benchmark runs timed out; three timed out without a
  feasible incumbent. Among the 27 source results eligible for a vehicle gap,
  the median was `31.6667%`, Type-7 p90 `349.4545%`, and maximum `484.2105%`
  worse than the retained reference vehicle count. Six questioned references
  and three no-incumbent results were retained without numeric imputation. The
  six zero gaps belong only to separate eight-customer conservative integer
  models. R3-316 is descriptive `S-PASS/C-NO-CLAIM`, not evidence of source
  optimality, quality, superiority, unrestricted capability, or population
  behavior.

Material R3-311, R3-315, and R3-316 outcomes are recorded above. Future entries retain
manifest IDs, code commits, datasets, seeds, statistical outcomes, sensitivity,
and final claim disposition without rewriting earlier entries.

- `NR-R3-010`: R3-330 froze a temporal/scenario calibration-versus-held-out
  contract with disjoint identities and five fail-closed leakage checks, but no
  authorized observed dispatch outcomes are available locally. Both splits remain
  `UNAVAILABLE_NO_OBSERVED_DATA`, all checks are `NOT_RUN_NO_DATA`, and the
  explicit outcome is `INSUFFICIENT_DATA`. Synthetic Twin replay is not used as
  held-out evidence; no fidelity, calibration, or external-validity claim is
  permitted.
- `NR-R3-011`: R3-331 loaded the content-addressed R3-330 split contract and
  R3-333 fidelity protocol, then executed the frozen bounded calibration gate.
  The calibration split and held-out split both contain zero authorized
  observed records, so all four targets returned `INSUFFICIENT_DATA`. No
  optimization, parameter-before/after artifact, checksum, held-out read, or
  synthetic replay occurred. This is `E-PASS / X-PASS / S-NOT-APPLICABLE /
  C-NO-CLAIM`; it is valid data-boundary evidence, not a Twin-fidelity result.
- `NR-R3-012`: R3-332 loaded the frozen R3-331 calibration outcome, R3-330
  split contract, and R3-333 protocol, then performed the one-shot held-out
  support gate. The authorized held-out split contains zero records, so all
  four metrics are `NOT_REPORTED_NO_DATA` with no estimate or uncertainty
  interval. No retuning, synthetic replay, external-validity claim, or missing
  value imputation occurred. This is `E-PASS / X-PASS / S-NOT-APPLICABLE /
  C-NO-CLAIM`; the no-data outcome is valid scientific boundary evidence.
- `NR-R3-013`: R3-334 froze time, zone, demand, and traffic regime axes and
  separated parameter drift from fidelity degradation. Both authorized split
  artifacts contain zero records, so the overall result is `INSUFFICIENT_DATA`
  and every regime/path is `NOT_ANALYZED_NO_DATA`. No parameter delta, fidelity
  estimate, unsupported-regime imputation, synthetic replay, or solved
  auto-calibration wording was introduced. This is `E-PASS / X-PASS /
  S-NOT-APPLICABLE / C-NO-CLAIM`.
- `NR-R3-014`: R3-335 froze separate boundaries for counterfactual replay,
  simulation comparison, and causal inference. With R3-332
  `INSUFFICIENT_DATA`, all three modes are `BOUNDARY_ONLY`, allowed scope is
  empty, and the status is `NO_VALIDITY_CLAIM`. No replay effect, simulation
  transfer, causal estimate, external-validity wording, or Twin-validity claim
  was promoted. This is `E-PASS / X-NOT-REQUIRED / S-NOT-APPLICABLE /
  C-NO-CLAIM`.
- `NR-R3-015`: R3-336 aggregated the frozen Twin evidence into a read-only
  non-fidelity report. With zero authorized observed records, all four fidelity
  thresholds are `NOT_EVALUATED_NO_DATA`, the time/zone/demand/traffic regimes
  are `NOT_ANALYZED_NO_DATA`, sensitivity is `NOT_RUN_NO_DATA`, data limits are
  `INSUFFICIENT_DATA`, and claim status is `C-NO-CLAIM`. No Twin-validity,
  causal, external-validity, stability, or simulation-transfer claim is
  permitted. This is valid scientific negative evidence, not an implementation
  failure.
- `NR-R3-016`: R3-340 froze `RADS-BASELINE-v1` and reproduced one bounded
  two-courier fixture, but the freeze contains no performance, safety,
  stability, fairness, scale, or causal evidence. The controls, full objective,
  risk bounds, selector, fallbacks, and digest rules are content-addressed;
  baseline reproducibility is an engineering/research-infrastructure result,
  not a RADS-H or Safe-RADS claim.
- `NR-R3-017`: R3-341 formalized `RADS-H-v1` with explicit threshold band,
  pressure persistence, minimum dwell, switching cost, regime reset, and
  switch/hold reasons. It intentionally executes no material comparison and
  therefore provides no empirical stability, switching-reduction, service,
  cost, safety, or superiority evidence. A minimum-dwell cooldown remains a
  separate comparator; it is not relabeled as hysteresis.
