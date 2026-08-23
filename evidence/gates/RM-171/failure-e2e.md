# RM-171 Failure and Degradation E2E

- Date: 2026-08-23 (Asia/Shanghai)
- Design: `docs/superpowers/specs/2026-08-23-rm-171-failure-degradation-e2e-design.md`
- Implementation checkpoint: `427be52`
- Gate decision: PASS
- Script: `scripts/failure-degradation-e2e.ps1 -TimeoutSeconds 240`
- Run ID: `55b3b3bb-cab2-4175-895e-845058036cf6`

## Real failure journeys

The script ran against the existing PostgreSQL 18.6, RabbitMQ 4.3.5, Redis
8.10.1, Java, and Python services. It used one generated run namespace and
preserved the named Compose volumes.

1. Redis container loss returned courier location `DEGRADED` while the
   PostgreSQL location row remained present; after Redis recovery, the next
   location returned `PROJECTED`.
2. Python compute termination made both health and dispatch unavailable while
   Java still created a `CREATED` order. Python health recovered after restart.
3. RabbitMQ stop left a newly created order's `order.created` Outbox row not
   `PUBLISHED`; after broker restart and relay recovery, it became `PUBLISHED`.
4. Repeating one order create idempotency key returned `replayed=true`, kept
   one idempotency row, and kept one durable `order.created` event.
5. A courier transitioned `ONLINE` to `OFFLINE`; Python returned no selected
   courier with `courier_state=offline`, and a stale Java shift command returned
   HTTP 409.
6. A local listener accepted the dispatch request without responding; the
   caller timed out in under three seconds, while Java still created a durable
   order. This is explicitly a bounded caller-timeout claim, not a compute
   success claim.

## Supporting gates

- `./scripts/resilience.ps1` -> PASS: Java application tests and two Python
  resilience tests.
- `./scripts/full-gate.ps1` -> PASS: control/security/recovery/compose checks,
  Java 61 tests, Python 142 tests at 95.88%, five schemas/15 fixtures, Web 49
  unit tests, and Web production build.
- `./scripts/verify.ps1` -> PASS, including PowerShell syntax for the failure
  script and task graph validation.
- GitHub Actions run `32613079169` for commit `94c7ce4` passed all five jobs,
  including Python, Java, Web browser smoke, bounded degradation, and control
  plane.

No browser fixture was used to produce the six failure claims. The script
restores Redis/RabbitMQ and terminates child processes in `finally`; durable
rows and named volumes are intentionally retained for inspection.
