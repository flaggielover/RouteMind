# RouteMind Spatial Lock-In Gate 2b Preregistration

Status: frozen before any Gate 2b synthetic-control or model output

Date: 2026-08-24

Protocol ID: `gate2b-stochastic-equilibrium-v1`

Machine-readable protocol:
`GATE2B_STOCHASTIC_EQUILIBRIUM_PREREGISTRATION.json`

## Scientific boundary

Gate 2b is a new confirmatory study. It is not a reanalysis or rescue of Gate 2.
The immutable historical state is:

```text
Gate 1 = PASS
Gate 2 = FAIL (UNCHANGED)
Negative-Control Diagnostic = PASS
Gate 3 eligibility = NO
Gate 3 executed = false
```

The diagnostic root cause for both layers was
`STABLE_STOCHASTIC_EQUILIBRIUM_CLASSIFIER_MISMATCH`. Gate 2b tests whether the
original short-horizon predictions locate a transition from a bounded symmetric
stochastic equilibrium to persistent sign-separated lock-in when the long-run
classifier targets a stationary distribution rather than monotone pointwise
convergence.

No Lean work, stabilization intervention, dispatch-algorithm design, or Gate 3
execution is authorized by this protocol. A Gate 2b PASS does not establish
novelty or external validity.

## Frozen historical inputs

The only threshold centers are the Gate 1 predictions:

| Layer | Frozen predicted alpha | Frozen 95% identification interval |
| --- | ---: | ---: |
| R | 2.60097908919399 | [2.59684653524659, 2.60537444184453] |
| M | 3.29064597856242 | [3.28304848117258, 3.29797102241973] |

Gate 2b never recomputes or recalibrates these quantities. The machine protocol
binds the Gate 1, Gate 2, and diagnostic files by SHA-256. Any mismatch produces
`GATE2B_FROZEN_INPUT_MISMATCH` and aborts before trajectories are created.

The Gate 1 95% identification interval overlapping the Gate 2b observed
transition bracket is a **supplementary correspondence diagnostic only**. It is
reported for each layer but is not a PASS, PARTIAL, or FAIL condition. The
primary threshold accuracy Gate is exclusively the pre-registered relative
prediction-error and transition-width rule below.

## Artifact boundary and contamination

Bulk artifacts use only:

```text
$ROUTEMIND_DATA_ROOT/research/level4/spatial_lockin/
  confirmatory/gate2b_stochastic_equilibrium/
```

The root comes from `ROUTEMIND_DATA_ROOT`; repository code must not hard-code an
absolute data path. Gate 2, diagnostic, and Gate 2b paths are disjoint. Every
artifact is exclusive-create JSON with a SHA-256 sidecar and a canonical content
digest. Existing output, overwrite, digest mismatch, cross-class access, or any
Gate 2b output predating this freeze is fail-closed contamination. Bulk traces
remain external and are not committed.

Required subdirectories are `controls/calibration`, `controls/holdout`,
`layer_r/coarse`, `layer_r/fine`, `layer_m/coarse`, `layer_m/fine`, `replay`, and
`reports`. Confirmatory and diagnostic artifacts are never pooled.

## Trajectory protocol

- Confirmatory seeds: all integers `51000` through `51063`, count `64`.
- Initial states: zero, `(0.01,0.01,0.01)`, and
  `(-0.01,-0.01,-0.01)`.
- Positive and negative initial states use the same seed and identical innovation
  stream. This is a paired common-random-number design, not 128 independent runs.
- Horizon: `4800` transitions, producing states through index `4800`.
- Burn-in: states through index `2400` are discarded.
- The primary terminal window is exactly states `3001` through `4800`, count
  `1800`. States `2401` through `3000` are a settlement buffer and diagnostic
  segment, never moved after execution.
- The terminal window is six contiguous blocks of `300` states.
- Noise is independent componentwise Gaussian with standard deviation `0.00002`
  in both layers, matching the frozen model specification.
- Layer R and Layer M use the existing implementations without parameter changes.

The fixed scalar projection in both layers is the existing service weight vector
`(0.8,0.7,0.9)` divided by its L1 norm `2.4`, namely
`(1/3,7/24,3/8)`. No projection is estimated from Gate 2b data.

## Run-level statistics

For terminal states `x_t`, let `y_t=w^T x_t`. All statistics use all `1800`
terminal states and population conventions except covariance, which uses the
usual sample denominator `1799`.

- Coordinate centrality is the three-vector of terminal coordinate means.
- Projection centrality is the mean of `y_t`.
- Covariance trace is the sum of the three sample coordinate variances.
- Projection OLS cumulative drift is `abs(beta_y) * 1799`, where `beta_y` is the
  OLS slope of `y_t` on terminal indices `0..1799`.
- Block-mean span is `max(block_mean_y)-min(block_mean_y)` across the six fixed
  blocks.
- Positive material-sign occupancy is the fraction of all terminal samples with
  `y_t >= 0.002`; negative occupancy uses `y_t <= -0.002`; the maximum is the
  material-sign occupancy.

Any missing, non-finite, wrong-length, or inconsistent statistic labels the run
`INVALID` and triggers a registered fail-closed reason at the Gate level.

## Frozen stochastic-equilibrium classifier

A finite run is `STOCHASTIC_RESTORED` only when all conditions hold:

1. each absolute coordinate mean is at most `0.002`;
2. absolute projection mean is at most `0.002`;
3. covariance trace is at most `2.5e-5`;
4. projection OLS cumulative drift is at most `0.002`;
5. projection block-mean span is at most `0.004`;
6. material-sign occupancy is strictly below `0.90`.

A finite run is `LOCKED` only when all conditions hold:

1. absolute projection mean is at least `0.01`;
2. at least `0.90` of terminal samples have the same material sign as the
   projection mean;
3. covariance trace is at most `0.001`;
4. projection OLS cumulative drift is at most `0.004`;
5. all six projection block means have the sign of the projection mean.

Every other finite run is `TRANSITIONAL`. Classification precedence is
`INVALID`, `STOCHASTIC_RESTORED`, `LOCKED`, then `TRANSITIONAL`. The centrality
bands are disjoint, so a finite run cannot satisfy both primary labels. High
variance alone is never lock-in.

These effect bounds were chosen before Gate 2b output: `0.002` is two orders of
magnitude below the old `0.02` tolerance but over fifty times the observed
alpha-zero stationary mean scale; `0.01` requires a materially separated locked
center; and the covariance/drift/block rules distinguish bounded fluctuation from
slow movement without requiring favorable finite-window slope signs.

## Strict synthetic calibration and holdout isolation

The classifier is checked only against independent synthetic families before any
RouteMind model sweep. Calibration seeds are `61000..61255`; holdout seeds are
`62000..62255`. Each phase has `256` independent seed units per family. These
ranges are disjoint from every identification, Gate 2, diagnostic, and Gate 2b
model seed.

The classifier and every numeric threshold are immutable after this protocol is
frozen. Calibration is a qualification Gate, not permission to tune. Calibration
outputs are frozen before the holdout command becomes executable. Holdout paths
must not be opened, read, listed by the study implementation, or generated before
calibration has a frozen PASS. After holdout execution, classifier changes are
unconditionally prohibited. A failed calibration or holdout remains FAIL; it is
not repaired by threshold changes.

The three fixed families use the same `4800/2400/1800/6x300` timing:

1. Stable: `x_(t+1)=A_s x_t+xi_t`, zero initial state, componentwise Gaussian
   noise SD `0.0005`, and
   `A_s=((.72,.05,0),(0,.65,.04),(0,0,.58))`.
2. Locked: scalar
   `z_(t+1)=.90 z_t+.12 tanh(8 z_t)+N(0,.0005)`, paired initial values `+0.01`
   and `-0.01`, mapped to state `z*(1,.875,1.125)`.
3. Near-critical: zero initial state, componentwise Gaussian noise SD `0.0008`,
   and diagonal transition matrix `diag(.9992,.9988,.9984)`.

Calibration and holdout must each independently satisfy:

- stable sensitivity at least `0.95` and its Wilson 95% lower bound at least
  `0.90`;
- locked paired-path sensitivity at least `0.95` and its Wilson lower bound at
  least `0.90`;
- stable-to-LOCKED false-positive rate at most `0.01`;
- locked-to-STOCHASTIC_RESTORED false-negative rate at most `0.01`;
- near-critical `TRANSITIONAL` rate at least `0.60`.

Locked sensitivity is pair-level: both signs must be `LOCKED` and their terminal
projection means must have opposite signs. The same rules are applied separately
to calibration and holdout; their counts are not pooled. Failure produces
`GATE2B_CLASSIFIER_CALIBRATION_FAILED` and prohibits model confirmation.

## Confirmatory alpha sweep

Each layer is centered only on its frozen Gate 1 prediction. The fixed coarse
multipliers are:

```text
0, 0.40, 0.65, 0.80, 0.90, 0.95,
1.00, 1.05, 1.10, 1.20, 1.40, 1.60
```

Multipliers `0.40` and `0.65` are weak-feedback negative controls. Multipliers
`1.40` and `1.60` are strong-feedback positive controls. Historical Gate 2
observed thresholds never select points.

After all coarse artifacts are frozen, select the first ascending adjacent coarse
pair labeled `ROBUST_RESTORED`, then `ROBUST_LOCKED`. Divide that exact multiplier
interval into `16` equal subintervals and run its `15` interior points. There is
no manual point selection, plot-based adjustment, horizon extension, repeated
sweep, or alternative bracket search. If no qualifying coarse pair exists, the
layer fails with `GATE2B_NO_TRANSITION` and no fine sweep occurs.

## Seed-pair aggregation

For one alpha and seed:

- `PAIRED_RESTORED`: positive and negative runs are both
  `STOCHASTIC_RESTORED`;
- `PAIRED_LOCKED`: both are `LOCKED` and projection means have opposite signs;
- `PAIRED_TRANSITIONAL`: every other finite combination;
- any `INVALID` member is retained as a failed seed unit.

An alpha is `ROBUST_RESTORED` or `ROBUST_LOCKED` only when at least `48/64`
paired seed units have the corresponding label and the two-sided Wilson 95%
lower bound is strictly above `0.60`. Otherwise it is `TRANSITIONAL`.

At alpha zero, the zero-initial run is the primary negative control. At least
`58/64` zero-initial runs must be `STOCHASTIC_RESTORED`, and the Wilson lower
bound must be strictly above `0.80`. Both weak controls must be
`ROBUST_RESTORED`. Both strong controls must be `ROBUST_LOCKED` and satisfy the
path-dependence criterion. Infrastructure and non-finite outcomes remain in the
denominator.

## Transition estimator and primary accuracy Gate

Using the combined coarse and deterministic fine grids:

```text
alpha_minus = largest alpha labeled ROBUST_RESTORED
alpha_plus  = smallest higher alpha labeled ROBUST_LOCKED
alpha_obs   = (alpha_minus + alpha_plus) / 2
width       = alpha_plus - alpha_minus
relative_prediction_error = abs(alpha_obs - frozen_alpha) / abs(alpha_obs)
relative_transition_width = width / abs(alpha_obs)
```

All tested points below `alpha_minus` must not be `ROBUST_LOCKED`; all points
above `alpha_plus` must not be `ROBUST_RESTORED`. A reversal or absent ordered
bracket is `GATE2B_NO_TRANSITION`.

The primary layer threshold Gate passes only when:

```text
relative_prediction_error <= 0.01
relative_transition_width <= 0.025
```

The frozen 95% identification interval/bracket overlap is reported next to these
values as `INTERSECTS` or `DOES_NOT_INTERSECT`, but it cannot change the verdict.

## Path dependence

At both strong-control multipliers, at least `48/64` paired seeds must have both
runs `LOCKED` with opposite terminal projection signs, and the Wilson lower bound
must be strictly above `0.60`. This is required independently in both layers.
Opposite initial conditions without opposite long-run signs do not count.

## Layer M operational correspondence

All Layer M metrics use the same terminal window. The study records regional
acceptance, served demand, waiting time, 12-minute SLA violations, courier state,
merchant utilization, and service inequality. The derived absolute regional
imbalance is `abs(a-b)/max(a+b,1e-12)` for nonnegative quantities; SLA disparity
is the absolute difference in regional violation rates.

The primary operational comparison pairs each seed/sign at `alpha_minus` and
`alpha_plus`. It passes only when:

1. mean service inequality at `alpha_plus` exceeds that at `alpha_minus` by at
   least `0.005`, and the 95% paired bootstrap interval has lower bound above
   zero;
2. among locked runs at and above `alpha_plus`, the sign of served-demand
   difference agrees with the latent projection sign for at least `48/64` seed
   pairs, with Wilson lower bound above `0.60`;
3. at least two of acceptance imbalance, waiting-time imbalance, 12-minute SLA
   disparity, courier-density imbalance, merchant-utilization imbalance, and
   served-demand imbalance have a positive upper-minus-lower paired contrast
   whose bootstrap lower bound exceeds zero.

The mechanism has no merchant preparation-time state. Prep-time imbalance is
therefore frozen as `NOT_IDENTIFIABLE_NO_PROXY`; no invented proxy is allowed and
this honest non-identifiability does not itself fail the operational Gate.

## Uncertainty

Regime and control proportions receive two-sided Wilson 95% intervals. Primary
paired continuous contrasts use `1000` paired bootstrap resamples. Layer R uses
bootstrap seed `73000`; Layer M uses `74000`, with deterministic offsets recorded
for individual statistics.

The threshold is additionally bootstrapped by resampling the 64 seed units with
replacement and recomputing all fixed-grid aggregate labels and the bracket. A
replicate without a valid transition is retained as invalid. At least `95%` of
replicates must produce a valid transition; otherwise the layer receives
`GATE2B_INCONCLUSIVE`. Percentile intervals are reported only across valid
replicates, together with the invalid fraction.

## Replay and lineage

Every record stores protocol digest, Git commit, implementation checkpoint,
model/classifier version, layer, seed, alpha/multiplier, initial condition,
horizon, windows, complete config, environment metadata, trace digest, and
artifact digest. Formal replay uses seeds `51000`, `51001`, `51031`, and `51063`
for every executed layer/stage/initial combination. Full trace digests must match.
A mismatch is `GATE2B_REPLAY_FAILED`.

## Fail-closed reason registry

The implementation must register these codes before any execution:

```text
GATE2B_FROZEN_INPUT_MISMATCH
GATE2B_ARTIFACT_EXISTS
GATE2B_CLASSIFIER_CALIBRATION_FAILED
GATE2B_NEGATIVE_CONTROL_FAILED
GATE2B_WEAK_CONTROL_FAILED
GATE2B_STRONG_CONTROL_FAILED
GATE2B_NO_TRANSITION
GATE2B_THRESHOLD_MISS
GATE2B_TRANSITION_TOO_WIDE
GATE2B_PATH_DEPENDENCE_FAILED
GATE2B_LAYER_R_FAILED
GATE2B_LAYER_M_FAILED
GATE2B_OPERATIONAL_MISMATCH
GATE2B_REPLAY_FAILED
GATE2B_CONFIRMATORY_CONTAMINATION
GATE2B_NONFINITE
GATE2B_INCONCLUSIVE
```

No code may be added after results solely to soften a failure. Unknown conditions
map to `GATE2B_INCONCLUSIVE`, not success.

## Verdict rule

`PASS` requires independent calibration and holdout PASS, all controls, ordered
transitions in both layers, both primary threshold accuracy conditions in both
layers, path dependence, Layer M operational correspondence, replay, integrity,
and no contamination.

`PARTIAL` is allowed only when every integrity, classifier, control, transition,
path, replay, and operational requirement passes in both layers, but at least one
layer is outside the PASS threshold band while remaining within both outer bands:

```text
relative_prediction_error <= 0.02
relative_transition_width <= 0.05
```

The Gate is `FAIL` for any scientific fail-closed condition or for exceeding an
outer PARTIAL bound. It is `ABORT` when frozen inputs, preregistration, artifact
lineage, or contamination checks fail before valid scientific execution.

Gate 3 eligibility is `YES` only for PASS, `CONDITIONAL` for PARTIAL, and `NO`
for FAIL or ABORT. Original Gate 2 remains `FAIL` under every outcome. Research
status may advance to `GO` only for the bounded purpose of Gate 3 after a Gate 2b
PASS; this still does not authorize a novelty claim.

## Locked execution order

1. commit and push this preregistration and both SHA-256 sidecars;
2. require its real CI to pass;
3. implement classifier, artifacts, reason codes, replay, and stage boundaries;
4. commit/push implementation and require real CI to pass;
5. execute and freeze synthetic calibration;
6. only after calibration PASS, execute and freeze untouched holdout;
7. only after holdout PASS, execute both coarse model sweeps;
8. execute only the deterministic fine points selected by the frozen rule;
9. execute replay and all Gate calculations;
10. freeze the external summary, repository validation report, machine summary,
    and SHA-256 sidecars; validate, commit, push, and observe real CI.

No later stage may be read or executed early. A failed stage remains failed; no
post-outcome tuning, seed replacement, rerun, horizon extension, or manual rescue
is allowed.
