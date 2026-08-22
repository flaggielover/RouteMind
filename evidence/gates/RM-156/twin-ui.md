# RM-156 Digital Twin Control Surface

Date: 2026-08-23

## Implemented boundary

- The existing Operations surface now has a distinct `simulation` data source
  alongside live, demo, and replay. The adapter reads `/api/v1/twin/state` and
  sends bounded commands to `/api/v1/twin/control`; live SSE and durable Java
  writes remain untouched.
- The simulation panel exposes scenario, seed, speed, strategy, step seconds,
  start/resume, pause, step, and reset controls. It also surfaces demand,
  courier supply, seeded traffic, simulated seconds/tick, status, replay digest,
  and the latest deterministic events.
- Existing map, route, lifecycle, exception, health, and metric regions remain
  visible in simulation mode. Loading/unavailable control-source failures are
  explicit, and responsive CSS keeps the control surface usable at mobile
  widths.
- Browser controls use stable command IDs generated at the UI boundary; the
  compute API remains authoritative for idempotency, state transitions, and
  replay provenance.

## Evidence

- Web unit/static check passes 42 tests across 10 files, Prettier, ESLint,
  TypeScript, and production build.
- `./scripts/full-gate.ps1` passes Java 60 tests, Python 139 tests at 95.71%,
  Web 42 unit tests/build, and 5 schemas/15 fixtures.
- `./scripts/web.ps1 -Action e2e` passes 19 desktop/mobile browser tests with
  one existing desktop-only skip. The new simulation test verifies source
  selection, control panel visibility, step-to-completion, event rendering,
  and desktop/mobile screenshots; the accessibility smoke tests remain green.
- Simulation adapter tests cover successful state/control mapping and explicit
  unavailable-source behavior. The panel tests cover metrics, event provenance,
  and playback command dispatch.

## Gate decision

Local L4 Twin browser and L5 UI degradation evidence is complete. Remote
GitHub Actions validation is required before `TASK_GRAPH.yaml` changes RM-156
to `passed`.
