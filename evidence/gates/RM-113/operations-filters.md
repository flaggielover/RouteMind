# RM-113 Operations Filters and Detail Drawers

- Date: 2026-08-22 (Asia/Shanghai)
- Revision: implementation checkpoint pending
- Boundary: Web operations projection interaction over verified snapshot data

## Interaction behavior

The operations board now has functional zone, lifecycle, exception, and freshness
filters. The result count is explicit and filtered orders/couriers are projected
into the map and queue. Order and courier detail panels expose route point count,
order version, source/freshness, zone, status, and position; unavailable metadata
is labeled rather than fabricated. Keyboard-selectable controls remain inside the
existing responsive shell.

## Executable evidence

1. `npm run check` in `apps/web` -> PASS; formatting, ESLint, TypeScript, 23 unit
   tests, and production build.
2. `npm run test:e2e` in `apps/web` -> PASS; 16 desktop/mobile role, viewport,
   and axe accessibility tests.
3. `./scripts/full-gate.ps1` -> PASS; Java 57 tests, Python 59 tests at 96.13%
   coverage, 5 schemas/15 fixtures, and Web static/unit/build gate.
4. `git diff --check` -> PASS before checkpoint commit.

## Evidence limits

The filter and drawer projection is local/browser validated over Demo and supplied
snapshot data. It does not claim server-side query pagination, durable commands,
or production entity authorization; those remain separate boundaries.
