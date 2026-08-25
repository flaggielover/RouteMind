# R4-403 Durable Tenant Isolation Evidence

Date: 2026-08-25 (Asia/Shanghai)

Entry revision: `3803da3d3d06cef26414ecc1aae07be61c34cbe8`

Status: in progress - `CI_PENDING`

## Durable boundary

- A canonical, non-nil UUID `TenantId` is required by secured OIDC requests.
  The verified token claim establishes the Java request scope; a caller-supplied
  `X-Tenant-Id` is rejected in secured mode. Local mode retains an explicit
  compatibility header and the stable legacy tenant
  `00000000-0000-0000-0000-000000000001`.
- Java transaction adapters apply tenant predicates to parties, orders,
  transitions, courier shifts and locations, assignment leases, decisions,
  audits, reconciliation reports, Outbox, Inbox, and event-stream reads.
  Cross-tenant global aggregate-ID collisions raise
  `tenant_scope_violation` instead of overwriting another tenant.
- API-visible idempotency and decision keys remain logical identities. A
  tenant-derived SHA-256 physical key plus tenant/logical unique indexes prevent
  cross-tenant replay while retaining legacy single-tenant keys unchanged.
- Events include `tenantId` in the v1 additive contract, durable Outbox record,
  JSON body, and RabbitMQ header. The Outbox relay and Inbox processor enter the
  event tenant scope before publishing, handling, or recording status. Missing
  `tenantId` in an older v1 event maps only to the legacy tenant; nil identities
  fail validation.
- Redis GEO keys and reconciliation queries are tenant namespaced. PostgreSQL
  remains durable truth; Redis remains a rebuildable projection.

## Concurrency and replay evidence

`TenantIsolationIntegrationTests` proves the following fail-closed behavior:

- tenants A and B can execute the same logical command key independently;
- the same pair can execute concurrently without cross-tenant replay;
- tenant B cannot read tenant A's order or overwrite its globally unique ID;
- equal logical audit keys resolve only within the current tenant;
- a duplicate event ID with an altered tenant cannot enter Inbox, and an event
  whose tenant differs from the current transaction scope is rejected;
- Outbox rows and event envelopes retain the transaction tenant; and
- nested request/worker scopes restore and clear their previous tenant.

## Migration and rollback

Flyway `V16__enforce_tenant_isolation.sql` adds a non-null `tenant_id` to all 15
durable tables, backfills legacy rows, adds tenant-aware uniqueness/indexes, and
introduces logical-key columns where a global physical primary key previously
encoded replay identity.

The migration test creates a populated V15 database in H2 2.4 PostgreSQL
compatibility mode, upgrades it to V16, verifies the legacy and logical-key
backfill plus all 15 tenant columns, executes
`db/rollback/U16__remove_tenant_isolation.sql`, and verifies that the introduced
columns are removed. `docs/runbooks/R4_TENANT_MIGRATION.md` makes rollback
conditional on zero non-legacy traffic; after tenant traffic begins, snapshot
restore is required because namespace collapse is unsafe.

## Local validation

- `./scripts/business-api.ps1 -Action test`: 96 tests passed, 0 failures,
  0 errors, 0 skipped. This includes architecture rules, full application and
  OIDC integration, five tenant-isolation integration tests, event
  serialization, relay scope, and Rabbit header coverage.
- `./scripts/compute-api.ps1 -Action check`: Ruff, formatting, mypy, six schemas,
  18 contract fixtures, 920 Python tests, 95.11% coverage, determinism,
  analytics, and semantic gates passed after the additive event-contract change.
- `./scripts/verify.ps1`: task graph, Round 3 negative-result and claim freezes,
  final figures, Round 4 graph, security, recovery, release, and staged-release
  gates passed. The local Docker CLI then remained unresponsive during
  `docker compose config --quiet`; the bounded invocation was stopped and no
  local Compose pass is claimed. PowerShell syntax was checked separately and
  passed.
- `git diff --check`: passed.

## Evidence boundary

This checkpoint proves the local Java/H2-compatible isolation design and
executable migration/rollback rehearsal. It does not claim a live external IdP,
production PostgreSQL migration, deployed tenant fleet, vendor WAF, or
production traffic result. R4-403 remains open until the implementation commit
passes all five real GitHub Actions jobs, including clean Linux Compose and
contract validation. R3-325 was not rerun, tuned, reinterpreted, or changed.
