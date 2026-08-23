# RM-216 Fulfillment Saga Evidence

Date: 2026-08-23
Implementation checkpoint: c98ea76
GitHub Actions: PASS - run 32649193769 (all five jobs)

## Scope

The Java business runtime remains authoritative for the order fulfillment saga.
The lifecycle now explicitly represents merchant preparation, courier assignment,
pickup, delivery, cancellation, assignment timeout, courier rejection,
reassignment pending, compensating, and compensated states. Payment processing is
intentionally absent.

## Local evidence

- `./scripts/business-api.ps1 test` - PASS, 79 Java tests.
- `./scripts/compute-api.ps1 check` - PASS, 185 Python tests, 6 schemas, and 18
  contract fixtures.
- `./scripts/web.ps1 check` - PASS, 52 web unit tests and production build.
- `./scripts/verify.ps1` - PASS repository fast gate.
- `V14__expand_fulfillment_saga.sql` widens persisted status/audit columns and
  constrains the full explicit state set.
- `FulfillmentSagaIntegrationTests` executes courier rejection, lease release,
  reassignment, timeout, compensation, cancellation, idempotent replay, and
  payment-event absence. Lease transitions are inspected for the same order and
  include bounded reasons.

## Transaction and authority boundary

`OrderCommandService` invokes the application-level fulfillment coordinator in
the same transaction before persisting a lifecycle transition. When an assigned
order enters timeout, rejection, delivery, or compensation, the coordinator
releases the committed PostgreSQL assignment lease and the lease event is
append-only. Assignment remains idempotent through the existing command key and
the order transition remains version-checked and auditable through
`order_transitions` and Outbox events.

No payment command, table, event, refund, or settlement claim is introduced.

## Remote validation

GitHub Actions run `32649193769` passed the Java, Python/contracts, Compose,
Web static/unit/browser, and resilience jobs for checkpoint `c98ea76`.
