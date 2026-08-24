# RouteMind Level-4 Spatial Lock-In: Gate 2

## Executive Verdict

```text
FAIL
```

The frozen short-horizon predictions were tested without recalibration against
withheld long-horizon simulations. Both layers exhibited a sharp, seed-robust,
sign-dependent transition close to the frozen prediction. However, the
pre-registered `alpha=0` negative control failed the exact restored-state
classification in both layers (`64/64 UNCLASSIFIED`), so the Gate is FAIL by the
frozen protocol. This is not converted to PASS because the transition looked good.

## Frozen Prediction Verification

- Frozen report SHA-256: `4a86d0c0989c8512182665e49f34f6aa35a83a2fcc5841e3534fada37f6d7656`.
- Frozen threshold envelope SHA-256:
  `85c06e9186a069739b75be40015b2c53350bc589c16121151d2c71aca812a8bb`.
- Layer R frozen prediction: `2.60097908919399`, interval
  `[2.59684653524659, 2.60537444184453]`.
- Layer M frozen prediction: `3.29064597856242`, interval
  `[3.28304848117258, 3.29797102241973]`.
- No long-horizon data was used to change these values.

The first preflight was correctly stopped because a JSON float serialized as
`2.6009790891939866` differed from the report's rounded decimal by `3.4e-15`.
The checker was fixed to accept only a fixed `1e-12` serialization tolerance;
predictions and intervals were not changed. CI passed before the confirmatory run.

## Pre-Registered Transition Definition

Definition: [GATE2_TRANSITION_DEFINITION.md](F:/Projects/RouteMind/research/level4/spatial_lockin/reports/GATE2_TRANSITION_DEFINITION.md)

- Horizon `1200`, final-window size `300`, burn-in `600`.
- Seeds `21000-21063`, all retained.
- Five initial conditions: zero, positive, negative, positive-half, negative-half.
- Fixed coarse multipliers and mechanically triggered fine multipliers.
- Symmetry tolerance: `epsilon_sym = max(0.02, 5 * no-feedback noise floor)`.
- Robust regime threshold: `>=80%` of 64 paired seeds with a two-sided 95%
  Wilson interval excluding `0.50`.
- Observed threshold: midpoint of the largest robust restored point and the
  smallest larger robust locked point.
- Sharp transition: width / midpoint `<=0.15`.

## Layer R Results

- Confirmatory run records: `6,720` (`21` alpha sets × `64` seeds × `5`
  initial conditions).
- No-feedback noise floor: `3.82150594661097e-05`; `epsilon_sym = 0.02`.
- Observed bracket: `[2.60097908919399, 2.66600356642384]`.
- Observed threshold: `2.63349132780891`.
- Transition width: `0.0650244772298496` (`2.47%` of midpoint), therefore sharp.
- Absolute error: `0.0325122386149248`.
- Relative error: `0.0123456790123457`.
- Frozen interval intersects observed bracket: yes.
- Multistability/path dependence: yes; locked points had `64/64` paired paths and
  Wilson interval `[0.9433759402, 1.0]`.
- Negative control: FAIL. Zero-alpha zero-initial runs were `64/64
  UNCLASSIFIED`, despite mean imbalance approximately `3.816e-05`.
- Layer result: FAIL only because `NEGATIVE_CONTROL_FAILED`.

## Layer M Results

- Confirmatory run records: `6,720` (`21` alpha sets × `64` seeds × `5`
  initial conditions).
- No-feedback noise floor: `3.86269840038694e-05`; `epsilon_sym = 0.02`.
- Observed bracket: `[3.29064597856242, 3.37291212802648]`.
- Observed threshold: `3.33177905329445`.
- Transition width: `0.0822661494640604` (`2.47%` of midpoint), therefore sharp.
- Absolute error: `0.0411330747320302`.
- Relative error: `0.0123456790123457`.
- Frozen interval intersects observed bracket: yes.
- Multistability/path dependence: yes; locked points had `64/64` paired paths and
  Wilson interval `[0.9433759402, 1.0]`.
- Negative control: FAIL. Zero-alpha zero-initial runs were `64/64
  UNCLASSIFIED`, despite mean imbalance approximately `3.855e-05`.
- Layer result: FAIL only because `NEGATIVE_CONTROL_FAILED`.

## Operational Correspondence

Layer M operational metrics moved in the same direction as the latent regime:

- At the lower bracket point (`alpha=3.29064597856242`), service inequality was
  approximately `0.01714` and served demand `156.011`.
- At the upper bracket point (`alpha=3.37291212802648`), service inequality was
  approximately `0.23238` and served demand `156.665`.
- The recorded operational correspondence check passed. Waiting time remained
  approximately `10.0` in this mechanism, so no waiting-time degradation claim is
  made.

## Seed and Initial-Condition Robustness

The locked regime was not a one-seed artifact: every locked transition point had
`64/64` paired seed paths, and positive/negative initial conditions converged to
opposite signs. Half-size perturbations were included in every run. The zero
initial condition remained a required negative control and failed the exact
classification rule.

## Negative Evidence and Model Discrepancy

The decisive negative result is the failed negative control. The final-window
imbalance magnitude was far below `epsilon_sym`, but the exact restored classifier
also required a non-positive growth slope and a non-increasing final-third mean;
the noisy zero-alpha paths did not satisfy those additional conditions. This is
recorded as `NEGATIVE_CONTROL_FAILED`, not reinterpreted as symmetry restoration.

The observed transitions are close to the frozen thresholds, but this cannot
override the failed control. No model discrepancy label is assigned beyond
`UNKNOWN`: diagnosing the negative-control behavior would require a separate
post-confirmatory diagnostic campaign.

## Confirmatory Artifacts

All bulk outputs are external under:

```text
$ROUTEMIND_DATA_ROOT/research/level4/spatial_lockin/confirmatory/gate2_long_horizon/
```

Machine-readable summary:

```text
gate2_validation.json
SHA-256: c81c3d67d8834abab58344b022e39a9e2d7b3a6aa429f63404f9a214cb1953c5
content digest: 984aa25739fbb2a1a67fa7357cd878d501b94b4a28beeb91030939de94232773
```

Run artifact SHA-256 values:

```text
r-coarse.json  88ed2b1e34c035af4e8c9e1aebc38fa53502b7063d58028aa009ffc30648184d
r-fine.json    e3ad6bc960430c053137815bd13005dd08bc666e1027fc4add18e8c92393e322
m-coarse.json  fc776837bbef79d5cef77c31b0b30acfa14dbd30fabf741be50927cfd102b93
m-fine.json    883523656cf2bcedf2c9b4370c4e787d8c4e1bc3ff2384ee7a14d1915b3c8825
```

The artifact store uses exclusive creation and SHA-256 sidecars; confirmatory
results were not moved into diagnostic or exploratory storage.

## Threats to Validity

- Both layers are controlled simulators, not external or quasi-experimental data.
- The negative-control classifier is deliberately conjunctive and failed under the
  declared noise process; its rule cannot be changed after observing results.
- The observed transition is a finite-horizon bracket, not a theorem about a
  global bifurcation.
- The reduced and mechanism thresholds differ; Gate 2 correctly evaluates each
  layer against its own frozen prediction and does not erase that discrepancy.
- No intervention was run, and no causal or novelty claim is made.

## Scientific Interpretation

The central prediction transfer is numerically encouraging: short-horizon
identification anticipated both long-horizon brackets within roughly `1.23%`, with
sharp transitions and sign-separated attractors. Nevertheless, the complete
pre-registered Gate is **FAIL** because both negative controls failed. The valid
scientific statement is therefore not that the phenomenon was established, but
that the protocol found a promising transition alongside a reproducibility/control
failure that must be resolved in a new pre-registered campaign.

## Gate 3 Eligibility

```text
GATE 3 ELIGIBILITY = NO
```

Gate 3 was not executed. Lean remains out of scope. No scientific novelty claim is
permitted.

## Decision Table

| Item | Layer R | Layer M |
| --- | ---: | ---: |
| Frozen alpha_c | 2.60097908919399 | 3.29064597856242 |
| Observed alpha_c | 2.63349132780891 | 3.33177905329445 |
| Absolute error | 0.0325122386 | 0.0411330747 |
| Relative error | 0.0123456790 | 0.0123456790 |
| Transition width | 0.0650244772 | 0.0822661495 |
| Multistability | PASS | PASS |
| Seed robustness | PASS | PASS |
| Initial-condition robustness | PASS | PASS |
| Negative control | FAIL | FAIL |
| Operational correspondence | N/A | PASS |

```text
GATE 2: FAIL
```
