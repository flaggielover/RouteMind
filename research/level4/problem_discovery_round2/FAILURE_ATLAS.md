# RouteMind Dynamic-Dispatch Failure Atlas

Status: discovery hypotheses only
Evidence registry: [EVIDENCE_INDEX.md](EVIDENCE_INDEX.md)

No item below is an observed RouteMind production failure. Each entry separates a
plausible mechanism from a supported scientific result.

## F01 - Pickup congestion amplification

- Trigger: many couriers are dispatched to the same constrained merchant within
  one preparation cycle.
- Subsystem and symptom: merchant pickup interface; courier bunching, longer
  pickup duration, and correlated downstream lateness.
- Mechanism: `SPECULATIVE` courier presence lowers effective handoff or preparation
  service rate, which causes further early dispatch and positive feedback.
- Established explanation: pickup-capacity simulation and state/delay-dependent
  queues already cover most ingredients [S07, S10, S13, S14].
- Theory coverage: `INFERRED` substantial but not complete for a dispatch-chosen
  arrival process.
- Falsifiable prediction: holding order load fixed, arrival concentration predicts
  lower effective completion rate after controlling for merchant state.
- Minimal experiment: observational calibration with an exogenous arrival-timing
  instrument; a simulation alone cannot establish the service law.
- Research potential: medium applied theory; R2-02.

## F02 - Preparation-time attribution failure

- Trigger: a courier arrives after food is ready or dispatch changes arrival time.
- Subsystem and symptom: ETA/merchant analytics; pickup time is attributed to
  preparation, and estimated preparation distributions shift when policy shifts.
- Mechanism: `KNOWN` pickup observes `max(readiness, arrival)` and late arrival
  produces a censored readiness time [S07].
- Established explanation: informative coarsening, endogenous censoring, and
  endogenous service dependence [S10--S12].
- Theory coverage: `SUPPORTED` the generic identification failure is covered;
  dispatch-specific probe-cost bounds are `UNKNOWN`.
- Falsifiable prediction: two dispatch policies with identical merchant demand can
  yield different naive preparation estimates.
- Minimal experiment: synthetic observational-equivalence construction followed
  by a standard-theory reduction check.
- Research potential: medium incremental; R2-04.

## F03 - Logged-policy support collapse

- Trigger: a historical assignment consumes a courier, removing future feasible
  actions that the target policy would require.
- Subsystem and symptom: offline evaluation; zero/near-zero effective support and
  unstable or silently biased value estimates.
- Mechanism: `KNOWN` action-dependent reusable-resource availability plus
  trajectory interference.
- Established explanation: no-overlap OPE, matching-market OPE, temporal/spatial
  interference, and reusable matching [S16--S22].
- Theory coverage: high; exact dispatch graph condition remains `UNKNOWN`.
- Falsifiable prediction: marginal action overlap can be positive while complete
  feasible-trajectory overlap is zero.
- Minimal experiment: exhaustive finite state model with two couriers and three
  requests.
- Research potential: low-to-medium incremental; R2-05.

## F04 - Rolling-horizon orphaning

- Trigger: every replan favors newly arriving urgent jobs and omits terminal
  service debt.
- Subsystem and symptom: optimizer; an old feasible order remains repeatedly
  unassigned despite spare capacity over the full horizon.
- Mechanism: `SPECULATIVE` receding-horizon myopia.
- Established explanation: online scheduling starvation and MPC terminal-cost
  pathologies are the likely direct reductions.
- Theory coverage: `INFERRED` high; no specialist gap was found.
- Falsifiable prediction: bounded-lookahead policies have unbounded age regret on
  an adversarial but feasible trace unless age debt enters the objective.
- Minimal experiment: construct the trace analytically; no platform build needed.
- Research potential: low Level-4, high engineering-test value; R2-10.

## F05 - Cancellation/reassignment contagion

- Trigger: delay causes cancellation, which frees and requeues work while inducing
  new assignment attempts.
- Subsystem and symptom: matching queue; bursts of retries, oscillating ownership,
  and backlog amplification.
- Mechanism: a retrial/reneging branching process.
- Established explanation: matching queues with reneging directly cover the core
  [S15].
- Theory coverage: `SUPPORTED` high.
- Falsifiable prediction: amplification changes near an effective reproduction
  ratio of one.
- Minimal experiment: estimate the branching ratio from synthetic event traces.
- Research potential: low; R2-07.

## F06 - Stale feasibility fracture

- Trigger: delayed availability replicas or concurrent solvers assign the same
  reusable courier.
- Subsystem and symptom: distributed control; conflicting assignments, rejection,
  and compensating replan storms.
- Mechanism: stale read plus non-atomic reservation.
- Established explanation: distributed consistency/lease protocols combined with
  reusable-resource matching [S21, S22].
- Theory coverage: `INFERRED` complete as an engineering safety problem.
- Falsifiable prediction: conflict probability rises with decision concurrency and
  delay relative to assignment duration.
- Minimal experiment: bounded-delay concurrency test.
- Research potential: low scientific, high correctness value; R2-06.

## F07 - Fairness-induced capacity reversal

- Trigger: short-run income concentration changes future courier participation.
- Subsystem and symptom: labor supply; a myopically efficient policy loses future
  capacity, while a fairer policy later improves SLA.
- Mechanism: `SPECULATIVE` retention state coupled to earnings dispersion.
- Established explanation: strategic supply and long-term ride-hailing fairness
  [S23, S26, S27].
- Theory coverage: medium-high; causal retention response is `UNKNOWN`.
- Falsifiable prediction: exogenous dispersion reduction increases subsequent
  active supply enough to offset immediate matching loss.
- Minimal experiment: requires external or quasi-experimental labor data, not a
  RouteMind-only simulation.
- Research potential: medium empirical, low current feasibility; R2-08.

## F08 - Compound-shock superadditivity

- Trigger: two individually manageable shocks share a bottleneck.
- Subsystem and symptom: network-wide SLA; joint loss exceeds additive marginal
  losses or crosses a cascade boundary.
- Mechanism: load redistribution and common-capacity saturation.
- Established explanation: interdependent and spatial cascading failure [S28,
  S29].
- Theory coverage: high unless a new invariant is identified.
- Falsifiable prediction: positive mixed finite difference in a preregistered
  factorial design.
- Minimal experiment: cheap factorial simulation, but it would demonstrate an
  instance rather than novelty.
- Research potential: low; R2-01.

## F09 - Capacity/flexibility paradox

- Trigger: extra compatibility or couriers alter routing priorities and congestion.
- Subsystem and symptom: queue/matching; increased tail delay after nominal
  capacity expansion.
- Mechanism: endogenous flow redistribution.
- Established explanation: queueing Braess and flexibility-delay paradoxes [S30,
  S31].
- Theory coverage: high.
- Falsifiable prediction: a minimal compatibility graph admits a monotonicity
  counterexample.
- Minimal experiment: unnecessary for novelty; reproduce established examples.
- Research potential: very low; R2-12.

## F10 - Prediction/decision reversal

- Trigger: a model improves average prediction loss around a combinatorial
  decision boundary.
- Subsystem and symptom: ETA or readiness prediction; lower validation error but
  worse dispatch cost after deployment.
- Mechanism: optimizer selection bias and decision-induced distribution shift.
- Established explanation: performative prediction, decision-focused optimizer's
  curse, and informational Braess [S32--S34].
- Theory coverage: high.
- Falsifiable prediction: ranking by predictive loss and prescriptive regret can
  reverse.
- Minimal experiment: standard decision-focused counterexample.
- Research potential: very low absent a new dispatch-specific invariant; R2-13.

## Atlas conclusion

`SUPPORTED`: the most counterintuitive signatures are already explainable by
mature theory. `INFERRED`: RouteMind is currently better positioned to reproduce,
stress-test, and integrate these phenomena than to claim one as new. `UNKNOWN`:
an externally observed failure with a signature inconsistent with these reductions
could reopen discovery.
