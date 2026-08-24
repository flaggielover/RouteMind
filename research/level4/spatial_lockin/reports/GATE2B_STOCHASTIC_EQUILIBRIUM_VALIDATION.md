# RouteMind Spatial Lock-In Gate 2b Validation Report

Date: 2026-08-24
Protocol: `gate2b-stochastic-equilibrium-v1`
Status: **FAIL**
Gate 3 eligibility: **NO**

## Executive Verdict

The pre-registered stochastic-equilibrium Gate 2b was executed in the frozen
order with independent synthetic calibration, untouched holdout, two model
layers, deterministic coarse/fine rules, replay, bootstrap, and artifact
integrity checks. The confirmatory verdict is `FAIL`, not `PARTIAL` and not an
abort. The failure is scientific and fail-closed:

- The coarse grid has `ROBUST_RESTORED` at `0.95x`, `TRANSITIONAL` at `1.00x`,
  and `ROBUST_LOCKED` at `1.05x` in both layers. Therefore the pre-registered
  adjacent restored-to-locked pair does not exist and the fine stage correctly
  returned `GATE2B_NO_TRANSITION` without selecting a replacement interval.
- The combined observed brackets are the coarse endpoints around the
  transitional point. Their relative width is `10.0%` in both layers, above
  the primary `2.5%` Gate and the outer `5%` PARTIAL bound. The observed
  midpoints equal the frozen predictions, so prediction error is `0%`; width,
  not centering, is decisive.

The frozen Gate 1 identification interval intersects each observed bracket,
but this is recorded only as the approved supplementary correspondence
diagnostic. It cannot change the verdict. Original Gate 2 remains `FAIL`
unchanged. No Gate 3, Lean formalization, novelty claim, or external-validity
claim is authorized.

## Historical Gate Context

The immutable pre-Gate-2b state was `Gate 1 = PASS`, `Gate 2 = FAIL`, negative-
control diagnostic = `PASS`, and Gate 3 eligibility = `NO`. Gate 2b is a new
confirmatory study of whether the short-horizon prediction is compatible with
a long-run transition from a bounded symmetric stochastic equilibrium to
persistent sign-separated lock-in. It is not a reanalysis or rescue of Gate 2.

## Frozen Inputs and Lineage

The preregistration was frozen in commit `49e5689` and pushed; its real CI run
`32721829559` passed all five jobs. The implementation was frozen in commit
`a6e85f5` and pushed; its real CI run `32723911174` passed all five jobs.

| Item | Value |
| --- | --- |
| Preregistration JSON SHA-256 | `aac5da0419b77bf76e8740dc7cc7ed2cff232f1b3299e1395d2bace60697dd26` |
| Implementation digest | `4526621f6e01a480c097d26a089a850f9bcfd9617bcb4eebc26fd58547ad8861` |
| Protocol SHA recorded by validation | `aac5da0419b77bf76e8740dc7cc7ed2cff232f1b3299e1395d2bace60697dd26` |
| Confirmatory root | `F:\Projects\RouteMind-Data\research\level4\spatial_lockin\confirmatory\gate2b_stochastic_equilibrium` |
| Python / platform | `3.14.6` / Windows 11 build `10.0.26200` |
| Validation envelope content digest | `91a6a19c7e6f9139d6074a825c80f5d422520caae14bbdf2222dd2df78208701` |
| Validation envelope SHA-256 | `a8da384878467595d64f025eb8df5fac9ad1d840c1b1027dd8f223b084437643` |

All eight external JSON artifacts and all eight sidecars were checked after
finalization. Every JSON SHA matched its sidecar. Confirmatory and diagnostic
artifacts remain in disjoint roots; bulk traces are not committed.

## Classifier and Isolation

Layer R is the frozen reduced model. Layer M is an independently implemented
two-region delivery mechanism with courier, merchant, customer, acceptance,
waiting, service, utilization, and SLA state. Both use the fixed projection
`w=(1/3, 7/24, 3/8)`, horizon `4800`, burn-in through `2400`, terminal states
`3001..4800` (1800 samples), and six blocks of 300.

The classifier labels a run `STOCHASTIC_RESTORED` only under the frozen
centrality, covariance, drift, block-span, and material-sign occupancy bounds;
`LOCKED` requires separated projection mean, sign occupancy, low covariance and
drift, and consistent signs in all six blocks. All other finite runs are
`TRANSITIONAL`; non-finite or malformed runs are `INVALID`.

Calibration seeds `61000..61255` and holdout seeds `62000..62255` were disjoint
from model seeds and from each other. Calibration was frozen `PASS` before the
holdout command became executable. Holdout was then run once and frozen
untouched; no classifier threshold, seed, model, or decision rule was changed
after either phase.

### Synthetic Calibration

Calibration passed with 256 units per synthetic family. Invalid count was zero;
locked-pair sensitivity was `1.000` (Wilson 95% lower `0.985216`), stable
sensitivity was `1.000` (Wilson lower `0.985216`), locked-to-restored false
negative rate was `0`, stable-to-locked false positive rate was `0`, and the
near-critical transitional rate was `0.96875`.

### Synthetic Holdout

The independent holdout also passed with exactly the same qualification
metrics: invalid count `0`, locked-pair sensitivity `1.000` (Wilson lower
`0.985216`), stable sensitivity `1.000` (Wilson lower `0.985216`), both error
rates `0`, and near-critical transitional rate `0.96875`.

## Frozen Seed Schedule

Confirmatory model seeds were exactly `51000..51063` (64 seed units), with
paired positive/negative initial conditions using common random numbers. Coarse
multipliers were exactly `0, .40, .65, .80, .90, .95, 1.00, 1.05, 1.10,
1.20, 1.40, 1.60`. The fine stage was allowed only on the first adjacent
`ROBUST_RESTORED -> ROBUST_LOCKED` coarse pair. No such pair existed, so both
fine outputs contain zero multipliers and the reason code
`GATE2B_NO_TRANSITION`.

## Layer Results

| Layer | Frozen alpha | Last restored alpha | First locked alpha | Observed bracket | Midpoint | Relative error | Relative width | Interval diagnostic | Verdict |
| --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | --- | --- |
| R | 2.6009790892 | 2.4709301347 | 2.7310280437 | [2.4709301347, 2.7310280437] | 2.6009790892 | 0.000% | 10.000% | INTERSECTS (supplementary) | FAIL |
| M | 3.2906459786 | 3.1261136796 | 3.4551782785 | [3.1261136796, 3.4551782785] | 3.2906459786 | 0.000% | 10.000% | INTERSECTS (supplementary) | FAIL |

At `alpha=0`, both layers passed the negative control (`64/64` restored;
Wilson lower `0.943376`). Weak controls `.40x` and `.65x` were restored, and
strong controls `1.40x` and `1.60x` were locked. All 64 paired seeds had
opposite long-run signs at strong controls in both layers, so path dependence
passed. No reversal, invalid run, or non-finite trace occurred.

The transition midpoint estimator is `alpha_obs=(alpha_minus+alpha_plus)/2`.
The primary accuracy rules were `relative error <=1%` and `relative width
<=2.5%`; the first passed and the second failed in both layers. The outer
PARTIAL limits (`2%`, `5%`) also fail because the width is `10%`. The 1000-
replicate threshold bootstrap was fully valid in each layer (`valid_fraction
1.0`, invalid `0`), with degenerate midpoint intervals at the midpoint and
width intervals `[0.1*alpha_obs, 0.1*alpha_obs]`.

## Layer M Operational Correspondence

The operational Gate passed independently of the threshold-width failure.
Service-inequality upper-minus-lower contrast was positive with a paired
bootstrap interval strictly above zero. Served-demand projection sign agreed
for `64/64` pairs (Wilson interval `[0.943376, 1.000000]`). Five supporting
contrasts were positive (acceptance, waiting, courier density, merchant
utilization, and served demand), exceeding the required two. SLA disparity was
zero. Merchant preparation-time imbalance is honestly recorded as
`NOT_IDENTIFIABLE_NO_PROXY`: this mechanism has no preparation-time state and
no proxy was invented.

## Negative Evidence and Threats

The decisive negative evidence is that the frozen classifier resolves a
transitional regime at exactly the coarse point between restored and locked;
the pre-registered fine-stage eligibility condition therefore fails. Even when
the endpoint bracket is used for the required summary, its ten-percent width
is four times the primary tolerance. This means the data support a broad
transition near the prediction, not a sharply identified threshold.

The experiment is synthetic and uses only two model layers, a fixed scalar
projection, finite terminal windows, and the specified nonlinear families.
It does not establish field validity, universality across dispatch policies,
causal impact in production, or mathematical novelty. The paired design and
common random numbers reduce variance but do not remove finite-window or model-
misspecification risk. These limitations are reasons to retain `NO-GO`, not
reasons to relax the frozen Gate.

## Reason Codes and Decision

The final registered codes are:

`GATE2B_TRANSITION_TOO_WIDE`, `GATE2B_NO_TRANSITION`,
`GATE2B_LAYER_R_FAILED`, `GATE2B_LAYER_M_FAILED`.

Integrity, calibration, holdout, controls, path dependence, operational
correspondence, bootstrap validity, and replay all passed. The layer failures
are therefore scientific threshold failures, not an infrastructure abort.
Gate 3 was not executed and remains ineligible. The RouteMind research line
must remain **NO-GO**; no claim that a new spatial lock-in theorem or phenomenon
has been established is justified by this run.

## External Artifact Manifest

The following JSON SHA-256 values are the immutable external references. Each
has a matching `.sha256` sidecar.

| Artifact | SHA-256 |
| --- | --- |
| `controls/calibration/results.json` | `8681666af677fb958dd8de426bf6ce91a270e962f488c2c97db5bfac14480273` |
| `controls/holdout/results.json` | `ae91966355d062eb656e8e6ec5da7c7620974310ca2bc4b23979b693c85cb480` |
| `layer_r/coarse/results.json` | `4316eee82609ddd104bca1c2ff23477efb2f4393239565cf5e42b1b1fc398e21` |
| `layer_r/fine/results.json` | `f9b4f8aa6dd03329a3d76337dbf3c60f73693fd41dac5ea591e263b3e009d546` |
| `layer_m/coarse/results.json` | `a40c8573fbe43eaa1d7dc77ea098da65c11baf147a4e76a645942c485dd7c3d1` |
| `layer_m/fine/results.json` | `1b2e64cdbc9ab7d042b5d3defccee20f1f38e037d66f0467d1c761870bffb3de` |
| `replay/replay.json` | `fefa37151bf0d695fcddf402bcc1273e57a490c1aca5eb61fe3e6b16c120a1aa` |
| `reports/gate2b_validation.json` | `a8da384878467595d64f025eb8df5fac9ad1d840c1b1027dd8f223b084437643` |
