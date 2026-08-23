# RouteMind Architectural Hardening Audit

Date: 2026-08-23  
Starting commit: `6b742b7`  
Scope: checked-in Java business runtime, Python compute runtime, React/Vite web
surface, contracts, persistence migrations, and executable gates.  
Status: RM-200 audit complete; implementation work begins at RM-201.

## Method and boundary

This is a read-only architecture audit performed after the Round 2 closure.
Repository state was checked with `git status`, branch/remote inspection, the
control-plane documents, `./scripts/resume.ps1`, file-size scans, direct clock
searches, dispatch persistence inspection, and solver/test inspection. The
external data root remains `F:\Projects\RouteMind-Data`; no application code
hard-codes that path.

The audit preserves the current ownership split:

- Java remains authoritative for orders, lifecycle transitions, durable
  persistence, Outbox/event production, and consistency-sensitive commands.
- Python remains authoritative for dispatch, optimization, simulation, Twin,
  RouteBench, RADS, and experiment computation.
- Web remains presentation and interaction only.

No accepted capability is removed or relabeled as complete by this audit.

## Measured structure

| Area | Observation | Architectural implication |
| --- | --- | --- |
| Web | `apps/web/src/App.tsx` is 1,550 lines and contains app bootstrap, source switching, realtime wiring, operations, customer, merchant, courier, and strategy pages. `styles.css` is 41,688 bytes. | Route and feature orchestration are coupled. Safe extraction can reduce change blast radius without a framework rewrite. |
| Compute API | `services/compute-api/src/routemind_compute/api/app.py` is 947 lines and combines Pydantic schemas, global service composition, endpoint declarations, translation helpers, and exception mapping. | Router boundaries and composition wiring are difficult to test independently. |
| Compute application | Several legitimate algorithms are intentionally larger (`vrptw.py` 391 lines, `travel.py` 562, `rads.py` 492, `twin_control.py` 391). | These are not automatic refactor targets; correctness boundaries matter more than line count. |
| Java | No Java production class exceeded the audit threshold of 220 lines; the largest classes are bounded application/API adapters. | Java structure is comparatively modular; prioritize time and assignment consistency rather than broad churn. |

## Findings

### BLOCKER

None found for the current Round 2 behavior. The existing full/verify and
remote CI evidence remains valid.

### HIGH

1. **Frontend orchestration debt (RM-201).** `App.tsx` owns route page
   rendering, source lifecycle, realtime subscription, command calls, and
   role-specific state. This makes a small feature or accessibility fix span a
   large shared file and makes feature-level tests less isolated. Extract route
   pages and feature orchestration while keeping the existing adapters and
   semantics.

2. **Compute API composition debt (RM-202).** `api/app.py` owns all endpoint
   models and handlers for health, dispatch, Twin, strategies, RouteBench,
   What-if, shadow, replay, and RADS. The module-level registry, travel
   provider, Twin control, and What-if runner are mutable process globals. Split
   routers/dependencies without adding a service boundary.

3. **No courier assignment lease (RM-204).** Java's
   `DispatchAssignmentCommandService` is transactionally idempotent by
   `idempotencyKey` and records `dispatch_assignment_audits`, but it does not
   reserve a courier, track a lease generation/expiry, or enforce a unique
   active assignment for a courier. Two distinct decisions can therefore pass
   their own idempotency checks before durable courier ownership is considered.
   Optimistic order versioning protects the order, not the courier resource.

4. **No independent solver verification boundary (RM-206).** The strategy
   registry validates decision shape and metadata, while `VrptwRoutePlanner`
   internally evaluates its own candidate routes. There is no independent
   verifier that recomputes route membership, capacity, windows, travel, and
   objective from solver output. Invalid solver output is therefore not
   structurally rejected by a separate implementation.

5. **Critical time acquisition is not unified (RM-203).** Java mostly injects a
   `Clock`, but `CourierCommandController` falls back to `Instant.now()` when a
   location omits `observedAt`. Python `api/app.py` emits `datetime.now(UTC)`
   for dispatch responses. Replay/simulation algorithms are seeded, yet the
   clock domain is not represented in their contracts or event metadata. This
   leaves event time, ingestion time, wall time, and simulated time implicit.

### MEDIUM

1. **Dispatch provenance is assignment-scoped rather than decision-scoped
   (RM-205).** The durable Java audit stores request/strategy/input/output
   digests after an assignment, but not a stable decision ID, candidate set,
   rejection reasons, location/preparation age, travel artifact identity,
   objective breakdown, alternatives, compute budget, or clock domain. Python
   experiment provenance has useful digests but is not a durable business-side
   decision ledger.

2. **Determinism is distributed rather than contractual (RM-207).** Seeded
   simulation, demand, and preparation generators and canonical RouteBench/RADS
   digests are good foundations. However, request/trace UUIDs, browser
   `Date.now()`/`Math.random()` command IDs, and Python response wall time remain
   mixed into the broader system. No auditor classifies which outputs require
   stable equality versus operationally allowed nondeterminism.

3. **Solver maturity is not surfaced consistently (RM-206).** The registry
   exposes name/version/capabilities/status, but not an honest maturity class,
   supported size, complexity, constraint coverage, or fallback semantics. The
   VRPTW implementation itself describes a bounded deterministic insertion
   baseline, which should remain labeled that way.

4. **Reference-data identity is incomplete (RM-205/RM-207).** Manifests and
   experiment artifacts carry dataset provenance in several paths, but a normal
   dispatch response does not consistently identify the travel/reference data
   version used for the decision. A content-addressed identity interface is
   needed before larger research or map-data claims.

5. **Test independence needs explicit hardening (RM-206/RM-208).** Existing
   tests cover constraints, digests, and deterministic baselines well. They do
   not yet establish a solver-independent route verifier, adversarial lease
   races, or a cross-feature hardening regression manifest. These are test gaps,
   not evidence to weaken existing assertions.

### LOW

1. `styles.css` is large but currently passes formatting, accessibility, and
   browser gates. It should be split by stable visual boundary only when RM-201
   extraction gives a measurable ownership benefit.
2. Some request IDs and correlation IDs are intentionally generated at API
   boundaries. They are operational identifiers, not deterministic simulation
   inputs, but the distinction should be documented by RM-207.

### DEFERRED

- Full OpenTelemetry export, analytical plane, authenticated multi-tenant
  production deployment, device-lab accessibility, large-scale external
  VRP/VRPTW validation, statistical RouteBench, RADS-H, auto-calibration, and
  national-scale visualization remain Enhancement Pass or later research work.
- This audit does not introduce Kafka, a data lake, Kubernetes, a distributed
  clock service, or a theorem prover.

## Dependency-ordered response

The task graph adds RM-201 through RM-209. The order is intentional:

1. Extract frontend and Compute API boundaries (RM-201/RM-202).
2. Establish clock and event-time semantics (RM-203).
3. Use that time model for durable courier leases and decision provenance
   (RM-204/RM-205).
4. Add independent solver verification and maturity labels (RM-206).
5. Formalize deterministic classes and a reproducibility auditor (RM-207).
6. Run cross-system regression (RM-208), then write the closure report and
   prepare the Enhancement Pass graph (RM-209).

This sequence avoids hiding consistency bugs behind a presentation refactor and
keeps each hardening concern independently verifiable.

## Evidence and limits

RM-200 changes no production behavior. Round 2 remains at 76/76 passed with
green Actions run `32616211116` on the starting checkpoint. The findings above
are architectural risks and testable work packages, not claims that production
deployment, full research validity, or cross-machine determinism already exist.
