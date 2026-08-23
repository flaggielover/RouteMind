# RM-180 Performance and Realtime Gate Design

## Scope

Measure the local dispatch, simulation, durable-event/SSE, and bounded-input
paths with fixed inputs. Results are a reproducible local baseline, not a
production capacity claim. The Java/Python ownership split remains unchanged:
Python owns dispatch and simulation; Java owns durable commands, Outbox, and
SSE projection.

## Gate

`scripts/performance-realtime-gate.ps1` starts the real Compose dependencies and
the repository Java/Python processes, then invokes the standard-library Python
measurement runner with seed `18023`:

- 128 dispatch requests at concurrency 8, recording status, p50/p95/max
  latency, throughput, and error count.
- 64 Twin `step` commands, recording simulated-time progression, scenario tick,
  event count, latency, and command replay behavior.
- 32 durable Java order-created events followed by the real SSE stream, with
  cursor ordering, event count, and fanout latency recorded.
- Explicit resource-bound checks: 65 dispatch candidates return 422, SSE
  replay emits no more than the 64-event batch limit, and an expired cursor
  returns 409 when the retained window has advanced.

The result includes platform/runtime/configuration metadata, a canonical
SHA-256 result digest, and a fixed seed. The wrapper prints logs on failure,
terminates process trees, and leaves named Compose volumes intact.

## Claims

The evidence reports measured local values and the exact environment. It does
not infer production RPS, cross-region behavior, browser paint latency, or a
capacity SLO. Existing Web browser smoke evidence remains the browser-update
functional boundary; this gate measures the Java SSE endpoint that feeds it.
