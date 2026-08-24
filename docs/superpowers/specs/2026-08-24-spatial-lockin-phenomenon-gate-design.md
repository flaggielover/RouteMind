# RouteMind Spatial Lock-In Phenomenon Gate Design

Date: 2026-08-24

Status: approved design, implementation not started

## 1. Scientific objective

Test one narrow claim:

> Can a long-run dispatch-induced spatial lock-in threshold be predicted out of
> sample from independently measured short-horizon local responses, and can the
> same prediction determine the minimum stabilizing intervention?

The work does not claim novelty from positive feedback, contraction, fixed-point
theory, pitchfork bifurcation, bistability, or the selected nonlinearities. The
highest permitted conclusion from synthetic evidence is `CONDITIONAL GO`.
Scientific novelty remains unsupported until external or quasi-experimental data
provide independent evidence.

The experiment is successful when it produces an honest, reproducible decision,
including `FAIL`. No parameter, tolerance, seed, nonlinearity, classification
rule, or Gate criterion may be changed after confirmatory execution begins.

## 2. Repository and concurrency boundary

All implementation is isolated under:

```text
research/level4/spatial_lockin/
```

Compact designs, configuration, code, tests, frozen summaries, and reports are
tracked in Git. Raw trajectories, bootstrap samples, sweep output, and generated
datasets are written beneath the runtime value of:

```text
ROUTEMIND_DATA_ROOT/research/level4/spatial_lockin/
```

Application code must not contain a workstation-specific absolute data path. A
missing `ROUTEMIND_DATA_ROOT` is a hard error for artifact-producing commands.
Existing concurrent changes to control-plane, progress, handoff, roadmap, task
graph, or Enhancement files are not modified, stashed, reset, or included in
research commits.

## 3. Assumption and claim taxonomy

The reduced model is discrete-time with a fully observed three-dimensional state:

\[
x_t=(c_t,m_t,d_t)^\top,
\qquad
x_{t+1}=Ax_t+\alpha b f(c^\top x_t)+\xi_t.
\]

The components are normalized two-region imbalances in courier supply, merchant
effective capacity, and latent customer demand. The baseline assumes comparable
regions, stationary parameters within a run, \(\alpha\ge 0\), zero-mean bounded
or configured Gaussian disturbances, and a Schur-stable open-loop matrix \(A\).
Schur stability implies that \(I-A\) is invertible. The baseline feedback is
cooperative, but sign assumptions are checked rather than silently imposed.

Results are labeled as follows:

- `exact`: algebraic statements for the declared reduced model;
- `local`: conclusions obtained from the linearization around symmetry;
- `approximate`: finite-sample estimates or reduced-model correspondence;
- `empirical`: observed seeded simulation outcomes;
- `heuristic`: operational interpretations not established by a theorem.

No local estimate is described as a global theorem. No finite-horizon crossover is
described as a bifurcation unless the pre-registered multistability and path-
dependence tests also pass.

## 4. Structural identifiability

Near symmetry, \(f(z)=z+O(z^3)\), so the local transition is:

\[
x_{t+1}=J_\alpha x_t+\xi_t,
\qquad
J_\alpha=A+\alpha M,
\qquad
M=bc^\top.
\]

The factors \(b\) and \(c\) are not separately identifiable from local autonomous
responses because \(b\mapsto sb\) and \(c\mapsto c/s\) leave \(M\) unchanged.
The experiment therefore estimates the identifiable objects \(A\) and \(M\), not
the factors.

Controlled local experiments at \(\alpha=0\) estimate \(J_0=A\). Experiments at
the fixed probe value \(\alpha_p=0.35\) estimate \(J_{\alpha_p}\), giving:

\[
\hat M=(\hat J_{\alpha_p}-\hat A)/\alpha_p.
\]

The feedback reproduction coefficient can be computed without factorizing
\(M\):

\[
\hat\kappa=
\operatorname{tr}\left((I-\hat A)^{-1}\hat M\right),
\qquad
\hat\alpha_c=1/\hat\kappa.
\]

Every design matrix must have numerical rank three. The infinity-norm condition
number of each state Gram matrix must not exceed \(10^6\). Factorizations of
\(M\) may be reported diagnostically but cannot affect the threshold prediction.

## 5. Double-blind experimental layers

### 5.1 Layer R: reduced-model recovery

Layer R generates short responses from a known three-state reduced model. The
estimator receives observations, intervention labels, and seeds but not the true
parameters. It validates update correctness, reproducibility, identifiability,
uncertainty calculation, threshold freezing, and long-horizon classification.

Passing Layer R proves only that the pipeline can recover its own declared model.
It is necessary but not sufficient for a scientific Gate pass.

### 5.2 Layer M: independent two-region delivery mechanism

Layer M is implemented independently from the reduced transition. It evolves:

- courier counts and migration from realized earning/service opportunity;
- merchant effective capacity from utilization and preparation backlog;
- customer latent demand from realized wait and service reliability;
- regional orders, accepted/served demand, wait, SLA breach proxy, utilization,
  courier opportunity, and regional service inequality.

Dispatch feedback strength controls how strongly allocation favors the currently
better-served region. This is a controlled scalar mechanism, not a named or
production dispatch algorithm. The reduced estimator sees only normalized local
population states and configured interventions. It does not import Layer M's
update functions or parameters.

Layer M is the cross-model correspondence test. If its short response does not
support the reduced identification diagnostics, or its frozen prediction does not
anticipate withheld long-run behavior, the relevant Gate fails even if Layer R
passes.

## 6. Pre-registered identification design

Confirmatory short-horizon configuration is fixed as follows:

- identification horizon: 12 transitions;
- perturbation magnitudes: `0.005`, `0.010`, `0.020`, `0.040`;
- perturbation directions: positive and negative coordinate axes plus four fixed
  mixed-sign directions;
- feedback settings: `0.0` and `0.35`;
- identification seeds: integers `11000` through `11063`;
- bootstrap resamples: `1000`, resampling whole trajectories;
- bootstrap confidence level: `95%` percentile interval;
- short-horizon noise levels: fixed per layer in the pre-registration manifest;
- no long-horizon state, equilibrium label, or threshold observation is available
  to the estimator.

Local-linearity is rejected when estimates from adjacent perturbation magnitudes
show more than `10%` relative drift in \(\kappa\), excluding comparisons whose
denominator is numerically indistinguishable from zero.

Residual diagnostics fail when any of the following holds:

- normalized residual RMSE exceeds `0.20` of response standard deviation;
- absolute lag-one residual autocorrelation exceeds `0.25`;
- absolute residual mean exceeds `0.10` residual standard deviations;
- residual scale grows monotonically over all four perturbation magnitudes.

Gate 1 additionally requires:

- numerical rank three for both feedback settings;
- condition number at most \(10^6\);
- estimated open-loop spectral radius strictly below `0.98`;
- the entire bootstrap interval for \(\kappa\) is positive;
- relative width of the \(\kappa\) interval is at most `0.50`;
- finite threshold and finite uncertainty bounds;
- Layer R relative threshold error at most `0.05`;
- Layer R threshold confidence interval contains the true threshold;
- Layer R relative Frobenius error at most `0.05` for \(A\) and `0.10` for \(M\).

Any failure makes `GATE 1 = FAIL`. Later stages may run only as explicitly labeled
diagnostics and cannot restore the Gate.

## 7. Freeze protocol and anti-circularity

Execution is separated into commands with one-way artifact dependencies:

1. `identify` consumes only pre-registered short-horizon data.
2. `freeze` writes an immutable threshold prediction and SHA-256 digest.
3. `validate-threshold` refuses to run without a matching frozen digest.
4. `freeze-intervention` derives and freezes \(\hat\lambda_c\).
5. `validate-intervention` refuses to run without both matching digests.
6. `report` consumes all artifacts without rewriting predictions.

Artifact creation uses exclusive-create semantics. An existing run identifier or
frozen prediction cannot be overwritten. The frozen threshold summary records the
implementation commit, dirty-worktree disclosure, model version, configuration
digest, estimator version, identification horizon, exact seed list, point estimate,
confidence interval, diagnostics, timestamp, and artifact digest.

The implementation and pre-registration are committed before identification.
The compact threshold prediction and external artifact digest are committed before
any withheld long-horizon execution. This intermediate checkpoint is pushed before
long-horizon validation so prediction timing is externally inspectable.

## 8. Pre-registered long-horizon validation

Validation uses independent seeds `21000` through `21063`, horizon `1200`, burn-in
`600`, and tail window `300`. For every parameter value, paired positive and
negative initial perturbations are run with matched seeds.

The alpha grid is derived mechanically from the frozen estimate and cannot use
observed outcomes. Coarse multipliers are:

```text
0.40 0.60 0.80 0.90 0.95 1.00 1.05 1.10 1.20 1.40 1.60
```

Fine multipliers are `0.90` through `1.10` in increments of `0.025`. Duplicate
points are removed before execution.

For each run, the signed service-advantage tail is classified using all of:

- `RESTORED`: tail magnitude no greater than the greater of `0.02` and five times
  the estimated no-feedback noise floor, with non-positive median local growth;
- `LOCKED`: tail magnitude above the same floor, sign persistence at least `0.90`,
  and paired positive/negative perturbations converge to statistically separated
  opposite-sign tail means;
- `AMBIGUOUS`: neither definition passes;
- `NOISY_SWITCHING`: the magnitude criterion passes but sign persistence fails.

A parameter value is robustly restored or locked only if at least `80%` of paired
seed runs receive the corresponding classification and the bootstrap confidence
interval for that proportion excludes `0.50`.

The observed transition is the interval between the largest robustly restored
alpha and the smallest larger robustly locked alpha. There is no claimed sharp
transition if this ordered bracket does not exist.

Gate 2 passes only when:

- a sharp transition bracket exists;
- the frozen 95% prediction interval intersects the observed bracket;
- midpoint normalized error is at most `0.10`;
- paired initial signs establish path dependence above the transition;
- negative controls restore symmetry.

The prediction is not revised if this Gate fails.

## 9. Pre-registered nonlinearity, ablation, and robustness family

The nonlinear response family is fixed before execution:

- unit-slope `tanh`;
- centered, unit-slope logistic response;
- unit-slope clipped-linear response with fixed saturation;
- unit-slope scaled `atan` response.

The fixed robustness axes are:

- disturbance standard deviation: `0.0`, baseline, and twice baseline;
- region baseline offset: `0.0` and `0.03`;
- customer response delay: `0`, `1`, and `3` transitions;
- primary coupling matrix plus two pre-registered stable coupling variants.

The confirmatory robustness set is the explicit Cartesian subset stored in the
manifest, not an open-ended search. Robustness passes when at least `75%` of its
pre-registered nontrivial cases have an ordered transition bracket and normalized
prediction error at most `0.15`. The report lists every failed case.

Feedback-chain ablations include courier only, merchant only, customer only, each
pair, all three, and all disabled. Each ablation re-runs short identification and
long validation; contributions to \(\kappa\) are reported as additive, synergistic,
antagonistic, or dominated without assuming additivity.

Negative controls are fixed as \(\alpha=0\), all feedback disabled, and the largest
coarse alpha strictly below the lower frozen confidence bound. Each must restore
symmetry or the simulator/claim Gate fails.

## 10. Minimal stabilization intervention

Intervention strength \(\lambda\in[0,1]\) acts only by reducing feedback gain:

\[
\alpha_{\mathrm{eff}}=\alpha(1-\lambda).
\]

For a stress test at \(\alpha_s=1.25\hat\alpha_c\), the frozen prediction is:

\[
\hat\lambda_c=\max(0,1-\hat\alpha_c/\alpha_s).
\]

The intervention grid is generated from fixed multipliers:

```text
0.00, 0.50, 0.80, 0.95, 1.00, 1.05, 1.20, 1.50
```

applied to \(\hat\lambda_c\), clipped to `[0,1]`, with duplicates removed. The
observed stabilization interval is defined analogously to the alpha transition.

Gate 3 passes only when:

- the prediction interval intersects the observed stabilization interval;
- midpoint absolute error is at most `0.05`;
- values below the bracket remain locked and values above restore symmetry;
- served-demand rate falls by no more than `10%` from the unstabilized stress run;
- mean wait increases by no more than `20%`;
- the intervention does not disable all allocation or population response.

The operational interpretation is a bounded fairness/service-floor damping of
regional concentration. No production algorithm is designed or named.

## 11. Implementation structure

```text
research/level4/spatial_lockin/
├── README.md
├── model.py
├── mechanism.py
├── identification.py
├── gates.py
├── artifacts.py
├── run.py
├── configs/
│   └── preregistration.json
├── tests/
│   ├── test_model.py
│   ├── test_identification.py
│   ├── test_mechanism.py
│   ├── test_artifacts.py
│   └── test_gates.py
└── reports/
    ├── FROZEN_THRESHOLD_PREDICTION.md
    └── SPATIAL_LOCKIN_PHENOMENON_GATE_REPORT.md
```

The package uses Python's standard library unless a dependency is proven necessary.
This avoids changing the shared Compute API dependency lock during concurrent work.
Small fixed-dimension linear algebra is explicit and tested. The experiment runner
is not exposed through production APIs.

## 12. Error handling and reproducibility

Invalid dimensions, non-finite values, unstable open-loop dynamics, unsafe paths,
rank deficiency, excessive conditioning, unknown nonlinearity, duplicate seeds,
digest mismatch, stage-order violation, and artifact overwrite attempts fail
closed with stable reason codes.

Each run records code commit, worktree disclosure, model/estimator version,
configuration digest, exact seed, timestamp, Python/platform metadata, experiment
ID, and parent artifact digests. Repeating a deterministic configuration and seed
must reproduce state/output digests. Stochastic differences are summarized across
the complete pre-registered seed set.

## 13. Test and evidence strategy

Unit tests cover model updates, fixed-seed replay, matrix inversion and spectral
checks, threshold computation, blind synthetic recovery, bootstrap determinism,
classification, intervention transformation, invalid inputs, external-root path
safety, exclusive artifact creation, and digest mismatch rejection.

Focused tests run before any experiment. The research package then runs a reduced
smoke campaign, followed by the complete pre-registered campaign. Existing
repository verification is run without altering concurrent control-plane files.

Compact Git evidence includes commands, commit identifiers, worktree disclosure,
artifact relative paths and SHA-256 digests, Gate results, negative results, and
explicit claim limits. Raw output remains external.

## 14. Verdict rules

`PASS` requires Layer R recovery, Layer M identification, Gate 2 threshold
prediction, robustness, interpretable ablations, and Gate 3 intervention prediction
to pass exactly as pre-registered.

`PARTIAL` is allowed only when the pipeline is technically valid but one or more
scientific correspondence Gates fail. It cannot be reported as evidence for the
central claim.

`FAIL` is mandatory for structural non-identifiability of the composite feedback,
unstable/ill-conditioned estimation, failed synthetic recovery, absent transition,
failed withheld prediction, modest-perturbation collapse, single-nonlinearity
dependence, failed intervention prediction, or trivial non-dispatch-specific
positive feedback.

`INCONCLUSIVE` is reserved for external execution loss or irrecoverable artifact
unavailability, not unfavorable data.

The final Level-4 direction decision is at most `CONDITIONAL GO`. Lean remains
ineligible unless the Phenomenon, Threshold Prediction, and Minimal Intervention
Gates pass, a human-readable theorem is identified, and its proof stabilizes.

## 15. Checkpoint order

1. Commit this approved design.
2. Implement and test code plus the immutable pre-registration manifest; commit.
3. Run short-horizon identification only.
4. Freeze, verify, commit, and push the numeric threshold prediction and digest.
5. Run withheld long-horizon validation, ablations, robustness, and intervention.
6. Produce Gate evidence, negative results, closure report, and decision report.
7. Commit and push the final checkpoint, then observe real CI without claiming a
   pass until the remote jobs complete.

