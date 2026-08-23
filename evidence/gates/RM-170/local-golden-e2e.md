# RM-170 Real Local Golden Delivery

- Date: 2026-08-23 (Asia/Shanghai)
- Design: `docs/superpowers/specs/2026-08-23-rm-170-local-golden-delivery-design.md`
- Implementation checkpoint: `13b08a9`
- Gate decision: PASS

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
- `./scripts/golden-delivery.ps1 -TimeoutSeconds 240` -> PASS on 2026-08-23
  after Docker Desktop engine recovery. The run used order
  `38385309-478b-44ce-997e-eb54744cafe1` and courier
  `6df2cfb3-340d-41d9-98a8-f79a465db2a9`.
- The real run passed PostgreSQL, RabbitMQ, and Redis health; Java and Python
  health; courier `ONLINE` and projected GEO location; order create/confirm;
  Python `contract_version=v1` dispatch; Java durable assignment; all four
  courier movement transitions; delivered order; one dispatch audit; one
  assignment Outbox row; `PUBLISHED` Outbox status; durable courier location;
  authenticated RabbitMQ diagnostics; and authenticated Redis ping.
- The first live attempt exposed a real publisher defect: the default Rabbit
  converter rejected `EventEnvelope`. Commit `13b08a9` serializes an explicit
  stable event map with normalized UUID/time scalars and terminates spawned
  process trees during cleanup. The Java gate and the subsequent real run
  passed with the repaired path.
