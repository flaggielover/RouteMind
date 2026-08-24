# Round 2 Frontier Map

Status: adversarial map as of 2026-08-24
Evidence registry: [EVIDENCE_INDEX.md](EVIDENCE_INDEX.md)

## Mature interior

The following objects are already inside established research programs and must
not be presented as RouteMind novelty:

- stochastic/dynamic meal pickup and delivery with random ready times [S01, S04];
- preparation-aware delayed matching and market thickness [S02];
- spatial queueing, pooling, and endogenous demand [S03];
- strategic driver participation, rejection, and repositioning [S23, S24];
- nonexclusive driver offers [S25];
- cascades and superadditive overload [S28, S29];
- capacity/flexibility and information paradoxes [S30, S31, S34];
- performative prediction and optimizer-induced decision reversal [S32, S33];
- reneging matching queues and reusable-resource matching [S15, S21, S22];
- generic spatio-temporal interference and no-overlap OPE [S16--S20].

`KNOWN`: adding RouteMind terminology or combining these components does not make
a new mathematical object.

## Contested boundary

### B1 - Policy-induced preparation coarsening (R2-04)

Candidate object: the family of observation maps

`O_pi = (X, A_pi, P=max(R_pi,A_pi), 1[R_pi>A_pi])`

where policy `pi` chooses inspection/arrival time and may also change the latent
preparation law through congestion. The dispatch interpretation is concrete, but
the object is strongly reducible to informative coarsening and endogenous
censoring [S10--S12].

- Surviving question: can a minimal random-probe budget be characterized under
  reusable-resource and SLA constraints?
- Missing evidence: no proof that the budget theorem differs materially from
  controlled sensing/experimental design.
- Frontier status: `INFERRED` Class 2, not a Level-4 lead.

### B2 - Endogenous preparation-arrival coupling (R2-02)

Candidate object: a controlled delayed queue-routing system with
`mu_m(t)=g(q_m(t),c_m(t))`, where dispatch controls courier arrivals `c_m` and
merchant state feeds back into assignment.

- Surviving question: is there an empirically defensible service law producing a
  nonstandard stability boundary?
- Missing evidence: courier presence affecting actual service capacity, as
  distinct from mere observation/censoring.
- Frontier status: `INFERRED` Class 2 due to state-dependent queue and food-
  delivery synchronization prior art [S02, S05, S07, S10, S13, S14].

### B3 - Reusable-resource OPE support graph (R2-05)

Candidate object: a policy-dependent directed graph of feasible assignment
trajectories, with point identification only when logged support covers target
paths.

- Surviving question: can graph structure produce sharper necessary and
  sufficient support conditions than generic sequential positivity?
- Missing evidence: no demonstrated separation from existing matching-market OPE,
  interference models, or no-overlap bounds [S16--S22].
- Frontier status: `INFERRED` Class 2.

## Evidence voids, not research gaps

The following are `UNKNOWN` because RouteMind lacks the relevant external data:

- the causal effect of courier crowding on merchant preparation/handoff capacity;
- the causal retention elasticity of couriers to income/fairness interventions;
- the real observation protocol and instrumentation for meal readiness;
- behavior-policy propensities and exposure mappings in a live matching market;
- cross-merchant correlated disruption tails.

An evidence void cannot be promoted to a novelty gap. It instead limits which
questions RouteMind can falsify credibly.

## Excluded territory

The campaign did not reopen adaptive hysteretic switching, vector-valued
prediction novelty, generic computation staleness, generic performative dispatch,
or the rejected sharp Spatial Lock-In threshold. These remain excluded by the
task contract and prior closure record.

## Frontier verdict

`SUPPORTED`: Round 2 found useful domain-specific formulations but no Class 3 or
Class 4 object. `INFERRED`: the frontier is currently methodological application
and validation, not new theory. `UNKNOWN`: a genuinely anomalous external or
quasi-experimental observation could create a future phenomenon-first lead.
