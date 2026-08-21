# RM-001 Local Infrastructure Gate Evidence

Date: 2026-08-21 Asia/Shanghai

Revision: Worktree based on `431576e`; the exact RM-001 checkpoint is the commit
containing this evidence file.

Images verified against Docker Hub's official library tag API and pulled locally:

- `postgres:18.6-alpine`
- `rabbitmq:4.3.5-management-alpine`
- `redis:8.10.1-alpine`

## Static and health gates

```text
docker compose config --quiet
PASS (exit 0)

scripts/verify.ps1
PASS: task graph, Compose configuration, required files, and script syntax

scripts/full-gate.ps1 -Infrastructure
PASS: PostgreSQL, RabbitMQ, and Redis healthy
PASS: RouteMind full available gate
PASS: containers started by the gate stopped; persistent volumes preserved
```

Expanded configuration bound only to loopback:

```text
PostgreSQL           127.0.0.1:15432 -> 5432
RabbitMQ AMQP        127.0.0.1:15673 -> 5672
RabbitMQ Management  127.0.0.1:15674 -> 15672
Redis                127.0.0.1:16379 -> 6379
```

## Protocol probes

```text
PostgreSQL: SELECT current_database(), current_user
PASS: routemind / routemind

RabbitMQ: rabbitmq-diagnostics -q ping
PASS: Ping succeeded

Redis: authenticated redis-cli ping
PASS: PONG
```

## Persistence gate

A PostgreSQL table row, RabbitMQ vhost, and Redis AOF key were created. After
`scripts/infra.ps1 down` removed containers and the network, `up` recreated them
using the named volumes. All three markers remained readable. The markers were
then deleted and containers stopped; the clean development volumes were preserved.

## Defects caught during validation

- Default host ports collided with an existing native PostgreSQL and another local
  project. RouteMind now uses an isolated default port range.
- PostgreSQL 18 requires mounting `/var/lib/postgresql`, not the pre-18 data path.
- PowerShell consumed `-d` as a common parameter instead of passing it to Compose;
  explicit argument arrays now guarantee detached startup.
- RabbitMQ now uses stable hostname and node name so volume data survives container
  recreation under one durable node identity.
