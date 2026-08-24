# Round 2 Top-3 Adversarial Audit

Status: final red-team assessment
Evidence registry: [EVIDENCE_INDEX.md](EVIDENCE_INDEX.md)
Candidate registry: [CANDIDATE_MATRIX.md](CANDIDATE_MATRIX.md)

The objective of this audit is to kill candidates that are useful but
mathematically reducible. No experiment was run and no theorem was derived.

## R2-04 - Policy-induced informative coarsening

### Minimal formulation

For order `i`, let `X_i` be observed context, `R_i(pi)` latent readiness time
under policy `pi`, `A_i(pi)` courier arrival selected by dispatch, and

`P_i(pi) = max(R_i(pi), A_i(pi))`.

In the idealized log, `D_i=1[R_i>A_i]` indicates that the courier waited, so
`R_i=P_i` when `D_i=1` and only `R_i<=A_i` is known when `D_i=0`. Real pickup
scans add interval/measurement error. The target is either `Law(R(pi*))` or the
counterfactual dispatch value under `pi*`.

The proposed object was a policy-indexed identified set

`I(pi*) = {Q : Q and some coarsening kernel generate Law(X,A,P,D)}`.

`SPECULATIVE`: a randomized arrival probe subject to SLA and reusable-courier
constraints might shrink `I(pi*)` at a quantifiable minimum cost.

### Ten most dangerous papers or frameworks

1. Coarsening at random and nonignorable coarsening: the observation map is a
   direct instance [S11].
2. Endogenous censoring and partial identification: the target is already a
   duration distribution with endogenous inspection/censoring [S12].
3. Observational equivalence of endogenous and exogenous service-delay dependence:
   a direct warning that mechanisms cannot be separated from queue logs [S10].
4. Current-status/interval-censoring theory: `D` is a current-status observation
   at the inspection time `A`.
5. Selective-label theory: exact readiness is selectively observed according to a
   decision-linked event.
6. Controlled sensing/active experimental design: choosing `A` to shrink an
   identified set is not dispatch-specific mathematics.
7. POMDP/dual-control theory: action changes both system evolution and information.
8. Instrumental-variable identification for confounded sequential decisions:
   randomized probes are standard identification devices.
9. Queue inference with partial information: service distributions from incomplete
   queue observations are established inverse problems.
10. Meal-delivery timestamp practice: pickup minus placement is explicitly only an
    upper bound when the courier arrives late [S07], while causal delivery analysis
    already flags preparation/pickup entanglement [S08].

### Explicit reduction matrix

- Latent `R`, inspection `A`, binary `D`: case-1 interval censoring/current-status
  data. Residue: none.
- Dependence between `A` and `R`: informative/endogenous censoring. Residue: none
  at the impossibility level [S11, S12].
- Policy changes `A`: controlled inspection/experimental design. Residue: only the
  dispatch feasibility constraint.
- Policy also changes `R`: treatment-dependent potential duration plus
  interference/mediation. Residue: no identified dispatch-specific invariant.
- Courier is reusable: constrained sensing resource/online matching [S21, S22].
  Residue: a potentially sharper budget, not a new identification principle.
- Pickup scan error: interval censoring/measurement error. Residue: none.

### Theorem survival matrix

- **T04.1:** unrestricted dependence makes `Law(R)` non-point-identifiable from
  `(A,P,D)`. Verdict: likely true, but directly classical; fails novelty.
- **T04.2:** conditional coarsening-at-random plus inspection support point-
  identifies `Law(R|X)`. Verdict: standard; fails novelty.
- **T04.3:** two different readiness mechanisms can induce the same operational log
  and different counterfactual dispatch values. Verdict: useful domain
  counterexample, but follows endogenous censoring/observational equivalence
  [S10--S12].
- **T04.4:** there is a positive minimum randomized-probe rate for uniform-width
  identification under SLA constraints. Verdict: `UNKNOWN`; may survive as an
  optimization result, but no separation from optimal design/controlled sensing
  has been shown.
- **T04.5:** a graph-dependent probe schedule is minimax optimal with reusable
  couriers. Verdict: `SPECULATIVE`; likely an incremental constrained-design
  theorem.

### Fatal-paper test

Replace "meal readiness" by "event time," "courier arrival" by "inspection or
censoring time," and "dispatch probe" by "designed inspection." The core
identification question remains unchanged and is covered by [S10--S12]. The
candidate therefore fails the fatal-paper test as a new mathematical object.

### Cheapest falsification

Construct a two-point readiness distribution and two endogenous arrival kernels
with identical observed `(A,P,D)` law but different counterfactual readiness. Then
map the construction to a standard current-status/endogenous-censoring example.
If the mapping is exact, the proposed impossibility theorem is a corollary. This
is a desk proof, not an experiment.

### Red-team verdict

`Class 2`, estimated specialist survival `22%`. Retain as an important RouteMind
measurement warning and possible applied-methods question. Kill as a Level-4 lead
until a theorem separates dispatch-constrained probing from existing controlled
coarsening theory.

## R2-02 - Endogenous preparation-arrival synchronization

### Minimal formulation

For merchant `m`, let `q_m(t)` be unfinished orders, `c_m(t)` couriers present,
`u_m(t)` dispatch-induced courier arrivals, and `s_m(t)` completions. A fluid
idealization is

`dq_m/dt = lambda_m(t) - mu_m(q_m(t),c_m(t))`,

`dc_m/dt = u_m(t-tau) - h_m(q_m(t),c_m(t))`,

with dispatch `u(t)=Pi(q_hat(t),c(t),travel(t))`. The hypothesis requires more
than waiting: `d mu_m / d c_m < 0` over a material range, so dispatch-induced
crowding changes actual service/handoff capacity. The candidate phenomenon is a
stable isolated kitchen and stable isolated courier flow becoming oscillatory
when coupled through delayed dispatch.

### Ten most dangerous papers or frameworks

1. State-dependent queue stability [S13].
2. Delay/queueing-time-dependent service rates [S10, S14].
3. Classical queueing-network fluid limits and Lyapunov stability.
4. Delay differential equations and Hopf bifurcation under feedback delay.
5. Polling systems with switchover/setup delay.
6. Matching queues and abandonment [S15].
7. Dynamic meal pickup/delivery with random ready times [S01].
8. Preparation-aware delayed matching and threshold policies [S02].
9. Preparation-delivery synchronization in ghost kitchens [S05].
10. Finite pickup-capacity food-delivery simulation [S07].

### Explicit reduction matrix

- Merchant order stock: single/multiclass queue. Residue: none.
- Courier arrivals controlled by dispatch: admission/routing control. Residue:
  none.
- `mu(q,c)` state dependence: state-dependent service network [S13, S14]. Residue:
  domain calibration only.
- Dispatch delay `tau`: delayed feedback/DDE. Residue: none.
- Courier-order compatibility: matching queue. Residue: none [S15].
- Spatial travel: stochastic routing/polling. Residue: none [S01, S04].
- Bunching at constrained pickup: finite-capacity handoff queue. Residue: empirical
  service law, not a new mathematical category [S07].

### Theorem survival matrix

- **T02.1:** a small-gain condition guarantees local stability. Verdict: standard
  control/queue result; fails novelty.
- **T02.2:** crossing a gain-delay boundary produces a Hopf bifurcation. Verdict:
  standard DDE phenomenon; fails novelty without a special invariant.
- **T02.3:** adding couriers worsens tail delay through service degradation.
  Verdict: a Braess/state-dependent-service counterexample; threatened by [S30,
  S31].
- **T02.4:** a food-delivery-specific coupling law yields a closed-form stability
  boundary. Verdict: potentially useful applied theorem, but still Class 2.
- **T02.5:** the coupled system has behavior impossible in any state-dependent
  queueing network. Verdict: no supporting argument; likely false.

### Fatal-paper test

Replace "merchant" with a state-dependent server, "courier bunching" with
congestion state, and "dispatch" with delayed admission control. The mathematical
system remains a controlled state-dependent queue/DDE. Existing theory owns the
stability and oscillation mechanisms [S10, S13, S14]. The candidate fails unless
an empirically justified service law creates a provable non-reducible structure.

### Cheapest falsification

Before simulation, seek exogenous variation in courier arrival concentration and
test whether it changes actual preparation/handoff completion capacity, not just
observed pickup time. RouteMind currently has no such proxy or external data, so
even this cheap causal falsification is unavailable. A synthetic positive result
would merely encode the assumed `mu(q,c)`.

### Red-team verdict

`Class 2`, estimated specialist survival `18%`. Kill as a Level-4 lead. It remains
a credible empirical operations question only if external data establish the
coupling law.

## R2-05 - OPE support collapse with reusable-resource interference

### Minimal formulation

At time `t`, state `S_t` includes pending requests and resource return times.
Policy `pi` selects matching `M_t` from feasible set `F(S_t)`. Matching changes
future state and feasibility:

`S_{t+1} ~ K(. | S_t, M_t)`, and `F_{t+1}=F(S_{t+1})`.

Logs are generated by behavior policy `mu`. The proposed support graph has nodes
`(t,S_t)` and edges for feasible matchings with positive `mu` probability. A
target value is point identified only if every target-reachable reward-relevant
path is sufficiently represented or recoverable under structural assumptions.

### Ten most dangerous papers or frameworks

1. Sequential positivity/overlap in causal inference and OPE.
2. Robust OPE bounds under latent confounding and no support [S17].
3. Spatio-temporal dependent policy experiments with interference and carryover
   in ride-sharing [S16].
4. OPE specialized to matching markets [S18].
5. OPE for combinatorial/slate actions [S19].
6. Counterfactual evaluation for algorithmic resource-allocation trials [S20].
7. Online matching with reusable resources [S21].
8. Ride-sharing matching with offline reusable resources [S22].
9. POMDP/MDP occupancy-measure and concentrability theory.
10. Partial identification and sensitivity analysis under interference/exposure
    mappings.

### Explicit reduction matrix

- Assignment consumes future capacity: MDP transition with reusable resource.
  Residue: none [S21, S22].
- One assignment affects other units: interference/exposure mapping. Residue: none
  [S16].
- Combinatorial action: slate/matching OPE. Residue: none [S18, S19].
- Behavior lacks target action: positivity violation/no-overlap bounds. Residue:
  none [S17].
- State omits return-time confounder: latent-confounded OPE/POMDP. Residue: none.
- Feasible set is policy-dependent: ordinary endogenous state support in an MDP.
  Residue: graph notation, not a new principle.

### Theorem survival matrix

- **T05.1:** one-step marginal overlap is insufficient for trajectory value
  identification. Verdict: standard sequential-overlap fact; fails novelty.
- **T05.2:** full target path support is sufficient in a finite fully observed
  model. Verdict: standard importance-sampling/g-formula condition.
- **T05.3:** absent overlap, only value bounds are identified. Verdict: direct
  prior art [S17].
- **T05.4:** matching compatibility permits weaker support than arbitrary MDPs.
  Verdict: `UNKNOWN`, but matching-market OPE [S18] is a severe threat.
- **T05.5:** a minimum exploration policy guarantees future feasible-set coverage
  with reusable resources. Verdict: likely an incremental exploration/online-
  matching theorem.

### Fatal-paper test

Encode each feasible matching as an action and all resource return times in the
state. The "support graph collapse" becomes ordinary sequential positivity in a
large finite MDP. Add interference through an exposure map and matching-specific
estimators; [S16--S22] cover every named ingredient. The candidate fails the test
as a new research object.

### Cheapest falsification

Enumerate a finite two-courier, three-request system. Compare the proposed graph
criterion with the standard support condition on state-action occupancy measures.
An exact equivalence kills the theorem immediately. This is a desk calculation;
no logs or platform implementation are justified.

### Red-team verdict

`Class 2`, estimated specialist survival `14%`. Kill as a Level-4 lead. Preserve
the support-graph visualization as an engineering diagnostic for whether an OPE
claim is even admissible.

## Cross-candidate decision

All three candidates survive as useful RouteMind research-platform questions but
fail the stronger non-reducibility requirement:

- R2-04 reduces to informative coarsening/endogenous censoring;
- R2-02 reduces to state-dependent queues plus delayed feedback;
- R2-05 reduces to MDP sequential support, interference, and matching-market OPE.

`SUPPORTED`: no Class 3 or Class 4 candidate remains. `INFERRED`: attempting cheap
synthetic experiments now would test assumptions chosen by RouteMind rather than
an independently observed phenomenon. `UNKNOWN`: external or quasi-experimental
data could expose a residual mechanism that this audit cannot see.
