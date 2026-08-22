# RM-151 Continuous Demand Arrival Generator

Date: 2026-08-22

## Implemented contract

- `DemandArrivalProfile` records a profile identifier, hourly rate, active tick
  window, pickup location, zone, merchant, order profile, and burst size.
- `DemandArrivalGenerator` uses a seeded pseudo-random stream and an explicit
  `ticks_per_hour` resolution. Each active tick performs one documented
  Bernoulli arrival decision with probability `min(rate / ticks_per_hour, 1)`;
  a successful decision emits the configured burst without additional random
  draws.
- Arrivals are ordered by `(tick, request_id)`. The canonical payload records
  the seed, generator resolution, profile metadata, and generated arrival
  metadata, then produces a SHA-256 replay digest.
- Profile identifiers, rates, tick windows, order profiles, burst sizes, and
  duplicate identifiers are validated explicitly. No unexplained random
  numbers are consumed.

## Evidence

- Compute check passes 92 tests at 96.34% coverage, including deterministic
  same-seed replay, changed-seed divergence, stable request identifiers,
  profile metadata propagation, and invalid-input rejection.
- `DemandEvent` carries zone, merchant, and order-profile metadata with a
  backwards-compatible standard profile default for existing simulations.
- The generator remains framework-free and compute-owned; it emits immutable
  inputs for the Digital Twin without moving durable order truth out of Java.

## Gate decision

Local L2 demand-generator and L6 demand-replay evidence is complete. Remote
Actions run `32581545061` passed all five jobs; RM-151 is fully validated.
