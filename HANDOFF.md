# RouteMind Handoff

Last Known Commit: Current `HEAD`; resolve with `git rev-parse HEAD`

Current Branch: main

Current Phase: Round 3 Scientific Research - Workstream D

Current Task: R3-348 - Execute preregistered RADS ablation

Task Status: R3-348 is active at E-IN-PROGRESS/X-IN-PROGRESS/S-IN-PROGRESS/C-DEFERRED. The six-dimension plan and fail-closed support audit pass Java 81/81, Python 881/881 at 95.43% coverage, six directed tests, and Web 92/92 plus build locally. R3-342 and R3-345 retain `INSUFFICIENT_DATA`; R3-325 was not rerun. Remote CI is pending, and R3-356 is not eligible until R3-349 passes.

Next: implement and validate the R3-348 fail-closed RADS ablation plan/support audit, record its truthful outcome, then continue to R3-343 and R3-349 by dependency order.

R3-336 evidence is `evidence/gates/R3-336/twin-non-fidelity.md`; plan digest is `ed63c2a2c7a8020076411f285ff3c7fccd3b12e7800de70c4ad5b4a9a674dd94` and byte SHA is `87359292944b701cedfa11546cbca2553c259645d83d6bb2b4e6857b9d58e571`.

R3-340 evidence is `evidence/gates/R3-340/rads-baseline-freeze.md`; baseline digest is `a907a0a722e8782aa76277637fa92205cc10046e5aca85b2de81e555623016c3` and byte SHA is `c477a1ae2b00fcd53251be26db4229c56b7e2e91d79b49f9303aba29b6014a02`.

R3-341 evidence is `evidence/gates/R3-341/rads-h-formalization.md`; plan digest is `4b846bc8b971df269c1c6439b325ab61b7803a83812ced39b352f519acb929c5` and byte SHA is `091a196bfbcaae57077cd862b87a30d7793300bae219f0b6c32e95cff6060e94`.

R3-342 evidence is `evidence/gates/R3-342/hysteresis-experiments.md`; plan digest is `725bce8111db8652c6b52ef1c71e63429594aa4a329e0372e524471ea41ac967` and byte SHA is `62eab0fca0a28a758ae6299a83c900752044f3c155f84245e09dadc6e7ac921d`. The read-only support audit returned `INSUFFICIENT_DATA` because all six required tick-level fields are absent from frozen R3-325 pair artifacts; all metrics are `NOT_REPORTED_NO_SWITCH_LOGS`.

R3-344 evidence is `evidence/gates/R3-344/safe-rads-formalization.md`; plan digest is `82fed4dc95bec7ccbfa10ead770d63e2de6f47bb081d0b5d05672382462f6644` and byte SHA is `a3570615177b19fa59688b23a0e85f76957c6090b75f1fd6d165f3506b171163`. This is a formal preregistration boundary only; no safety, calibration, efficiency, or superiority claim is authorized.

R3-345 evidence is `evidence/gates/R3-345/safe-rads-experiments.md`; plan digest is `182a3e6217f2c8e918049a4d55b78e340c8882a58e5dad106a7f738c3433783c` and byte SHA is `74d83b8fc695e623d6b1a89466f3836bcf6dec618745080920df8080dbb68288`. The support audit returned `INSUFFICIENT_DATA`; all seven metrics are `NOT_REPORTED_NO_SAFE_OUTCOMES`.

R3-351 evidence is `evidence/gates/R3-351/shadow-disagreements.md`; plan digest is `f2dfc31a57db3dcd7c3ad2c4f432b41efcbdd7c252274904550a818508734022` and byte SHA is `00a79ee8571465197f43f6c47c43b7a328f11724cca2cf482253cfdfbdb847dc`. The two-record corpus lacks alternate outcomes and disagreement strata; result is `INSUFFICIENT_DATA`, not superiority evidence.

R3-353 evidence is `evidence/gates/R3-353/interference.md`; plan digest is `4a1b3477a7da89e42ded5d58e38b086bf459863cd2e320bf038f383b2438de8c` and byte SHA is `7500c777993eee907e2642e30a70eefc938778bb9bee8de12dc3496e102db8e5`. The frozen design has no simulation outcomes; result is `INSUFFICIENT_DATA`, simulation-scoped only.

R3-354 evidence is `evidence/gates/R3-354/ope-identifiability.md`; plan digest is `bbce6870d64222128ab06015a5a8a0642cbc30b0f6677b5da2c9e4422b3e3609` and byte SHA is `a7f254babad7382d4d6f1db66d2a82606a4f9e3fdc53109f69445c0b3fabda5d`. Result is `OPE_NOT_IDENTIFIABLE_FROM_CURRENT_LOGS`; no propensity or OPE effect claim is permitted.

R3-335 evidence is `evidence/gates/R3-335/what-if-validity.md`; plan digest is `81c52721886c646d2ff468f500c334566e3ed7f4f66bf0f63a9c4478f4b42023` and byte SHA is `20640a2cd366fd992dec681c3dc4139b4b352cb9609bf71ba0542a9bceb9a57d`.

R3-333 evidence is `evidence/gates/R3-333/fidelity-protocol.md`; protocol digest is `de453fdf1181b2e5a52839eb9f1b7536db3f5f5fb1177f4b5351269cfa3c1825` and byte SHA is `a3007f1ca9892fd0b7746797e53dec9ab5aecc5e243d188b16f12564df2ea8ff`.

R3-324 resume capsule: the exact frozen 16-test Holm step-down family retains
protocol/regime/metric/hypothesis identity, raw p-values, stable family ranks,
multipliers, sequential thresholds, monotonic adjusted p-values, rejection
decisions, family disposition, claim boundary, and content digest. The reference
vector adjusts first to 0.016/0.030/0.042/0.052, rejects 3/16, and has digest
`53580e4f...e18c`; ties at the boundary adjust deterministically to 0.05.
Invalid values, identity drift, incomplete/duplicate families, and frozen
protocol drift fail closed. Twenty-two directed tests pass at 100% module branch
coverage; statistical integration is 143/143. The full local gate passes Java
81/81, Python 657/657 at 95.88%, Web 92/92 plus build, contracts, controls, and
determinism gates. During validation, a real Java same-instant transition flake
was diagnosed and repaired with monotonic aggregate/outbox event time; the fixed
clock regression and originally failing lease test pass. Implementation revision
`c3e394b` passed all five jobs in Actions run `32720233681`; R3-324 is closed.
Next: define R3-333's variable-appropriate Twin fidelity metrics, absolute
thresholds, improvement tests, and fail-closed INSUFFICIENT_DATA behavior;
R3-331 remains dependent on this protocol. R3-330 evidence is
`evidence/gates/R3-330/twin-dataset-contract.md`; its contract digest is
`fb3f3162ac073815cba838f3fde5a3b8ac94604e21dc4f9049bdf3785d108eaa`.
The R3-327 report implementation `ed01044` passed all five jobs in Actions run
`32737520239`; its report digest remains
`0c7e29af8c89ed9ca7cb094525745f488c4b4d69e73ab6a4a7f47dd4e5ae9eac`.
The report digest is
`0c7e29af8c89ed9ca7cb094525745f488c4b4d69e73ab6a4a7f47dd4e5ae9eac`; it
retains the six `NON_ESTIMABLE` assignment cells and makes no strategy claim.

R3-323 resume capsule: exact SciPy 1.18.0 one-sided noncentral paired-t planning
records the content-addressed variance source, frozen MDE/noninferiority distance,
family/local alpha, target, raw/rounded/planned counts, achieved power at required
and capped counts, runtime identity, disposition, and stable digest. The frozen
16-test Holm family uses conservative local alpha 0.003125; counts round to four
and retain the 20-200 cap without weakening design inputs. Synthetic variance
0.0016 yields raw 55, planned 56, power 0.8104064287044574. Variance 0.01 requires
324 and remains UNDERPOWERED_AT_CAP at 200 with power 0.5269065070498476. An
observed R3-325 pilot must contain exactly eight pairs. Forty-one directed tests pass
at 100% module coverage; integration is 120/120; the full local gate passes Java
80/80, Python 635/635 at 95.83%, and Web 92/92 plus build. Ruff, strict mypy,
contracts, lock/security, determinism, analytics, semantic metrics, and controls
pass. Implementation revision `b18d171` passed all five jobs in Actions run
`32718029279`; R3-323 is closed. R3-324 is active. Next: implement the exact
16-test Holm step-down family with stable identities, ties, monotonic adjusted
p-values, reject decisions, and fail-closed family validation; then run local and
remote gates. No pilot or confirmatory campaign ran.

R3-322 resume capsule: validated CRN plans feed candidate-minus-comparator paired
mean, median, sample SD, standard error, two-sided 95% Student-t interval,
paired Cohen's dz, 10% Winsorized mean, and complete leave-one-pair-out
sensitivity. Reports retain every four-stream seed/digest and have stable content
digests; forged, mixed, duplicate, incomplete, non-finite, out-of-range, and
zero-variance samples fail explicitly. Five Student-t references pass within
`5e-10`; 29 directed tests pass at 95.71% module coverage, integration is
101/101, and the full local gate passes Java 80/80, Python 594/594 at 95.76%, Web
92/92 plus build, contracts, determinism, analytics, semantic metrics, and
controls. Standard vector report digest: `8cc4f549...e585c`. No campaign ran.
Implementation revision `349a27e` passed all five jobs in Actions run
`32715625853`; R3-322 is closed. R3-323 is active. Next: freeze the power method,
record supplied variance/MDE/alpha/power/count/cap/disposition, validate against
independent vectors and underpowered cases, then run local and remote gates. Any
fixture variance must remain labeled synthetic until R3-325 runs the real pilot.

R3-321 closure capsule: demand, merchant, courier, and traffic have distinct
logical owners; preregistered SHA-256 derivation produces arm-independent 63-bit
seeds; each stream is realized once and both arms bind identical realization
digests; order alternates by replicate parity. The implementation explicitly
records `VARIANCE_CONTROL_NOT_OBSERVATION_INDEPENDENCE`. Directed tests passed
21/21 at 96.12% module coverage. The full local gate passed Java 80/80, Python
565/565 at 95.76%, Web 92/92 plus production build, 6 schemas / 18 fixtures,
determinism, analytics, semantic metrics, and repository controls. Implementation
revision `00475b8` passed all five jobs in Actions run `32714350193`. No pilot was
executed. R3-322 is active; implement Student-t paired intervals, paired Cohen's
dz, median, 10% Winsorized mean, leave-one-pair-out sensitivity, and fail-closed
sample validation, then run full local and remote gates.

Completed: Repository reconnaissance found an empty greenfield root and an existing
external data boundary. RM-000 established the authoritative control plane, task
graph validation, quality gates, recovery scripts, architecture contract, and ADR.
RM-001 added pinned PostgreSQL/RabbitMQ/Redis Compose infrastructure, isolated host
ports, health automation, stable RabbitMQ identity, and persistent volumes.
RM-002 added the Java 17/Spring Boot 4.1.1 business runtime, Maven Wrapper,
layered module boundaries, health and system endpoints, Flyway, and PostgreSQL
schema ownership.
RM-003 added the Python 3.12-3.14/FastAPI compute runtime, an isolated pinned uv
bootstrap, a hash-bearing lock file, framework-free dispatch strategy contracts,
strict boundary/type/lint gates, and loopback-only health/system endpoints.
RM-004 added independently versioned JSON Schema 2020-12 API/event contracts,
a conservative compatibility policy, positive/negative fixtures, permanent v1
compatibility baselines, and an executable validator in the frozen Python gate.
RM-005 has a least-privilege GitHub Actions workflow with independent control,
Java, and Python/contract jobs. The Python bootstrap is now portable across
Windows and Linux PowerShell.
RM-010 implements sealed customer, merchant, and courier identities, audited
party aggregates, Flyway V2 persistence, and a JPA repository adapter. H2
repository tests and a real PostgreSQL 18.6 migration/constraint probe passed.
RM-011 implements the order lifecycle state machine, immutable transition audit,
JPA persistence, Flyway V3, and optimistic database versioning. Domain and
repository tests plus a real PostgreSQL migration/persistence probe passed.
RM-020 implements the versioned event envelope, transactional order command and
Outbox write, pessimistic claim, stable event IDs, bounded retry, and RabbitMQ
publisher confirms. Flyway V4 and real PostgreSQL/RabbitMQ health/persistence
validation passed.
RM-021 implements durable event-ID deduplication, processing-before-ack
semantics, bounded retries, and observable dead-letter state. Flyway V5 and real
PostgreSQL validation passed.
RM-022 implements durable courier locations, a rebuildable Redis GEO projection,
nearby queries, and explicit `PROJECTED`/`DEGRADED` write outcomes. Flyway V6,
real PostgreSQL/Redis validation, and Redis-outage durability tests passed.
RM-030 implements the versioned Python dispatch result, a replaceable strategy
registry, and a deterministic Haversine nearest baseline with tie-breaking,
latency, and decision metadata.
RM-031 implements weighted-greedy and Hungarian baselines through the same
registry, including rectangular matrix assignment and benchmark provenance.
RM-040 implements point and matrix travel-time provider contracts, a
deterministic local Haversine estimator, and timeout/error fallback with
explicit provider and fallback metadata.
RM-050 implements an immutable seeded scenario manifest, deterministic event
kernel, dispatch/travel integration, replayable state transitions, and a
canonical SHA-256 replay digest.

RM-060 implements the shared React/TypeScript role-aware web surface under
`apps/web`, with Operations, Strategy, Customer, Merchant, and Courier routes,
typed deterministic demo data, independent Java/Python health probes, accessible
responsive controls, a schematic dispatch map, lifecycle timeline, and Playwright
desktop/mobile/axe smoke gates. The surface explicitly labels demo state and does
not own durable business state. Evidence is in
`evidence/gates/RM-060/2026-08-22-role-aware-web.md`.
The RM-060 checkpoint commit `9eaada1` passed all four GitHub Actions jobs in run
`32548856880`.

RM-080 adds bounded request/trace context, structured completion logs, request
count/latency metrics, health/SLI documentation, a Java Micrometer registry-backed
`/metrics` endpoint, Python Prometheus metrics, and deterministic failure injection
for travel-provider and Redis projection degradation. A fixed 100-request local
bounded-burst smoke is included. Local full gate passed with Java 34 tests and
Python 36 tests at 98.07% coverage. Evidence is in
`evidence/gates/RM-080/2026-08-22-observability-resilience.md`.
The RM-080 checkpoint commit `c1913f3` passed all five GitHub Actions jobs in
run `32552399489`, including the focused resilience job.

RM-090 defines and implements the Python research boundary for RouteBench and
lineage. `BenchmarkManifest` records code/scenario/seed/load/city/failure,
configuration, runtime, hardware, and dataset provenance. `RouteBenchRunner`
compares registered strategies through fresh Digital Twin kernels and emits
deterministic replay/output digests plus observed runtime. `ResearchLineage`
stores typed hypothesis, observation, result, and conclusion nodes with parent
links, canonical payloads, and manifest/hypothesis queries. Local full gate
passed with 40 Python tests at 97.75% coverage and Java/Web/control regression.
Evidence is in `evidence/gates/RM-090/2026-08-22-routebench-lineage.md`.
The RM-090 checkpoint commit `a32802d` passed all five GitHub Actions jobs in
run `32553160352`.

RM-070 defines and implements a bounded Python Agent Runtime and Orchestrator.
Read/research tool permissions, role grants, argument keys, metadata, and
per-session call counts are bounded and validated. Immutable audit records
capture accepted, rejected, and failed calls. Orchestration emits deterministic
fallbacks for missing plans, denied tools, handler failures, and call-budget
exhaustion, while the existing dispatch registry remains independent of agent
availability. Local full gate passed with 45 Python tests at 96.47% coverage,
Java 34 tests, and Web/control regression. Evidence is in
`evidence/gates/RM-070/2026-08-22-agent-runtime.md`.
The RM-070 checkpoint commit `3b1c5b2` passed all five GitHub Actions jobs in
run `32553873639`.

RM-091 implements the deterministic RADS research baseline. Immutable risk
signals and encoded states feed a decomposed distance/risk objective with stable
tie-breaking and explicit explanations. `RadsExperimentRunner` compares RADS
with registered baselines and records full, distance-only, and risk-only
ablations across explicit risk multipliers with stable manifest and output
digests. The reduced experiment shows the registered distance baselines choosing
the near/high-risk courier while full/risk-only RADS chooses the farther/low-risk
courier. Local full gate passed with 50 Python tests at 95.47% coverage, Java 34
tests, and Web/control regression. Evidence is in
`evidence/gates/RM-091/2026-08-22-rads-baseline.md`.
The RM-091 checkpoint commit `50e666d` passed all five GitHub Actions jobs in
run `32554498417`.

RM-081 implements isolated strategy Shadow Mode and a deterministic regression
gate. The active strategy is evaluated first and remains authoritative; candidate
exceptions become bounded failures and never mutate business state. Immutable
observations record both outcomes, metrics, and digests while excluding wall
clock latency from reproducibility hashes. Explicit sample, candidate failure,
assignment-rate drop, and disagreement thresholds produce `promote` or `hold`
with stable reason codes. Local full gate passed with 56 Python tests at 96.05%
coverage, Java 34 tests, and Web/control regression. Evidence is in
`evidence/gates/RM-081/2026-08-22-shadow-regression.md`.
The RM-081 checkpoint commit `8b92bf0` passed all five GitHub Actions jobs in
run `32555440040`.

RM-082 adds a local static security and supply-chain hygiene gate. It scans only
Git-tracked files for private keys, high-confidence provider tokens,
non-placeholder secret assignments, and sensitive artifacts; checks Python/npm
lock metadata, workflow least-privilege permissions, and Compose image/loopback
hygiene; and runs three standard-library self-tests from `verify.ps1`. Local
full gate passed with Java 34 tests, Python 56 tests at 96.05% coverage, Web
regression, and security checks. Evidence is in
`evidence/gates/RM-082/2026-08-22-security-supply-chain.md`.
The RM-082 checkpoint commit `5498fee` passed all five GitHub Actions jobs in
run `32556047734`.

RM-083 defines immutable PostgreSQL/RabbitMQ/Redis recovery artifacts with
relative paths, SHA-256, byte size, source revision, and contiguous restore order.
The local rehearsal validator verifies fixture package integrity and reports
bounded ready/blocked reasons; rollback metadata is reproducible and requires
explicit acknowledgement without executing a state change. Local full gate
passed with Java 34 tests, Python 56 tests at 96.05% coverage, Web regression,
security checks, and four recovery-contract self-tests. Live service restore is
explicitly not claimed and remains deferred_external. Evidence is in
`evidence/gates/RM-083/2026-08-22-recovery-contract.md`.
The RM-083 checkpoint commit `4b47d4e` passed all five GitHub Actions jobs in
run `32556590018`.
The RM-083 CI evidence commit `ac4723c` passed all five GitHub Actions jobs in
run `32556661332`.

RM-084 defines immutable release artifact provenance and a canonical release
manifest covering source revision, contracts, migrations, health checks, and a
content-addressed rollback package. Its read-only preflight reports stable
blocker codes for mutable or incomplete inputs and unsafe/missing repository
files. Local full gate passed with Java 34 tests, Python 56 tests at 96.05%
coverage, Web checks/build, security/recovery/release self-tests, and schema
fixtures. Evidence is in
`evidence/gates/RM-084/2026-08-22-release-preflight.md`.
The implementation checkpoint is `ada92bc`; the CI evidence checkpoint is
`5459b50`, and GitHub Actions run `32557262937` passed all five jobs.

RM-085 design defines immutable ordered cohorts, integer basis-point thresholds,
and deterministic `promote`/`hold`/`rollback` precedence. Rollback wins on
unhealthy required checks, breached safety limits, or unavailable rollback
readiness; promotion cannot skip the next declared stage. The contract is
read-only and leaves traffic shifting, live monitoring, and production restore
external. Design is in
`docs/design/p8-staged-release-decision-contract.md`; the task graph now marks
RM-085 `in_progress`.
The implementation checkpoint `4367caf` adds deterministic evaluation and five
self-tests; local full gate passed. Evidence is in
`evidence/gates/RM-085/2026-08-22-staged-release.md`. The task remains
`passed` after Actions run `32558073285` passed all five jobs.

Tests Run: Stage 0 gates passed. RM-001 passed Compose validation, real health,
PostgreSQL SQL, RabbitMQ diagnostics, Redis authenticated ping, loopback binding,
cross-`down/up` persistence for all three services, and the unified infrastructure
gate. RM-002 passed seven unit, architecture, HTTP, and migration tests; a live
PostgreSQL 18.6 run returned health `UP`, system identity `business-api/java/v1`,
and Flyway history `1:true`. RouteMind processes and containers were stopped.
RM-003 passed Ruff, format, strict mypy, 16 tests with 100% statement/branch
coverage, locked synchronization, and a live Uvicorn HTTP probe. The Python
process was stopped cleanly.
RM-004 validated four schemas and twelve fixtures, including UUID/date-time
formats, dispatch invariants, and stable event/correlation/causation/trace fields.
RM-005 passed all three jobs in GitHub Actions run 32496271644. The first run
caught Windows-specific Java wrapper paths; commit `de5e608` made JDK and wrapper
discovery portable, after which control, Java, and Python/contract jobs passed.
RM-010 passed 18 Java tests, architecture checks, Flyway V2/Hibernate validation
on PostgreSQL 18.6, health `UP`, role-scoped uniqueness, and audit-order checks.
RM-011 passed 22 Java tests, explicit happy/forbidden/repeated/stale command
coverage, Flyway V3/Hibernate validation on PostgreSQL 18.6, and persisted
transition audit rows.
The RM-011 commit `9872d76` passed all three GitHub Actions jobs in run
`32498473119`.
RM-020 passed 27 Java tests, full available gates, Flyway V4/Hibernate
validation on PostgreSQL 18.6, RabbitMQ health via the Compose-mapped port, and
transactional order-to-Outbox persistence.
RM-021 passed 30 Java tests, full available gates, Flyway V5/Hibernate
validation on PostgreSQL 18.6, duplicate suppression, and persisted
`DEAD_LETTER` attempt/error evidence.
RM-022 passed 33 Java tests, full available gates, Flyway V6/Hibernate
validation on PostgreSQL 18.6, authenticated Redis GEOSEARCH, durable courier
location persistence, and degradation behavior when the projection is unavailable.
RM-030 passed the full compute gate: 23 Python tests, strict mypy, Ruff, all
contract fixtures, and 100% statement/branch coverage. The nearest baseline
selects by `(distance_km, courier_id)` and the registry records solve latency,
strategy version, candidate count, and assignment status.
RM-031 passed the full available gate with 26 Python tests and 96.43% total
statement/branch coverage. Weighted-greedy and Hungarian results share the
versioned registry contract; a smoke benchmark records strategy, version,
latency, selected courier, and provenance.
The RM-031 commit `bf44e12` passed all three GitHub Actions jobs in run
`32503389125`.
The RM-030 commit `2a9b3de` passed all three GitHub Actions jobs in run
`32502960806`.
RM-040 passed the full available gate with 29 Python tests and 97.24% total
statement/branch coverage. Point/matrix estimates are deterministic and
primary provider failures or timeouts are marked as fallback results.
RM-050 passed the full available gate with 32 Python tests and 97.92% total
statement/branch coverage. Repeated runs with the same manifest and seed are
byte-identical; changed seed or inputs produce a different replay digest.
The RM-050 commit `595a221` and follow-up baseline coverage commits `ccce5fa`
and `53ab288` passed all three GitHub Actions jobs in run `32505121861`.
The RM-040 commit `cf71191` passed all three GitHub Actions jobs in run
`32504045099`.

Known Failures: Global `JAVA_HOME` points to JDK 8 while the active `PATH` JDK is
17. Repository Java commands deliberately resolve and validate the active JDK.
Maven is not installed globally; use the repository wrapper script.
The first Python dependency sync took several minutes because uv's cache and the
workspace are on filesystems that do not support hardlinks. The script now fixes
copy mode; subsequent frozen syncs are incremental.

Known Blockers: NONE

Important Context: Keep Java business correctness separate from Python compute and
research. Do not store large datasets or runtime databases in Git. The configured
data boundary is `F:\Projects\RouteMind-Data` on this workstation.

RM-086 implementation checkpoint `45850cd` adds the framework-independent Java
policy, five unit tests, and local full-gate evidence. The task remains
`passed` after Actions run `32558622055` passed all five jobs.

Next Recommended Action: Commit and push the Round 2 gap audit and expanded
task graph, observe planning CI, then implement RM-100's explicit LIVE/DEMO/
REPLAY adapter and minimal Java/Python read contracts.
The RM-088 design now binds release/staged/auth/rate digests, requires
fail-closed immutable edge references for apply/rollback, and keeps local
preflight/plan read-only. Design is in
`docs/design/p8-deployment-edge-security-adapter.md`. The implementation adds
the pure Java `DeploymentEdgeAdapter`, immutable request/capability/decision
records, stable operation digests, and five focused tests. Local Java (49 tests)
and repository gates pass; implementation evidence is in
`evidence/gates/RM-088/2026-08-22-deployment-edge-security.md`.
GitHub Actions run `32559680696` passed all five jobs.

The RM-087 design now defines immutable limits, normalized descriptors, reject
versus throttle precedence, deterministic retry-after, and the explicit
non-claim that distributed counters and WAF remain external. Design is in
`docs/design/p8-rate-limit-input-protection.md`.

The implementation checkpoint `24831c0` adds the Java evaluator and five unit
tests; local full gate passed. Evidence is in
`evidence/gates/RM-087/2026-08-22-rate-limit-input.md`. The task is now
`passed` after Actions run `32559165335` passed all five jobs.

Round 2 gap audit: `docs/reviews/ROUND_2_GAP_AUDIT.md`.
Round 2 foundation design:
`docs/superpowers/specs/2026-08-22-round2-live-product-foundation-design.md`.
The graph now contains 48 Round 2 tasks (RM-100 through RM-190); Round 1 tasks
remain passed, RM-106 is CI-validated, and RM-107 is the current active task.

Next Candidate Task: implement RM-110 operations command-center data projection.

Relevant Files: `TASK_GRAPH.yaml`, `MASTER_ARCHITECTURE.md`, `compose.yaml`,
`scripts/full-gate.ps1`, `scripts/business-api.ps1`,
`scripts/compute-api.ps1`, `services/business-api/README.md`,
`services/compute-api/README.md`, `contracts/README.md`,
`docs/runbooks/local-development.md`

Do Not Do: Do not collapse the dual runtime, treat Redis as durable truth, bypass
Outbox/Inbox reliability, put large data in Git, or mark tasks passed without gates.

RM-100 implementation checkpoint `8b70f9e` passed local gates and all five jobs
in Actions run `32561918020`; evidence is in
`evidence/gates/RM-100/2026-08-22-live-product-foundation.md`. RM-101 checkpoint
`3237144` added the Java v1 operations read response with explicit
merchant/courier projections and bounded health summary. Local gates and all
five Actions jobs in run `32562416957` passed; evidence is in
`evidence/gates/RM-101/operations-read-api.md`. RM-102 is implemented and
CI-validated with durable command idempotency, role-aware lifecycle validation,
expected-version conflicts, and transactional Outbox commands. Checkpoint
`ad988bc` and Actions run `32563322826` passed all five jobs; evidence is in
`evidence/gates/RM-102/order-command-api.md`. Continue with RM-103.
RM-103 adds bounded candidate validation, versioned strategy decisions, travel
provider metadata, and explicit 503 strategy/travel failure responses. Local
full gate passed; evidence is in `evidence/gates/RM-103/dispatch-api.md`.
Checkpoint `7506a5d` and Actions run `32563779670` passed all five jobs.
Continue with RM-104. The web source boundary has local evidence in
`evidence/gates/RM-104/web-live-data-source.md`; push and observe CI, then
continue with RM-105.
RM-105 defines the v1 event-stream item schema, monotonic decimal cursor,
exclusive `Last-Event-ID` reconnect, replay provenance, stale-state semantics,
and supported event types. Local contract evidence is in
`evidence/gates/RM-105/realtime-contract.md`; checkpoint `3c218e5` and Actions
run `32564387503` passed all five jobs. Continue with RM-106.
RM-106 adds a bounded read-only Java SSE projection over durable Outbox events,
exclusive decimal reconnect cursors, explicit stale conflicts, and bounded
subscriber-loss logging. Local full gate passed with 57 Java tests, 59 Python
tests at 96.13% coverage, 5 schemas/15 fixtures, and 9 Web unit tests plus build.
Evidence is in `evidence/gates/RM-106/java-sse.md`; checkpoint `21beadc` and
Actions run `32565242420` passed all five jobs. RM-107 evidence is in
`evidence/gates/RM-107/web-realtime.md`; checkpoint `48ef6fa` and Actions run
`32565914443` passed all five jobs. Continue with RM-108.
RM-108 adds the verified live activity projection with cursor, trace, freshness,
and explicit Demo/Replay labels. Local full gate passed with 15 Web unit tests,
16 Playwright tests, Java 57 tests, Python 59 tests at 96.13% coverage, and
5 schemas/15 fixtures. Checkpoint `4181f3c` and Actions run `32566340978` passed
all five jobs. Continue with RM-110.
RM-110 adds explicit operations projection loading/degraded/unavailable states,
source and freshness metadata, projection health, exception visibility, and
route-geometry fallback handling. Local full gate passed with 17 Web unit tests,
16 Playwright tests, Java 57 tests, Python 59 tests at 96.13% coverage, and
5 schemas/15 fixtures. Checkpoint `4b4ab79` and Actions run `32567110886` passed
all five jobs. RM-110 is now passed; continue with RM-111.
RM-111 defines the provider-neutral geospatial map contract and deterministic
local schematic fallback. It validates WGS84 coordinates and bounds, carries
markers/routes/zones/selection and freshness, and makes tile/routing capability
explicit without paid credentials. Local full gate passed with 21 Web unit
tests, 16 Playwright tests, Java 57 tests, Python 59 tests at 96.13% coverage,
and 5 schemas/15 fixtures. Checkpoint `d73be4f` and Actions run `32567620315`
passed all five jobs. RM-111 is now passed; continue with RM-112.
RM-112 connects the provider-neutral adapter to the operations map. Explicit tile
templates render a provider layer and attribution; no template keeps the local
schematic fallback visibly labeled and routing remains not configured. Local full
gate passed with 22 Web unit tests, 16 Playwright tests, Java 57 tests, Python 59
tests at 96.13% coverage, and 5 schemas/15 fixtures. Checkpoint is awaiting
Actions validation. Checkpoint `e199a9a` and Actions run `32568087013` passed all
five jobs. RM-112 is now passed; continue with RM-113.
RM-113 adds functional zone/lifecycle/exception/freshness filters and order/courier
detail panels. Local full gate passed with 23 Web unit tests, 16 Playwright tests,
Java 57 tests, Python 59 tests at 96.13% coverage, and 5 schemas/15 fixtures.
Checkpoint is awaiting Actions validation. Checkpoint `549fb87` and Actions run
`32568470723` passed all five jobs. RM-113 is now passed; continue with RM-114.
RM-114 adds a recorded exception queue with order-linked inspection, snapshot-derived
supply/demand imbalance, and an explicit unavailable overtime-risk state. Local full
gate passed with 24 Web unit tests, 16 Playwright tests, Java 57 tests, Python 59
tests at 96.13% coverage, and 5 schemas/15 fixtures. Checkpoint is awaiting Actions
validation.
Checkpoint `550f2a2` and Actions run `32568845070` passed all five jobs. RM-114 is
now passed; continue with RM-120.
RM-120 connects the customer role to the Java-owned durable order command path,
including idempotency, validation/conflict/timeout states, trace metadata, and
explicit demo/replay write protection. Realtime `order.created` events now add
orders to an empty live projection and forward lifecycle events retain versions.
Local full gate passed with Java 57 tests, Python 59 tests at 96.13% coverage,
Web 29 unit tests and build, 16 Playwright tests, and 5 schemas/15 fixtures.
Checkpoint `fbecdd0` and Actions run `32569640180` passed all five jobs. RM-120 is
now passed; RM-121 checkpoint `b4e1694` and Actions run `32572069719` also passed
all five jobs. RM-121 full gate evidence is recorded at
`evidence/gates/RM-121/merchant-workflow.md`.
RM-121 adds Java-owned merchant preparation states, validated actor permissions,
durable Flyway status expansion, transition persistence repair, and a merchant UI
that drives accept, start preparation, and mark ready commands with idempotency,
expected versions, traces, and explicit degradation. Local full gate passed with
Java 59 tests, Python 59 tests at 96.13% coverage, Web 31 unit tests/build, 16
Playwright tests, and 5 schemas/15 fixtures. RM-122 courier shift and delivery
workflow passed local and remote validation in Actions run `32573723273` (all five
jobs green).
RM-122 adds durable courier shift state, courier location commands with idempotent
outbox events, optional `ACCEPTED` and `ARRIVED` order audit states, courier order
commands through delivery completion, and explicit live/degraded projection state.
Local full gate passed with Java 60 tests, Python 59 tests at 96.13% coverage, Web
34 unit tests/build, 16 Playwright tests, and 5 schemas/15 fixtures. Evidence is
recorded at `evidence/gates/RM-122/courier-workflow.md`; remote Actions run
`32573723273` passed all five jobs. RM-123 role command error/degradation handling
passed local and remote validation in Actions run `32574390001` (all five jobs
green).
RM-123 role command adapters classify failures as conflict, validation, timeout, or
unavailable while preserving the original idempotency key and trace context; live
degraded snapshots disable writes with an explicit reason. Local full gate passed
with Java 60 tests, Python 59 tests at 96.13% coverage, Web 36 unit tests/build, 16
Playwright tests, and 5 schemas/15 fixtures. Evidence is recorded at
`evidence/gates/RM-123/role-degraded-states.md`; remote Actions run `32574390001`
passed all five jobs.
RM-124 adds a keyboard-dismissible mobile navigation drawer, 44px role links,
responsive courier/customer/merchant action layouts, and mobile browser/axe
coverage. Local full gate passed with Java 60 tests, Python 59 tests at 96.13%
coverage, Web 38 unit tests/build, 17 Playwright passes plus one desktop-only skip,
and 5 schemas/15 fixtures. Evidence is recorded at
`evidence/gates/RM-124/mobile-workflows.md`; remote Actions run `32575052384`
passed all five jobs. RM-130 constraint-aware dispatch model is now locally complete.
RM-130 adds optional capacity, current load, courier state, availability bounds,
service risk, estimated travel, pickup readiness, service duration, delivery time
windows, and a maximum risk threshold to the compute-owned DispatchProblem. All
registered baseline strategies use the shared eligibility boundary and return
stable infeasibility reasons; the API exposes eligible counts and reason metadata.
Local full gate passed with Java 60 tests, Python 65 tests at 96.47% coverage, Web
38 unit tests/build, and 5 schemas/15 fixtures. Evidence is recorded at
`evidence/gates/RM-130/constraint-dispatch-model.md`; Actions run `32575824899`
passed all five jobs. RM-131 capacity, preparation, and risk-aware scoring is now
the active task.
RM-131 registers the versioned `risk-aware` strategy with deterministic weights for
distance, pickup readiness, overtime risk, service risk, and courier load balance.
The same constrained fixtures remain available to nearest, weighted-greedy,
Hungarian, and risk-aware strategies; rationale and weight metadata are recorded
in each decision. Local full gate passed with Java 60 tests, Python 69 tests at
96.57% coverage, Web 38 unit tests/build, and 5 schemas/15 fixtures. Evidence is
recorded at `evidence/gates/RM-131/risk-aware-scoring.md`; remote Actions run
`32576213676` passed all five jobs. RM-132 minimum-cost flow and partitioned
assignment is now locally complete.
RM-132 adds a bounded successive-shortest-augmenting-path solver for rectangular
request/courier matrices, courier capacity, deterministic residual rematching, and
explicit unassigned reasons. `partitioned-assignment` reuses the solver per zone
without crossing courier partitions; single-order calls remain registry-compatible
and record assignment mode/count metadata. Local full gate passed with Java 60
tests, Python 74 tests at 96.03% coverage, Web 38 unit tests/build, and 5
schemas/15 fixtures. Evidence is recorded at
`evidence/gates/RM-132/flow-assignment.md`; remote Actions run `32576849657`
passed all five jobs. RM-132 is fully validated. RM-140 dynamic travel model
contract passed local/full validation and remote Actions run `32577433788` (all
five jobs green). Evidence is recorded at
`evidence/gates/RM-140/dynamic-travel.md`. RM-141 network and zone travel
provider is now the active task.
RM-141 network and zone travel provider is locally complete. The bounded
network fixture provides deterministic shortest paths, route geometry, edge and
zone metadata, matrix reuse, and explicit unavailable-route fallback. Local
full gate passed with Java 60 tests, Python 80 tests at 95.32% coverage, Web 38
unit tests/build, and 5 schemas/15 fixtures. Evidence is recorded at
`evidence/gates/RM-141/network-travel.md`; checkpoint is awaiting remote Actions
validation.
RM-141 remote Actions run `32577972174` passed all five jobs; the task is fully
validated. RM-142 data-root matrix and artifact adapter is now the active task.
RM-142 is locally complete: manifests carry canonical artifact metadata and
digests, the adapter resolves only inside `ROUTEMIND_DATA_ROOT`, and checksum or
path failures are explicit. Local full gate passed with Java 60 tests, Python
85 tests at 95.22% coverage, Web 38 unit tests/build, and 5 schemas/15
fixtures. Evidence is recorded at
`evidence/gates/RM-142/data-root-adapter.md`; checkpoint is awaiting remote
Actions validation.
RM-142 remote Actions run `32578382074` passed all five jobs; the task is fully
validated. RM-143 traffic and incident travel updates is now the active task.
RM-143 is locally complete: versioned simulated updates apply by effective time,
zone, edge, and incident, while context replay digests and provider metadata
remain deterministic. Local full gate passed with Java 60 tests, Python 89 tests
at 96.40% coverage, Web 38 unit tests/build, and 5 schemas/15 fixtures.
Evidence is recorded at `evidence/gates/RM-143/traffic-updates.md`; remote
Actions run `32579007370` passed all five jobs and the task is fully validated.
RM-150 continuous Digital Twin state kernel is now the active critical-path
task.
RM-150 is locally complete: `TwinClock` separates forward-only simulated time
from wall-clock observation, and the seeded scenario kernel records simulated
end tick without polluting replay digest. Local full gate passed with Java 60
tests, Python 90 tests at 96.37% coverage, Web 38 unit tests/build, and 5
schemas/15 fixtures. Evidence is recorded at
`evidence/gates/RM-150/continuous-twin.md`; remote Actions run `32579369219`
passed all five jobs and the task is fully validated. RM-151 continuous demand
arrival generator is now the active task.
RM-151 is locally complete: `DemandArrivalGenerator` uses explicit seeded
Bernoulli decisions per active tick, deterministic burst expansion and ordering,
profile metadata propagation, and a canonical replay digest. Local compute and
full gates pass with Java 60 tests, Python 92 tests at 96.34% coverage, Web 38
unit tests/build, and 5 schemas/15 fixtures. Evidence is recorded at
`evidence/gates/RM-151/demand-arrivals.md`; remote Actions run `32581545061`
passed all five jobs; RM-151 is fully validated. RM-153 dynamic merchant
preparation model is now the active task.
RM-153 is locally complete: `MerchantPreparationModel` schedules expected and
actual preparation on deterministic capacity slots, exposes queue load,
readiness and evolving late risk, and applies actual-ready state to dispatch.
Compute check passes 96 tests at 96.16% coverage; evidence is recorded at
`evidence/gates/RM-153/merchant-preparation.md`; full repository gate and
remote Actions run `32582291443` passed all five jobs. RM-153 is fully
validated. RM-154 traffic, supply, and failure perturbation modeling is now
the active task.
RM-154 is locally complete: `PerturbationScenario` emits bounded, windowed
traffic, supply, merchant-delay, and dependency-failure events, feeds traffic
into `DynamicTravelContext`, and separates simulated from live failure metrics.
Full local gate passes Java 60, Python 100 at 95.96%, Web 38 unit tests/build,
and 5 schemas/15 fixtures. Evidence is recorded at
`evidence/gates/RM-154/twin-perturbations.md`; remote Actions run
`32582936237` passed all five jobs. RM-154 is fully validated.

RM-155 remains blocked because RM-152 depends on RM-133. The next unblocked
critical task is RM-160, which exposes the compute-owned strategy registry and
bounded execution API while preserving versioned provenance and explicit
failure metadata.

RM-160 is fully validated. The compute catalog and bounded execution API are
covered by 104 Python tests at 95.78%, full local gates, browser smoke (17
passed plus one desktop-only skip), and GitHub Actions run `32600128160` with
all five jobs green. The task graph now activates RM-161, which depends on
RM-160 and RM-090 and adds versioned strategy parameter schemas and experiment
provenance.

RM-161 is fully validated after remote Actions run `32600780985` passed all
five jobs. It adds bounded
versioned parameter schemas for weighted-greedy and risk-aware, preserves
generic RouteBench manifest metadata separately from strategy parameters, and
adds `POST /api/v1/experiments/routebench` backed by the existing seeded
RouteBench/ScenarioKernel. Compute check passes 109 tests at 95.39%; full
available gates pass Java 60, Web 38 unit/build, and 5 schemas/15 fixtures.
The task graph now activates RM-163; RM-162 remains blocked by RM-156.

RM-163 is fully validated after remote Actions run `32601227912` passed all
five jobs. The new shadow
evaluation endpoint exposes active/candidate comparisons, ordered observations,
assignment/disagreement/failure metrics, promote/hold reasons, manifest/run
digests, and `candidate_authority: none`, while preserving active-strategy
authority and bounded candidate failures. Compute check passes 111 tests at
95.41%; full available gates pass Java 60, Web 38 unit/build, and 5
schemas/15 fixtures. The task graph now activates RM-133, the VRP/VRPTW
strategy baseline; RM-155 remains dependency-blocked until RM-133 and RM-152
pass.

RM-133 is fully validated after remote Actions run `32602269612` passed all five
jobs. It adds the bounded deterministic
`VrptwRoutePlanner`, the `vrptw` registry strategy, explicit capacity/service/
time-window/availability checks, stable unassigned reason codes, and a
two-stop reproducible reference baseline. Compute check passes 119 tests at
95.57%; full available gates pass Java 60, Web 38 unit/build, and 5 schemas/15
fixtures. The task graph now activates RM-134 dynamic insertion; RM-152 is also
unblocked while RM-162 remains blocked by RM-156.

RM-134 is fully validated after remote Actions run `32602785200` passed all five
jobs. `VrptwRoutePlanner.insert` evaluates
all positions against the active route snapshot, returns an immutable proposed
route with incremental travel cost, and emits stable identity, capacity,
time-window, availability, and bounded-limit rejection codes. Compute check
passes 122 tests at 95.56%; full available gates pass Java 60, Web 38
unit/build, and 5 schemas/15 fixtures. Evidence is recorded at
`evidence/gates/RM-134/dynamic-insertion.md`. The task graph now activates
RM-135 dynamic replanning; RM-152 is also unblocked while RM-162 remains
blocked by RM-156.


RM-135 is fully validated after remote Actions run `32603303249` passed all
five jobs. `DynamicReplanningPolicy` covers arrival, lateness, incident,
courier-loss, and material-change triggers with deterministic improvement
gating, debounce/cooldown state, trace, and before/after metrics. Compute check
passes 131 tests at 95.66%; full available gates pass Java 60, Web 38
unit/build, and 5 schemas/15 fixtures. The task graph now activates RM-152
courier motion; RM-162 remains blocked by RM-156.


RM-152 local implementation is complete. `CourierMotionEngine` advances an
immutable route with the existing travel-provider abstraction, interpolates
locations in simulated time, emits stable route/arrival/pickup/delivery/
completion events, and returns idle/en-route/servicing/available state. The
snapshot includes a canonical replay digest and a Redis GEO-compatible
`(longitude, latitude, member)` projection; Redis remains rebuildable hot state.
Compute check passes 135 tests at 95.46%; full available gates pass Java 60,
Web 38 unit/build, and 5 schemas/15 fixtures. Evidence is recorded at
`evidence/gates/RM-152/courier-motion.md`. GitHub Actions run `32603896737`
passed all five jobs, including browser smoke;
RM-152 is fully validated and RM-155 is now active.

RM-155 local implementation is complete. `TwinControlService` wraps the
existing `ScenarioKernel` in a bounded process-local control boundary and the
FastAPI adapters expose `/api/v1/twin/control` plus `/api/v1/twin/state`.
Commands cover start/pause/resume/step/reset/speed/scenario/seed/strategy,
advance only simulated time, and use recent `command_id` deduplication with
explicit 409 conflicts. State/events carry strategy version, simulated time,
generation, deterministic event IDs, and canonical replay digest. Compute check
passes 139 tests at 95.71%; full available gates pass Java 60, Web 38
unit/build, and 5 schemas/15 fixtures. Evidence is recorded at
`evidence/gates/RM-155/twin-control-api.md`. GitHub Actions run `32604701074`
passed all five jobs, including browser smoke; RM-155 is fully validated and
RM-156 is now active.

RM-156 local implementation is complete. The Operations surface now has a
distinct simulation data source backed by the Python Twin API, with scenario,
seed, speed, strategy, step, pause/resume, and reset controls. Existing map,
routes, lifecycle, metrics, exceptions, and health regions remain visible while
simulated time, seeded traffic/supply/demand metrics, replay digest, and recent
events are explicit. Web check passes 42 unit tests/build; browser smoke passes
19 tests with one existing desktop-only skip, including the new desktop/mobile
simulation control flow. Evidence is recorded at
`evidence/gates/RM-156/twin-ui.md`. GitHub Actions run `32605590683` passed all
five jobs, including browser smoke; RM-156 is fully validated and RM-157 is now
active.

RM-157 local implementation is complete. The replay source verifies a
canonical SHA-256 artifact before enabling playback, exposes scenario/seed/
provenance and explicit replay-vs-live labeling, and supports play, pause,
reset, seek, step, speed, and event detail inspection. Web check passes 43
unit tests/build; browser smoke passes 21 desktop/mobile tests with one
existing desktop-only skip; the full available gate passes Java 60, Python 139
at 95.71%, and 5 schemas/15 fixtures. Evidence is recorded at
`evidence/gates/RM-157/replay.md`. The implementation checkpoint is `c8d2ac2`.

RM-157 is fully validated after GitHub Actions run `32606493460` passed all five
jobs, including the Web static, unit, and browser smoke gates. The task graph
now records RM-157 passed (40/48 Round 2, 68/76 repository) and activates
RM-158 What-if scenario comparison.

RM-158 local implementation is complete. The compute-owned What-if runner and
`POST /api/v1/experiments/what-if` derive bounded demand, supply, preparation,
traffic, strategy, and risk variants from a recorded manifest and return
reproducible replay/manifest/output/comparison digests. The Strategy surface
exposes controls, baseline/variant metrics, loading/error/clear states, and
explicitly labels results as scenario comparisons rather than causal production
claims. Compute check passes 142 Python tests at 95.88%; Web check passes 47
unit tests/build; browser smoke passes 23 desktop/mobile tests with one
existing desktop-only skip; full available gates pass Java 60 and 5 schemas/15
fixtures. Evidence is recorded at `evidence/gates/RM-158/what-if.md`; the
implementation checkpoint is `90f85ea`.

RM-158 is fully validated after GitHub Actions run `32607641909` passed all five
jobs, including the Python compute and Web browser smoke gates. The task graph
now records RM-158 passed (41/48 Round 2, 69/76 repository) and activates
RM-162 strategy comparison visualizations; RM-160 and RM-161 are already passed.

RM-162 local implementation is complete. The Strategy Comparison panel uses a
bounded multi-variant What-if request and renders actual assignment rate,
simulated duration, observed compute runtime, and scenario-risk bars. It keeps
recorded-run, comparison, replay, manifest, and output digests visible, while
completion, overtime, distance, utilization, fairness, and cost are explicitly
shown as unavailable from the recorded run. Web check passes 49 tests/build;
browser smoke passes 23 desktop/mobile tests with one existing desktop-only
skip; full available gates pass Java 60, Python 142 at 95.88%, and 5 schemas/15
fixtures. Evidence is recorded at `evidence/gates/RM-162/strategy-comparison.md`;
the implementation checkpoint is `95901cd`.

RM-162 is fully validated after GitHub Actions run `32608343277` passed all five
jobs, including Python compute and Web browser smoke. The task graph now records
RM-162 passed (42/48 Round 2, 70/76 repository) and activates RM-136 advanced
dispatch integration and audit; RM-170 remains blocked by RM-136.

## Current Resume Capsule
- Resume at RM-230 Reliability Center surface. Preserve Java lifecycle
  authority, durable location sequence ordering, Redis-as-projection, and the
  explicit non-disciplinary anomaly boundary and honest ETA lineage boundary.
- RM-215 evidence is `evidence/gates/RM-215/reconciliation.md`; checkpoint
  `d26a121` and GitHub Actions run `32647766636` passed all five jobs.
- Round 2 remains 48/48, Hardening remains 10/10, and Enhancement is 19/27 with
  RM-230 active. Repository total is 105/113. RM-228 remains independently
  eligible, while RM-230 is the active reliability sequence.
- Human action required: NONE. Keep `.codex-tmp/` untouched and untracked.

RM-216 closure, RM-217 implementation, RM-218 notes, and RM-219 status: checkpoint `c98ea76` is
remote-green in Actions run `32649193769`, and RM-217 checkpoint `7234ff6` is
remote-green in Actions run `32650330974`. V15 adds bounded courier location
history; event sequence and ingestion metadata are propagated to operations
snapshots and Web realtime handling. RM-218 adds read-oriented integrity states
and privacy-bounded hotspots; checkpoint `a61b559` is remote-green in Actions
run `32651238530`. RM-219 checkpoint `8fab1a6` is remote-green in Actions run
`32651955908`; it implements a deterministic five-component ETA baseline with
explicit unavailable inputs and outcome lineage. RM-220 local evidence is 201
Python tests at 95.23%, full available gate green, and explicit calibration-
confidence gating. RM-220 is fully validated in Actions run `32652719384`.
RM-221 is fully validated in Actions run `32653393681`; keep the waterfall
descriptive and reconcile observed duration without causal claims. RM-222 is
fully validated in Actions run `32654207318`. RM-223 is fully validated in
Actions run `32655392123`; evidence is recorded in
`evidence/gates/RM-223/city-zone-drilldown.md`. Continue autonomously with
RM-224. Its local evidence is recorded in
`evidence/gates/RM-224/arc-flow.md`; preserve order-route lineage and explicit
empty/stale/unavailable states. RM-225 is fully validated in Actions run
`32657006258`; evidence is recorded in `evidence/gates/RM-225/geo-layers.md`.
RM-226 is closed in checkpoint `470d67f` with evidence in
`evidence/gates/RM-226/decision-xray.md` and Actions run `32658324255`.
RM-227 is closed in checkpoint `c63d336` with evidence in
`evidence/gates/RM-227/strategy-analytics.md` and Actions run `32659202824`.
RM-233 is closed in checkpoint `b5174d8` with evidence in
`evidence/gates/RM-233/reference-data-versioning.md` and Actions run
`32659704665`.
Continue autonomously with RM-230.

## Current Research Resume Capsule
- Workstream: B - Statistical RouteBench.
- Current task: R3-321 common-random-number stream ownership.
- Engineering Gate: E-IN-PROGRESS.
- Experiment Gate: X-NOT-REQUIRED.
- Statistical Gate: S-NOT-APPLICABLE.
- Claim Gate: C-NOT-APPLICABLE.
- R3-311 evidence: `evidence/gates/R3-311/solomon-vrptw.md`; compact result
  `docs/research/r3/results/solomon/solomon-stratified-six-results-v1.json`.
- R3-311 CI: preregistration run `32697011223`, implementation run
  `32699067563`, and closure run `32699784206` passed all five jobs.
- R3-311 result: campaign `r3-311-20260824T065444Z-8a0a4ea5c098` retained all
  six; 4 verified complete incumbents, 2 no-incumbent timeouts, Wilson 95%
  `[0.299993, 0.903229]`, final `E-PASS/X-PASS/S-FAIL/C-NO-CLAIM`.
- R3-315 evidence: `evidence/gates/R3-315/exact-cross-check.md`; compact result
  `docs/research/r3/results/exact-cross-check/solomon-prefix-eight-exact-results-v1.json`.
- R3-315 CI/results: preregistration run `32700423191` and implementation run
  `32701927556` passed all five jobs. Campaign
  `r3-315-20260824T073439Z-1bae0447b562` retained 6/6; complete enumeration,
  CP-SAT `OPTIMAL`, independent verification, and 0% transformed candidate gaps
  held for all six. Proof scope is the derived conservative model only.
- R3-312 protocol: replicate `_1` for all six structural families at each of
  200/400/600/800/1000 customers, 30 total; five seconds, one thread, one
  isolated process each. Archive/member hashes are frozen under the external
  data root, and questioned/marked SINTEF references cannot receive scalar gaps.
  Manifest SHA-256 is
  `6c35a47e03d53a71f32240953fe1a088412637b893cb6d5a25a924a7bef9a2d2`.
- R3-312 implementation revision `eac087e` passed all five jobs in Actions run
  `32706450863`. Campaign `r3-312-20260824T083216Z-eac087e32790` then retained
  all 30 results: 29 verified complete incumbents and one no-incumbent timeout.
  The 200 scale was 5/6 and larger scales were each 6/6 under the frozen policy.
- Every R3-312 incumbent used more vehicles than its retained reference; there
  were no same-vehicle scalar distance gaps. External audit verified 31 JSON
  files plus 31 sidecars with zero errors. Compact result is
  `docs/research/r3/results/gehring-homberger/scale-first-replicates-results-v1.json`
  with SHA-256 `45ad7967cac4985d869663b6f5208e03c26e18995d33b6903535d8b627460daf`.
- R3-312 is `E-PASS/X-PASS/S-NOT-APPLICABLE/C-NO-CLAIM`. R3-316 now owns the
  frozen all-outcome protocol for median, p90, best, worst, timeout, infeasible,
  and reference-comparability results across R3-311, R3-312, and the scoped
  transformed-model R3-315 evidence.
- R3-312 closure revision `4f678fd` passed all five jobs in Actions run
  `32707794770`.
- R3-316 manifest `r3-316-bks-gap-analysis-v1` is frozen with SHA-256
  `6c6332896dff30e878f77a161e576b88b42422cc2e2a617c1fa4f43f9ca6f77b`.
  It binds all 42 upstream records and keeps 36 source-BKS results separate from
  six derived exact results. Vehicle gap, conditional same-vehicle distance gap,
  and transformed exact gap use separate Type-7 distributions; all outcome rates
  retain failures and no-incumbent results.
- The R3-316 freeze is explicitly post-inspection, not blinded preregistration.
  Direct run `32708520338` was concurrency-cancelled; descendant `d86c41e`
  contains the unchanged freeze and passed all five jobs in run `32708578105`.
- R3-316 implementation revision `9f68e99` passed all five jobs in Actions run
  `32710816931`. Campaign `r3-316-20260824T092121Z-9f68e9902a9b` then retained
  all 42 records with zero exclusions/errors: 32 timeout-with-feasible, three
  timeout-no-feasible, and one feasible incumbent among 36 source results.
- Approved source vehicle gaps had `n=27`, median `31.6667%`, p90 `349.4545%`,
  and max `484.2105%`; conditional same-vehicle distance gaps had `n=4`, median
  `2.6745%`, p90 `8.8185%`, and max `10.3053%`. Six scoped transformed exact
  gaps were all `0%`; the domains were never pooled.
- Independent audit verified the immutable result SHA-256
  `6e5571fcba1fd7069e4eb6604fff3f70533495fe1970fb2b5c0df257514eefb1`,
  all inputs, exact artifacts, identities, formulas, and Type-7 summaries.
  Compact result is
  `docs/research/r3/results/gap-analysis/bks-gap-analysis-results-v1.json`.
- R3-316 is `E-PASS/X-PASS/S-PASS/C-NO-CLAIM`; no source optimality,
  superiority, or population claim is authorized.
- R3-316 closure revision `c0967c1` passed all five jobs in Actions run
  `32711507127`.
- R3-320 protocol `r3-320-statistical-routebench-v1` is locally frozen against
  that closure before any R3-B campaign data. It binds `risk-aware@1.0.0` versus
  `weighted-greedy@1.0.0`, an independent per-request risk formula, assignment
  margin `-0.02`, eight numeric stress regimes, four CRN streams, disjoint pilot
  and confirmatory seeds, prospective power bounds, a 16-test Holm family,
  mandatory safety diagnostics, exclusions/stopping, lineage, and zero cost.
- Strict loader and directed mutation tests must pass locally and remotely.
  Material R3-325 data remain prohibited until R3-321/322/323/324 and the R3-325
  implementation checkpoint pass. After remote R3-320 validation, close it and
  activate R3-321 immediately.
- R3-320 manifest is 9,737 bytes with SHA-256
  `a6dae9d55641ff7966ef4a50cc00a63da3e936620c3c48f23cd2c2ce039375b5`.
  Local full gates pass: Java 80/80, Python 544/544 at 95.76% (protocol loader
  97.46% across 51 directed tests), Web 92/92 plus build, 6 schemas / 18
  fixtures, determinism, analytics, semantic metrics, Ruff, and mypy.
- R3-320 freeze revision `8c592d4` passed all five jobs in Actions run
  `32713127743` and closes `E-PASS/X-NOT-REQUIRED/S-NOT-APPLICABLE/
  C-NOT-APPLICABLE`. R3-321 is active; implement the exact frozen SHA-256 seed
  derivation and prove stable demand/merchant/courier/traffic digests without
  claiming independent observations.
- Concurrent state: `465488f` implements the separate spatial-lock-in
  negative-control diagnostic. Preserve subsequent `research/level4/spatial_lockin/`
  changes and do not claim them as Round 3 task work.
- Human action required: NONE. Keep `.codex-tmp/` untouched and untracked.
