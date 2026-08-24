# Round 2 Assumption Stress Map

Status: qualitative structural audit
Evidence registry: [EVIDENCE_INDEX.md](EVIDENCE_INDEX.md)

## A01 - Exogenous merchant preparation

Removing the assumption permits preparation/service to depend on order age,
queue state, batching, or courier congestion. This can change stability rather
than only constants [S10, S13, S14]. Structural risk: high. Novelty residue:
low-to-unknown because state-dependent service is mature. Candidate: R2-02.

## A02 - Directly observed readiness

Removing the assumption changes point observation into policy-dependent
coarsening: `P=max(R,A)` reveals exact `R` only on part of the sample [S07]. If
`A` and `R` are dependent, standard ignorability fails [S10--S12]. Structural
risk: high. Novelty residue: low; dispatch-specific probe design is unknown.
Candidate: R2-04.

## A03 - Obedient couriers

Rejection, repositioning, waiting, and strategic availability turn centralized
matching into a game. Strategic ride-hailing and decline-aware dispatch directly
cover this transition [S23, S24]. Structural risk: high. Novelty residue: very
low. Candidate R2-03 killed.

## A04 - Exclusive offers

Removing exclusivity creates acceptance contention and option value, but live-
platform nonexclusive notification work is direct prior art [S25]. Structural
risk: medium. Novelty residue: negligible. Candidate R2-11 killed.

## A05 - Independent requests and no interference

Assignments alter spatial supply and future feasible matches. Spatio-temporal
policy evaluation explicitly models interference and carryover [S16]. Structural
risk: high. Novelty residue: low. Candidate: R2-05.

## A06 - Static action support

Reusable couriers make the feasible action set depend on earlier actions and
return times [S21, S22]. This can destroy trajectory overlap while marginal
overlap remains. Structural risk: high. Novelty residue: low-to-unknown because
no-overlap bounds and matching-market OPE already exist [S17, S18]. Candidate:
R2-05.

## A07 - Instantaneous consistent availability

Removing the assumption permits concurrent conflicting reservations. The change
is structural for correctness but reduces to consistency/lease design plus
reusable matching. Structural risk: high. Novelty residue: negligible. Candidate
R2-06 killed.

## A08 - No abandonment or retrials

Removing the assumption changes conservation equations and can produce feedback,
but matching queues with reneging already establish the core object [S15].
Structural risk: medium-high. Novelty residue: very low. Candidate R2-07 killed.

## A09 - Independent/light-tailed disturbances

Correlation and heavy tails alter SLA chance constraints and cascade risk.
Cascading networks and stochastic/robust routing already own the main reductions
[S01, S04, S28, S29]. Structural risk: high near saturation. Novelty residue:
very low without a new dependence invariant. Candidates R2-01 and R2-09 killed.

## A10 - More capacity/flexibility is monotone beneficial

Removing monotonicity exposes flow-redistribution paradoxes. Queueing Braess and
flexibility-delay results directly show the qualitative reversal [S30, S31].
Structural risk: medium. Novelty residue: negligible. Candidate R2-12 killed.

## A11 - Prediction is passive

Deployed predictions change decisions and possibly the data distribution;
optimizer selection can reverse predictive and prescriptive rankings [S32, S33].
Structural risk: high. Novelty residue: negligible under the campaign exclusion
zone. Candidate R2-13 killed.

## A12 - Static labor supply

Retention and participation make current earnings distribution a future capacity
state [S23, S26, S27]. Structural risk: high over long horizons. Novelty residue:
low; the missing ingredient is credible causal data, not a new generic model.
Candidate R2-08 killed.

## A13 - Unconstrained pickup interface

Finite curb or handoff capacity can couple spatial dispatch to local congestion
[S07]. Structural risk: medium-high. Novelty residue: low because queue capacity
and state-dependent service are established; an empirically validated dispatch-
specific law remains unknown. Candidate: R2-02.

## A14 - Perfectly specified terminal value

Finite-horizon replanning without service debt can starve old work. Structural
risk: medium. Novelty residue: low because online scheduling and MPC already
explain the mechanism. Candidate R2-10 killed.

## Stress conclusion

`SUPPORTED`: removing unrealistic assumptions often changes stability,
identifiability, or equilibrium structure, not merely performance constants.
`INFERRED`: those structural changes still map to mature theories. The assumption
audit identifies high-value validation targets for RouteMind, but it does not
establish Level-4 novelty.
