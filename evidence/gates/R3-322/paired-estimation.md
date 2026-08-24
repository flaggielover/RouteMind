# R3-322 paired estimation and uncertainty evidence

Date: 2026-08-24 (Asia/Shanghai)

## Scope

R3-322 implements the paired estimator frozen by
`r3-320-statistical-routebench-v1`. It operates on synthetic unit-test samples
only in this task. It does not run the RouteBench pilot or confirmatory campaign,
inspect campaign outcomes, or support a strategy-effect claim.

## Statistical contract

- Every observation carries its validated R3-321 common-random-number plan. A
  sample must use one protocol, phase, and regime with unique pair replicates.
- The primary contrast is always candidate minus comparator. The report retains
  n, candidate/comparator arm means, every pair and four-stream seed/digest,
  paired mean, median, sample standard deviation, standard error, two-sided 95%
  Student-t interval, and paired Cohen's dz.
- Sensitivity reports the 10% Winsorized paired mean and every leave-one-pair-out
  mean plus its range and maximum absolute shift. Sensitivity cannot replace the
  primary arithmetic-mean analysis.
- Fewer than two complete pairs, duplicate/mixed identities, non-finite or
  boolean values, metric-bound violations, and zero paired variance fail
  explicitly. Zero variance is not silently converted into an infinite or zero
  effect size.
- Student-t CDF and quantile calculations use a convergent regularized incomplete
  beta implementation and are checked against independent published reference
  critical values. No normal approximation or untracked statistical dependency
  is substituted.

## Validation

- Five external-reference two-sided 95% Student-t critical values spanning 1,
  2, 5, 10, and 30 degrees of freedom pass within `5e-10`; computed CDFs return
  0.975 within `2e-13`, and lower-tail quantiles are symmetric.
- The standard differences `(1, 2, 3, 4, 5)` produce mean/median 3, sample
  standard deviation `sqrt(2.5)`, critical value `2.7764451051977908`, interval
  `[1.0367568385224448, 4.963243161477555]`, and report SHA-256
  `8cc4f549a880f1563b3b2dbe4a3a4e6867b6ece7c2f4166a469f6311fafe585c`.
- 29 directed tests pass. Isolated branch-aware module coverage is 95.71%; the
  protocol + CRN + estimator integration set passes 101/101.
- The full local gate passes Java 80/80, Python 594/594 at 95.76% total coverage,
  Web 92/92 plus production build, 6 schemas / 18 fixtures, determinism,
  analytics, semantic metrics, and repository controls.
- Initial validation rejected three critical-value checks because the negative
  tail retained an older `2e-12` relative tolerance while the positive tail used
  `5e-10` for truncated references. The implementation outputs differed by at
  most about `2.6e-10`; the test now independently checks the positive reference
  and exact numerical symmetry. No assertion or quality threshold was weakened
  to conceal an algorithmic discrepancy.
- R3-321 closure revision `d848593` passed all five GitHub Actions jobs in run
  `32714698835`.

Implementation revision `349a27e` passed all five GitHub Actions jobs in run
`32715625853`, including frozen Python/contracts and browser smoke.

Final disposition: `E-PASS / X-NOT-REQUIRED / S-NOT-APPLICABLE /
C-NOT-APPLICABLE`. No campaign data or effect claim exists.
