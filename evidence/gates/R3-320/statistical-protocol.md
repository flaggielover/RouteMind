# R3-320 Statistical RouteBench protocol evidence

Date: 2026-08-24 (Asia/Shanghai)

## Scope

R3-320 freezes the prospective R3-B comparison before pilot or confirmatory
campaign data. It does not execute RouteBench, estimate an effect, perform power
analysis, or support a strategy claim.

The machine-readable protocol is
`docs/research/r3/manifests/statistical-routebench/statistical-routebench-v1.json`.
It is 9,737 bytes with frozen SHA-256
`a6dae9d55641ff7966ef4a50cc00a63da3e936620c3c48f23cd2c2ce039375b5`;
the loader binds this exact byte identity after semantic validation.
It is frozen against R3-316 closure revision
`c0967c1208be2249e672dc5ca9b8a32a687d4110`, whose five GitHub Actions jobs
passed in run `32711507127`.

## Prospective design

- Candidate: `risk-aware@1.0.0` with the committed default five-weight vector.
  Comparator: `weighted-greedy@1.0.0` with distance weight 1.0.
- Primary paired risk is recomputed independently from immutable selected-courier
  service and overtime risks; a strategy score or rationale is never an outcome.
  Unassigned, timed-out, or strategy-failed requests receive risk 1.0.
- The co-primary assignment difference uses every preregistered request and a
  fixed non-inferiority margin of `-0.02`.
- Eight ordered regimes cover normal, surge, shortage, merchant delay, travel
  degradation, location staleness, compute budget, and queue pressure with
  explicit numeric perturbations.
- Demand, merchant, courier, and traffic streams are paired across arms. R3-321
  must implement their ownership and digest-stable seed derivation before data.
- The bounded pilot uses eight pairs per regime solely for prospective variance
  and power. Confirmatory replicate identities start at 1000 and cannot reuse
  pilot seeds. R3-323 freezes the resulting count between 20 and 200 pairs per
  regime; exceeding the ceiling is labeled underpowered, not repaired by changing
  alpha or the effect threshold.
- The primary analysis uses mean paired differences, unadjusted two-sided
  Student-t 95% intervals, directional paired tests, paired Cohen's dz, and one
  Holm family of eight risk-superiority plus eight assignment-noninferiority
  tests. Overall H1-B1 support requires every regime's interval threshold and
  both Holm-adjusted directional gates to pass; ordinary intervals are not
  mislabeled simultaneous intervals.
- Runtime, strategy failure, fallback, and timeout are mandatory safety
  diagnostics. Sensitivity analyses cannot replace the frozen primary analysis.

## Outcome integrity and stopping

Bad outcomes, timeouts, fallbacks, nulls, and unfavorable effects are retained.
Only pre-execution checksum/parser/license failures or a confirmed symmetric
harness defect may exclude a pair, and every attempt remains in the ledger.
There is no efficacy interim look or desired-result stopping. Resource, input,
verifier, implementation, or external-authorization blockers stop execution with
all outputs retained and an incomplete/underpowered disposition.

R3-325 material execution remains prohibited until R3-321, R3-322, R3-323, and
R3-324 pass and the R3-325 implementation checkpoint is remote green. The maximum
confirmatory envelope is 3,200 single-thread arm runs, 30 seconds per arm, 1 GiB
peak memory, 512 MiB external artifacts, and zero external cost.

## Executable evidence

`statistical_routebench_protocol.py` strictly loads the protocol and fails closed
on changes to identities, arms, metrics, margins, regimes, random streams, power,
inference, safety diagnostics, exclusions, stopping, resources, or lineage.
Directed tests mutate each scientifically material section. No test invokes a
pilot or material campaign.

Local validation passed 51 directed protocol tests with 97.46% module coverage,
the complete Python suite at `544/544` and 95.76% total coverage, Java `80/80`,
Web `92/92` plus production build, 6 schemas / 18 contract fixtures,
determinism, analytics, semantic metrics, repository controls, Ruff, and mypy.

Current disposition: `E-IN-PROGRESS / X-NOT-REQUIRED / S-NOT-APPLICABLE /
C-NOT-APPLICABLE`. Remote CI is required before R3-320 can close.
