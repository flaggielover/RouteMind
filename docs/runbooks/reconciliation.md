# Reconciliation Runbook

## Endpoints

- `POST /api/v1/reliability/reconciliation/checks` starts one detect-only scan.
- `GET /api/v1/reliability/reconciliation` returns the latest in-memory or
  PostgreSQL-backed report; it returns 404 before the first stored run.

The scheduled scan is enabled by default. Configure it with
`ROUTEMIND_RECONCILIATION_ENABLED`,
`ROUTEMIND_RECONCILIATION_INITIAL_DELAY_MS`, and
`ROUTEMIND_RECONCILIATION_DELAY_MS`. Disabling the scheduler does not disable the
manual endpoint.

## Status interpretation

- `HEALTHY`: every invariant and the evidence append passed for that run.
- `DRIFT_DETECTED`: at least one bounded violation was observed. Other checks may
  also be unavailable.
- `DEGRADED`: no violation was observed, but at least one check or the evidence
  store was unavailable. This is not proof of health.

Each check is independently `PASS`, `FAIL`, or `UNAVAILABLE`. Use its evidence and
violation codes to identify the affected entity. `checkedAt` is the scan time;
`runId` identifies the append-only evidence row; `repairMode` must always be
`DETECT_ONLY`.

## Response procedure

1. Capture `runId`, `checkedAt`, aggregate status, unavailable checks, and every
   violation code before changing state.
2. Restore unavailable PostgreSQL or Redis dependencies and run another manual
   scan. Do not reinterpret the earlier degraded run as healthy.
3. For projection-only drift, verify durable courier locations before rebuilding
   Redis through the existing projection rebuild path.
4. For lease, assignment, terminal-order, or decision-reference drift, preserve
   the evidence row and investigate the durable transaction/audit history. Do not
   issue ad hoc SQL repair or delete audit records.
5. Any repair requires a separately reviewed policy with authorization,
   idempotency, rollback, and post-repair reconciliation evidence.

The detector never mutates an order, lease, decision, audit, or courier location.
No production alert routing or autonomous remediation is implied by this runbook.
