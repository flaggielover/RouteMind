# RouteMind Spatial Lock-In Gate 2 Transition Definition

Status: pre-registered before withheld long-horizon execution

Date: 2026-08-24

This file fixes the confirmatory Gate 2 classification and aggregation rules. It
contains no withheld outcomes and must be committed before the first long-horizon
sweep is executed or inspected.

## Frozen inputs

The only threshold inputs are the already frozen short-horizon predictions:

| Layer | Frozen alpha_c | Frozen 95% interval |
| --- | ---: | ---: |
| Layer R | 2.60097908919399 | [2.59684653524659, 2.60537444184453] |
| Layer M | 3.29064597856242 | [3.28304848117258, 3.29797102241973] |

The frozen threshold envelope is verified by SHA-256
`85c06e9186a069739b75be40015b2c53350bc589c16121151d2c71aca812a8bb`.
No long-horizon trajectory is allowed to modify these values or their intervals.

## Horizon and seeds

- Horizon: `1200` transitions.
- Burn-in: discard ticks `0-599`.
- Convergence window: final `300` retained ticks (`900-1199`).
- Confirmatory seeds: integers `21000` through `21063`, all retained.
- Initial conditions: zero, positive `(+0.01,+0.01,+0.01)`, negative
  `(-0.01,-0.01,-0.01)`, plus positive/negative half-size perturbations
  `(+0.005,+0.005,+0.005)` and `(-0.005,-0.005,-0.005)`.
- Matched seeds are reused across alpha values and signs. This is pairing for
  variance reduction, not an independence claim.

The coarse alpha multipliers are the fixed list:

```text
0.40, 0.60, 0.80, 0.90, 0.95, 1.00, 1.05, 1.10, 1.20, 1.40, 1.60
```

The fine multiplier grid is fixed at `0.90, 0.925, ..., 1.10`. It is evaluated
only when at least one adjacent coarse pair has different robust classifications;
the grid is never placed manually around a visually attractive point. The rule
is applied independently to each layer and is recorded in the machine-readable
summary.

## State and operational metrics

For Layer R, the state is the three-vector emitted by the reduced model. For Layer
M, the state is the three-vector of normalized courier, merchant-capacity, and
latent-demand regional imbalance emitted by the independent mechanism.

For a retained window with vectors `x_t`, define:

```text
imbalance_mean = mean(||x_t||_2)
imbalance_median = median(||x_t||_2)
imbalance_variance = variance(||x_t||_2)
sign_persistence = max over coordinates of the fraction of retained signed
                    service-advantage observations agreeing with the final sign
```

The primary scalar for classification is `imbalance_mean`. The sign used for
path dependence is the service-advantage projection `c^T x` for Layer R and the
fixed service-score projection from Layer M's pre-registered service weights for
Layer M. The projection is recorded with every run; no projection is fitted after
the sweep.

Layer M additionally records mean and median regional service inequality, accepted
orders, served demand, waiting time, courier opportunity, and merchant utilization
over the same convergence window. These are descriptive operational metrics, not
causal effects.

## Symmetry and lock-in classification

The no-feedback noise floor is the median `imbalance_mean` across all zero-alpha
confirmatory runs for the layer. The symmetry tolerance is fixed as:

```text
epsilon_sym = max(0.02, 5 * no_feedback_noise_floor)
```

Each seed/sign run receives exactly one classification:

- `RESTORED`: `imbalance_mean <= epsilon_sym`, final-window linear growth slope is
  non-positive, and the final third of the window has no positive monotone trend.
- `LOCKED`: `imbalance_mean > epsilon_sym`, sign persistence is at least `0.90`,
  the final-window variance is finite, and the final-third mean differs from the
  preceding-third mean by no more than `25%` of `epsilon_sym` plus `0.01`.
- `NOISY_SWITCHING`: magnitude exceeds `epsilon_sym` but sign persistence is below
  `0.90`.
- `AMBIGUOUS`: all remaining cases, including non-convergent or non-finite runs.

The zero initial condition is a negative control. A positive/negative pair at a
given alpha is path-dependent only if both signs are classified `LOCKED`, their
final projected signs are opposite, and the two final-window means have a 95%
paired bootstrap interval for their difference that excludes zero.

## Seed aggregation and confidence intervals

For each alpha and layer, a regime is `ROBUST_RESTORED` or `ROBUST_LOCKED` only
when at least `80%` of the 64 matched seed runs have the corresponding class and
the two-sided 95% Wilson interval for that proportion excludes `0.50`. Otherwise
the alpha is `UNRESOLVED`.

The Wilson interval is computed on the fixed complete seed list. Infrastructure
errors are retained as failed records and do not reduce the denominator. A run
with non-finite output is `AMBIGUOUS`, not silently dropped.

For all primary quantities report count, mean, median, standard deviation, and a
95% percentile bootstrap interval over the fixed seeds. Bootstrap resampling is
performed only after the raw run records are archived and never changes the class
labels.

## Observed transition and width

The primary observed threshold estimator is the midpoint of the ordered bracket:

```text
lower = largest alpha classified ROBUST_RESTORED
upper = smallest tested alpha > lower classified ROBUST_LOCKED
alpha_c_obs = (lower + upper) / 2
transition_width = upper - lower
```

The bracket is valid only if the restored point and locked point are adjacent in
the tested ordered grid after unresolved points are removed, and all lower tested
points are not locked while all higher tested points are not restored. If no valid
bracket exists, the layer has `NO_SHARP_TRANSITION` and no threshold number is
reported.

The transition is called `SHARP` only when:

```text
transition_width / alpha_c_obs <= 0.15
```

Otherwise it is a `BROAD_CROSSOVER`; the report must not use bifurcation language.

## Growth, decay, multistability, and negative controls

Growth/decay slope is estimated by ordinary least squares on log magnitude only
when every magnitude is positive; it is supportive evidence and never the primary
threshold estimator.

Multistability at alpha requires robust locked classification for both positive and
negative initial conditions, opposite final signs, and the paired difference test
above. A larger variance without this sign-separated outcome is not multistability.

Negative controls must include alpha zero and the largest tested coarse alpha below
the lower frozen confidence bound. They must be `ROBUST_RESTORED`; failure is a
Gate 2 failure, not a reason to move the tolerance.

## Prediction error and Gate 2 verdict

For each layer independently:

```text
E_alpha = abs(alpha_c_obs - frozen_alpha_c)
E_alpha_rel = E_alpha / abs(alpha_c_obs)
```

The frozen interval is considered covering when it intersects the observed
transition bracket. Coverage alone is insufficient.

Layer-level prediction passes only if the transition is `SHARP`, the midpoint
relative error is at most `0.10`, the frozen interval intersects the bracket,
multistability/path dependence is present above the bracket, and negative controls
restore symmetry.

The overall Gate 2 verdict is:

- `PASS`: both layers pass independently and Layer M operational metrics show the
  same restored/locked ordering with no more than `20%` relative disagreement in
  the sign of service inequality.
- `PARTIAL`: Layer R passes but Layer M fails, or either layer shows a broad
  crossover/uncertain transition while the other evidence remains valid.
- `FAIL`: either layer has no reproducible transition, no sharp bracket, badly
  wrong frozen prediction, no sign/path robustness, a failed negative control, or
  confirmatory contamination.
- `ABORT`: frozen artifact verification or artifact lineage fails before analysis.

Gate 3 is not evaluated here. `GATE 3 ELIGIBILITY` is `YES` only for overall
`PASS`, `CONDITIONAL` for `PARTIAL`, and `NO` for `FAIL` or `ABORT`.
