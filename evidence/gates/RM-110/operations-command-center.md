# RM-110 Operations Command Center Projection

- Date: 2026-08-22 (Asia/Shanghai)
- Revision: `4b4ab79`; Actions run `32567110886`
- Boundary: Web operations projection over Java durable reads and Python dispatch metadata

## Projection behavior

The operations view now exposes source and freshness metadata, service projection
health, and explicit loading, degraded, unavailable, empty, and exception states.
The map tolerates live orders without route geometry and labels that limitation;
selected order details retain source and snapshot freshness. Live initialization is
loading until the Java/Python snapshot resolves, while Demo remains deterministic
and Replay remains explicitly unavailable without a verified artifact.

## Executable evidence

1. `npm run check` in `apps/web` -> PASS; formatting, ESLint, TypeScript, 17 unit
   tests, and production build.
2. `npm run test:e2e` in `apps/web` -> PASS; 16 desktop/mobile role, viewport,
   and axe accessibility tests.
3. `./scripts/full-gate.ps1` -> PASS; Java 57 tests, Python 59 tests at 96.13%
   coverage, 5 schemas/15 fixtures, and Web static/unit/build gate.
4. `git diff --check` -> PASS before checkpoint commit.

## Evidence limits

This gate proves local/browser projection states and metadata behavior with the
existing deterministic Demo fixture and live/replay boundary adapters. It does
not claim production map tiles, live service availability, or provider-backed
route geometry; those remain explicit follow-on capabilities.
