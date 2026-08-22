# RM-100 Live Product Foundation Gate

- Date: 2026-08-22 (Asia/Shanghai)
- Revision: implementation checkpoint recorded by the accompanying commit
- Worktree: implementation changes only; no unrelated files
- Boundary: local service and browser validation; no production deployment or live provider claim

## Contract and ownership

The web data boundary now exposes explicit `live`, `demo`, and `replay` modes.
LIVE composes the Java read-only operations snapshot with the Python dispatch
decision. DEMO remains the deterministic fixture used by offline tests. REPLAY
is explicit and unavailable until a verified artifact is supplied. HTTP errors,
timeouts, and unavailable services produce a labeled unavailable LIVE snapshot;
the adapter never substitutes DEMO data silently.

Java owns durable order and party state and reads courier locations through the
existing projection boundary. Python validates bounded candidates and invokes the
existing strategy registry without writing durable business state. The browser
does not call PostgreSQL or Redis directly.

## Commands and results

1. `./scripts/verify.ps1` -> PASS (control-plane, security, repository, and
   contract gates).
2. `./scripts/business-api.ps1 -Action test` -> PASS; 50 Java tests passed.
3. `./scripts/compute-api.ps1 -Action check` -> PASS; 58 Python tests passed,
   96.15% total coverage, 4 schemas and 12 fixtures validated.
4. `./scripts/full-gate.ps1` -> PASS; Java, Python, Web, and repository gates
   passed together.
5. `apps/web`: `npm run check` -> PASS; 8 unit tests and production build.
6. `apps/web`: `npm run test:e2e` -> PASS; 16 Playwright desktop/mobile tests,
   including axe accessibility checks.

## Executable behavior

- `GET /api/v1/operations/snapshot` returns `source: live` and explicit empty
  arrays when durable state is empty.
- `POST /api/v1/dispatch/snapshot` returns a versioned strategy decision and
  trace metadata, and rejects unknown strategies or duplicate candidates.
- Live adapter tests prove Java/Python composition, explicit unavailable state,
  and distinct replay behavior.

## Evidence limits

This gate proves the local contract and ownership boundary only. It does not
claim production availability, real courier traffic, a verified replay artifact,
SSE/realtime delivery, or end-to-end command execution; those are later tasks in
the Round 2 graph.
