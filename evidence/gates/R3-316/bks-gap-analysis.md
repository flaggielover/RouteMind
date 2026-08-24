# R3-316 best-known-solution and optimality-gap evidence

## Frozen secondary analysis plan

- Manifest: `docs/research/r3/manifests/gap-analysis/bks-gap-analysis-v1.json`.
- Manifest SHA-256:
  `6c6332896dff30e878f77a161e576b88b42422cc2e2a617c1fa4f43f9ca6f77b`.
- Frozen: `2026-08-24T08:48:27Z` against revision
  `4f678fd79b91d8911aa265f779330e89c03725d1`, before the R3-316 analyzer was
  implemented or materially executed.
- Disclosure: all upstream outcomes already existed and had been inspected. This
  is a frozen secondary descriptive analysis plan, not a blinded or
  data-generation-time preregistration. RQ-A2 and its no-positive-threshold
  boundary were frozen earlier in `docs/research/r3/RESEARCH_CONTRACT.md`.

### Frozen inputs

- R3-311 Solomon summary: 6 selected/retained, SHA-256
  `5d420f2beee4ea936cff0016b2221ad3ba190e38822af75ab86e7b161d645421`.
- R3-312 Gehring-Homberger summary: 30 selected/retained, SHA-256
  `45ad7967cac4985d869663b6f5208e03c26e18995d33b6903535d8b627460daf`.
- R3-315 exact cross-check summary: 6 selected/retained, SHA-256
  `61f9207c4b9788aaf320ded2953420347b419bb54370bc470e00aaeae6939c3f`.
- The all-outcome ledger therefore has 42 records. The 36 source-double/BKS
  records and six derived conservative integer-optimum records are separate
  analysis universes and may not be pooled.

### Design decision

Three aggregation designs were considered:

1. A big-M or weighted scalar across vehicles and distance was rejected because
   the arbitrary scale can reverse or obscure hierarchical objective direction.
2. Categorical direction alone was rejected because it cannot satisfy the frozen
   median, p90, best, and worst acceptance criteria.
3. The selected stratified hierarchy reports vehicle-count gap on approved
   references, conditional distance gap only at equal vehicle count, and exact
   transformed gap only in the proven derived-model domain. Every timeout,
   no-incumbent result, questioned reference, and unfavorable result remains in
   the outcome ledger and its appropriate denominator.

Numeric gaps use `100 * (candidate - reference) / reference`; negative is better,
zero equal, and positive worse. Best is the minimum and worst the maximum. Median
and p90 use Hyndman-Fan Type 7 interpolation. `REFERENCE_QUALITY_REVIEW` and
`REFERENCE_GAP_NOT_APPLICABLE` records remain visible but cannot enter numeric
gap distributions. Missing values are never converted to zero or infinity.

### Frozen gates

- `E-PASS` requires directed tests, full local gates, and green remote
  implementation CI.
- `X-PASS` requires immutable execution against all three frozen input digests.
- `S-PASS` requires all 42 records accounted, exact denominator/statistic
  reproduction, explicit omission reasons, and passing domain/reference guards;
  it is descriptive correctness rather than inferential support.
- `C-NO-CLAIM` is required: no optimality, superiority, external-validity,
  unrestricted-capability, or population-trend wording is authorized.

Material analysis is prohibited until this manifest is committed and remote CI
is green, and then until the implementation checkpoint also passes remote CI.
Current gates: `E-IN-PROGRESS / X-IN-PROGRESS / S-IN-PROGRESS / C-DEFERRED`.

The direct manifest run `32708520338` was cancelled by workflow concurrency when
the subsequent spatial-lock-in checkpoint was pushed. Descendant revision
`d86c41e`, which contains the unchanged R3-316 manifest commit `9e0e1ee`, passed
all five GitHub Actions jobs in run `32708578105`; this is the accepted remote
manifest gate.

## Implementation checkpoint

- Added
  `services/compute-api/src/routemind_compute/application/benchmark_gap_analysis.py`.
  It validates the frozen protocol, repository-relative input paths and SHA-256
  identities, upstream schema/task/manifest/count contracts, unique run identities,
  outcome totals, hierarchical reference direction, and every omission reason.
- The analyzer builds a 42-record all-outcome ledger and separate source-BKS and
  derived-exact summaries. It reports complete R3-317 outcome/rate vectors,
  reference-status counts, and Type-7 `n/minimum/median/p90/maximum` distributions
  without zero/infinity imputation or cross-domain pooling.
- R3-315 transformed gaps are not trusted from the compact summary alone. All six
  external exact artifacts are resolved below `ROUTEMIND_DATA_ROOT`, checked
  against both summary SHA/byte lineage and sidecars, then used to independently
  recompute candidate-versus-exact transformed gaps and proof/verification guards.
- Output is an immutable `gap-analysis.json` plus SHA-256 sidecar beneath a
  distinct R3-316 campaign directory. It binds manifest, campaign, revision,
  implementation CI run, three input digests, environment, ledger, audits,
  descriptive results, and claim disposition.
- Sixty-two directed synthetic tests cover manifest drift, digest/path escapes,
  source and exact semantic mutations, outcome/accounting failures, Type-7
  direction, external artifact corruption, immutable output, and CLI behavior.
  They do not materially execute the frozen real inputs.
- Full local validation passed repository controls, Java `80/80`, Python
  `493/493` at `95.70%` total coverage, the new module at 99%, Web `92/92` plus
  production build, 6 schemas / 18 contract fixtures, determinism, analytics,
  and semantic-metric gates.

Implementation revision `9f68e9902a9b81e3830c189ba16b847badebae65`
passed all five GitHub Actions jobs in run `32710816931`. Only then was the
frozen material analysis executed.

## Material result and independent audit

- Campaign: `r3-316-20260824T092121Z-9f68e9902a9b`.
- External artifact:
  `experiments/r3/R3-316/r3-316-20260824T092121Z-9f68e9902a9b/gap-analysis.json`
  under `ROUTEMIND_DATA_ROOT`, 29,943 bytes, SHA-256
  `6e5571fcba1fd7069e4eb6604fff3f70533495fe1970fb2b5c0df257514eefb1`.
- The sidecar, three frozen input digests, and all six R3-315 external artifact
  digests/sidecars matched. The independent audit found 42 unique ledger records,
  split 36 source-double/BKS and six derived exact, with zero exclusions,
  duplicates, or errors.
- Source outcomes were `TIMEOUT_WITH_FEASIBLE=32`, `TIMEOUT_NO_FEASIBLE=3`,
  and `FEASIBLE_INCUMBENT=1`. Thus 35/36 timed out and 33/36 yielded accepted,
  independently verified complete incumbents. No source result was optimal,
  infeasible-proven, resource-limited, or failed.
- Reference classifications were four same-vehicle, 23 vehicle-worse, six
  reference-quality-review, and three not-applicable. All remained in the
  denominator and ledger even when a numeric gap was prohibited.
- Approved vehicle gaps: `n=27`, min `0%`, median `31.666666666666668%`, Type-7
  p90 `349.4545454545455%`, max `484.2105263157895%`. Conditional same-vehicle
  distance gaps: `n=4`, min `0%`, median `2.674529092839976%`, p90
  `8.818457913719254%`, max `10.305343511450381%`.
- The six derived conservative integer cases were independently proven optimal
  and verified; their separate transformed exact-gap distribution was `n=6`
  with min/median/p90/max all `0%`.
- An independent PowerShell recomputation matched ledger identities, source
  vehicle-gap formulas, complete outcome/reference counts, and all three Type-7
  distributions. Compact committed result:
  `docs/research/r3/results/gap-analysis/bks-gap-analysis-results-v1.json`.

## Gate disposition

- Engineering: `E-PASS`.
- Experiment: `X-PASS`.
- Statistical: `S-PASS` for the frozen deterministic descriptive analysis only.
- Claim: `C-NO-CLAIM`.

R3-316 supports only the frozen descriptive wording. It does not establish
source-instance optimality, RouteMind superiority, one pooled scalar gap, or
population behavior. R3-320 is activated.
