# R3-358 Negative Scientific Results Audit

Date: 2026-08-25 (Asia/Shanghai)
Status: closed with append-only negative evidence preserved
Implementation: `200c4d41bf93a0199b389770c3edb2dbb469a792`
GitHub Actions: PASS - run `32782886790` (all five jobs)

## Frozen audit boundary

Manifest:
`docs/research/r3/manifests/negative-results/r3-358-negative-results-audit-v1.json`

- Manifest digest:
  `e36e3be33cb61138472cf94966ea31a2fb7432af142a5d50c011e6359fd6dcf5`
- Manifest byte SHA-256:
  `396a3a921a28bdeb30f4429b97ce75a509b9193c47897a8ec7bf36c782d33e91`
- Immutable 31-entry prefix digest:
  `89fe0c2eb1cab8da5162c4769f4bcef41bc8b904dcc0f933a1bf069192032706`
- Entries NR-R3-001 through NR-R3-026 remain unchanged. Entries NR-R3-027
  through NR-R3-031 add the missing task-specific outcomes for R3-312,
  R3-325, R3-327, R3-355, and R3-356.

The standard-library gate checks sequential unique identifiers, the immutable
prefix, 24 required task identities, six negative-result categories, and seven
exact source-artifact hashes. Future monotonic appends are accepted. Mutation,
deletion, reordering, source drift, and coverage loss fail closed.

## Preserved unfavorable outcomes

- R3-312 retains unfavorable Homberger scale and timeout outcomes.
- R3-325 remains frozen exactly as
  `E-PASS / X-PASS / S-FAIL / C-NO-CLAIM`; it was not rerun or reinterpreted.
- R3-327 retains its six non-estimable assignment regimes and remains
  `S-FAIL / C-NO-CLAIM`.
- R3-355 remains deferred because current logs do not identify OPE. No
  propensity values or estimators were fabricated.
- Both R3-356 reproduction attempts remain append-only. The recovered checker
  does not erase the first attempt or strengthen any upstream claim.

Scientific failure, null evidence, non-estimability, and insufficient data are
valid terminal evidence. They are not implementation failures.

## Executable evidence

- The live gate validates all 31 frozen entries and their source identities.
- Three directed tests prove a valid append is accepted while frozen mutation
  and deletion are rejected.
- `./scripts/full-gate.ps1`: PASS - Java 81/81, Python 905/905 at 95.17% total
  coverage, Web 92/92 plus production build, and all static, contract,
  research, determinism, and bounded-resilience controls.
- Actions run `32782886790`: all five jobs passed for implementation SHA
  `200c4d41bf93a0199b389770c3edb2dbb469a792`, including the control-plane job
  that executes the negative-results gate and its self-tests.

## Final disposition

R3-358 closes
`E-PASS / X-NOT-REQUIRED / S-NOT-APPLICABLE / C-NO-CLAIM`.
No unfavorable evidence was deleted, rewritten, or promoted into a claim.
