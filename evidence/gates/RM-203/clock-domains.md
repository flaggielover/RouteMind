# RM-203 Clock Domain Evidence

Date: 2026-08-23  
Implementation checkpoint: `b6202f0` (`feat(clock): make time domains explicit`)  
Remote validation: GitHub Actions run `32626153743`

## Contract

- `WALL` is the UTC live domain. Python live dispatch responses identify it;
  Java courier location fallback uses the injected UTC `Clock` bean.
- `SIMULATED` is owned by Python Digital Twin ticks and scenario time. Scenario
  and Twin state/event digests carry the domain and never derive it from wall
  time.
- `REPLAY` is the Web verified artifact cursor domain. Simulation/replay command
  identifiers use bounded monotonic session sequences rather than wall-clock
  entropy; snapshot `generatedAt` remains a separate UI ingestion timestamp.
- Existing event contract version `1.0` remains unchanged. The event-time and
  ingestion-time distinction is recorded in ADR 0004.

## Local executable evidence

- Compute API: Ruff lint/format, strict mypy, contracts (5 schemas / 15
  fixtures), and 144 tests PASS at 95.94% coverage.
- Business API: 61 Java tests PASS, including Spring context and persistence
  coverage after injecting `Clock` into `CourierCommandController`.
- Web: format, lint, typecheck, 49 unit tests, and build PASS; Playwright PASS
  with 34 passed and 2 existing mobile-project skips.
- Source scan confirms the simulation/replay UI paths no longer use `Date.now()`
  or `Math.random()` and the courier fallback no longer calls unbound
  `Instant.now()`.

## Remote gate

GitHub Actions run `32626153743` completed successfully. All five jobs passed:
Control plane and Compose, Java business runtime, Role-aware web application,
Bounded degradation and resilience, and Python compute and contracts.

## Scope and residual risk

This checkpoint establishes domain ownership and additive metadata. It does not
claim distributed clock synchronization, production latency measurement, or a
complete event-consumer migration; future consumers must preserve producer event
time and separately capture receipt time.
