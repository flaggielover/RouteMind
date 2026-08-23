# RM-180 Round 2 Performance and Realtime Gate

- Date: 2026-08-23 (Asia/Shanghai)
- Design: `docs/superpowers/specs/2026-08-23-rm-180-performance-realtime-design.md`
- Implementation checkpoint: `56c17be`
- Script: `scripts/performance-realtime-gate.ps1`
- Gate decision: PASS (local measured run; no production capacity claim)
- Seed: `18023`
- Result digest: `92f8396b9184f2b1be3bc7f3b77c9d23a4644f9c4e108156565fcded2cf50316`

## Reproducibility context

The gate ran on Windows 11 build `10.0.26200-SP0` with Python `3.14.6`, Java
`17.0.1`, and an Intel Core i9-13900HX host with approximately 32 GiB RAM.
The existing loopback Compose stack was healthy and used PostgreSQL
`18.6-alpine`, RabbitMQ `4.3.5-management-alpine`, and Redis `8.10.1-alpine`.
The run used 128 dispatch requests at concurrency 8, 64 Twin step commands,
80 durable Java order events, and a 64-event SSE batch limit.

## Measured results

- Dispatch: 128/128 HTTP 200 responses, candidate bound 65 returned HTTP 422,
  p50 `8.596 ms`, p95 `33.850 ms`, max `236.632 ms`, measured wall-clock
  throughput `305.510 RPS`.
- Twin: 64/64 HTTP 200 step commands, simulated time advanced to `64.0 s`,
  scenario tick remained `1` (the API's tick field is scenario state, not a
  step counter), event count `3`, p50 `2.048 ms`, p95 `16.107 ms`, max
  `26.077 ms`, measured wall-clock throughput `124.606 RPS`, and duplicate
  speed command replayed successfully.
- SSE/event fanout: 80 order-create requests (including deterministic
  idempotent replays) produced an ordered unique cursor batch of 64 events;
  first cursor `96`, last cursor `159`, stream latency `69.106 ms`, stale
  cursor returned HTTP 409, and `/metrics` returned HTTP 200.

## Supporting gates

- `./scripts/performance-realtime-gate.ps1` -> PASS with the result digest
  above. The wrapper starts the existing local services, records child logs,
  and terminates process trees in `finally`.
- `./scripts/verify.ps1` -> PASS, including task graph, secret isolation,
  Compose hygiene, Python checks, and PowerShell syntax.
- `./scripts/full-gate.ps1` -> PASS: Java 61 tests, Python 142 tests at
  95.88% coverage, five schemas/15 fixtures, Web 49 unit tests, and Web
  production build.

These numbers are a deterministic local regression gate for the stated
configuration and seed. They do not establish production SLOs, capacity, or
cross-host scalability.
