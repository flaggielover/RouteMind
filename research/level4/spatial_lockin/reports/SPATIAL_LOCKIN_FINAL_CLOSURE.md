# Spatial Lock-In Threshold Prediction: Final Closure

Date: 2026-08-24
Research line: `RouteMind Level-4 Direction 3`
Status: **CLOSED / NO-GO**

## Decision

The Spatial Lock-In Threshold Prediction line is formally closed after the
pre-registered Gate 2b campaign. The experiment is a valid scientific failure,
not an infrastructure abort and not a reason to tune the classifier or rescue
the hypothesis.

The most that the evidence supports is:

> Short-horizon local-response identification accurately localized the center
> of a long-horizon stochastic regime-transition region, but confirmatory
> validation did not support the preregistered sharp-threshold hypothesis. The
> observed transition remained materially broad, so the Spatial Lock-In
> Threshold Prediction research line is closed as NO-GO.

This is a lineage result, not a novelty claim.

## Supported

Gate 2b calibration and independent holdout both passed without post-holdout
classifier changes. In both the reduced model (Layer R) and the independent
two-region delivery mechanism (Layer M), the frozen coarse sweep showed:

```text
0.95x predicted alpha_c -> ROBUST_RESTORED
1.00x predicted alpha_c -> TRANSITIONAL
1.05x predicted alpha_c -> ROBUST_LOCKED
```

The observed midpoint equaled the frozen Gate 1 prediction in both layers, so
the center error was `0%`. Weak and strong controls, path dependence,
bootstrap validity, replay, operational correspondence, and artifact integrity
passed. The Gate 1 interval/bracket intersection was reported only as the
approved supplementary diagnostic.

## Not Supported

The data do not support a sharp critical threshold `alpha_c` with the frozen
narrow transition width. Both layers had an approximately `10%` observed
transition width, exceeding the primary `<=2.5%` PASS bound and the `<=5%`
PARTIAL upper bound. The preregistered fine-stage eligibility condition also
failed because the transitional point lay between the restored and locked
coarse points; fine refinement correctly returned `GATE2B_NO_TRANSITION`.

The following claims are explicitly prohibited:

- sharp bifurcation threshold;
- precise spatial lock-in critical point;
- theorem-supported `alpha_c`;
- minimum stabilization intervention derived from `alpha_c`;
- Gate 3 result or eligibility;
- Lean theorem or Lean evidence;
- new scientific phenomenon or Level-4 contribution from this line.

## Frozen History

| Stage | Immutable result |
| --- | --- |
| Gate 1 | `PASS`; Layer R `2.60097908919399`, Layer M `3.29064597856242` |
| Gate 2 | `FAIL_UNCHANGED` |
| Independent negative-control diagnostic | `PASS`; root cause `STABLE_STOCHASTIC_EQUILIBRIUM_CLASSIFIER_MISMATCH` |
| Gate 2b calibration | `PASS` |
| Gate 2b holdout | `PASS` |
| Gate 2b final | `FAIL`; reason codes `GATE2B_TRANSITION_TOO_WIDE`, `GATE2B_NO_TRANSITION`, `GATE2B_LAYER_R_FAILED`, `GATE2B_LAYER_M_FAILED` |
| Gate 3 | Not executed; eligibility `NO` |
| Lean | Not eligible; no artifacts produced |

## Integrity Audit

The following checks were completed before closure:

- all nine tracked historical reports with sidecars matched their SHA-256
  values;
- Gate 2 and Gate 2b machine summaries still report `FAIL` and Gate 3 `NO`;
- no Gate 3 or `.lean` artifact exists in the research tree;
- diagnostic reports remain in the diagnostic namespace and are not included
  in the Gate 2b confirmatory artifact root;
- all eight Gate 2b external JSON artifacts matched their sidecars;
- the only external data root is connected through `ROUTEMIND_DATA_ROOT`;
- no bulk experiment artifact was added to Git.

Authoritative historical artifacts:

- [Frozen Gate 1 threshold prediction](FROZEN_THRESHOLD_PREDICTION.md)
- [Original Gate 2 validation](GATE2_LONG_HORIZON_VALIDATION.md)
- [Gate 2 machine summary](GATE2_VALIDATION_SUMMARY.json)
- [Negative-control diagnostic report](NEGATIVE_CONTROL_DIAGNOSTIC_REPORT.md)
- [Gate 2b preregistration](GATE2B_STOCHASTIC_EQUILIBRIUM_PREREGISTRATION.md)
- [Gate 2b validation](GATE2B_STOCHASTIC_EQUILIBRIUM_VALIDATION.md)
- [Gate 2b machine summary](GATE2B_VALIDATION_SUMMARY.json)

## Lineage and Next Use

The failed line remains useful as a negative constraint: local-response
identification can center a broad regime transition without identifying a
sharp threshold. That observation may inform future problem discovery, but it
must not be reused as evidence for a new candidate without an independent
definition, prior-art audit, and fresh falsification plan.

Round 2 therefore starts in a new namespace and does not reuse Spatial Lock-In
seeds, thresholds, classifier labels, or confirmatory conclusions as evidence.

