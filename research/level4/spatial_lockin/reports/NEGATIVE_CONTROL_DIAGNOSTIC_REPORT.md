# RouteMind Spatial Lock-In Negative-Control Diagnostic

## Executive Verdict

```text
Diagnostic verdict: PASS
Original Gate 2: FAIL (UNCHANGED)
Primary root cause: STABLE_STOCHASTIC_EQUILIBRIUM_CLASSIFIER_MISMATCH
GATE 2b ELIGIBILITY: CONDITIONAL
GATE 3 ELIGIBILITY: NO
```

`PASS` means that this post-confirmatory study identified a clear and reproducible
cause for the negative-control failure. It does not mean Gate 2 passed. No Gate 2
criterion, trajectory, threshold, hash, or verdict was changed.

## Immutable Gate 2 Context

Gate 1's frozen predictions remain `2.60097908919399` for Layer R and
`3.29064597856242` for Layer M. Gate 2's observed midpoints remain
`2.63349132780891` and `3.33177905329445`, respectively, with approximately
`1.23%` relative prediction error. Path dependence and operational correspondence
remain positive findings, while the overall Gate 2 verdict remains `FAIL` and
Gate 3 eligibility remains `NO`.

The diagnostic verified the frozen Gate 1, Gate 2, and preregistration hashes
before execution. Its preregistration SHA-256 is
`0db5478439e28aa979b5eb845d2ad65abc49e2add096c4f94797cbb9f5c9bfc9`.
The external diagnostic summary SHA-256 is
`a53abf8eb323c4088b10dc4c106fcee719ce64ffa410bb6111290db8d675e3c3`.

## Diagnostic Preregistration

The protocol was committed as `f85a855` and passed CI run `32705713198` before
diagnostic execution. The implementation checkpoint `465488f` passed CI run
`32707426263` before the one-time artifact-producing run. The run executed at
repository commit `4f678fd`, which contains `465488f` unchanged plus an unrelated
Homberger closure checkpoint.

The frozen campaign used alpha zero, diagnostic seeds `41000-41063`, initial
states zero and `+/-0.001`, horizons `1200/2400/4800/9600`, windows
`150/300/600/1200`, four 300-state placements, zero-noise controls, exact Gate 2
replay seeds, moving-block slope intervals, analytical stability, stationary
covariance, noise audits, and 256 stable plus 256 locked synthetic references.

## Classifier Decomposition

The 64 archived alpha-zero, zero-initial records per layer gave:

| Frozen clause | Layer R | Layer M |
| --- | ---: | ---: |
| Finite inputs | 64/64 | 64/64 |
| Mean imbalance at or below `epsilon_sym` | 64/64 | 64/64 |
| OLS slope non-positive | 30/64 | 30/64 |
| Final-third mean no greater than preceding-third mean | 30/64 | 31/64 |
| All RESTORED clauses | 28/64 | 28/64 |

The exact all-clause restoration rate is therefore `43.75%`, far below the frozen
`80%` robust-control requirement. Gate 2 necessarily remains failed.

There is a non-decisive historical artifact-label inconsistency. The coarse JSON
`records` retained their pre-aggregation default `UNCLASSIFIED` field, while the
Gate 2 aggregator applied `_classify` to copies in memory. This explains the
historical report's `64/64 UNCLASSIFIED` display. Recomputing the frozen clauses
from the archived numeric fields produces `28/64 RESTORED` in each layer. This is
a serialization/reporting issue, not a model or classifier-logic defect, and it
does not alter the Gate because `28/64` still fails the frozen rate threshold.

## Layer R Analysis

At alpha zero, Layer R has eigenvalues approximately
`0.482863 +/- 0.010415i` and `0.634274`; the spectral radius is `0.634274 < 1`.
The noise-free zero state stayed exactly zero, both small perturbations contracted
to numerical zero by step 1200, and the independent one-step reference had zero
maximum absolute error.

The archived mean imbalance was `3.81616e-05`, only `0.191%` of
`epsilon_sym=0.02`. The 8x/1x ratios were `0.99918` for mean imbalance and
`0.99262` for variance. Mean and variance horizon-slope bootstrap intervals both
included zero. These observations reject the preregistered instability and
insufficient-horizon explanations.

## Layer M Analysis

The independently reconstructed alpha-zero Layer M Jacobian has eigenvalues
approximately `0.480664`, `0.489937`, and `0.635296`; its spectral radius is
`0.635296 < 1`. The zero state stayed exactly zero. Positive and negative small
perturbations contracted by a factor of approximately `2.84e-13`; the independent
one-step reference differed by at most `9.02e-17`, below the `1e-12` tolerance.

The archived mean imbalance was `3.85496e-05`, or `0.193%` of the symmetry
tolerance. The 8x/1x mean and variance ratios were `0.99963` and `0.99413`.
There was no population clamp activation. Layer M therefore shows the same stable
stochastic mechanism as Layer R rather than a separate operational instability.

Layer M's reconstructed residual variance shares were `33.31%` courier,
`33.32%` merchant, and `33.37%` demand. This near-equality reflects the frozen
equal-variance component noise. Separate stochastic-arrival and service-time
noise mechanisms are not present in `layer-m-v1` and were not fabricated in the
decomposition.

## Slope Distribution

Layer R's slope mean was `2.49e-09`, median `1.46e-09`, and standard deviation
`1.59e-08`; `53.125%` were positive. Its 2.5%-97.5% empirical range was
`[-2.86e-08, 3.26e-08]`. Layer M's mean was `2.20e-09`, median `1.60e-09`, and
standard deviation `1.63e-08`; the positive fraction was also `53.125%`, with
2.5%-97.5% range `[-2.99e-08, 3.56e-08]`.

No individual slope in either layer was distinguishable from zero under the
pre-registered moving-block interval. OLS, Theil-Sen, mean first difference, and
block-averaged estimators all had means on the order of `1e-09`. The evidence is
consistent with slope signs fluctuating around zero, not systematic positive
drift.

## Window and Horizon Sensitivity

The new-seed all-clause rates did not converge toward the required `80%` at longer
horizons. From 1x to 8x they changed from `46.875%` to `42.1875%` in Layer R and
from `43.75%` to `40.625%` in Layer M, while every path continued to pass the
magnitude clause.

Across `150/300/600/1200` windows, Layer R all-clause rates ranged only
`40.625%-46.875%`; Layer M ranged `39.0625%-45.3125%`. Moving the 300-state window
from burn-in zero to 900 changed rates from `34.375%` to `43.75%` for Layer R and
from `35.9375%` to `43.75%` for Layer M. Neither the preregistered finite-window
nor burn-in-artifact threshold was reached.

The largest archived final-third growth difference was `6.81e-06` in Layer R and
`7.01e-06` in Layer M. No record met the pre-registered material-growth rule; all
were tiny relative to the `0.002` tolerance-scaled materiality threshold.

## Noise Diagnostics

Both noise audits passed. Each zero-initial layer supplied `307200` stationary
innovations. Component variances were approximately `4.01e-10`, within `0.42%`
of the intended `(2e-05)^2`. Component innovation means were between `7.12e-09`
and `2.94e-08`. Absolute lag-one innovation autocorrelations were below `0.0018`,
and absolute cross-component correlations were below `0.00262`, both below the
fixed `0.00722` bound.

State magnitude lag-one autocorrelation was approximately `0.302` in Layer R and
`0.320` in Layer M, while projection autocorrelation was `0.649` and `0.664`.
This is expected state persistence under a stable autoregressive process; it is
not innovation serial dependence.

## Analytical Stability and Stationary Covariance

The Layer R discrete Lyapunov solution converged in 23 iterations. Its predicted
stationary covariance matched the pooled observed covariance with `0.391%`
relative Frobenius error. The Layer M linearized Lyapunov calculation converged in
24 iterations and matched with `0.213%` relative error. These results strongly
support bounded stationary neighborhoods under persistent additive noise.

The approximately `3.8e-05` scale is more than `1e11` double-precision epsilon
units and is not near a floating-point floor. Zero-noise references, equivalent
one-step calculations, population clamps, and replay checks found no numerical
artifact.

## Synthetic False-Negative Rate

The unchanged classifier labeled `124/256` known-stable AR(1) paths RESTORED and
`132/256` AMBIGUOUS: a `51.5625%` stable-reference false-negative rate. Its 95%
Wilson interval is `[45.46%, 57.62%]`, which crosses 50%. This point estimate meets
the preregistered diagnostic threshold but is not independently decisive.

All `256/256` known locked references were labeled LOCKED. The preregistered
candidate stochastic criterion achieved `256/256` stable sensitivity and
`256/256` locked specificity, with both Wilson lower bounds `98.52%`. These are
deliberately simple synthetic references, so this validates only a possible new
criterion, not RouteMind's real-world scientific claim.

## Replay Verification

All six required frozen replay seeds matched their archived trace digests in both
layers. The stronger audit also matched all 64 alpha-zero traces per layer. The
classifier hand-reference cases and deterministic synthetic replay passed.

```text
Replay: PASS
Model implementation defect: NO
Classifier logic defect: NO
Non-decisive raw-label serialization inconsistency: YES
```

## Root Cause

| Candidate cause | Layer R | Layer M | Evidence | Verdict |
| --- | --- | --- | --- | --- |
| Genuine instability | No | No | Spectral radii near 0.63; bounded 8x moments | Rejected |
| Stable stochastic equilibrium | Yes | Yes | Lyapunov covariance and horizon stability | Supported |
| Slope criterion mismatch | Yes | Yes | 53.125% positive; 0/64 significant | Supported |
| Final-window artifact | No | No | Rate range below 0.25; no material growth | Rejected as primary |
| Horizon too short | No | No | 8x does not improve restoration rate | Rejected |
| Noise mismatch | No | No | Innovation mean/variance/ACF/correlation pass | Rejected |
| Model/classifier logic defect | No | No | References and self-checks pass | Rejected |
| Replay defect | No | No | Required and all-seed replay pass | Rejected |

Both layers satisfy the frozen decision rule for:

```text
STABLE_STOCHASTIC_EQUILIBRIUM_CLASSIFIER_MISMATCH
```

The original Gate 2 classifier appears poorly calibrated for a stochastic
equilibrium because it requires favorable signs from finite-window slope and
third-window differences even when the process has settled in distribution.
This finding does not imply that Gate 2 should have passed.

## Threats to Validity

- The models are synthetic and internally specified; there is no external or
  quasi-experimental delivery data.
- The stable synthetic classifier false-negative point estimate barely exceeds
  its 50% diagnostic threshold, and its interval includes 50%.
- The candidate criterion was tested on simple, well-separated stable and locked
  references. Perfect synthetic classification can overstate real discrimination.
- Layer M's equal residual shares are partly structural because equal independent
  Gaussian noise was injected into its three components.
- Local Jacobian and covariance agreement diagnose the alpha-zero neighborhood;
  they are not a global theorem or evidence for the threshold phenomenon itself.
- The archived raw-label serialization inconsistency limits reliance on the old
  per-record label text, although hashes and numeric summaries replay exactly.

## Gate 2b Recommendation

```text
GATE 2b ELIGIBILITY: CONDITIONAL
```

A separate Gate 2b is scientifically defensible only after freezing a new
stochastic-restoration criterion before seeing any new confirmatory outcomes. It
must use untouched seeds, retain bounded mean and variance, test statistically
meaningful drift rather than a required slope sign, validate covariance stability,
and preserve synthetic stable/locked calibration. These diagnostic seeds and
outcomes may not be used for Gate 2b tuning.

No Gate 2b was executed in this task.

## Gate 3 Status

```text
GATE 3 ELIGIBILITY: NO
```

Gate 3 remains prohibited until a separately preregistered Gate 2b passes. Lean,
algorithm design, threshold re-fitting, scientific novelty claims, and external
validity claims remain out of scope.

## Artifact Lineage

Bulk evidence is under
`$ROUTEMIND_DATA_ROOT/research/level4/spatial_lockin/diagnostic/negative_control/`.
Eight JSON artifacts and eight SHA-256 sidecars were checked with zero integrity
failures. The external bulk artifact hashes are recorded in the machine summary;
confirmatory artifacts were read-only throughout.

## Final Decision

```text
RouteMind Spatial Lock-In Negative-Control Diagnostic

Diagnostic verdict: PASS
Original Gate 2: FAIL (UNCHANGED)
Layer R root cause: STABLE_STOCHASTIC_EQUILIBRIUM_CLASSIFIER_MISMATCH
Layer M root cause: STABLE_STOCHASTIC_EQUILIBRIUM_CLASSIFIER_MISMATCH
alpha=0 analytical stability: rho_R=0.634274; rho_M=0.635296
Observed long-run imbalance: R=3.81616e-05; M=3.85496e-05
Original slope-condition rejection rate: R=53.125%; M=53.125%
Original window-condition rejection rate: R=53.125%; M=51.5625%
Synthetic stable classifier false-negative rate: 51.5625%
Implementation defect found: NO model/classifier logic defect
Replay: PASS
Primary root cause: STABLE_STOCHASTIC_EQUILIBRIUM_CLASSIFIER_MISMATCH
Scientific implication: bounded stochastic stationarity requires a distributional,
not deterministic finite-window-sign, restoration criterion
GATE 2b ELIGIBILITY: CONDITIONAL
GATE 3 ELIGIBILITY: NO
Next action: freeze an independent Gate 2b protocol with new seeds; do not run Gate 3
```
