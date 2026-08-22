# RM-060 Role-Aware Web Gate

- Time: 2026-08-22T11:18:02+08:00
- Revision before checkpoint: `b5220cc785e0ff5cbb5b0ac6269e29a006adb05e`
- Worktree: feature changes present, no unrelated files
- Scope: local deterministic demo snapshot plus independent Java/Python health probes

## Commands and results

1. `./scripts/web.ps1 check` — PASS
   - Prettier format check, ESLint, TypeScript 5.9.3, and Vite production build passed.
   - Vitest: 2 files, 5 tests passed.
2. `./scripts/web.ps1 e2e` — PASS
   - Playwright desktop Chromium and mobile Chromium projects.
   - 16 tests passed: five role routes, full order lifecycle, shared queue/map selection,
     mobile viewport overflow check, mobile screenshot, and axe WCAG smoke for all routes.
3. `./scripts/full-gate.ps1` — PASS
   - Control plane and Compose validation passed.
   - Java business gate: 33 tests passed.
   - Python/contract gate: 32 tests passed, 97.92% statement/branch coverage,
     4 schemas and 12 fixtures passed.
   - Web static and unit gate passed.

## Evidence boundary

The browser surface labels its source `Demo snapshot`. This evidence proves local
role-aware rendering, lifecycle visibility, accessibility, responsive behavior,
and service-health failure presentation. It does not claim live order queries,
authenticated commands, WebSocket delivery, or production deployment.
