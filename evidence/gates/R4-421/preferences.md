# R4-421 Durable Tenant-Aware User Preferences Evidence

Date: 2026-08-25 (Asia/Shanghai)

Status: `LOCAL_VALIDATED / CI_PENDING`

## Implementation boundary

- `V17__create_user_preferences.sql` creates tenant-scoped preference, command
  idempotency, and append-only audit tables. `U17__remove_user_preferences.sql`
  is the recoverable local rollback script.
- Java owns validation, defaults, version preconditions, stable tenant/principal
  keys, idempotency, audit, and response state. OIDC identity comes only from a
  verified JWT; local mode is a bounded compatibility identity. The API does not
  accept a target tenant or target principal.
- `GET` returns deterministic version-zero defaults. `PUT` requires
  `expectedVersion` and `Idempotency-Key`; stale writes return
  `preference_version_conflict`; same request keys replay without a second audit.
- Web `PreferencesPanel` and `data/preferences.ts` expose loading, ready, stale,
  conflict, unavailable, and rollback states. Draft values remain visible after
  failed saves; demo, replay, and degraded sources are read-only.

## Executable evidence

- Java full Maven gate: passed with `109/109` tests after R4-421 additions. The
  targeted preference suite includes payload policy, service idempotency and
  conflict tests, architecture boundary checks, and `UserPreferenceIntegrationTests`.
- HTTP integration covers verified OIDC role binding, default reads, durable
  version `1` writes, idempotent replay, `409` stale conflict, cross-tenant
  version-zero isolation, and same-subject cross-role denial.
- Web check: passed. `35` test files / `95` tests, Prettier, ESLint, TypeScript,
  unit tests, and Vite production build all pass.
- `git diff --check`: passed. No external provider, notification, production
  data, or paid service was used. R3-325 remains frozen exactly as
  `E-PASS / X-PASS / S-FAIL / C-NO-CLAIM` and was not rerun.

Remote GitHub Actions validation is the remaining Evidence Gate for this task.
