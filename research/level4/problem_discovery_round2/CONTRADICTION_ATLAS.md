# Round 2 Contradiction Atlas

Status: literature tensions, not established contradictions
Evidence registry: [EVIDENCE_INDEX.md](EVIDENCE_INDEX.md)

The pairs below often use different models and estimands. A tension is useful only
if a hidden variable can be isolated; it is not evidence that either source is
wrong.

## X01 - Pooling helps versus pooling hurts

- Reports: meal-delivery pooling creates route efficiency, while dedicated service
  can be optimal when demand is endogenous or customers are impatient [S03, S04].
- Hidden variables: service-area size, customer patience, demand endogeneity, and
  pooling accumulation delay.
- Resolution hypothesis: pooling's route economies are dominated by waiting under
  low endogenous demand.
- Candidate impact: fully explained comparative statics; no new candidate.

## X02 - Earlier assignment helps versus strategic delay helps

- Reports: prompt assignment protects deadlines, but delayed matching thickens the
  market and can reduce total cost [S01, S02].
- Hidden variables: preparation-time uncertainty, number of feasible matches,
  courier waiting cost, and deadline slack.
- Resolution hypothesis: the value of information/flexibility changes sign across
  a slack-to-travel ratio.
- Candidate impact: direct prior art; constrains R2-02 and R2-14.

## X03 - More flexibility helps versus increases delay

- Reports: compatibility usually improves matching options, yet flexibility can
  worsen delay in bipartite queues [S21, S30].
- Hidden variables: routing discipline, load imbalance, heavy-traffic scaling, and
  compatibility topology.
- Resolution hypothesis: flexibility reroutes service away from a critical class.
- Candidate impact: kills generic R2-12.

## X04 - Accurate preparation predictions help versus observed labels are biased

- Reports: preparation-aware matching yields large operational gains [S02], while
  pickup timestamps can only upper-bound readiness when couriers arrive late [S07]
  and causal attribution is entangled [S08].
- Hidden variables: direct readiness instrumentation, inspection timing, policy
  endogeneity, and label construction.
- Resolution hypothesis: prediction gains assume labels or latent states that
  naive operational logs do not identify.
- Candidate impact: motivates R2-04, but coarsening theory [S10--S12] prevents a
  novelty inference.

## X05 - Exogenous service distribution versus delay-dependent service

- Reports: many routing models treat ready/service times as exogenous [S01, S04],
  while queueing evidence/theory allows service requirements or rates to depend on
  delay and congestion [S10, S14].
- Hidden variables: merchant work protocol, batching, courier crowding, and order
  aging.
- Resolution hypothesis: dispatch changes inspection time in some settings and
  actual service capacity in others; these are distinct causal pathways.
- Candidate impact: R2-02 must measure the service pathway, while R2-04 addresses
  the observation pathway.

## X06 - More information improves control versus worsens equilibrium

- Reports: ETA/readiness information enables anticipatory dispatch [S01, S02], but
  informational Braess shows information can worsen equilibrium outcomes [S34].
- Hidden variables: strategic response, commitment, congestion externalities, and
  whether information is public or private.
- Resolution hypothesis: control benefits dominate for obedient agents; strategic
  rerouting can reverse them.
- Candidate impact: R2-14 reduces to established information design/congestion.

## X07 - Marginal overlap versus trajectory non-overlap

- Reports: conventional OPE reasons about action propensities, while interference,
  reusable resources, and matching couple future feasible sets [S16--S22].
- Hidden variables: resource return time, exposure mapping, horizon, and policy-
  dependent feasibility.
- Resolution hypothesis: positive one-step propensity does not imply support for a
  counterfactual resource trajectory.
- Candidate impact: useful framing for R2-05, but robust bounds under no overlap
  and matching-specific OPE already exist [S17, S18].

## X08 - Short-run fairness cost versus long-run efficiency gain

- Reports: fairness constraints can reduce immediate matching freedom, while
  long-run fairness work treats participation and future outcomes as endogenous
  [S23, S26, S27].
- Hidden variables: retention elasticity, outside options, heterogeneity, and time
  horizon.
- Resolution hypothesis: a participation-stock state converts a static constraint
  into a dynamic capacity investment.
- Candidate impact: R2-08 remains empirically dependent and mathematically
  reducible.

## Contradiction conclusion

`INFERRED`: every identified tension has a plausible hidden-variable resolution
inside established theory. None currently forces a new mathematical object.
`UNKNOWN`: causal data on merchant capacity response and courier retention could
reveal a residual contradiction, but such data are not present in RouteMind.
