# RouteMind Product Readiness Audit

Campaign: Product & Demo Readiness
Audit revision: 2026-08-30 / `9e6a0ffed87b5e0d7987edd33c48999b949c7539`
Scope: local product operation, observable runtime behavior, and truthful demo UX.

This is a separate product campaign. It does not change Round 1-4 task counts,
frozen scientific results, Human Gates, external contracts, or production claims.
R4-422 remains frozen at `LIVE_VALIDATED / PROVIDER_ACCEPTED /
DELIVERY_OBSERVED / NO_PRODUCTION_CLAIM`.

## Audit Verdict

RouteMind is a substantial, truthful offline product surface with strong domain,
dispatch, Digital Twin, replay, decision-provenance, reliability, and accessibility
foundations. The demo source is understandable and visually coherent. The live
product path is not yet a one-command local product: infrastructure startup can
hang when Docker is unavailable or unresponsive, Java and Python are launched by
separate commands, database migration is implicit in Java startup, and there is no
single lifecycle command that verifies prerequisites, starts all runtimes, waits
for readiness, loads a deterministic scenario, prints endpoints, and cleans up.

The most important product gap is integration rather than missing algorithms. The
frontend composes a Java snapshot and a Python dispatch snapshot, but the live
snapshot does not attach durable decision-ledger records, route/travel metadata,
merchant preparation details, queue depth, RabbitMQ state, Redis GEO status, or
notification/incident state. Those capabilities exist in backend code or tests but
are difficult to discover from the primary live surface. Demo and replay correctly
label fixture state and keep writes disabled.

## Evidence Collected

| Area | Evidence | Observation |
| --- | --- | --- |
| Repository | `git status`, `resume.ps1` at this revision | `main` equals `origin/main`; only pre-existing untracked `.codex-tmp/`; 167/197 Round 4 graph tasks passed; no eligible Round 4 task. |
| Prerequisites | `scripts/doctor.ps1` | Git, Python 3.14.6, Java, Node, Docker, Compose, and `RouteMind-Data` detected. |
| Compose | `docker compose config --quiet` | Configuration parses successfully. |
| Infrastructure runtime | `scripts/infra.ps1 up` and `docker compose ps` | Both commands failed to return within the bounded observation window; no health summary was produced. Docker Desktop responsiveness is therefore unverified and is a P0 startup blocker on this machine. No volumes were removed. |
| Python runtime | `scripts/compute-api.ps1 run`, `GET /healthz` startup observation | Python starts independently on `127.0.0.1:18081` and shuts down cleanly on Ctrl+C. Dependency readiness is not part of this process because the compute runtime is stateless. |
| Java runtime | `scripts/business-api.ps1 test-offline` | Maven wrapper resolves repository JDK 17 correctly; full test process was still running at the end of the bounded observation window. Live readiness was not established without infrastructure. |
| Web runtime | `npm run dev -- --host 127.0.0.1` | Vite starts independently at `http://127.0.0.1:4173/`. |
| Web live mode | Browser inspection of `/operations` | No verified OIDC session fails closed with `Identity unavailable`; operations are not shown as live. This is truthful but not demo-friendly without an explicit local session/fixture path. |
| Web demo mode | Browser inspection after selecting Demo | Operations board, map, lifecycle, dispatch activity, decision X-Ray, reliability, geo layers, flow, city/zone, Digital Twin, and role navigation render with explicit `DEMO`/fixture labels. |
| Web test gate | `npm run check` | Formatting/lint/typecheck passed; Vitest executed 96 tests but reported 3 worker startup timeouts/unhandled errors. The command is not a clean local pass under current parallel worker pressure. |
| Compute gate | `scripts/compute-api.ps1 check` | Ruff, formatting, and mypy stages passed before the long pytest phase; no failure was observed in the bounded output. |
| Browser UX | Existing Playwright suite and live browser DOM/screenshot | Desktop layout is dense and operationally oriented; mobile focus/recovery and accessibility are covered by existing tests. |

## Capability Gap Matrix

Legend: Exists is verified in implementation; Works locally means a bounded local
run or executable test; User-visible describes the primary product surface;
E2E integrated means the path is connected across authoritative runtime boundaries;
Reliable reflects explicit retry/degraded/recovery behavior; UX quality is the
current audit judgment. `LIVE`, `SIMULATED`, `REPLAY`, `MOCK`, and `DEGRADED` remain
distinct labels in the UI.

| Capability | Exists | Works locally | User-visible | E2E integrated | Reliable | UX quality | Priority | Required action |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Local infrastructure (PostgreSQL/RabbitMQ/Redis) | Yes | Blocked by Docker hang | Partial health badges | No single lifecycle path | Compose healthchecks exist; operator timeout is weak | P1 | P0 | Add bounded, diagnostic `dev-up`/`dev-down` lifecycle and daemon failure guidance. |
| Java business runtime and migrations | Yes | Unit/build evidence; live blocked by infra | Health badge and live source | Partial | Graceful shutdown and Flyway exist | P1 | P0 | Orchestrate startup after dependency readiness and surface migration errors. |
| Python compute runtime | Yes | Health endpoint starts independently | Dispatch/strategy panels when data is supplied | Partial | Bounded API errors and fallback metadata | P1 | P1 | Include in shared lifecycle and readiness summary. |
| Frontend dev server | Yes | Yes | Yes | No backend-backed default | N/A | Good | P1 | Make one documented command print its endpoint and source mode. |
| Order lifecycle | Yes | Golden E2E script and demo fixture | Lifecycle timeline, role surfaces | Real Java path exists; live frontend only maps one current status | Idempotency/conflict tests exist | Good in demo, thin live | P1 | Attach full event history or an explicit “current status only” indicator to live reads. |
| Customer/merchant/courier state | Yes | Commands and demo fixture | Role pages and operations cards | Live parties are flattened; merchant prep/queue not mapped | Degraded/write-disabled states exist | Good demo, incomplete live | P1 | Expand live projection contract for role-relevant state. |
| Courier location/GEO | Yes | Java + Redis degradation E2E evidence | Map markers and location freshness | Live snapshot includes location, not GEO health/history | Sequence/stale handling exists | Good | P1 | Show projection status, sequence, and stale age in live drawer. |
| Dispatch strategy and assignment | Yes | Python API and golden E2E | Dispatch activity, strategy lab, X-Ray | Assignment command and ledger are separate from web snapshot | Solver verification/fallback exists | Good demo, fragmented live | P0 | Compose ledger-backed decision record with assignment state in one read model. |
| Route/travel estimate | Yes | Provider abstraction and local fallback tests | Map route is schematic; decision X-Ray marks unavailable | Not attached to live operations projection | Provider fallback is explicit in compute API | P1 | Expose provider, duration, fallback, and unavailable reason when present. |
| Digital Twin/simulation | Yes | Twin API, unit tests, UI controls | Operations simulation controls and Twin panel | Uses demo base data plus compute control; no scenario catalog | Seed/generation/digest controls exist | Good | P1 | Add reusable named scenario manifests and load/reset affordance. |
| Replay/Shadow/What-if | Yes, separately | Replay and What-if tests/UI; Shadow API | Replay and Strategy surfaces; Shadow not primary nav | Replay/What-if are frontend-connected; Shadow is API-only | Digest verification and bounded controls exist | P1 | Link recorded run, replay, and Shadow status from Strategy Lab. |
| RouteBench/RADS | Yes in compute/research | Python tests and artifacts | Research Center shows lineage/readiness | No operational workflow | Research boundaries are explicit | P2 | Keep read-only and label as research; add discoverable entry from Strategy Lab. |
| Decision Ledger/provenance | Yes in Java and domain projection | Ledger tests and X-Ray projection tests | X-Ray shows bounded/inferred fields | Live loader does not fetch ledger record by decision ID | Append-only/digest contracts exist | P1 | Add a live ledger lookup or explicit unavailable state with request ID. |
| System health/readiness | Yes | Health probes and tests | Header health badges, Reliability Center | Does not include infrastructure or migration readiness | Per-service timeout/degraded handling exists | P0 | Add dependency/readiness phases and infrastructure probes to one control-plane view. |
| RabbitMQ/event flow | Yes | Outbox and failure E2E scripts | Activity stream shows selected events only | Broker state/queue depth not projected | Outbox retry/DLQ semantics exist | P1 | Add queue/publisher activity summary sourced from safe local telemetry. |
| Redis/GEO state | Yes | Failure E2E evidence | Location status can be degraded | Projection health is not a first-class live metric | Durable fallback exists | P1 | Surface Redis projection status and last successful projection. |
| Database/business state | Yes | Golden E2E and migrations | Orders/parties via operations snapshot | Live read is connected | PostgreSQL is authoritative | P1 | Show snapshot provenance, version, and query freshness in entity drawers. |
| Notification state | Yes as provider boundary | Offline contract tests; live intentionally gated | Not visible in primary product | No user-facing notification timeline | Fail-closed provider boundary | P2 | Add a read-only notification readiness/last-attempt state, never provider claims. |
| Incidents/failures | Yes in resilience scripts and reliability model | Failure E2E exists but infra currently blocked | Alerts and Reliability Center are fixture/read-only | Live incident feed is not attached | Failure paths tested in scripts | P1 | Add a deterministic incident/scenario feed and live degradation timeline. |
| Metrics/observability | Yes | Metrics endpoints/tracing tests | Reliability and metric panels are bounded | OTel export is disabled by default; no unified local collector | Trace IDs and semantic metrics exist | P1 | Add local metrics/queue/latency summary without claiming external telemetry. |

## Sufficient Foundations (Do Not Rewrite)

- Java authoritative state, explicit lifecycle transitions, optimistic/versioned
  commands, Outbox/Inbox boundaries, and Redis-as-projection are sufficient.
- Python strategy registry, solver verification, travel-provider abstraction,
  Digital Twin controls, replay digest verification, What-if, Shadow, RouteBench,
  and RADS boundaries are sufficient for local product work.
- The shared React shell, role-aware routing, source labels, degraded/write-disabled
  semantics, responsive navigation, accessibility tests, and schematic map fallback
  are sufficient foundations. Product work should connect and clarify them rather
  than replace the shell for visual novelty.
- Existing golden-delivery and failure/degradation scripts are valuable evidence;
  the campaign should wrap/reuse them rather than duplicate domain logic.

## Coherent Flow Assessment

The demo source presents a complete visual lifecycle from order creation through
delivery. The real local path is executable in `scripts/golden-delivery.ps1` when
PostgreSQL, RabbitMQ, Redis, Java, and Python are available: courier shift/location,
order create/confirm, dispatch, durable assignment, courier accept/arrive/pickup,
delivery, Outbox publication, and Redis GEO are all asserted. The gap is that this
flow is a script-driven verification journey rather than a single product entry
point, and the live web snapshot does not yet carry the complete event/ledger/route
lineage into the same selected-order view.

The desired observable chain is therefore only partially integrated:
`state change -> dispatch -> provenance -> route estimate -> transition -> event -> web`.
Java and Python implement the pieces; the web currently observes a composed snapshot
and SSE activity but lacks several authoritative links.

## Scenario Readiness

The Digital Twin supports seeded control and replay primitives, and the repository
has failure/degradation E2E coverage. Named reusable manifests for baseline, dinner
rush, shortage, merchant delay, traffic degradation, provider failure, dispatch
pressure, and recovery are not exposed as one discoverable scenario runner. Current
readiness is `PARTIAL`: deterministic kernel and replay exist, catalog/runner UX and
cross-service setup do not.

## Campaign Control

- Campaign namespace: `PR-*` (separate from Round 1-4 and RM tasks).
- Audit checkpoint: this document plus `PRODUCT_READINESS_BACKLOG.md`.
- Audit status: `AUDITED / IMPLEMENTATION_READY`.
- Round 4 progress changed: `NO`.
- Scientific claims changed: `NO`.
- External operations/cost: `NONE / USD 0.00`.
- First eligible implementation: `PR-001` after the audit checkpoint is green.

## Implementation Checkpoint

`PR-001` is implemented in `e3c2c57` and passed Actions run `33298506156`.
`PR-002` is implemented in the current checkpoint and adds `.env` validation,
explicit PostgreSQL/RabbitMQ/Redis health probing, phase checkpoints, process
early-exit detection, and bounded log-tail diagnostics. Focused local checks pass;
the bounded startup observation still times out explicitly when Docker Desktop is
unresponsive and leaves no tracked application state. Evidence is under
`evidence/gates/PR-002/readiness-diagnostics.md`. The next eligible task is
`PR-003`.

`PR-003` is implemented in checkpoint `539b2a2` and passed Actions run
`33299831918`. It adds the finite catalog
`docs/product/scenarios/product-readiness-scenarios-v1.json` and the deterministic
runner `scripts/deterministic_scenarios.py`. All eight named scenarios derive
inputs from `(scenario_id, seed)`, run through the existing `ScenarioKernel`,
verify a repeated replay digest, and retain `SIMULATION`/non-causal labels.
Provider failure uses the existing bounded fallback provider; `RECOVERY` means
replay recovery, not service-restart evidence. Focused catalog, lint, and runner
tests pass. The next eligible task is `PR-004`.

`PR-004` is implemented in the current campaign checkpoint. Java now exposes an
order-centric `operational` aggregate on `GET /api/v1/operations/snapshot`, joined
by tenant-scoped durable order ID to the latest dispatch decision ledger and its
matching courier location. Decision, route, courier, party linkage, and freshness
states are typed and explicit; route data is `NO_ROUTE_ESTIMATE` in the live path
because no durable route estimate is present, while fallback/stale route fixtures
are covered by focused tests. The web loader consumes this aggregate directly and
does not issue a synthetic compute dispatch request. Evidence is under
`evidence/gates/PR-004/authoritative-read-model.md`.

`PR-005` is implemented in the same checkpoint. Reliability Center now presents a
source-scoped observability summary for readiness, SSE cursor/age, dispatch
latency, degraded reasons, and publisher/queue/Redis projection telemetry. The
latter remain explicitly unavailable until an authoritative local telemetry source
is attached; no values are inferred. Evidence is under
`evidence/gates/PR-005/observability-coherence.md`.

`PR-006` is implemented in the same checkpoint. Digital Twin controls use the
frozen eight-entry scenario catalog, and Strategy Lab labels replay verification
and shadow availability by source. Unsupported controls remain unavailable and
all replay/what-if outputs retain their existing non-production authority labels.
Evidence is under `evidence/gates/PR-006/strategy-replay-shadow.md`.

## PR-007 / PR-008 Closure Audit (2026-08-30)

PR-007 remains pending for this run. A bounded prerequisite check confirmed that
`docker compose config --quiet` passes, but the active Docker Desktop
`desktop-linux` daemon did not answer `docker version` within 10 seconds. No
containers or durable state were started, removed, or reset, and no resilience
claim is made. Evidence is under
`evidence/gates/PR-007/resilience-reconnect.md`.

PR-008 is not eligible to bypass this block because the product-readiness
backlog explicitly depends on PR-007. Its UX acceptance criteria and the
user-owned `09a1fae` visual checkpoint remain unchanged for a future bounded
closure run.
