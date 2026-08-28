# RouteMind Science Readiness

Audit date: 2026-08-28 (Asia/Shanghai)
Source revision: `ab585f82fbcdd68aaa75cf8597d7f68be6c385aa`

## Verdict

`SCIENCE_READY_WITH_NONBLOCKING_GAPS`

`CLAUDE_SCIENCE_CAN_START = YES`, but only for bounded, local, exploratory
discovery, hypothesis generation, experiment design, and falsifiable replay
work. This is not a production, external-validity, causal, novelty, Twin
fidelity, RADS superiority, or strategy-superiority authorization.

The platform has deterministic seeded execution, content-addressed manifests,
write-once artifacts, explicit failed/partial outcomes, replay and what-if
boundaries, statistical estimation, and append-only negative-result controls.
The gaps below are nonblocking for exploratory work because they are represented
as explicit `PARTIAL`, `INSUFFICIENT_DATA`, or `NO-CLAIM` states rather than
silently promoted results.

## Immutable Scope

- R3-325 remains exactly `E-PASS / X-PASS / S-FAIL / C-NO-CLAIM`.
- R4-405 and R4-406 remain `TARGET_PENDING / NO_TARGET_CLAIM`.
- `EXTERNAL_VKE_VALIDATION` and `TOKYO_VM_EXTERNAL_VALIDATION` remain
  `INCONCLUSIVE`; no new paid diagnostic is authorized.
- R4-411B remains `FAILED / PARTIAL_NO_PRODUCTION_CLAIM`; no new Google call or
  consumed contract reuse is allowed.
- R4-422 remains `BLOCKED / PREPARED_NOTIFICATION_PROVIDER_HUMAN_GATE`; no AWS
  account, credential, or notification send is authorized.
- HERE is retired and is not an active runtime provider.

## Entry Gates

| Gate | Status | Evidence-based disposition |
| --- | --- | --- |
| S1 Reproducible experiment execution | `PARTIAL_NONBLOCKING` | Seeded ScenarioKernel and statistical campaign are repeatable, manifest-bound, and resumable at completed-pair boundaries. A hard process termination during an in-flight pair does not persist that pair until the next bounded rerun. |
| S2 RouteBench | `PARTIAL_NONBLOCKING` | Seven registered strategies, benchmark manifests, paired statistical protocols, raw pair artifacts, and external benchmark adapters exist. Broad real-data coverage and automated trend regression are not yet a single end-to-end gate. |
| S3 Digital Twin | `PARTIAL_NONBLOCKING` | Seeded replay, perturbations, reset/snapshot, what-if, and fidelity protocols exist. Observed calibration and held-out records are zero, so no fidelity or transfer claim is admissible. |
| S4 Policy/RADS | `PARTIAL_NONBLOCKING` | State encoding, risk objective, selector, RADS-H/Safe-RADS boundaries, fallback and explanation hooks exist. Switching/safety outcomes and policy-learning support are absent from the frozen corpus. |
| S5 Metrics | `PARTIAL_NONBLOCKING` | A versioned semantic registry and RouteBench/RADS/Twin metric primitives exist, but the full operational and research metric catalog is not centrally populated. |
| S6 Ablation/stress | `PARTIAL_NONBLOCKING` | Preregistered ablation dimensions and eight stress axes are frozen and perturbation code is deterministic. A unified component-toggle campaign and empirical outcomes are not present. |
| S7 Research lineage | `PARTIAL_NONBLOCKING` | Decision Corpus, manifest digests, run/seed/reference identities, independent reproduction, and append-only negative results are present. A single cross-subsystem run identifier is not yet universal. |
| S8 Linux campaign readiness | `PARTIAL_NONBLOCKING` | Python/Compose paths are portable and bounded single-host Linux execution is viable. There is no remote launcher, distributed worker pool, or artifact synchronization protocol for high-scale campaigns. |

No gate is `FAIL_BLOCKING` for the scoped exploratory start. Confirmatory,
external, or production claims remain blocked by their own evidence contracts.

## Capability Audits

### Experiment execution

`ScenarioManifest` captures scenario identity, seed, demand/courier state,
delays, traffic multiplier, clock domain, and reference data. `ScenarioKernel`
uses a seeded RNG and emits decisions, transitions, simulated end tick, and a
replay digest. `BenchmarkManifest` adds code version, dataset provenance,
strategy/version, parameter/configuration, runtime, failure labels, hardware,
and reference data. The statistical campaign adds authorization revision/CI,
CRN stream identities, bounded resource estimates, UTC timestamps, explicit
failure/timeout/fallback/defect outcomes, and write-once checksummed artifacts.

`CampaignArtifactStore` isolates each campaign and pair below
`ROUTEMIND_DATA_ROOT`, verifies existing bytes before reuse, and reloads
completed pairs on restart. Unknown or malformed artifacts fail closed. A
process kill between arm execution and pair write is retained as a known
operational gap; it cannot contaminate another pair and is reproducible on
rerun.

### RouteBench capability matrix

| Capability | Status | Current evidence |
| --- | --- | --- |
| Scenario schema and identity | `PARTIAL` | `ScenarioManifest` is strict and digestable; it relies on manifest/reference-data identity rather than a separate schema-version field. |
| Scenario/workload generation | `READY` (bounded synthetic) | Frozen local stress generator and deterministic pilot executor. |
| Synthetic reproducibility | `READY` | Seeded CRN streams, replay digests, and determinism tests. |
| Real-data adapter boundary | `READY` | `DataRootArtifactAdapter` and public benchmark checksum/lineage adapters. |
| Solomon / Gehring-Homberger integration | `READY` (bounded sources) | Parser, verifier, exact cross-check, and retained R3 evidence; not a production traffic claim. |
| Baseline registry | `READY` | `nearest`, `weighted-greedy`, `hungarian`, `minimum-cost-flow`, `partitioned-assignment`, `vrptw`, and `risk-aware` are registered. |
| Policy/version capture | `READY` | Strategy descriptors and versioned parameter schemas. |
| Batch comparison | `READY` | `RouteBenchRunner` and statistical campaign pair execution. |
| Metric collection | `PARTIAL` | Assignment/risk/runtime/failure metrics are present; the full operational catalog is not. |
| Confidence/statistical aggregation | `READY` (pilot scope) | Paired means, Student-t intervals, effect sizes, sensitivity, power and Holm plans; confirmatory inference remains unexecuted. |
| Raw and aggregate export | `READY` | Pair-level records plus campaign ledger and report artifacts. |
| Regression detection | `PARTIAL` | Digest and contract drift are rejected; no continuous historical-effect trend gate exists. |

`vrptw` is a bounded deterministic insertion heuristic and is not claimed to
be a general VRPTW optimizer. `minimum-cost-flow` and
`partitioned-assignment` are engineering strategies, not research claims.

### Digital Twin

Demand arrivals, courier motion, merchant delay, traffic multipliers, supply,
staleness, incident/dependency failure, seeded noise, simulated clock, reset,
snapshot, replay, and bounded what-if branches are implemented. Calibration,
held-out validation, drift, and fidelity contracts are strict and fail closed,
but the eligible observed-record count is zero. The existing R3 non-fidelity
report therefore remains the authoritative result; synthetic records cannot
substitute for observed data.

Controlled intervention, counterfactual comparison, ablation, robustness,
distribution shift, stress, and policy switching are `PARTIAL`: the mechanisms
and protocols exist, while empirical outcome artifacts and unified campaign
aggregation remain future work.

### RADS and policy research

| Candidate | Current state | Entry condition |
| --- | --- | --- |
| RADS-H | `SCAFFOLD / RESEARCH_CANDIDATE` | Preserve tick-level switch/dwell/service/cost logs and run the frozen paired protocol. |
| Safe-RADS | `SCAFFOLD / RESEARCH_CANDIDATE` | Produce constraint-violation, feasibility, calibration, and efficiency outcomes under a new authorized manifest. |
| Self-Calibrating Digital Twin | `SCAFFOLD / RESEARCH_CANDIDATE` | Supply disjoint observed calibration and held-out records. |
| Decision X-Ray | `SCAFFOLD / RESEARCH_CANDIDATE` | Capture executable state/policy bundles and same-model replay lineage. |
| Policy Boundary Learning | `SCAFFOLD / RESEARCH_CANDIDATE` | Reach the frozen strategy-class and stability-cell support thresholds. |
| Multi-Agent Tradeoff Analysis | `MISSING / RESEARCH_CANDIDATE` | Define a new provider-neutral study contract; no implementation or claim is implied by this audit. |

Implemented primitives include `RadsStateEncoder`, `RadsObjective`,
`RadsSelector`, risk-aware scoring, formal hysteresis state transitions,
parameterized variants, fallback/degradation boundaries, and explanation
strings. Empirical policy effect, safety, switching stability, and superiority
remain unclaimed.

### Decision ledger and lineage

The Decision Corpus records state digest/version, candidate scores and reasons,
selected action, alternatives, objective/risk components, verification checks,
reference-data identity, clock/sequence, outcome, and source-event digest.
RouteBench and statistical artifacts add experiment/protocol/scenario/seed,
strategy/version, parameter, CRN stream, environment, hardware, timestamps,
and output digests. This is sufficient to answer “why A over B?” within a
captured subsystem and to replay the same state when the referenced bundle is
available. It is not yet a universal cross-subsystem `run_id` contract.

### Metric readiness matrix

| Family | Metric | Status |
| --- | --- | --- |
| Operational | delivery/pickup latency | `PARTIAL` (ETA and delay-accounting primitives; no complete central mart metric) |
| Operational | timeout/SLA violation | `PARTIAL` |
| Operational | courier utilization, empty travel, batching efficiency, fairness, workload imbalance | `MISSING` |
| Operational | travel distance, order completion | `PARTIAL` |
| Optimization | objective value, solver latency, feasibility | `READY` within decision/solver and bounded benchmark scopes |
| Optimization | optimality gap | `READY` only for verified exact/derived benchmark comparisons |
| Optimization | fallback rate | `READY` in the semantic registry |
| Optimization | recomputation rate | `MISSING` |
| RADS | policy selection, switching, hysteresis events, risk score, fallback/degradation, decision stability | `PARTIAL` (primitives/contracts exist; required outcome logs are absent) |
| Digital Twin | calibration error, prediction error, simulation-real discrepancy, drift, scenario divergence | `PARTIAL` protocol-only; no observed records |
| Research | mean, variance, confidence interval, quantiles, effect size, raw run samples, seed grouping | `READY` for the frozen paired statistical pipeline |

The central semantic registry currently exposes archived events, orders,
decisions, assignment/fallback rates, solver success, and simulation
completion. Missing metrics are never synthesized from aggregate winners.

### Ablation and robustness

R3-348 freezes dimensions for risk term, switching, uncertainty/calibration,
traffic, merchant-delay, counterfactual feature, and threshold sensitivity;
R3-349 freezes eight axes (seeds, demand, supply, merchant delay, traffic,
location noise, location staleness, compute constraints). `perturbations.py`
and the statistical regime/CRN protocol provide deterministic ingredients.
The current corpus contains no component-level ablation or RADS cross-regime
outcomes, and `location_noise` has no supported source regime. A future
provider-neutral manifest should add explicit component flags and a bounded
grid runner; it must be a new version and cannot alter R3-325.

### Statistical analysis

Repeated seeds, paired comparisons, Student-t intervals, effect sizes,
leave-one-pair-out sensitivity, prospective power, multiplicity plans, raw
pair records, machine-readable reports, and standard-library independent
reproduction are available. R3-325's confirmatory family was deliberately not
executed; its `S-FAIL / C-NO-CLAIM` state is preserved.

### Data root and portability

`F:\Projects\RouteMind` is the code source of truth and
`F:\Projects\RouteMind-Data` is the intended large-data root. Portable code
uses `ROUTEMIND_DATA_ROOT`; current process inspection reported that variable
as `MISSING`, so large-artifact commands must receive an explicit configured
root before execution. Repository searches found the expected documentation
and test fixtures but no production-code hardcoding of the F: data path.

`DataRootArtifactAdapter`, content-addressed campaign stores, checksum
sidecars, and independent reproduction path checks provide the required
boundary. Compose and Python dependencies are environment-driven; Linux
single-host execution is supported. True high-scale blockers are the absence
of a remote launcher/worker scheduler and remote artifact synchronization or
checkpoint transfer protocol. These do not block bounded local exploratory
runs.

### Falsifiability and claim boundary

Negative results, failed hypotheses, partial/insufficient-data outcomes,
exclusions, frozen digests, and no-claim states are first-class. The campaign
stopping policy forbids desired-result stopping, favorable-seed selection,
silent exclusion, and post-result deletion. `negative_results_gate.py`, the
claim matrix gate, independent reproduction, and append-only evidence protect
this boundary.

## True blockers and follow-up

There are no blocking items for the scoped exploratory Claude Science start.
Before confirmatory or broad claims, the following remain required:

1. New authorized observed-data campaigns for Twin calibration/held-out
   fidelity and RADS outcomes.
2. A unified component-toggle ablation runner and a complete central metric
   catalog for the intended study.
3. A remote/high-scale Linux execution and artifact synchronization contract.
4. Any external provider, production, notification, or cloud validation Human
   Gate already recorded in Round 4.

These are explicit post-entry tasks, not retroactive changes to frozen science.
