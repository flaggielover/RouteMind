# RouteMind Level-4 Spatial Lock-In Gate

This isolated package tests whether short-horizon local responses predict a
withheld long-horizon spatial lock-in threshold and minimum stabilizing
intervention. It does not introduce a production dispatch algorithm or Lean.

The approved design is
`docs/superpowers/specs/2026-08-24-spatial-lockin-phenomenon-gate-design.md`.

## Stage boundary

Only these Step 1-4 commands exist in the initial checkpoint:

```powershell
python -m research.level4.spatial_lockin.run verify-preregistration
python -m research.level4.spatial_lockin.run identify-diagnostic
python -m research.level4.spatial_lockin.run identify-confirmatory
python -m research.level4.spatial_lockin.run freeze-threshold
python -m research.level4.spatial_lockin.run verify-frozen-threshold
```

Artifact-producing commands require `ROUTEMIND_DATA_ROOT`. Confirmatory and
diagnostic artifacts are rooted separately and use exclusive creation plus
SHA-256 sidecars. `freeze-threshold` reads only the confirmatory short-horizon
summary. No withheld long-horizon command is present before the frozen threshold
checkpoint is pushed.

## Independence boundary

`reduced_model.py` implements Layer R. `mechanism.py` implements Layer M with its
own region state, dispatch response, population updates, and operational metrics.
Layer M does not import Layer R or its nonlinearities. `identification.py` receives
only shared immutable trajectories and estimates the identifiable pair `(A, M)`
where `M = bc^T`; it never receives Layer M internals.

## Claim boundary

Synthetic passage can support at most `CONDITIONAL GO`. It cannot establish
scientific novelty or external validity.
