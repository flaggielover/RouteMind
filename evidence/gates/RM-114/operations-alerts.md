# RM-114 Operations Exceptions, Imbalance, and Alerts

- Date: 2026-08-22 (Asia/Shanghai)
- Revision: implementation checkpoint pending
- Boundary: Web alert projection derived from recorded operations snapshot data

## Alert behavior

The operations surface now renders a recorded exception queue from priority and
order lifecycle state. Each alert selects the affected order and preserves its
existing trace/state detail. Supply/demand imbalance is calculated from snapshot
order and available-courier counts. Overtime risk is explicitly unavailable when
the source provides no recorded risk metric; no benchmark value is fabricated.

## Executable evidence

1. `npm run check` in `apps/web` -> PASS; formatting, ESLint, TypeScript, 24 unit
   tests, and production build.
2. `npm run test:e2e` in `apps/web` -> PASS; 16 desktop/mobile role, viewport,
   and axe accessibility tests.
3. `./scripts/full-gate.ps1` -> PASS; Java 57 tests, Python 59 tests at 96.13%
   coverage, 5 schemas/15 fixtures, and Web static/unit/build gate.
4. `git diff --check` -> PASS before checkpoint commit.

## Evidence limits

Alerts and imbalance are locally projected from the current snapshot. This gate
does not claim durable alert acknowledgement, server-side alert routing, or a
production overtime model.
