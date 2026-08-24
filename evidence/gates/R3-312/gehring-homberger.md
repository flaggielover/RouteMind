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

Implementation revision `eac087e3279000802ce6eae51c3264fd0d5c2f31` passed all
five GitHub Actions jobs in run `32706450863`, satisfying the remote gate before
material execution.

## Material execution and closure

- Campaign `r3-312-20260824T083216Z-eac087e32790` executed all 30 frozen
  identities sequentially in separate processes under the five-second,
  one-thread policy. All 30 were retained; no substitution or exclusion occurred.
- Outcomes were one `FEASIBLE_INCUMBENT`, 28 `TIMEOUT_WITH_FEASIBLE`, and one
  `TIMEOUT_NO_FEASIBLE`. All 29 incumbents passed independent complete-solution
  verification; no verification issue was observed.
- The 200-customer stratum was `DEGRADED_UNDER_FROZEN_POLICY` at 5/6 verified
  complete. The 400, 600, 800, and 1000 strata were each 6/6 and therefore
  `SUPPORTED_UNDER_FROZEN_POLICY`. These labels describe only the fixed policy
  and fixed first-replicate census.
- Incumbent quality was unfavorable. Every retained incumbent used more vehicles
  than its source reference, including the six references whose quality status
  separately prohibits scalar comparison. Mean vehicle excess by size was 1.2,
  12.833333, 25.333333, 39.666667, and 63.0; mean vehicle ratio was 1.148889,
  2.071675, 2.391974, 2.586111, and 3.002018. No same-vehicle scalar distance gap
  existed.
- External audit found 31 JSON artifacts and 31 SHA-256 sidecars, 62 files and
  4,383,423 bytes, with zero identity, digest, lineage, outcome, verification, or
  reference-guard errors. Campaign summary SHA-256 is
  `ef8b6355de608f0e4b664778b43982a715982151bff224b6cc08f9aa8dd579c8`;
  the canonical 31-JSON bundle SHA-256 is
  `ec1a70ed886f93ac7737ef3bbdc2e6824d0c1794ff0d44c2ba44067ea0cfd257`.
- The committed compact result is
  `docs/research/r3/results/gehring-homberger/scale-first-replicates-results-v1.json`
  with SHA-256
  `45ad7967cac4985d869663b6f5208e03c26e18995d33b6903535d8b627460daf`.

R3-312 closes `E-PASS / X-PASS / S-NOT-APPLICABLE / C-NO-CLAIM`. The evidence
does not authorize optimality, superiority, unrestricted solver-capability, or
population scale-trend claims. The apparent monotone descriptive vehicle-ratio
pattern is not a statistical trend result.
