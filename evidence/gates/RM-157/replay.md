# RM-157 Verified Replay Playback

Date: 2026-08-23

## Implemented boundary

- The Web Operations surface now has a real replay source backed by a fixed,
  deterministic artifact. Replay remains explicitly distinct from live, demo,
  and simulation state.
- The artifact carries scenario, seed, provenance, ordered events, and a
  canonical SHA-256 digest. The browser verifies the digest before enabling
  playback controls; invalid or unverified artifacts remain blocked.
- Verified playback supports play, pause, reset, seek, step, speed, and event
  inspection. Visible events are derived from the simulated cursor and the
  selected event exposes its details without mutating durable business state.

## Evidence

- The artifact digest verification, successful load, cursor stepping, seeking,
  reset, and visible-event projection pass in `replay.test.ts`.
- `npm run check` passes 11 Web test files and 43 tests, plus Prettier, ESLint,
  TypeScript, and the production build.
- `./scripts/web.ps1 -Action e2e` passes 21 desktop/mobile browser tests with
  one existing desktop-only skip. The new replay test verifies source
  selection, digest verification, event visibility after stepping, event
  detail inspection, and desktop/mobile screenshots; existing simulation,
  role, responsive, and axe coverage remains green.
- `./scripts/full-gate.ps1` passes Java 60 tests, Python 139 tests at 95.71%,
  Web 43 unit tests/build, and 5 schemas/15 contract fixtures.

## Gate decision

Local L2 replay verification and L4 replay browser evidence are complete. The
remote Actions Evidence Gate is pending for the implementation checkpoint.
