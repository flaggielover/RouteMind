# Product Readiness Backlog

Namespace: `PR-*`  
Campaign: Product & Demo Readiness  
Created from audit revision `9e6a0ffed87b5e0d7987edd33c48999b949c7539`

This backlog is intentionally finite and separate from `TASK_GRAPH.yaml`. It does
not inflate Round 4 counts or alter Round 4, Round 3, Human-Gate, external-provider,
or scientific status. Tasks are local-first and may reuse existing APIs/scripts.

## Status Summary

| ID | Priority | Status | Depends on | Focus |
| --- | --- | --- | --- | --- |
| PR-001 | P0 | implemented | none | One bounded local lifecycle entrypoint |
| PR-002 | P0 | implemented | PR-001 | Verify dependency/readiness ordering and diagnostics |
| PR-003 | P1 | implemented | PR-001, PR-002 | One-command deterministic scenario runner |
| PR-004 | P1 | ready | PR-002 | Live projection joins assignment, ledger, route, and freshness |
| PR-005 | P1 | pending | PR-002, PR-004 | Event/queue/projection observability summary |
| PR-006 | P1 | pending | PR-003, PR-004 | Scenario/replay catalog and operator controls |
| PR-007 | P2 | pending | PR-004, PR-005 | Resilience/reconnect/stale-state product closure |
| PR-008 | P2 | pending | PR-005, PR-006, PR-007 | UX information architecture and visual polish closure |

## Task Definitions

### PR-001 — Bounded Local Lifecycle Entrypoint (P0)

Dependencies: none.

Acceptance criteria:

- A documented PowerShell command verifies prerequisites, validates Compose,
  starts PostgreSQL/RabbitMQ/Redis, waits with a deadline, and prints endpoints.
- It starts Java, Python, and optionally the web server with captured log paths,
  preserves startup failures, and records process IDs for safe tree cleanup.
- A matching stop command is idempotent, does not delete persistent volumes by
  default, and cleans only processes started by the command.
- Optional deterministic data loading is explicit and cannot be mistaken for live.

Verification: script unit tests for ordering, timeout, failure, cleanup, and argument
handling; Compose config gate; a bounded local smoke run when Docker responds; no
external calls.

### PR-002 — Dependency Readiness and Startup Diagnostics (P0)

Dependencies: PR-001.

Acceptance criteria:

- Readiness distinguishes process-up, dependency-ready, migration-ready, and
  API-ready states for Java and Python.
- A failed dependency names the exact service, endpoint/command, timeout, and
  relevant log tail; no hidden retry loop runs forever.
- Java startup ordering is PostgreSQL/RabbitMQ/Redis ready -> migration -> API;
  Python and web readiness are independently reported.

Verification: injected unavailable dependency tests, restart smoke, malformed
configuration test, and clean shutdown evidence.

### PR-003 — Deterministic Local Scenario Runner (P1)

Dependencies: PR-001, PR-002.

Acceptance criteria:

- A finite manifest catalog exposes `NORMAL_BASELINE`, `DINNER_RUSH`,
  `COURIER_SHORTAGE`, `MERCHANT_DELAY`, `TRAFFIC_DEGRADATION`,
  `ROUTING_PROVIDER_FAILURE`, `DISPATCH_PRESSURE`, and `RECOVERY` only where
  real interfaces support the behavior.
- Each run records scenario ID, seed, configuration, source label, and output
  digest; rerunning the same manifest is replayable.
- Scenario setup uses real domain/API interfaces and does not bypass invariants.

Verification: manifest schema tests, repeated digest test, representative local
run, and explicit unsupported/degraded behavior tests.

### PR-004 — Authoritative Live Operations Projection (P1)

Dependencies: PR-002.

Acceptance criteria:

- The selected live order view links current lifecycle/version, assignment,
  decision ID/request ID, strategy/version, route/travel provider metadata when
  available, fallback state, courier freshness, and source provenance.
- Missing records remain explicitly unavailable; no demo fixture is silently merged
  into a live record.
- SSE activity and snapshot cursor/freshness remain tenant-safe and idempotent.

Verification: Java/Python contract fixtures, web live loader tests, ledger-link test,
stale/reconnect test, and browser smoke with a verified local fixture session.

### PR-005 — Operational Observability Summary (P1)

Dependencies: PR-002, PR-004.

Acceptance criteria:

- Operations and Reliability Center show service readiness, event cursor/age,
  publisher/queue activity where locally observable, Redis projection status,
  dispatch latency, and explicit degraded reasons.
- Every metric identifies source and freshness; fixture, live, simulation, replay,
  and unavailable values are not pooled.
- Raw JSON/log blobs are replaced by structured summaries with drill-through IDs.

Verification: projection tests, stale/empty/error states, accessibility smoke, and
local restart/reconnect evidence.

### PR-006 — Scenario, Replay, and Shadow Control Surface (P1)

Dependencies: PR-003, PR-004.

Acceptance criteria:

- Strategy Lab exposes named scenario selection, verified replay artifact state,
  What-if comparison, and Shadow evaluation status with clear authority labels.
- Controls are disabled or fail closed when the selected source cannot support them.
- Seed, manifest, strategy version, replay/output digests, and unavailable metrics
  are visible without scientific or production claims.

Verification: component/browser tests for each source, malformed manifest, failed
  compute API, and replay verification failure.

### PR-007 — Resilience and Recovery Product Closure (P2)

Dependencies: PR-004, PR-005.

Acceptance criteria:

- Frontend reconnects after backend restart, identifies stale data, preserves the
  last known source label, and recovers without duplicate event application.
- Service restart, duplicate command/event, timeout, malformed input, Redis loss,
  and RabbitMQ loss each produce bounded, inspectable UI states.

Verification: reuse `golden-delivery.ps1` and `failure-degradation-e2e.ps1` where
  applicable; add focused browser and API recovery evidence.

### PR-008 — Product UX Closure (P2)

Dependencies: PR-005, PR-006, PR-007.

Acceptance criteria:

- Navigation presents operations, strategy/scenario, and role workflows as one
  coherent product with consistent source/freshness/status language.
- Loading, empty, error, degraded, stale, and unavailable states are complete on
  every primary route; dead or misleading controls are removed or made explicit.
- Desktop/mobile layout, keyboard focus, contrast, and screen-reader names remain
  green under existing accessibility gates.

Verification: web static/unit/browser/axe gates plus a short operator usability
walkthrough recorded in evidence; no decorative-only rewrite.

## Execution Rule

Complete tasks in dependency order using `audit -> implement -> test -> evidence ->
commit -> push -> observe CI`. Mark only this backlog's statuses in this file. Do
not add `PR-*` entries to the Round 1-4 task list.
