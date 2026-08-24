# RouteMind Level-4 Spatial Lock-In Gate

This isolated package tests whether short-horizon local responses predict a
withheld long-horizon spatial lock-in threshold and minimum stabilizing
intervention. It does not introduce a production dispatch algorithm or Lean.

The approved design is
`docs/superpowers/specs/2026-08-24-spatial-lockin-phenomenon-gate-design.md`.

## Stage boundary

The package exposes frozen historical commands and the isolated Gate 2b stages:

```powershell
python -m research.level4.spatial_lockin.run verify-preregistration
python -m research.level4.spatial_lockin.run identify-diagnostic
python -m research.level4.spatial_lockin.run identify-confirmatory
python -m research.level4.spatial_lockin.run freeze-threshold
python -m research.level4.spatial_lockin.run verify-frozen-threshold
python -m research.level4.spatial_lockin.run run-gate2
python -m research.level4.spatial_lockin.run run-negative-control-diagnostic
python -m research.level4.spatial_lockin.run verify-gate2b-preregistration
python -m research.level4.spatial_lockin.run run-gate2b-calibration
python -m research.level4.spatial_lockin.run run-gate2b-holdout
python -m research.level4.spatial_lockin.run run-gate2b-coarse
python -m research.level4.spatial_lockin.run run-gate2b-fine
python -m research.level4.spatial_lockin.run finalize-gate2b
```

Artifact-producing commands require `ROUTEMIND_DATA_ROOT`. Confirmatory and
diagnostic artifacts are rooted separately and use exclusive creation plus
SHA-256 sidecars. `freeze-threshold` reads only the confirmatory short-horizon
summary. `run-gate2` first verifies the immutable Gate 1 report and threshold
artifact, then executes only the pre-registered Gate 2 sweep. It never executes
Gate 3. `run-negative-control-diagnostic` verifies the separately frozen
post-confirmatory protocol and immutable Gate 2 evidence, writes only to the
diagnostic class, and cannot change Gate 2 or execute Gate 3.

Gate 2b uses a separate exclusive-create confirmatory namespace. Its holdout
command requires a frozen calibration PASS with the same implementation digest;
coarse confirmation requires both independent synthetic stages to pass. Fine
points are generated only by the frozen 16-subdivision rule. `finalize-gate2b`
replays the fixed seeds and freezes the scientific verdict without executing
Gate 3. A failed stage remains failed and cannot be overwritten or tuned.

## Independence boundary

`reduced_model.py` implements Layer R. `mechanism.py` implements Layer M with its
own region state, dispatch response, population updates, and operational metrics.
Layer M does not import Layer R or its nonlinearities. `identification.py` receives
only shared immutable trajectories and estimates the identifiable pair `(A, M)`
where `M = bc^T`; it never receives Layer M internals.

## Claim boundary

Synthetic passage can support at most `CONDITIONAL GO`. It cannot establish
scientific novelty or external validity.
