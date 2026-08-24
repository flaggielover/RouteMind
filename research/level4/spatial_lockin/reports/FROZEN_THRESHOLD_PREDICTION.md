# Spatial Lock-In Gate: Frozen Threshold Prediction

Status: frozen before withheld long-horizon validation

Date: 2026-08-24

## Stage boundary

This report is generated from confirmatory short-horizon identification only.
The withheld validation seed range `21000-21063`, long-horizon trajectories,
equilibrium labels, and intervention outcomes were not read or executed before
this prediction was frozen.

The pre-registration digest is:

```text
e90ae55058610a28a16d06e26f120d7509e0d3ec2b804e6c08bea02fc09a929a
```

The implementation checkpoint observed at identification/freeze time was
`beb58835748e34b509eeff2793e1cac7760f202b`. The worktree disclosure retained in
the artifact contains only the pre-existing `.codex-tmp/` runtime outputs; no
research source changes were hidden.

## Confirmatory Gate 1

Both layers completed the fixed 12-transition design with perturbation magnitudes
`0.005, 0.010, 0.020, 0.040`, feedback settings `0.0, 0.35`, identification seeds
`11000-11063`, and `1000` trajectory-bootstrap resamples.

| Quantity | Layer R: reduced | Layer M: delivery mechanism |
| --- | ---: | ---: |
| Gate status | PASS | PASS |
| reason codes | none | none |
| predicted alpha_c | 2.60097908919399 | 3.29064597856242 |
| 95% alpha_c interval | [2.59684653524659, 2.60537444184453] | [3.28304848117258, 3.29797102241973] |
| kappa | 0.384470603456442 | 0.303891699840913 |
| local-linearity drift | 0.00420330856705767 | 0.00520022990400329 |
| normalized residual RMSE | 0.00681050070947221 | 0.00665866077600921 |
| Gram condition numbers | 1.63508675 / 1.52142803 | 1.41883718 / 1.28957160 |

Layer R recovery diagnostics were:

```text
A relative Frobenius error       0.000041865371635687
M relative Frobenius error       0.00169556507351621
threshold relative error         0.000210284286787183
true reduced-model threshold     2.60152614926484
```

These values support the engineering identification Gate only. They do not show
that the independent delivery mechanism has the same threshold as the reduced
model; the different Layer M estimate is retained as the required cross-model
test.

## Frozen artifact lineage

All paths below are relative to `ROUTEMIND_DATA_ROOT/research/level4/spatial_lockin/`.
Raw trajectories and JSON envelopes are external and are not copied into Git.

```text
confirmatory/identification/short-horizon-v1-trajectories.json
confirmatory/identification/short-horizon-v1-summary.json
confirmatory/threshold/frozen-prediction-v1.json
```

Frozen threshold envelope SHA-256:

```text
85c06e9186a069739b75be40015b2c53350bc589c16121151d2c71aca812a8bb
```

Frozen threshold content digest:

```text
0487bf67caf593e09877f2868919f91c791a551d48bd39fa395990fa4da31fdd
```

The freeze command was re-run intentionally. It failed closed with
`ARTIFACT_EXISTS`; the existing prediction was not overwritten. Read-back
verification returned `PASS` and matched the SHA-256 sidecar.

## Decision at this checkpoint

`GATE 1 = PASS` for the short-horizon estimator and synthetic recovery.

`GATE 2 = NOT RUN`.

`GATE 3 = NOT RUN`.

The scientific direction remains `CONDITIONAL GO` at most. No novelty or
long-run threshold claim is made until the frozen prediction is pushed and the
withheld validation stages are independently executed.
