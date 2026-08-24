# R3-312 Gehring-Homberger scale/timeout evidence

## Preregistration checkpoint

- Manifest: `docs/research/r3/manifests/gehring-homberger/scale-first-replicates-v1.json`.
- Manifest SHA-256:
  `6c35a47e03d53a71f32240953fe1a088412637b893cb6d5a25a924a7bef9a2d2`.
- Frozen: `2026-08-24T07:45:22Z`, before implementation-specific material
  execution, against revision `f9e9a494163a870b7e13f28b045e16d79be7a78a`.
- Selection: for each size 200/400/600/800/1000 and each C1/C2/R1/R2/RC1/RC2
  family, select replicate `_1`; 30 selected, no result-based substitution.
- Source: five official SINTEF archives, 60 members each, stored only below
  `ROUTEMIND_DATA_ROOT`; archive and selected-member digests are frozen.
- Bound: one isolated process per instance, sequential execution, five solver
  seconds and one thread each, at most 150 configured solver seconds, zero
  external cost.
- Output: every outcome uses R3-317 and every incumbent uses R3-314. Timeout,
  resource, infeasible, unverified, and unfavorable results cannot be excluded.
- Reference quality: SINTEF-questioned C1_4_1/C2_4_1/C2_6_1/C1_8_1 values and
  unexplained C1_10_1/C2_10_1 label markers are retained but scalar comparison is
  forbidden.
- Analysis: fixed-census descriptive support/degradation labels by scale;
  `S-NOT-APPLICABLE`, with no p-value, population trend, superiority, or
  optimality claim.

Material execution is prohibited until this manifest is committed and the
implementation checkpoint passes its required local and remote validation.
Current gates: `E-IN-PROGRESS / X-IN-PROGRESS / S-NOT-APPLICABLE / C-DEFERRED`.

## Implementation checkpoint

- Added `services/compute-api/src/routemind_compute/application/homberger_evaluation.py`.
  The runner validates the frozen five-scale census and source archive/member
  lineage, verifies the selected archive member before parsing, reuses the
  canonical VRPTW model, classifies every R3-317 outcome, independently applies
  the R3-314 verifier, and records source-double reference gaps only when the
  frozen quality flag permits them.
- Each instance is written as an immutable JSON artifact with a SHA-256 sidecar;
  the campaign summary binds schema, campaign, revision, manifest, and selected
  identity plus source/reference lineage for all 30 retained artifacts and
  reports descriptive scale labels. Memory errors and all unfavorable solver
  outcomes remain retained.
- Sixty directed tests cover protocol drift, source archive corruption,
  reference-quality withholding, resource outcomes, independent verification,
  immutable artifact binding, scale summaries, path safety, and CLI behavior.
- Full local validation passed repository controls, Java `80/80`, Python `431/431`
  at `95.50%` coverage, Web `92/92` plus production build, contracts, and all
  available gates. The Homberger module itself is at 100% statement/branch
  coverage.

No material Homberger instance has been executed. The implementation checkpoint
is ready for commit and remote CI observation; material execution remains gated
until that remote run is green.
