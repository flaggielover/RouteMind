# R3-323 prospective power analysis evidence

Date: 2026-08-24 (Asia/Shanghai)

Base revision: `e44bd5b798e6b0b40df112aab438630da64d2834` plus the R3-323
implementation worktree

## Scope and method

R3-323 implements prospective power accounting for the two frozen R3-B primary
metrics. It uses a one-sided noncentral paired Student-t calculation from pinned
SciPy 1.18.0. Familywise alpha 0.05 is divided by the 16 preregistered tests,
giving local alpha 0.003125: the most stringent first-step bound in the frozen
Holm family. Required counts are rounded upward to multiples of four and bounded
by 20-200 pairs per regime.

The input records protocol, regime, metric, complete pilot pair count, paired
variance, source kind, and source digest. Synthetic validation is explicitly not
an observed pilot. A future `r3_325_pilot` input must contain exactly eight pairs.
Risk plans use the distance from null 0 to MDE -0.02; assignment noninferiority
plans use the distance from margin -0.02 to planning alternative 0.

Counts above 200 retain the unconstrained required count and achieved power at
the cap, with disposition `UNDERPOWERED_AT_CAP`. The implementation never changes
MDE, alpha, target power, or the cap to obtain a favorable disposition, and
non-significance is not represented as equivalence.

`scipy==1.18.0` is an exact runtime dependency and
`scipy-stubs==1.18.0.1` is an exact development dependency. The lock file was
regenerated with repository-pinned uv 0.12.5. Runtime identity is checked before
a plan is emitted. Dependency and method references inspected on 2026-08-24:

- <https://pypi.org/project/scipy/>
- <https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.nct.html>
- <https://pypi.org/project/scipy-stubs/>

## Validation vectors

For paired variance `0.0016`, MDE distance `0.02`, standardized effect `0.5`,
local alpha `0.003125`, and target power `0.8`, exact noncentral-t search requires
55 pairs. Rounding gives 56 planned pairs and power `0.8104064287044574`; power
at the 200-pair cap is `0.9999902112916629`. Risk plan digest is
`1c33c22c56a0f82cece652db276099ffc040f5161cfc18831021041797d84b2e`;
assignment plan digest is
`89a75d94a906f9be297f7372b37a22f95a44e83120f9fe902f88f580546e567b`.

For paired variance `0.01`, effect `0.2`, the unconstrained and rounded required
count is 324. The retained 200-pair plan has power `0.5269065070498476`, is
explicitly `UNDERPOWERED_AT_CAP`, and has digest
`b20f228b688c21f378277f94eac5024a0b13cce69d6a5ddc7bb88711cb9946cb`.

The standard one-sided reference `effect=0.5, alpha=0.05` yields power
`0.7980537143957398` at 26 pairs and first reaches target 0.8 at 27 pairs.

## Executed gates

- `./scripts/compute-api.ps1 -Action lock` and `-Action sync`: PASS; 64 packages
  resolved and the exact SciPy/stub dependencies installed.
- Ruff and strict mypy over the compute source/tests: PASS; 113 source files
  type checked in the full gate.
- Protocol/power/estimation directed suite: PASS, 120/120.
- Isolated power-module branch gate: PASS, 41/41 with 100% statement/branch
  coverage (required threshold 95%). Failure paths include blank/drifted identity,
  invalid variance/probability/count/rounding, invalid numerical output, runtime
  version drift, and required count beyond the numerical planning range.
- `./scripts/full-gate.ps1`: PASS at 2026-08-24T18:34+08:00. Java 80/80;
  Python 635/635 at 95.83% total coverage; Web 34 files / 92 tests plus
  production build; 6 schemas / 18 fixtures; controls, dependency lock,
  determinism, analytics, and semantic metrics passed.
- `routebench-power` is registered `DETERMINISM_CRITICAL`; plan payloads are
  content-addressed.

Current disposition: `E-IN-PROGRESS / X-NOT-REQUIRED / S-NOT-APPLICABLE /
C-NOT-APPLICABLE`. Local gates pass; remote GitHub Actions validation is pending.
No observed pilot, confirmatory campaign, statistical effect, or strategy claim
was produced.
