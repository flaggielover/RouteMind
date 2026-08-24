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
