# RouteMind Level-4 Problem Discovery - Round 2 Final Report

Status: complete
Decision date: 2026-08-24
Verdict: **B - ONLY APPLICATION/INCREMENTAL CANDIDATES**
Evidence registry: [EVIDENCE_INDEX.md](EVIDENCE_INDEX.md)

## Executive decision

Round 2 did not discover a defensible Level-4 research core. Fourteen serious
candidates were generated across the three required zones and eleven fresh
failure families. Seven reduce to direct existing methods or theorems (`Class 1`)
and seven remain potentially meaningful domain extensions (`Class 2`). No
candidate reached `Class 3` or `Class 4`.

The three strongest questions are scientifically useful for RouteMind as a
research platform:

1. policy-induced informative coarsening of preparation completion (R2-04);
2. endogenous preparation-arrival synchronization (R2-02);
3. OPE support collapse under reusable-resource interference (R2-05).

The adversarial audit nevertheless found direct reductions to, respectively,
informative censoring, state-dependent queueing with delayed feedback, and
sequential-support/interference OPE. They are not authorized as Level-4 leads.

## Spatial Lock-In closure dependency

`KNOWN`: the Spatial Lock-In Threshold Prediction line is closed `NO-GO` in
[SPATIAL_LOCKIN_FINAL_CLOSURE.md](../spatial_lockin/reports/SPATIAL_LOCKIN_FINAL_CLOSURE.md).
Gate 2 remains `FAIL_UNCHANGED`; Gate 2b remains `FAIL`; Gate 3 and Lean remain
ineligible. Round 2 uses none of its seeds, classifiers, thresholds, or positive
interpretations. The only inherited rule is scientific fail-closed discipline.

The useful negative finding remains narrowly stated: short-horizon identification
localized the center of a broad long-horizon stochastic transition region, but
the preregistered sharp-threshold hypothesis failed. It is lineage evidence, not
a novelty result.

## Discovery method

The campaign followed the frozen sequence:

`plausible failure -> mechanism -> mathematical object -> reduction attack ->
cheap falsification design -> decision`.

No candidate experiment, confirmatory run, theorem proof, or Lean artifact was
created. The literature work was a targeted adversarial audit rather than a
systematic review. Therefore "no identical title found" was never treated as
novelty evidence.

The complete artifacts are:

- [CANDIDATE_MATRIX.md](CANDIDATE_MATRIX.md): 14 formulations, reductions,
  falsifications, costs, feasibility, scores, and survival estimates;
- [FAILURE_ATLAS.md](FAILURE_ATLAS.md): ten counterintuitive failure signatures;
- [CONTRADICTION_ATLAS.md](CONTRADICTION_ATLAS.md): eight literature tensions and
  hidden-variable resolutions;
- [ASSUMPTION_STRESS_MAP.md](ASSUMPTION_STRESS_MAP.md): fourteen assumptions whose
  removal may change structure;
- [FRONTIER_MAP.md](FRONTIER_MAP.md): mature interior, contested boundary, and
  evidence voids;
- [TOP3_ADVERSARIAL_AUDIT.md](TOP3_ADVERSARIAL_AUDIT.md): ten threats per Top-3
  candidate, reduction matrices, theorem-survival tests, and fatal-paper tests;
- [ROUND2_MACHINE_SUMMARY.json](ROUND2_MACHINE_SUMMARY.json): machine-readable
  decision record.

## Required search zones

### Zone A - Compound disruption and cascading failure

R2-01 formalized the mixed loss difference

`Delta(A,B)=L(A+B)-L(A)-L(B)+L(0)`.

`KNOWN`: interacting overload and discontinuous spatial cascades are established
[S28, S29]. `INFERRED`: RouteMind could benchmark superadditivity but would not
create a new object without a new invariant or universality result. Classification:
`Class 1`; killed.

### Zone B - Queueing, routing, and merchant preparation

R2-02 isolates actual service-capacity feedback; R2-04 separately isolates the
observation/censoring pathway. This separation is important because pickup delay
can be caused by latent readiness, courier arrival, or both [S07, S08].

`KNOWN`: stochastic ready-time routing, preparation-aware delayed matching,
synchronization, pickup capacity, and state-dependent service are all established
[S01, S02, S05, S07, S10, S13, S14]. `INFERRED`: R2-02 and R2-04 are credible
applied questions but reducible. Classification: `Class 2`; killed as Level-4.

### Zone C - Strategic courier response and combinatorial dispatch

R2-03 modeled acceptance/repositioning as a platform-driver Stackelberg game;
R2-11 modeled nonexclusive offer contention. Strategic driver networks,
decline-aware dispatch, and live-platform nonexclusive notifications are direct
prior art [S23--S25]. Classification: `Class 1`; killed.

## Fresh families

At least five fresh families were required; eleven were audited:

- informative preparation coarsening (R2-04);
- reusable-resource OPE support collapse (R2-05);
- stale distributed feasibility (R2-06);
- cancellation/retrial amplification (R2-07);
- fairness-retention-capacity feedback (R2-08);
- correlated tail dependence (R2-09);
- rolling-horizon orphaning (R2-10);
- nonexclusive notifications (R2-11);
- capacity/flexibility paradox (R2-12);
- prediction/decision reversal (R2-13);
- readiness disclosure information design (R2-14).

`SUPPORTED`: all eleven map to mature frameworks. The first three contain useful
RouteMind-specific diagnostics; none establishes mathematical non-reducibility.

## Top-3 disposition

### R2-04 - Informative preparation coarsening

- Precise question: what can be identified about latent readiness when dispatch
  chooses the inspection time and may change the latent process?
- Candidate theorem: characterize the identified set and minimum constrained
  randomized-probe rate.
- Strongest threat: endogenous censoring and observational-equivalence theory
  [S10--S12].
- Estimated specialist survival: `22%`.
- Decision: `Class 2`; no lead. The impossibility statement is likely a direct
  corollary, while the probe-cost result lacks a non-reducibility argument.

### R2-02 - Preparation-arrival synchronization

- Precise question: can courier bunching reduce effective merchant service enough
  to destabilize a system whose isolated components are stable?
- Candidate theorem: gain-delay stability boundary for a calibrated service law.
- Strongest threat: state-dependent service queues and standard delay-feedback
  bifurcation [S10, S13, S14].
- Estimated specialist survival: `18%`.
- Decision: `Class 2`; no lead. RouteMind lacks external evidence that courier
  presence changes actual service capacity rather than only observation time.

### R2-05 - Reusable-resource OPE support collapse

- Precise question: when is a counterfactual matching policy identified if each
  assignment changes future feasible actions?
- Candidate theorem: graph-structured necessary and sufficient path-support
  condition.
- Strongest threat: matching-market OPE, no-overlap bounds, spatio-temporal
  interference, and reusable matching [S16--S22].
- Estimated specialist survival: `14%`.
- Decision: `Class 2`; no lead. Encoding resource return times in state reduces
  the condition to sequential positivity in an MDP.

## Reviewer-panel assessment

- **NeurIPS:** R2-04 and R2-05 have clean ML/causal formulations, but a new domain
  wrapper around selective observation or support failure is insufficient. A
  separation theorem or new minimax rate would be required.
- **ICML:** the proposed synthetic falsifications would be self-confirming unless
  grounded in an externally observed anomaly. No learning result currently
  survives the generic POMDP/OPE reductions.
- **Operations Research:** R2-02 is the best domain fit, but state-dependent
  queues, preparation-aware matching, and pickup congestion make it incremental
  until a calibrated structural law yields genuinely new comparative statics.
- **Control theory:** delayed feedback, local stability, small-gain conditions, and
  Hopf transitions are standard. A dispatch label does not change that verdict.

`INFERRED`: a competent reviewer panel would reject a Level-4 novelty claim today
while potentially welcoming a carefully scoped applied-methods paper supported by
external data.

## Final research decision

### Research core

There is **no selected lead candidate**. RouteMind currently has a viable
engineering and research-platform core, but not a defensible Level-4 theorem core.
The strongest formulations are useful warnings and benchmark targets, not a new
phenomenon.

### Why no candidate survives

- the observable phenomena are already known in broader queueing, causal,
  matching, network, or control theory;
- the purported novelty generally disappears after state augmentation or a change
  of domain nouns;
- critical causal mechanisms require external or quasi-experimental data that
  RouteMind does not have;
- synthetic experiments would instantiate assumed mechanisms and could not
  establish their real existence or novelty;
- no candidate currently supports a materially new human-readable theorem.

### Single next decisive action

**Reclassify RouteMind as an engineering/research-platform project and pause the
Level-4 theorem campaign until an external or quasi-experimental dispatch anomaly
arrives that is not explained by the Failure Atlas.**

This is a stop rule, not an instruction to manufacture Round 3. A future anomaly
must include its observation protocol and credible causal variation before it can
reopen discovery.

### Authorization state

- Candidate/confirmatory experimentation: **NOT AUTHORIZED**.
- Theorem derivation: **NOT AUTHORIZED**.
- Lean formalization: **NOT ELIGIBLE / NOT AUTHORIZED**.
- Engineering use of the atlases as test-design input: **AUTHORIZED**, provided it
  is not represented as scientific confirmation.

## Claim boundary

`KNOWN`: the cited theories and repository verdicts state what this report says
they state. `SUPPORTED`: the targeted audit found direct reductions for every
candidate. `INFERRED`: no candidate is likely to survive a specialist Level-4
review. `SPECULATIVE`: a future external anomaly may expose a non-reducible
mechanism. `UNKNOWN`: exhaustive novelty status across all literature and all
future data.
