# R3-356 Independent Round 3 Reproduction

Date: 2026-08-25 (Asia/Shanghai)
Status: closed with all four scoped results independently reproduced
Recovery implementation: `76468caf2f5f50806b86b3b5da5a444b3605856a`
GitHub Actions: PASS - run `32781478836` (all five jobs)

## Frozen retrospective boundary

Manifest:
`docs/research/r3/manifests/reproduction/r3-356-independent-reproduction-v1.json`

- Canonical digest:
  `aaab4e70a7daa04d6850c886edb80ac652d47f0fad89e89e75b550530f874d93`
- Byte SHA-256:
  `06463bdc496f8d2504db054ca67b37d017493b8a0659542de1872f91bf2daf50`
- The disclosure class is `RETROSPECTIVE_CLEAN_ROOM_REPRODUCTION`: upstream
  results existed and were inspected before the reproduction plan was frozen.
- The alternate checker uses only the Python standard library and imports none
  of the original benchmark, statistical, Twin, or RADS analysis modules.
- Raw external inputs, committed inputs, sidecars, and embedded content digests
  are checked before observations are recomputed. Missing inputs and identity
  drift fail closed.
- Contradictions are written to the result and produce a nonzero CLI exit. The
  checker does not tune expectations, substitute synthetic data, or rerun
  R3-325.

## Retained recovery history

Original implementation `f17fed261798fab98d6201d4e19d032af094070c`
passed all five jobs in Actions run `32779935291`. Material attempt 1 was
retained byte-for-byte at
`docs/research/r3/results/reproduction/r3-356-independent-reproduction-attempt-1.json`
with SHA-256
`09897e3db418cb5a41aa8343f009c50fd7bf7ee7b187cc58981b313b0427d307`.

Attempt 1 reproduced R3-316, R3-336, and R3-349 and retained one R3-327
contradiction. The observed and expected non-estimable assignment-regime sets
contained the same six identities; the checker had sorted observations
alphabetically but compared them to frozen protocol order. This was a checker
ordering defect, not a changed scientific outcome. Recovery projects the set
in frozen regime order and adds a deliberately non-alphabetic two-regime
fixture. No expected value or frozen input changed.

Recovery implementation `76468caf2f5f50806b86b3b5da5a444b3605856a`
passed all five jobs in Actions run `32781478836` before recovery material
execution.

## Independent result

Formal result:
`docs/research/r3/results/reproduction/r3-356-independent-reproduction-v1.json`

- Result digest:
  `9eea07d71c037199eca311e242308da1f517904f082099098dea409fd985c36e`
- Independently recomputed digest: exact match.
- Byte SHA-256:
  `feb374e75420ec6c9e100dde634c80f936c8bf10d19da182562c879154dc61e7`
- Overall status: `REPRODUCED_WITH_NO_CONTRADICTIONS`.
- Contradictions: zero.

The four scoped targets were independently recomputed as follows:

- R3-316: `REPRODUCED`. The checker accounted for all 42 unique ledger
  records, retained 36 source and six derived records, recomputed source
  outcome/reference-comparison counts, and matched all three preregistered
  Type-7 gap distributions. The descriptive disposition remains
  `S-PASS / C-NO-CLAIM`.
- R3-327: `REPRODUCED`. The checker matched the report content digest, all 16
  regime/metric cells, eight pairs and four CRN streams per cell, the six
  non-estimable assignment regimes, zero failures/fallbacks/timeouts, and
  absent confirmatory inference. The scientific outcome remains exactly
  `S-FAIL / C-NO-CLAIM`.
- R3-336: `REPRODUCED`. Zero observed, calibration, and held-out records
  independently imply `INSUFFICIENT_DATA`, unevaluated thresholds, unsupported
  regimes, unrun sensitivity analysis, and `C-NO-CLAIM`.
- R3-349: `REPRODUCED`. Seven source regime axes are present without RADS
  variant outcomes, location noise is unsupported, eight pairs are below the
  minimum of 30, and broad robustness claims remain prohibited under
  `C-NO-CLAIM`.

Independent reproduction is claim input, not a new effect estimate. It does
not promote R3-316's descriptive result, R3-327's statistical failure, the
Twin no-data result, or the RADS robustness insufficiency into a supported
scientific claim. R3-325 remains frozen exactly as
`E-PASS / X-PASS / S-FAIL / C-NO-CLAIM`.

## Executable evidence

- R3-356 directed tests: 12/12 passed, including standard-library import
  isolation, source/digest failure, contradiction retention, non-overwrite,
  CLI exit behavior, and non-alphabetic protocol-order regression.
- `./scripts/full-gate.ps1`: PASS in non-interactive CI-equivalent mode - Java
  81/81, Python 905/905 at 95.17% total coverage, Web 92/92 plus production
  build, Ruff, formatting, strict mypy, six schemas/18 fixtures, determinism,
  analytics, semantic metrics, repository controls, and bounded resilience.
- Actions run `32781478836`: all five jobs passed for recovery implementation
  SHA `76468caf2f5f50806b86b3b5da5a444b3605856a`.

## Final disposition

R3-356 closes `E-PASS / X-PASS / S-NOT-APPLICABLE / C-NO-CLAIM`.
The scoped results are reproducible through an alternate checker, the failed
attempt remains append-only evidence, and no upstream claim status was
strengthened.
