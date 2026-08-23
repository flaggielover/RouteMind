# RM-170 Real Local Golden Delivery

- Date: 2026-08-23 (Asia/Shanghai)
- Design: `docs/superpowers/specs/2026-08-23-rm-170-local-golden-delivery-design.md`
- Implementation checkpoint: pending commit
- Gate decision: IMPLEMENTED; execution pending Docker Desktop engine recovery

## Implemented path

`scripts/golden-delivery.ps1` starts the existing PostgreSQL/RabbitMQ/Redis
Compose stack, launches Java and Python from repository scripts, waits for
`/actuator/health` and `/healthz`, and drives the public command path:

1. Courier `ONLINE` and location write (Redis GEO projection enabled).
2. Customer order create and confirmation.
3. Python risk-aware dispatch snapshot with a UUID courier candidate.
4. Java versioned dispatch assignment with input/output digests.
5. Courier accept, arrive, pickup, and deliver transitions.
6. PostgreSQL checks for `DELIVERED`, one dispatch audit, one assignment Outbox
   event, `PUBLISHED` Outbox status, and durable courier location.
7. Authenticated RabbitMQ diagnostics and Redis ping/GEO-backed location path.

The Java Outbox relay now runs on a bounded one-second schedule only when the
Rabbit publisher is enabled, so real local events reach RabbitMQ without a
second service or a direct database mutation.

## Evidence status

- `./scripts/business-api.ps1 -Action test` -> PASS, 61 Java tests.
- `./scripts/verify.ps1` -> PASS, including PowerShell syntax for the new
  golden-delivery script.
- `./scripts/golden-delivery.ps1` -> NOT YET EXECUTED: Docker Desktop returned
  HTTP 500 from `dockerDesktopLinuxEngine` for `docker compose ps`; both the
  `desktop-linux` and `default` Docker contexts were unavailable. No
  cross-service success is claimed until the engine responds.
