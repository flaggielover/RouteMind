# RM-150 Continuous Digital Twin State Kernel

Date: 2026-08-22

## Implemented contract

- `TwinClock` advances simulated ticks explicitly and exposes simulated seconds;
  it cannot move backward and never derives simulation time from wall clock.
- `ScenarioKernel` advances the clock in stable demand order, applies seeded
  delay choices, emits assignment transitions, and records the deterministic
  simulated end tick in run provenance.
- Wall-clock elapsed time is an observation-only field excluded from equality
  and replay digest, so repeated fixed-input runs remain byte-identical while
  simulation and execution time stay distinct.

## Evidence

- Compute check passes 90 tests at 96.37% coverage, including deterministic
  replay, seed provenance, explicit clock separation, forward-only advancement,
  state transitions, travel availability, and unassigned behavior.
- Full available gate passes Java 60 tests, Python 90 tests at 96.37%, Web 38
  unit tests/build, and 5 schemas/15 fixtures.
- The kernel remains framework-free and compute-owned; no durable business state
  is moved from Java.

## Gate decision

Local L2 twin-kernel and L6 simulation-reproducibility evidence is complete.
Remote Actions validation is required before RM-150 is finally marked passed.
