# RM-130 Constraint-Aware Dispatch Model

Date: 2026-08-22

## Implemented contract

- `DispatchProblem` remains backward compatible for existing strategies while
  accepting demand units, pickup readiness, service duration, delivery windows,
  and a maximum service-risk threshold.
- `CourierCandidate` now carries capacity/current load, availability bounds,
  explicit state, service risk, and estimated travel seconds. Validation rejects
  non-finite or contradictory values at the compute boundary.
- A shared eligibility evaluator filters every registered baseline strategy. It
  deterministically explains unavailable state, insufficient capacity, excessive
  risk, courier shift cutoff, and missed delivery-window constraints. No eligible
  candidate produces an explicit unassigned decision with reasons.
- The dispatch API accepts the optional constraint fields and returns eligible
  candidate counts plus infeasibility metadata without mutating durable business
  state.

## Evidence

- Compute check passes 65 tests with 96.47% coverage, including API selection and
  explicit infeasibility cases for state, capacity, risk, time windows, and shift
  availability.
- Dispatch request schema and the valid fixture include the optional constraint
  contract. Repository validation passes 5 schemas and 15 contract fixtures.
- Full available gate passes Java 60 tests, Python 65 tests at 96.47%, Web 38 unit
  tests/build, and repository integrity checks.

## Gate decision

Local L2 dispatch-model and L6 dispatch-correctness evidence is complete. Actions
run `32575824899` passed all five jobs, including Python compute/contracts and the
bounded degradation gate. RM-130 is fully validated.
