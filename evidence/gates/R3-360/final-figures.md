# R3-360 Final Scientific Figures and Tables

Date: 2026-08-25 (Asia/Shanghai)
Status: closed with manifest-linked descriptive artifacts
Implementation: `8753c7e7e1306a28b63bd5c4fc7e6a682dbdc60c`
GitHub Actions: PASS - run `32789597203` (all five jobs)

## Frozen lineage

Final plan:
`docs/research/r3/manifests/final-figures/r3-360-final-figures-v2.json`.

- Plan digest:
  `10e12aa0f586ad94e963396feb0a045fc1b21fe4ff0cd7537d0d769f145bb30d`
- Bundle digest:
  `2b230697ea367ace51afcd52c7544efd6cd024abca0104f10a35b50ebce34684`
- Source identities: the frozen R3-327 external report, R3-336 and R3-349
  manifests, R3-356 reproduction result, and final Claim Matrix are bound by
  exact byte SHA-256 and, where applicable, content digest.
- Repository output: `docs/research/r3/results/final-figures/`
- External final output:
  `ROUTEMIND_DATA_ROOT/research/r3/R3-360/r3-360-final-figures-v2/`

The external v1 bundle is an immutable pre-QA draft. Browser inspection found
a column overlap in its evidence-support figure. The final v2 bundle corrects
the layout without changing source data, row values, or scientific status.

## Artifact inventory and negative outcomes

The deterministic standard-library generator produced three SVG figures and
three CSV tables. The content-addressed index verifies every committed byte.

- RouteBench table: 16/16 cells retained; eight scenario-risk intervals, two
  assignment-rate intervals, and six assignment-rate cells explicitly marked
  `NON_ESTIMABLE_PAIRED_VARIANCE_OR_POWER`.
- Evidence-support table: 12/12 rows retained; Twin has zero observed records;
  RADS has no variant outcomes, eight pairs versus 30 required for present
  axes, and `location_noise` is unsupported.
- Claim table: 7/7 rows retained; zero `C-PASS`, two `C-NO-NOVELTY`, five
  `C-NO-CLAIM`, and zero deferred rows.
- Confirmatory inference: `NOT_EXECUTED`.
- Excluded rows: zero.

Axes, units, descriptive 95% intervals where estimable, uncertainty status,
requirements, exclusions, and negative/no-data outcomes are visible. The
figures do not create or strengthen a scientific claim.

## Validation

- Committed bundle validator: PASS, six artifacts and exact 16/12/7 row counts.
- Directed tests: 6/6 PASS, covering execution-policy freeze, no-data and
  unsupported-state retention, zero supported claims, SVG parsing, immutable
  external writes, and plan tamper rejection.
- Ruff and strict Mypy: PASS for the generator and tests.
- Browser-rendered QA: PASS at 1400x1320, 1400x930, and 1100x760.
- Screenshot SHA-256: RouteBench
  `2f950756a991f67b8e743f2f344bb9542d9953fd9b6c68606d7d5fd12f553e2b`,
  support `f849f8e2231cb4744539889e97b5a4baa78913b9778d21d411dddc889c9b6761`,
  claims `191c81d345303663d005566cc2848eb89880e5e6a1337ebb99e6bb28070f6d92`.
- GitHub Actions run `32789597203`: Control plane and Compose, Java, Python,
  bounded degradation/resilience, and Web static/unit/browser jobs all passed.

## Frozen boundary

No experiment ran. R3-325 remains exactly
`E-PASS / X-PASS / S-FAIL / C-NO-CLAIM`; it was not rerun, tuned,
reinterpreted, optimized, or promoted.

R3-360 closes
`E-PASS / X-NOT-REQUIRED / S-NOT-APPLICABLE / C-NOT-APPLICABLE`.
