# R4 Tenant Migration Runbook

## Invariants

- `tenant_id` comes from the verified OIDC `tenant_id` claim in secured mode.
- `X-Tenant-Id` is rejected in secured mode. It is a local-development-only compatibility input when OIDC is disabled.
- Java transaction adapters apply explicit tenant predicates. Redis GEO keys are tenant namespaced.
- Events carry `tenantId`; inbox deduplication uses the event tenant. Idempotency and decision keys use a tenant-derived physical key while preserving the logical API key.
- The stable legacy tenant is `00000000-0000-0000-0000-000000000001`.

## Deployment

1. Take and verify a PostgreSQL snapshot.
2. Stop command traffic and drain the outbox relay.
3. Deploy V16. It backfills all durable rows to the legacy tenant, adds non-null columns, tenant indexes, and logical-key columns.
4. Run the Java gate. Its migration test upgrades a populated V15 database and verifies all 15 durable tables.
5. Enable OIDC with a canonical, non-nil UUID `tenant_id` claim and resume traffic.

## Rollback

Before any non-legacy traffic, stop writers and execute
`db/rollback/U16__remove_tenant_isolation.sql`. The automated gate executes this script against the populated V15→V16 rehearsal database.

After non-legacy traffic, do not run the down script. Tenant-derived physical keys and tenant-specific rows cannot be safely collapsed. Stop writers and restore the verified pre-V16 snapshot instead. This is the deliberate fail-closed boundary.

## Verification

- Confirm no null or nil `tenant_id` values.
- Confirm the API cannot read a tenant-A order under tenant B.
- Confirm identical logical idempotency keys execute independently in tenants A and B.
- Confirm outbox event `tenant_id` equals the transaction tenant.
- Confirm `main` CI is green before enabling traffic.
