# RouteMind Round 3 Scientific Closure Report

Date: 2026-08-25 (Asia/Shanghai)
Status: CLOSED - 43 passed, 2 explicitly deferred/reclassified
Control-plane inception: `59eb53b` (`research: establish round 3 scientific control plane`)
Closure implementation: `9e9537e6775fa908b910ebb060fd66662ba3a05c` (Actions run `32790948926`, all five jobs)

## Closure decision

Round 3 is scientifically closed. The R3-365 implementation passed real GitHub
Actions. This report does not turn engineering success into experimental,
statistical, novelty, or production support.

The closed graph contains 45 Round 3 task records:

- 43 tasks, including R3-365, are passed;
- R3-313 was optional and non-blocking, performed no Li and Lim compatibility
  assessment, and is preserved as prepared Round 4 task R4-437; and
- R3-355 remains deferred because R3-354 established
  `OPE_NOT_IDENTIFIABLE_FROM_CURRENT_LOGS`; no propensity was fabricated and no
  IPS or doubly robust estimator ran.

The terminal inventory is 43 passed and two explicitly deferred/reclassified
tasks. No required task is left pending.

## Gate inventory

The final candidate gate distribution across all 45 tasks is:

- Engineering: 43 `E-PASS`, one `E-DEFERRED` R3-313, and one `E-DEFERRED`
  R3-355.
- Experiment: 22 `X-PASS`, 21 `X-NOT-REQUIRED`, and two `X-DEFERRED`.
- Statistical: one `S-PASS`, three `S-FAIL`, 39 `S-NOT-APPLICABLE`, and two
  `S-DEFERRED`.
- Task claim status: 26 `C-NO-CLAIM`, 14 `C-NOT-APPLICABLE`, and five
  `C-DEFERRED`.

The only `S-PASS` is R3-316's deterministic descriptive gap analysis. The three
`S-FAIL` records are R3-311, R3-325, and its R3-327 report. A task-level
`S-PASS` does not authorize a scientific claim.

The final seven-row Claim Matrix is stricter and is authoritative for proposed
scientific claims:

- `C-PASS`: 0
- `C-NO-NOVELTY`: 2 (`R3-A2`, `R3-E1`)
- `C-NO-CLAIM`: 5 (`R3-A1`, `R3-B1`, `R3-C1`, `R3-D1`, `R3-D2`)
- `C-DEFERRED`: 0

Its supported scientific claims section is exactly `None`.

## Engineering results

Round 3 established a reproducible scientific engineering system:

- public benchmark acquisition, archive/member checksum validation, parsers,
  outcome semantics, independent route verification, and exact derived-model
  cross-checking;
- frozen Statistical RouteBench protocols, common-random-number stream
  ownership, paired estimation, power analysis, multiple-comparison control,
  immutable pilot artifacts, and statistical reports;
- calibration/held-out split contracts, fidelity thresholds, drift and
  non-fidelity handling for the Digital Twin;
- frozen RADS baseline, RADS-H and Safe-RADS formal boundaries, support audits,
  ablation, robustness, policy-boundary, and counterfactual evidence contracts;
- privacy-bounded Decision Corpus, interference and OPE identifiability audits,
  alternate reproduction, prior-art audit, append-only negative results, final
  claim review, and manifest-linked figures; and
- executable gates that reject frozen-outcome mutation, unsupported claim
  promotion, negative-result deletion, figure-lineage drift, and premature
  Round 4 activation.

Java continues to own durable business truth and transactions. Python continues
to own optimization, simulation, RouteBench, RADS, analytics, experiments, and
bounded agent intelligence. No research task moved hard real-time dispatch
correctness to an LLM.

## Workstream A: external validity and solver science

Public Solomon and Gehring-Homberger inputs are external-data-root artifacts
with exact archive/member lineage.

- The six-instance Solomon pilot retained four independently verified complete
  incumbents and two no-incumbent timeouts. Its 4/6 rate had Wilson 95% interval
  `[0.299993, 0.903229]`; the preregistered hypothesis failed.
- The 30-instance Gehring-Homberger campaign retained 29 verified complete
  incumbents and one no-incumbent timeout. Every incumbent used more vehicles
  than its retained reference, so availability did not become a quality claim.
- Six derived eight-customer conservative integer models completed exhaustive
  enumeration, exact CP-SAT optimization, and independent verification. All
  transformed candidate gaps were 0%, scoped only to those derived models.
- R3-316 accounted for all 42 records with zero exclusions. Approved source
  vehicle gaps had `n=27`, median `31.6667%`, Type-7 p90 `349.4545%`, and max
  `484.2105%`; conditional same-vehicle distance gaps had `n=4`, median
  `2.6745%`, p90 `8.8185%`, and max `10.3053%`.

These results do not establish source-instance optimality, RouteMind
superiority, unrestricted solver capability, or population behavior. Native Li
and Lim pickup-delivery applicability was not assessed in Round 3.

## Workstream B: Statistical RouteBench

R3-325 is permanently frozen exactly as
`E-PASS / X-PASS / S-FAIL / C-NO-CLAIM`.

- The pilot retained all 128 arm results across eight regimes, eight paired
  units, two strategies, and four common-random-number streams.
- The R3-327 report retained all 16 regime/metric cells. Eight scenario-risk
  and two assignment-rate cells have unadjusted descriptive paired 95%
  Student-t intervals.
- Six assignment-rate cells are explicitly
  `NON_ESTIMABLE_PAIRED_VARIANCE_OR_POWER`.
- The 16-test confirmatory family was not executed, Holm-family p-values are
  null, and no confirmatory or strategy-superiority claim exists.

R3-325 was never rerun, tuned, reinterpreted, optimized, or selectively filtered
to obtain a pass.

## Workstream C: Digital Twin science

The calibration and held-out protocols are implemented, but the repository has
zero eligible observed calibration or held-out records. R3-331, R3-332, R3-334,
and R3-336 therefore close with honest insufficient-data/non-fidelity outcomes.

- All frozen fidelity thresholds remain unevaluated for lack of observed data.
- No synthetic record was substituted for an observed-data requirement.
- No calibration, held-out fidelity, broad Twin validity, or production
  generalization claim exists.

The observed-data, privacy, calibration, and held-out campaign is preserved as
R4-431 through R4-433 behind external and human-approval gates.

## Workstream D: RADS research

RADS-BASELINE-v1 and the RADS-H/Safe-RADS formal boundaries are reproducible.
The frozen R3-325 artifacts do not contain the tick-level variant identities,
switch logs, safety outcomes, ablations, policy-boundary support, or executable
counterfactual replay needed for the planned empirical claims.

- RADS-H, Safe-RADS, stability-map, policy-boundary, counterfactual,
  ablation, and robustness audits retain `INSUFFICIENT_DATA` or explicitly
  unsupported states.
- Seven robustness axes have source regimes but no RADS variant outcomes;
  `location_noise` is unsupported; eight pairs are below the frozen minimum 30.
- No switching, safety, policy-effect, counterfactual, ablation, cross-regime
  robustness, broad RADS, or superiority claim exists.

Outcome instrumentation and a separately authorized, powered campaign are
preserved as R4-434 through R4-436. The future graph forbids optimizing away
Round 3's insufficient-data results.

## Workstream E: advanced evaluation and closure

The Decision Corpus contains bounded source evidence but cannot support the
planned broad evaluation claims.

- Shadow disagreement mining, dispatch interference analysis, and
  counterfactual Decision X-Ray close with explicit missing-support outcomes.
- R3-354 found no logged propensities, verified exploration/action overlap,
  sufficient state richness, or shared-resource context. OPE is not identifiable.
- R3-356 used a standard-library-only alternate checker to reproduce R3-316,
  R3-327, R3-336, and R3-349 with zero contradictions. Its first attempt and
  order-only checker defect remain append-only evidence.
- R3-357 reviewed 16 original or peer-reviewed sources across nine categories:
  five `SUBSUMED`, two `CLOSE_PRIOR`, two `PARTIAL_GAP`, and no
  `PLAUSIBLE_GAP`.
- R3-358 freezes 31 negative-result entries across 24 task identities and six
  categories with an append-only prefix digest.
- R3-360 generates three SVG figures and three CSV tables from five hash-locked
  source families, preserving 16/12/7 rows, zero exclusions, and zero `C-PASS`.

Independent reproduction, a partial search gap, polished figures, and green CI
do not independently authorize a scientific or novelty claim.

## External validity

Evidence is bounded to the exact public benchmark members, derived models,
simulation pilot, manifests, and repository/external artifacts recorded in task
evidence. It does not establish:

- production city performance, real courier/customer outcomes, or causal impact;
- provider-backed road-network quality, live traffic fidelity, or region support;
- broad Twin fidelity or RADS robustness;
- optimality beyond exact derived models; or
- patentability, novelty, or thesis claim acceptance.

Production deployment, identity/tenancy, provider validation, observed Twin data,
powered RADS evaluation, external-environment reproduction, and broad agent
evaluation remain Round 4 work.

## Reproducibility and evidence integrity

Round 3 evidence uses frozen manifests, exact source hashes, content digests,
sidecars, immutable external outputs, code revisions, CI run identities, seeds,
environment records, independent verification, and alternate reproduction.

Primary closure artifacts are:

- `docs/research/r3/RESEARCH_CONTRACT.md`
- `docs/research/r3/CLAIM_MATRIX.md`
- `docs/research/r3/NEGATIVE_RESULTS.md`
- `docs/research/r3/PRIOR_ART_AUDIT.md`
- `docs/research/r3/results/reproduction/r3-356-independent-reproduction-v1.json`
- `docs/research/r3/results/final-figures/r3-360-final-scientific-figures-v2.json`
- `evidence/gates/R3-356/independent-reproduction.md`
- `evidence/gates/R3-358/negative-results.md`
- `evidence/gates/R3-359/claim-review.md`
- `evidence/gates/R3-360/final-figures.md`

`PROGRESS.md` and the per-task evidence directories retain the complete CI and
checkpoint ledger. Representative closure-spine runs include R3-300
`32692144152`, R3-311 `32699067563`, R3-315 `32701927556`, R3-312
`32706450863`, R3-316 `32710816931`, R3-320 `32713127743`, R3-325
`32725900984`, R3-327 `32737520239`, R3-336 `32752905068`, R3-349
`32777694427`, R3-356 `32781478836`, R3-358 `32782886790`, R3-357
`32787178651`, R3-359 `32787968109`, and R3-360 `32789597203`. Every named
run completed all five CI jobs.

## Deferred and reclassified work

R3-313 and R3-355 are not silently passed:

- R3-313 is reclassified to optional R4-437. It activates only if native
  pickup-delivery semantics enter scope and must return `COMPATIBLE`,
  `TRANSFORMED`, or `NOT_APPLICABLE` with evidence.
- R3-355 is reclassified to R4-438 through R4-440. Decision-time propensity and
  overlap instrumentation comes first; R4-440 activates only after a positive
  R4-439 identifiability audit.

All production-heavy work removed from the scientific critical path is preserved
in `docs/research/ROUND_4_TASK_GRAPH.yaml`.

## Round 4 prepared state

The prepared graph is `PREPARED_NOT_STARTED` and contains 38 pending tasks in
six workstreams. Its executable gate verifies:

- exact task identity and dependency order;
- 15 external-evidence gates and 12 human-approval gates;
- three conditional/optional tasks with activation conditions;
- 11 Round 3 reclassification lanes;
- the final zero-`C-PASS` Claim Matrix and frozen R3-325 status; and
- absence of every R4 task from the active `TASK_GRAPH.yaml`.

Round 4 preparation proves no production, provider, agent, scientific, or thesis
claim and starts no R4 task.

## Closure evidence

R3-365 implementation `9e9537e6775fa908b910ebb060fd66662ba3a05c`
passed all five jobs in GitHub Actions run `32790948926`: Control plane and
Compose, Java, Python, bounded degradation/resilience, and Web
static/unit/browser. The control job executed the Round 4 graph gate and all
seven mutation tests in a clean checkout.

Closure checkpoint `5dc668496225e333d1996b66c925bdd309985ac6` then recorded
Round 3 as closed, R3-313/R3-355 as explicit deferred/reclassified
dispositions, and Round 4 as `PREPARED_NOT_STARTED`. All five jobs passed again
in Actions run `32791413681`.

The final evidence-synchronization checkpoint
`fb33b8e5eed5b1af8c435ad83cb2de86d295817d` passed all five jobs in Actions
run `32791713983`. At that checkpoint the tracked worktree was clean and
`main == origin/main`; the user-owned untracked `.codex-tmp/` directory was
preserved without modification.
