# RM-104 Web Live Data Source With Explicit Modes

- Date: 2026-08-22 (Asia/Shanghai)
- Revision: implementation checkpoint recorded by the accompanying commit
- Boundary: browser data-source selection and truthful source availability

## Contract

The web shell exposes explicit `LIVE`, `DEMO`, and `REPLAY` modes. LIVE composes
the Java durable operations snapshot with the Python dispatch decision. DEMO is
a deterministic offline fixture. REPLAY remains a distinct mode until a
verified replay artifact is supplied. A LIVE fetch or dispatch failure produces
an unavailable LIVE snapshot and never silently substitutes DEMO data.

## Executable evidence

1. `./scripts/web.ps1 check` -> PASS; formatting, ESLint, TypeScript, build, and
   9 unit tests passed.
2. `./scripts/web.ps1 e2e` -> PASS; 16 browser smoke tests passed across desktop
   and mobile projects, including all five role routes, source-mode selection,
   viewport containment, and accessibility checks.
3. `python scripts/validate_control_plane.py` and `git diff --check` -> PASS.

## Failure semantics

- LIVE request failure renders `Live unavailable` and an empty unavailable
  snapshot; no fixture data is injected into that state.
- DEMO selection renders the deterministic fixture and labels it `Demo
  snapshot`.
- REPLAY selection renders `Replay` and requires a verified artifact, otherwise
  it remains unavailable with an explicit detail message.

## Evidence limits

The browser gate uses the local Vite server and deterministic test doubles for
service failure. Live production availability, deployment routing, and replay
artifact verification are deployment/data-plane concerns outside this local
surface gate.
