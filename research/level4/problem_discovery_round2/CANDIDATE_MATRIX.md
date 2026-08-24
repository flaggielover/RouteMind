# Round 2 Candidate Matrix

Status: frozen discovery-stage ranking
Decision scale: Class 0 (classical) to Class 4 (strong evidence of a new object)
Evidence registry: [EVIDENCE_INDEX.md](EVIDENCE_INDEX.md)

## Scoring rule

Each score is 0--100 in this fixed order:

`problem novelty / non-reducibility / phenomenon / theorem / algorithm /
falsifiability / RouteMind fit / benchmark / reproducibility / feasibility /
reviewer survival / Level-4 ceiling`.

Scores are comparative discovery triage, not measured probabilities. The stated
survival probability is a conservative estimate of surviving a specialist
novelty review after the reduction attack.

## Frozen ranking

1. **R2-04 - Policy-induced informative coarsening of preparation completion**
   (`Class 2`, survival `22%`, Top-3). Problem: can the latent preparation-time
   law be identified when dispatch chooses courier arrival time and pickup reveals
   either exact completion or only `R <= A`? Mechanism: `P = max(R, A)` with `A`
   policy-dependent and possibly affecting `R`. Object: policy-indexed coarsening
   kernel and identified set. Closest theory: informative coarsening, endogenous
   censoring, selective labels, queue inference [S07, S10--S12]. Reduction:
   controlled current-status/duration model. Strongest objection: the core
   impossibility and partial-identification language already exist. Opportunity:
   a dispatch-specific minimal-probe bound could still be useful, but no
   irreducibility is established. Candidate theorem: characterize the identified
   set and minimum randomized inspection support. Falsification: construct two
   preparation kernels with identical `(A,P)` law but different counterfactual
   readiness; then test whether standard coarsening theory already gives the same
   construction. Cost: low. Difficulty: medium-high. Undergraduate feasibility:
   moderate with supervision. Scores: `58/42/64/61/45/88/91/68/91/78/36/48`.

2. **R2-02 - Endogenous preparation-arrival synchronization instability**
   (`Class 2`, survival `18%`, Top-3). Problem: can dispatch-induced courier
   bunching reduce effective merchant service rate enough to create oscillation
   although isolated merchant and courier subsystems are stable? Mechanism:
   arrival intensity chosen by matching, service `mu(n_courier)` degraded by
   pickup congestion, delayed feedback to assignment. Object: state-dependent
   delayed queue-routing map. Closest theory: state-dependent queues, delay-
   dependent service, pickup congestion, and synchronized meal dispatch
   [S01, S02, S05, S07, S10, S13, S14]. Reduction: controlled queueing network or
   delay differential system. Objection: oscillation/Hopf behavior is standard
   after adding delayed negative feedback. Opportunity: a physically justified
   food-delivery service law could yield a useful domain theorem, but not yet a
   new mathematical object. Candidate theorem: a gain-delay stability boundary
   with a counterexample to monotonic courier capacity. Falsification: two-node
   fluid model with independently calibrated congestion response. Cost: low-
   medium. Difficulty: high. Undergraduate feasibility: low-moderate. Scores:
   `54/39/72/67/55/80/94/73/86/61/32/52`.

3. **R2-05 - OPE support collapse under reusable-resource interference**
   (`Class 2`, survival `14%`, Top-3). Problem: can a dispatch policy's value be
   identified from logs when one assignment changes future resource availability
   and therefore the feasible action set for all later requests? Object:
   trajectory-level support graph for combinatorial matching with reusable
   resources. Closest theory: spatio-temporal interference, no-overlap OPE,
   matching-market OPE, and reusable online matching [S16--S22]. Reduction:
   partially observed MDP with interference and action-dependent support.
   Objection: each technical ingredient and value-bounding response already has
   direct prior art. Opportunity: sharper graph-specific bounds could be useful,
   but likely incremental. Candidate theorem: necessary and sufficient logged-
   support condition for point identification of a finite-horizon matching value.
   Falsification: enumerate a two-courier, three-request model and compare the
   condition with standard sequential positivity. Cost: low. Difficulty: high.
   Undergraduate feasibility: low. Scores:
   `49/35/58/63/59/92/86/74/90/59/29/44`.

4. **R2-10 - Rolling-horizon orphaning under repeated reoptimization**
   (`Class 2`, survival `10%`, killed as Level-4). Problem: can repeated finite-
   horizon optimization perpetually postpone a feasible low-priority order?
   Object: receding-horizon service debt. Reduction: online scheduling/MPC with
   terminal-cost omission and starvation. Objection: finite-horizon myopia and
   starvation are classical. A dispatch-specific competitive lower bound may be
   publishable applied theory, not a new object. Experiment: adversarial two-zone
   arrival trace. Cost: low. Difficulty: medium. Undergraduate feasibility: high.
   Scores: `42/30/61/48/58/96/90/72/96/88/24/37`.

5. **R2-08 - Fairness-retention-capacity feedback** (`Class 2`, survival `9%`,
   killed). Problem: can short-run fairness loss improve long-run capacity through
   retention, reversing the efficiency frontier? Object: controlled participation
   stock coupled to matching. Reduction: dynamic matching/mean-field control with
   endogenous participation [S23, S26, S27]. Objection: long-run fairness and
   strategic supply response are existing topics. Experiment: stylized retention
   response sweep. Cost: medium; difficulty: high; undergraduate feasibility:
   low. Scores: `44/31/65/53/61/71/88/52/66/52/24/41`.

6. **R2-14 - Readiness disclosure as information design** (`Class 2`, survival
   `9%`, killed). Problem: should a platform reveal noisy readiness or queue
   information when disclosure changes courier arrival and merchant behavior?
   Object: signaling policy over a queue-routing game. Reduction: Bayesian
   persuasion/information design plus queueing game [S02, S06, S34]. Objection:
   an application of mature mechanisms. Experiment: two-message equilibrium.
   Cost: low; difficulty: high; undergraduate feasibility: low-moderate. Scores:
   `40/28/59/55/58/82/79/43/90/58/22/38`.

7. **R2-06 - Stale availability and feasibility fracture** (`Class 2`, survival
   `8%`, killed). Problem: delayed replicas can cause conflicting assignments of
   the same courier. Object: lease/assignment protocol over reusable resources.
   Reduction: distributed consistency plus online reusable matching [S21, S22].
   Objection: the impossibility is principally a systems consistency tradeoff, not
   dispatch mathematics. Experiment: bounded-delay adversarial trace. Cost: low;
   difficulty: medium; undergraduate feasibility: high. Scores:
   `34/20/54/35/67/98/93/61/99/91/18/29`.

8. **R2-07 - Cancellation-reassignment retrial amplification** (`Class 1`,
   survival `6%`, killed). Problem: can cancellation and reassignment create a
   self-exciting backlog? Object: matching queue with reneging and retrials.
   Reduction is direct [S15]. Objection: abandonment/retrial queues already own
   the mechanism. Experiment: branching-ratio estimate. Cost: low; difficulty:
   medium; undergraduate feasibility: high. Scores:
   `28/14/61/38/44/91/87/56/93/84/13/25`.

9. **R2-03 - Strategic courier acceptance and repositioning** (`Class 1`,
   survival `6%`, killed). Problem: characterize platform assignment when couriers
   reject and reposition strategically. Object: Stackelberg matching/queueing
   game. Direct reduction: strategic ride-hailing and decline-aware dispatch
   [S23, S24]. Experiment: two-zone equilibrium. Cost: low; difficulty: high;
   undergraduate feasibility: low. Scores:
   `25/12/58/49/60/77/88/50/84/48/12/27`.

10. **R2-01 - Compound-disruption superadditivity** (`Class 1`, survival `5%`,
    killed). Problem: when is `Delta(A,B)=L(A+B)-L(A)-L(B)+L(0)` large? Object:
    mixed finite difference of a network loss functional. Reduction: cascading
    overload, interacting network failure, or robust sensitivity [S28, S29].
    Objection: superadditivity alone is descriptive, and regime changes under
    coupled stress are established. Experiment: factorial stress grid. Cost:
    medium; difficulty: medium; undergraduate feasibility: high. Scores:
    `24/15/63/42/40/98/90/76/96/92/12/28`.

11. **R2-09 - Correlated tail risk in combinatorial SLA** (`Class 1`, survival
    `5%`, killed). Problem: correlated preparation and travel tails defeat
    marginally calibrated dispatch. Object: chance-constrained pickup-delivery
    problem with dependence ambiguity. Reduction: DRO/chance constraints and
    stochastic routing [S01, S04]. Objection: correlation-aware robust routing is
    a standard extension. Experiment: copula stress test. Cost: medium; difficulty:
    medium; undergraduate feasibility: moderate. Scores:
    `27/16/55/39/57/96/84/67/94/79/13/26`.

12. **R2-12 - More capacity or flexibility worsens SLA** (`Class 1`, survival
    `4%`, killed). Problem: can adding couriers or compatibility edges increase
    tail delay? Object: monotonicity counterexample. Direct reduction: queueing
    Braess/flexibility paradox [S30, S31]. Experiment: minimal N-network. Cost:
    low; difficulty: medium; undergraduate feasibility: high. Scores:
    `20/10/70/45/31/99/82/71/99/93/9/23`.

13. **R2-11 - Nonexclusive-notification contention** (`Class 1`, survival `3%`,
    killed). Problem: parallel courier offers create acceptance collisions and
    opportunity cost. Object: stochastic offer/acceptance matching. Direct live-
    platform prior art is fatal [S25]. Experiment: unnecessary. Cost: low;
    difficulty: medium; undergraduate feasibility: high. Scores:
    `15/7/56/36/48/90/87/45/96/86/6/17`.

14. **R2-13 - Better prediction worsens realized dispatch** (`Class 1`, survival
    `3%`, killed). Problem: lower prediction loss selects a worse combinatorial
    action after deployment. Object: decision loss under endogenous distribution
    and optimizer selection. Direct reduction: performative prediction,
    decision-focused learning, optimizer's curse, and informational Braess
    [S32--S34]. Experiment: unnecessary until a dispatch-specific residue exists.
    Cost: low; difficulty: medium; undergraduate feasibility: high. Scores:
    `17/8/65/38/42/96/83/70/98/90/7/20`.

## Ranking decision

`SUPPORTED`: all fourteen candidates reduce to established frameworks at Class 1
or Class 2. `INFERRED`: R2-04, R2-02, and R2-05 are worth retaining as frontier
questions because their RouteMind observation/action structure is unusually
concrete, not because novelty has been established. `UNKNOWN`: whether a deeper
specialist search would expose a Class-3 residue. No candidate authorizes an
experiment, theorem program, or Lean formalization.
