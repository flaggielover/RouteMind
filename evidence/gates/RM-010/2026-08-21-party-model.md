# RM-010 Evidence - Core Identity and Party Model

Date: 2026-08-21
Commit under validation: working tree before commit `4ecf96b`

## Acceptance evidence

- Explicit sealed `CustomerIdentity`, `MerchantIdentity`, and
  `CourierIdentity` types enforce role, identifier, external-reference, and
  display-name invariants.
- `Party` retains `AuditMetadata` and only permits strictly advancing update
  timestamps.
- Flyway `V2__create_parties.sql` owns the `routemind.parties` table, role-scoped
  external-reference uniqueness, status/type checks, and audit ordering.
- `JpaPartyRepositoryAdapter` maps the domain model to the migration-owned table.

## Local gates

Command: `scripts/business-api.ps1 -Action test`

Result: PASS - 18 tests, 0 failures, 0 errors. Includes architecture checks,
Flyway versions 1 and 2, all three role round trips, role-scoped uniqueness,
audit retention, and invalid domain inputs.

## Real PostgreSQL gate

Commands: `scripts/infra.ps1 -Action up`, `scripts/business-api.ps1 -Action run`,
PostgreSQL 18.6 probes via `docker compose exec postgres psql`, then clean
shutdown with `scripts/infra.ps1 -Action down`.

Results:

- Business API started against `jdbc:postgresql://127.0.0.1:15432/routemind`.
- Flyway migrated schema from version 1 to version 2; Hibernate `ddl-auto=validate`
  completed successfully.
- `/actuator/health` returned `{"status":"UP"}`.
- A customer and merchant accepted the same external reference.
- A duplicate customer reference was rejected by
  `uk_parties_type_external_reference`.
- An insert with `updated_at < created_at` was rejected by
  `ck_parties_audit_order`.
- Probe rows were deleted and infrastructure was stopped; persistent volumes
  were preserved.
