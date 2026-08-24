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
