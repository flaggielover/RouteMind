# RM-201 Frontend Modularization Evidence

Date: 2026-08-23  
Implementation checkpoint: `f057d36` (`refactor(web): modularize role route surfaces`)  
Remote validation: GitHub Actions run `32624822845`

## Change

- Extracted the role-facing route and feature views from `apps/web/src/App.tsx`
  into `apps/web/src/routes/RoleViews.tsx`.
- Reduced `App.tsx` from 1,550 lines before the change to approximately 770
  lines while keeping route selection, live/demo/replay/simulation semantics,
  command adapters, accessibility labels, and responsive behavior intact.
- Kept the existing React/Vite/TypeScript boundary; no capability or endpoint
  was removed and no new network service was introduced.

## Local executable evidence

From `apps/web` at checkpoint `f057d36`:

- `npm run format:check` PASS
- `npm run lint` PASS
- `npm run typecheck` PASS
- `npm run test:unit` PASS (14 files, 49 tests)
- `npm run build` PASS
- `npm run test:e2e` PASS (34 passed, 2 existing mobile-project skips)

`./scripts/full-gate.ps1` was attempted. The run stopped after the local Docker
CLI produced no output while executing `docker compose config`; this is recorded
as an environment limitation and is not claimed as a local full-gate pass.

## Remote gate

GitHub Actions run `32624822845` completed successfully. All five jobs passed:
Control plane and Compose, Java business runtime, Role-aware web application,
Bounded degradation and resilience, and Python compute and contracts.

## Scope and residual risk

This checkpoint is a structural frontend boundary refactor. Behavioral claims
are limited to the listed static, unit, build, and Playwright gates; production
deployment and cross-browser coverage beyond the configured projects remain out
of scope.
