# RouteMind Round 3 Research Contract

Contract version: `r3-research-contract-v1`
Date frozen: 2026-08-24 (Asia/Shanghai)
Data root: `ROUTEMIND_DATA_ROOT` only; no fixed drive letter in runtime code

## Scientific status model

- `E-*` records implementation and engineering verification.
- `X-*` records whether the manifest-bound experiment actually ran and reproduced.
- `S-*` records predefined statistical criteria, uncertainty, assumptions, and
  support or failure.
- `C-*` records final claim admissibility after prior art, independent
  verification, reproduction, and wording review.

`E-PASS` never implies `X-PASS`, `S-PASS`, or `C-PASS`. `S-FAIL` with
`C-NO-CLAIM` is a valid research result. CI contributes only to engineering
integrity and encoded reproducibility checks.

## Research questions and preregistered boundaries

### External validity and solver science

RQ-A1: On a preregistered compatible Solomon VRPTW subset, what proportion of
RouteMind outputs are independently verified complete feasible solutions within
the resource limit?

H0-A1: The lower bound of the verified feasible completion rate is below 0.95.
H1-A1: The two-sided 95% Wilson interval lower bound is at least 0.95. This gate
supports only a scoped feasibility claim, not optimality or superiority.

RQ-A2: What objective gaps, route counts, timeouts, infeasible results, and
resource failures occur against cited best-known or proven reference values?
Gap statistics are descriptive across every preregistered instance. No positive
quality threshold is set until source semantics and reference status are verified.

### Statistical RouteBench

RQ-B1: Does the current risk-aware strategy reduce paired scenario risk relative
to weighted-greedy without material assignment loss under a preregistered stress
matrix?

H0-B1: The mean paired risk difference is non-negative or the assignment-rate
difference is below the -0.02 non-inferiority margin.
H1-B1: The 95% paired interval for risk difference is below zero and assignment
rate is non-inferior at -0.02. Scenario-family hypotheses use Holm correction.
Runtime, failures, and fallbacks are co-primary safety diagnostics, not hidden
secondary output. A pilot estimates variance and run count before the campaign.

### Digital Twin science

RQ-C1: Does calibration on an immutable training split improve prespecified
fidelity metrics on a disjoint held-out split, and does the result meet absolute
scope thresholds frozen in R3-333?

`VALIDATED_FOR_SCOPE` requires every primary absolute threshold and leakage check
to pass. `PARTIALLY_VALIDATED` requires improvement but at least one absolute
threshold to fail. `FAILED_VALIDATION` records adequate data with failed primary
gates. `INSUFFICIENT_DATA` records inadequate sample/support. Calibration fit
alone cannot answer RQ-C1, and held-out data cannot be reused for tuning.

### RADS research

RQ-D1: Does formal hysteresis reduce harmful strategy switching compared with
RADS-BASELINE-v1 and a simple cooldown without materially degrading service?

H0-D1: Switch frequency reduction is below 25%, or assignment/service quality
crosses the -0.02 non-inferiority margin, or route-cost degradation exceeds 3%.
H1-D1: Switch frequency falls by at least 25%, service is non-inferior at -0.02,
and route-cost degradation remains within 3%, using paired uncertainty and Holm
correction across primary regimes.

RQ-D2: Can an explicitly constrained Safe-RADS variant satisfy a preregistered
risk/SLA constraint with a measured and bounded efficiency cost?

R3-344 must formalize the constraint and epsilon before data. Penalty-only models
cannot satisfy this question and cannot use safety wording.

### Advanced evaluation

RQ-E1: Are candidate effects identifiable under shared courier-resource
interference and current logged action support? Lack of propensities or overlap
must produce `OPE_NOT_IDENTIFIABLE_FROM_CURRENT_LOGS`; propensity scores will not
be invented.

## Experiment manifest minimum

Every material run records experiment/hypothesis identity, code commit,
environment, dataset and checksum, reference-data version, scenario, strategy and
version, parameters, seeds, random-stream policy, solver/version/thread count,
resource limits, timestamps, output paths/checksums, frozen statistical plan, and
execution status. Large artifacts stay outside Git under `ROUTEMIND_DATA_ROOT`;
Git stores manifests, checksums, schemas, small fixtures, and summaries.

## Exclusions and stopping

Only prespecified parser-invalid, checksum-invalid, license-disallowed, or
execution-defect runs may be excluded; each exclusion remains in the run ledger.
Bad seeds, poor solver results, failed fidelity gates, and null effects are not
exclusions. Bounded pilots stop at their manifest limit. Material campaigns stop
for resource-bound, invalid data, verifier failure, or preregistered sequential
criteria, never because a desired answer has appeared.

## Resource policy

Before a material campaign, record run count, CPU-time estimate, peak memory,
disk estimate, and external cost. Local bounded pilots without credentials or
legal ambiguity may proceed autonomously. Paid/cloud campaigns, new credentials,
or licensing uncertainty require explicit authorization.

## Scientific non-claims

Round 3 does not assume novelty, causal validity, production safety, Twin fidelity,
solver optimality, nationwide generality, or strategy superiority. What-if and
Decision X-Ray outputs remain model/system counterfactuals. Empirical switching
stability is not theoretical stability. Claims become admissible only through the
central claim matrix and final C gate.
