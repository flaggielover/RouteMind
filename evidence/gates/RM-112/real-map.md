# RM-112 Real Map Layer With Local Fallback

- Date: 2026-08-22 (Asia/Shanghai)
- Revision: implementation checkpoint pending
- Boundary: Web map surface selecting configured tiles or explicit local fallback

## Map behavior

The operations map now consumes the provider-neutral adapter. When
`VITE_MAP_TILE_URL_TEMPLATE` contains an explicit `{z}`/`{x}` tile template, the
surface renders a configured tile layer and attribution while keeping routing
capability separate. With no configured provider, it remains a deterministic
schematic projection and labels `Offline fallback`; no network tile or paid
credential is assumed. Marker selection, route geometry, loading states, and
source/freshness metadata remain available in both modes.

## Executable evidence

1. `npm run check` in `apps/web` -> PASS; formatting, ESLint, TypeScript, 22 unit
   tests, and production build.
2. `npm run test:e2e` in `apps/web` -> PASS; 16 desktop/mobile role, viewport,
   and axe accessibility tests.
3. `./scripts/full-gate.ps1` -> PASS; Java 57 tests, Python 59 tests at 96.13%
   coverage, 5 schemas/15 fixtures, and Web static/unit/build gate.
4. `git diff --check` -> PASS before checkpoint commit.

## Evidence limits

Local validation covers configured-template selection and the no-provider
fallback. It does not claim availability, correctness, or licensing of any
external tile provider, and routing remains explicitly not configured.
