# RM-204 Assignment Lease Protocol Evidence

Date: 2026-08-23

## Scope

The Java business authority now reserves, commits, expires, and releases a durable
assignment lease. PostgreSQL migration V11 creates the current one-row-per-courier
lease table and append-only transition events. Assignment audit rows and the
`dispatch.assignment.applied` outbox payload carry `leaseId` and `leaseGeneration`.

## Executable evidence

- `./scripts/business-api.ps1 -Action test`
  - Maven BUILD SUCCESS
  - 66 tests, 0 failures, 0 errors
  - Flyway migrations 1 through 11 applied and Hibernate schema validation passed
- `BusinessApiApplicationTests.assignmentLeasePreventsOneCourierBeingCommittedToTwoOrders`
  - two confirmed orders compete for one courier
  - first assignment commits one durable lease
  - second decision receives `courier_already_assigned`
  - exactly one committed current lease and two auditable lease events remain
- `DispatchAssignmentLeaseEntityTests`
  - duplicate commit is idempotent
  - stale generation is rejected
  - commit before expiry, expiry at boundary, and post-expiry commit rejection
  - release and duplicate release are bounded and auditable by repository contract
- `DispatchAssignmentLeaseTests`
  - active window is explicit and expires at the boundary
  - replacement uses a new lease id and higher generation

## Authority and recovery

The lease repository uses a pessimistic courier-row lock inside a Spring transaction.
Order state remains authoritative in Java and PostgreSQL; a failed order transition
rolls the reservation back. Expiry and release are explicit methods and append an
event with a reason, providing a bounded recovery seam for a scheduler or courier
acknowledgement workflow. Redis is not used as durable lease truth.

## Residual scope

The 30-second TTL is an application default and should be configured per dispatch
policy once courier acknowledgement SLA is available. A background expiry worker and
external courier acknowledgement API are intentionally staged for a later task; the
current protocol already prevents stale or expired decisions from committing.
