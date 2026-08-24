# RouteMind Spatial Lock-In Negative-Control Diagnostic Preregistration

Status: frozen before diagnostic execution

Date: 2026-08-24

Protocol ID: `negative-control-diagnostic-v1`

This post-confirmatory study diagnoses the pre-registered Gate 2
`NEGATIVE_CONTROL_FAILED` result. It cannot modify the Gate 1 predictions, Gate 2
protocol, confirmatory artifacts, observed thresholds, Gate 2 `FAIL`, or Gate 3
ineligibility. A successful diagnosis is not a successful Gate 2 result.

## Immutable source context

- Gate 2 verdict: `FAIL`.
- Gate 3 eligibility: `NO`.
- Gate 2 seeds: integers `21000` through `21063`.
- Gate 2 horizon: `1200`; burn-in: `600`; final window: `300`.
- Gate 2 noise standard deviation: `0.00002` independently per state component
  and transition in both layers.
- Gate 2 symmetry tolerance at the failed controls: `0.02`.
- Layer R model: `layer-r-v1` from the digest-verified main preregistration.
- Layer M model: `layer-m-v1` from the digest-verified main preregistration.
- Gate 1 report SHA-256:
  `4a86d0c0989c8512182665e49f34f6aa35a83a2fcc5841e3534fada37f6d7656`.
- Frozen threshold artifact SHA-256:
  `85c06e9186a069739b75be40015b2c53350bc589c16121151d2c71aca812a8bb`.
- Main preregistration digest:
  `e90ae55058610a28a16d06e26f120d7509e0d3ec2b804e6c08bea02fc09a929a`.

All diagnostic artifacts are exclusively created below
`diagnostic/negative_control/` under the configured `ROUTEMIND_DATA_ROOT`.
Confirmatory paths are read-only. Existing diagnostic output is an error; it is
never overwritten.

## Competing hypotheses

- `H1 GENUINE_INSTABILITY`: alpha-zero dynamics are unstable, so dispersion or
  mean magnitude grows with horizon.
- `H2 STABLE_STOCHASTIC_EQUILIBRIUM`: deterministic dynamics are stable and
  persistent zero-mean noise produces a bounded stationary neighborhood whose
  finite-window slope signs fluctuate.
- `H3 FINITE_WINDOW_CLASSIFICATION_ARTIFACT`: the exact slope or final-third
  clause is materially sensitive to window length or placement while the state
  distribution remains stable.
- `H4 INSUFFICIENT_HORIZON`: the Gate 2 endpoint precedes settlement and longer
  horizons materially improve the same classifier.
- `H5 NUMERICAL_OR_IMPLEMENTATION_DEFECT`: deterministic references, hand checks,
  classifier decomposition, or seeded replay disagree with the implementation.
- `H6 NOISE_SPECIFICATION_MISMATCH`: innovations have material mean, variance,
  serial dependence, cross-correlation, clipping, or state dependence not
  represented by the intended independent Gaussian process.

These hypotheses are competing explanations. The root-cause rules below, rather
than narrative preference, determine the result.

## Fixed runs

### Replay and decomposition

The exact archived alpha-zero, zero-initial-condition Gate 2 records for all 64
seeds are decomposed without reclassification. Seeds `21000`, `21001`, `21002`,
`21003`, `21031`, and `21063` are re-run with the frozen model, horizon, noise,
and initial state. Their full trace digests must match the archived records.

For each archived record, retain these exact booleans independently:

1. `magnitude_pass`: `imbalance_mean <= epsilon_sym`.
2. `slope_pass`: the implemented OLS slope of Euclidean magnitude over the final
   300 states is `<= 0`.
3. `window_pass`: the mean magnitude in the final third of that window is `<=`
   the mean in its first third.
4. `finite_pass`: all classifier inputs are finite.
5. `all_pass`: the conjunction used by the frozen `RESTORED` classifier.

No clause, label, tolerance, or archived value is changed.

### New system trajectories

- Alpha: exactly `0`.
- Diagnostic seeds: integers `41000` through `41063`, all retained.
- Initial imbalances: zero, `(0.001, 0.001, 0.001)`, and
  `(-0.001, -0.001, -0.001)`.
- Horizons: `1200`, `2400`, `4800`, and `9600` transitions.
- Stochastic setting: the frozen layer-specific standard deviation `0.00002`.
- Noise-free setting: standard deviation `0`, seed `41000`, the three fixed
  initial imbalances, and horizon `1200`.

The longest trajectory is generated once for each layer/seed/initial condition;
shorter horizons are exact prefixes. This preserves paired paths and prevents
fresh-noise differences from masquerading as horizon effects.

### Fixed analysis windows

- Window-length sensitivity on horizon `1200`: final `150`, `300`, `600`, and
  `1200` states (`0.5x`, `1x`, `2x`, and `4x` the frozen window).
- Window-placement/burn-in sensitivity: non-overlapping 300-state windows
  beginning after transitions `0`, `300`, `600`, and `900` in the 1200-step run.
- Horizon comparison: the final 300 states at each fixed horizon.
- Stationary analysis: the final 4800 states of the 9600-step run, split into
  four contiguous blocks of 1200.

The original Gate 2 result is always reported from its original final 300-state
window. Sensitivity analyses are diagnostic labels only.

## Fixed estimators

The primary slope is the exact Gate 2 ordinary-least-squares slope of Euclidean
magnitude against integer time. On the original 300-state window it is compared
with, without selecting a winner:

- Theil-Sen median pairwise slope;
- mean first difference `(last - first) / (n - 1)`;
- block-averaged OLS slope using 10 consecutive blocks of 30 states.

The exact slope distribution reports mean, median, population standard deviation,
minimum, maximum, quantiles `0.025`, `0.25`, `0.50`, `0.75`, and `0.975`, and
fractions above, below, and equal to zero. Statistical distinguishability uses a
95% circular moving-block bootstrap interval with block length `30`, `1000`
resamples, and deterministic bootstrap seeds `43000 + layer_offset + run_index`,
where `layer_offset` is `0` for R and `10000` for M. A slope is distinguishable
from zero only if this interval excludes zero.

Final-window growth is `final_third_mean - preceding_third_mean`; its relative
difference divides by `max(preceding_third_mean, 1e-15)`. Materiality is reported
against both the across-time standard deviation in the same window and
`epsilon_sym`: a change is material only when its absolute value exceeds both
`0.5` time-series standard deviations and `0.10 * epsilon_sym`.

Autocorrelation uses the conventional lag-k centered sample correlation. Report
lags `1`, `5`, `10`, and `30` for state magnitude and projection, and lags `1`,
`5`, and `10` for component innovations. Segment comparisons report block means,
variances, coefficients of variation, and first-to-last ratios. No off-the-shelf
unit-root p-value is used because overlapping nonlinear magnitudes and paired
simulation paths violate its simple reference assumptions.

## Analytical and numerical references

For Layer R at alpha zero, compute all eigenvalues of the frozen matrix `A`, its
spectral radius, and the deterministic reference `x[t+1] = A x[t]`. With
`Q = (0.00002)^2 I`, solve the discrete Lyapunov equation by fixed-point iteration
from zero until the maximum element update is at most `1e-18`, or fail after
`100000` iterations. Compare predicted and observed covariance with Frobenius
relative error.

For Layer M, compute the central-difference Jacobian of its deterministic
alpha-zero observation transition at zero using step `1e-6`. Report its
eigenvalues and spectral radius. Use the same numerical Lyapunov procedure with
the empirically reconstructed one-step innovation covariance. The Layer M
covariance comparison is mechanistic support, not an exact linear identity.

Deterministic zero must remain within Euclidean norm `1e-14`. Each nonzero
noise-free perturbation must shrink to at most `1e-8` of its initial norm by step
1200. Hand-computed one-step Layer R and independently reconstructed one-step
Layer M references must agree with their implementations to maximum absolute
error `1e-12`.

Tiny-scale precision is evaluated against machine epsilon, the population clamps,
the noise standard deviation, and `epsilon_sym`. A numerical artifact requires a
deterministic discrepancy above the fixed tolerances or a result that changes
under an independently calculated algebraically equivalent reference by more
than `1e-12`; small magnitude alone is not evidence of an artifact.

## Noise audit

Innovations are reconstructed componentwise from the fixed alpha-zero transition
and its deterministic counterpart. For each layer and initial condition report
mean, variance, standard deviation, min/max, clipping count, lag autocorrelation,
cross-component correlation, and exact replay equality.

An intended Gaussian innovation audit passes when all of the following hold:

- absolute component mean is at most four estimated standard errors;
- component variance differs from `(0.00002)^2` by at most `20%`;
- absolute lag-one innovation correlation is at most `4 / sqrt(n)`;
- absolute cross-component correlation is at most `4 / sqrt(n)`;
- no Layer R clipping exists and no Layer M population clamp activates in the
  stationary alpha-zero runs;
- same-seed generation is bit-for-bit reproducible.

Normality is described with empirical quantiles and skewness but is not a Gate;
finite simulation samples cannot prove a distributional family.

Layer M residual contribution is reported separately for courier, merchant, and
demand updates as each component's share of total innovation variance. Stochastic
arrival and service-time mechanisms do not exist separately in `layer-m-v1` and
must be marked `NOT_MODELED`, not assigned fabricated contributions.

## Synthetic classifier controls

Synthetic seeds are integers `42000` through `42255`.

The stable reference is a three-dimensional independent AR(1):
`x[t+1] = 0.65 * x[t] + xi[t]`, with zero initial state and independent Gaussian
`xi` of standard deviation `0.00002`. Its ground truth is stable with spectral
radius `0.65`.

The locked reference is a sign-conditioned stationary process initialized at
`(+/-0.05, +/-0.05, +/-0.05)`:
`x[t+1] = 0.95 * x[t] + 0.0025 * sign(x[0]) + xi[t]`, componentwise, with
independent Gaussian `xi` of standard deviation `0.00002`. Its stationary
magnitude is above `epsilon_sym` and its sign is fixed. Positive and negative
initial signs alternate by seed parity.

Both controls use horizon `1200`, final window `300`, and the unchanged Gate 2
classifier. Report stable false-negative rate, locked sensitivity, specificity,
false-positive rate, and the complete label distribution. A usable classifier
control requires locked sensitivity at least `0.80`; otherwise diagnostic root
cause is `INCONCLUSIVE` unless an implementation defect explains the failure.

## Candidate stochastic-restoration criterion

This is evaluated only on the synthetic controls and new diagnostic alpha-zero
paths. It is not substituted into Gate 2 and is not a Gate 2b execution. A path is
a candidate stochastic restoration when:

- final-window mean magnitude is at most `epsilon_sym`;
- final-window magnitude variance is at most `epsilon_sym^2 / 4`;
- the absolute final-third minus preceding-third mean is at most
  `0.10 * epsilon_sym`, or its 95% moving-block bootstrap interval includes zero;
- every value is finite.

The absence of a required finite-window slope sign is motivated before diagnostic
execution by convergence in distribution under persistent additive noise. The
candidate is considered reference-valid only if stable-control sensitivity and
locked-control specificity are both at least `0.90` with Wilson lower bounds above
`0.80`. This only supports later protocol design.

## Root-cause decision rules

The diagnostic selects exactly one primary category. Rules are evaluated in this
fail-closed order; later rules cannot override an earlier one.

1. `REPLAY_FAILURE`: any frozen replay trace digest differs.
2. `MODEL_IMPLEMENTATION_BUG`: a deterministic model reference exceeds its fixed
   tolerance, excluding a classifier-only disagreement.
3. `CLASSIFIER_IMPLEMENTATION_BUG`: component conjunction or hand-constructed
   classifier cases disagree with the frozen classifier function.
4. `NUMERICAL_ARTIFACT`: the fixed numerical precision rule fails without a more
   specific model implementation defect.
5. `DYNAMICAL_INSTABILITY`: deterministic spectral radius is at least one, or
   both mean magnitude and variance have positive across-horizon bootstrap slopes
   excluding zero and their 8x/1x ratios exceed `1.5`.
6. `NOISE_MODEL_MISMATCH`: the fixed innovation audit fails in a way sufficient
   to explain a directional state drift.
7. `INSUFFICIENT_HORIZON`: the unchanged all-clause restoration rate increases by
   at least `0.30` to at least `0.80` at 8x, while mean magnitude falls by at least
   `50%` from 1x.
8. `BURN_IN_ARTIFACT`: the unchanged all-clause rate is below `0.50` in the first
   placement and at least `0.80` after the 900-transition burn-in, with a rate
   increase of at least `0.30`.
9. `STABLE_STOCHASTIC_EQUILIBRIUM_CLASSIFIER_MISMATCH`: all deterministic spectral
   radii are below one; deterministic perturbations decay; stochastic 8x/1x mean
   magnitude and variance ratios are each below `1.5`; the noise audit passes;
   at least `95%` of system paths pass magnitude while at most `50%` pass the full
   classifier; stable synthetic false-negative rate is at least `0.50`; and locked
   synthetic sensitivity is at least `0.80`.
10. `FINITE_WINDOW_ARTIFACT`: window or placement changes the all-clause rate by
    at least `0.25`, while maximum/minimum ensemble mean magnitude across those
    analyses is at most `1.25`.
11. `MULTIPLE_CAUSES`: two or more otherwise-primary supported causes remain
    material and no ordered rule adequately explains the observations alone.
12. `INCONCLUSIVE`: no earlier rule is fully met.

`FINITE_WINDOW_ARTIFACT`, `BURN_IN_ARTIFACT`, and other supported but non-primary
findings may be secondary causes. Layer R and Layer M are classified independently;
the overall primary category is their shared category, `MULTIPLE_CAUSES` when both
are clear but differ, or `INCONCLUSIVE` when either layer is inconclusive.

## Diagnostic verdict and future eligibility

- Diagnostic `PASS`: a reproducible primary cause other than
  `DYNAMICAL_INSTABILITY`, `MODEL_IMPLEMENTATION_BUG`, or `INCONCLUSIVE` is
  identified for both layers.
- Diagnostic `FAIL`: alpha zero is genuinely unstable or a model defect materially
  undermines the research mechanism.
- Diagnostic `INCONCLUSIVE`: a reliable root cause cannot be separated.

Gate 2b eligibility is at most `CONDITIONAL` in this study. It is `CONDITIONAL`
only when the diagnostic passes, synthetic controls validate the candidate at the
fixed Wilson thresholds, replay passes, and no model defect is found. Otherwise it
is `NO`. A future Gate 2b still requires a separately frozen criterion, untouched
new confirmatory seeds, and no reuse of these diagnostic outcomes for tuning.

Gate 3 eligibility remains `NO` under every diagnostic outcome. Gate 3, Lean,
threshold sweeps, dispatch-algorithm design, and scientific novelty claims are out
of scope.

## Outputs and fail-closed behavior

Bulk JSON is written with exclusive creation under:

- `classifier_decomposition/`
- `horizon_sensitivity/`
- `window_sensitivity/`
- `stationary_analysis/`
- `synthetic_controls/`
- `layer_r/`
- `layer_m/`

The repository receives only an immutable machine summary, SHA-256 sidecars, and
`NEGATIVE_CONTROL_DIAGNOSTIC_REPORT.md`. The runner must verify this document's
frozen digest, all Gate 1/Gate 2 hashes, artifact-class isolation, and absence of
pre-existing output before simulation. Missing, malformed, non-finite, partial,
hash-mismatched, or replay-mismatched evidence produces a registered reason code
and cannot be omitted from a denominator. No result is overwritten or rescued by
post-hoc parameter changes.
