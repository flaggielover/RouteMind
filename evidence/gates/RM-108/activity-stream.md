# RM-108 Live Activity and Event Stream Shell Integration

- Date: 2026-08-22 (Asia/Shanghai)
- Revision: implementation checkpoint pending
- Boundary: role-aware Web activity projection over verified realtime events

## Activity behavior

The operations shell now renders a bounded activity stream beneath the dispatch
trace. Live entries expose business event type, decimal cursor, trace context,
freshness, and `Live` source labeling from the RM-107 consumer. Demo entries are
derived only from the deterministic lifecycle fixture and are labeled `Demo`;
Replay remains explicitly unavailable until a verified replay artifact exists.
The activity component is a projection and never owns order, dispatch, or durable
business state.

## Executable evidence

1. `npm run check` in `apps/web` -> PASS; formatting, ESLint, TypeScript, 15 unit
   tests, and production build.
2. `npm run test:e2e` in `apps/web` -> PASS; 16 desktop/mobile role, viewport,
   and axe accessibility tests.
3. `./scripts/full-gate.ps1` -> PASS; Java 57 tests, Python 59 tests at 96.13%
   coverage, 5 schemas/15 fixtures, and Web static/unit/build gate.
4. `git diff --check` -> PASS before checkpoint commit.

## Evidence limits

This gate proves local and browser projection behavior with injected events and
deterministic Demo/Replay source labels. It does not claim production activity
retention, cross-tab coordination, or live deployment availability.
