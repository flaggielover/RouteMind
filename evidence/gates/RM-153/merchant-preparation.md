# RM-153 Dynamic Merchant Preparation Model

Date: 2026-08-22

## Implemented contract

- `MerchantPreparationProfile` configures baseline preparation time,
  deterministic capacity slots, bounded stochastic variability, order-profile
  multipliers, and a late-risk horizon.
- `MerchantPreparationModel` sorts orders by `(enqueued_at_seconds, order_id)`
  and schedules expected and actual preparation on stable merchant capacity
  slots. Each variable-delay order consumes exactly one seeded jitter draw;
  zero-variability profiles consume no random numbers.
- `MerchantPreparationRun.state_at` exposes queue load, status, expected/actual
  preparation and ready times, and a bounded late-preparation risk that grows
  after expected readiness until actual readiness. `states_at` provides a stable
  snapshot for simulated time.
- `MerchantPreparationState.apply_to` supplies the simulated actual-ready
  boundary to `DispatchProblem`, so dispatch can account for preparation state.
  The model remains compute-owned simulation state; Java durable order
  lifecycle and Outbox truth are unchanged.

## Evidence

- Compute check passes 96 tests at 96.16% coverage, including same-seed
  replay, changed-seed digest divergence, capacity queue evolution, expected
  versus actual readiness, late-risk progression, dispatch readiness
  propagation, and explicit invalid-input rejection.
- Canonical run payload records seed, profiles, orders, stochastic outcomes,
  capacity schedule, and ready-time provenance in a SHA-256 replay digest.

## Gate decision

Local L2 preparation-model and L6 preparation-replay evidence is complete. The
checkpoint is awaiting full repository and remote Actions validation.
