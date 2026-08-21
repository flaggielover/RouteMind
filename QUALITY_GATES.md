# RouteMind Quality Gates

Apply gates by blast radius. Small documentation edits do not require a broker
restart test; event-delivery changes do.

## L1 Static quality

- Control plane: `./scripts/verify.ps1`
- Compose: `docker compose config --quiet`
- Infrastructure health: `./scripts/infra.ps1 up`
- Java: formatter, compiler, static analysis, migration validation
- Python: formatter/linter, type checker, package and schema validation
- Web: formatter, linter, type checker, production build
- Contracts: schema parse, examples, compatibility checks

## L2 Unit and component

Test domain invariants, state transitions, algorithms, error mapping, deterministic
ties, serialization, and boundary behavior without unnecessary infrastructure.

## L3 Integration

Use real PostgreSQL, Redis, RabbitMQ, migrations, HTTP/service boundaries, and
contract fixtures where the behavior under test depends on them. Mocks do not prove
broker acknowledgement, database transaction, or Redis degradation semantics.

## L4 End-to-end

Validate customer order through merchant acceptance/preparation, dispatch,
assignment, pickup, delivery, and completion, including role-visible state.

## L5 Failure and resilience

Inject duplicate/reordered messages, worker and broker restart, poison messages,
Redis loss, database latency, dependency timeout, and partial outage. Verify bounded
retry, DLQ, recovery, durability, observability, and degraded behavior.

## L6 System, performance, and research

Run seeded simulation, RouteBench comparison, regression, load, latency,
throughput, algorithm-correctness, resource, switching, robustness, and
reproducibility gates. Record hardware when relevant.

## Evidence rules

- Store compact, durable evidence in `evidence/gates/<task-id>/`.
- Include command, time, code revision/worktree state, result, and relevant output.
- Large logs and datasets belong under `ROUTEMIND_DATA_ROOT`; committed evidence
  links them by manifest and checksum when needed.
- `passed` means every task gate passed. Use `implemented` or `validating` while
  evidence remains incomplete.
- Distinguish local, CI, live-provider, and production verification.
