# External and Downstream Blocker Inventory

Evaluated: 2026-09-02 (Asia/Shanghai)

These thirteen tasks have no remaining ordinary local implementation. Their
task-specific evidence records preserve preparation and prohibit substitution
of local/synthetic output for an external or downstream result.

## Production target chain

- `R4-405` — `blocked`; local telemetry/cost-attribution preparation is passed.
  Exact blocker: frozen inconclusive Vultr VKE/Tokyo VM target evidence and no
  authorized paid retry. Reactivate only from a new target Evidence Contract and
  Human Gate.
- `R4-406` — `blocked`; backup/restore/reconciliation tooling and prior attempts
  are retained. Exact blocker: no qualified cross-target restore with RPO/RTO,
  reconciliation, isolation and rollback evidence. Reactivate with an authorized
  independent target after R4-405 target qualification.
- `R4-407` — `blocked`; workload/chaos/incident tooling is ready. Exact blocker:
  R4-405/R4-406 target qualifications. Reactivate with a budgeted Human Gate.
- `R4-408` — `blocked`; staged-release gates and rollback tests are ready. Exact
  blocker: no R4-407-qualified target/run. Reactivate only after R4-407 passes.
- `R4-409` — `blocked`; closure audit plumbing is ready. Exact blocker: R4-408
  has no staged-deployment evidence. Reactivate only after the full production
  chain passes.

## Provider and product chains

- `R4-411` — `deferred_external`; HERE retirement, support outcome and prior
  attempts are terminally recorded. Exact blocker: no selected/approved live
  replacement-provider Human Gate in this historical task. Reactivation is via
  the separately controlled replacement-provider gate, never by rewriting HERE
  history.
- `R4-412` — `blocked`; provider-neutral dynamic matrices, traffic, incidents,
  fallback and lineage are locally ready. Exact blocker: no authorized live
  replacement-provider stream. Reactivate after provider approval/evidence.
- `R4-413` — `blocked`; local travel lane is ready. Exact blocker: R4-412 live
  evidence. Reactivate only after R4-412 passes.
- `R4-422` — `blocked`; consent, privacy, retries, Gmail adapter, credential
  recovery and one synthetic receipt observation are retained. Exact blocker:
  no provider-wide delivery/bounce/failure/SLA/production reliability evidence.
  Reactivate only under a new exact provider Evidence Contract and Human Gate.
- `R4-424` — `blocked`; local accessibility/browser/product checks are ready.
  Exact blocker: R4-422 notification reliability. Reactivate after R4-422
  passes; one receipt cannot establish end-to-end production closure.

## Data, powered execution and independent reproduction

- `R4-431` — `blocked`; observed-data schemas, split/calibration/held-out
  pipelines, provenance and negative paths are ready. Exact blocker: no
  owner-authorized observed Twin dataset with consent/privacy/retention/split/
  deletion approvals. Reactivate when such data is approved under
  `ROUTEMIND_DATA_ROOT`; synthetic fixtures are ineligible.
- `R4-436` — `deferred_external`; scheduler, RADS implementations,
  instrumentation and artifact retention are ready. Exact blocker: R4-435
  scientific preregistration plus owner-approved compute/cost. Reactivate only
  from the frozen preregistration and resource Human Gate.
- `R4-460` — `blocked`; independent-reproduction package and prior attempt are
  retained. Exact blocker: independent operator/environment plus terminal
  R4-411, R4-433 and R4-436 inputs. Reactivate only when all are available.

None of these dispositions asserts production readiness, provider truth,
observed-data fidelity, powered significance, or independent reproduction.
