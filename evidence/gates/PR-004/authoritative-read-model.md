# PR-004 Authoritative Live Operations Projection

Status: implemented locally; no Round 4 task transition.

The Java `OperationsOrderReadModel` is serialized under each order in
`GET /api/v1/operations/snapshot`. `OperationsSnapshotService` reads the
tenant-scoped durable orders, decision ledger, and courier location store, then
joins by the persisted `orderId` and ledger `courierId`. No browser-side order,
party, assignment, or route heuristic is used.

Focused evidence:

- `OperationsOrderReadModelAssemblerTests`: 5/5, including complete join,
  pre-dispatch absence, fallback/stale route, cross-order leakage protection,
  terminal determinism, and injected-clock freshness.
- `BusinessApiApplicationTests`: 17/17, including serialized
  `NO_DECISION_YET`, `NO_ROUTE_ESTIMATE`, and `UNAVAILABLE` states.
- Web live boundary: 3/3 focused tests; one authenticated Java snapshot request,
  zero synthetic compute dispatch requests, order-scoped ledger/request linkage,
  and explicit party/route absence.
- Web quality: lint, typecheck, production build, and serial Vitest 39 files /
  108 tests passed. The default Prettier directory scan remains blocked by the
  existing generated `playwright-report/data` permission boundary.

Route/travel metadata is structurally supported (`provider`, fallback state,
duration, distance, observed time, freshness). The live source returns
`NO_ROUTE_ESTIMATE` because no durable route observation is currently available;
tests prove degraded/fallback/stale serialization without fabricating geometry.
