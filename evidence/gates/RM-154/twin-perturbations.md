# RM-154 Digital Twin Perturbations

Date: 2026-08-22

## Implemented contract

- `ScenarioPerturbation` is an explicit, bounded scenario input with kind,
  target scope, effective window, source, and effect parameters. Supported
  kinds are traffic, courier supply, merchant delay, and dependency failure.
- `PerturbationScenario` validates unique identifiers and stable ordering;
  `PerturbationRun` records the complete scenario, seed, and canonical SHA-256
  replay digest.
- `state_at` emits active perturbation events and metrics at simulated time:
  traffic multipliers/delays are converted to the existing
  `DynamicTravelContext`/`TravelUpdate` contract, supply changes are clamped at
  zero, merchant delays aggregate by merchant, and dependency failures are
  reported explicitly.
- Failure metrics keep simulated injection separate from live dependency
  failure. No live service is claimed by a simulated event, and no unbounded
  random or network behavior is introduced.

## Evidence

- Compute check passes 100 tests at 95.96% coverage, including seeded replay,
  stable ordering, active windows, traffic context propagation, supply and
  merchant metric effects, dependency source separation, and invalid-input
  rejection.
- Full repository gate passes Java 60 tests, Python 100 tests at 95.96%, Web 38
  unit tests/build, and 5 schemas/15 fixtures.

## Gate decision

Local L2 twin-perturbation, L5 simulation-failure, and L6 robustness evidence
is complete. GitHub Actions run `32582936237` passed all five required jobs
(Java, Python, control plane/resilience, and Web browser smoke), so RM-154 is
fully validated.
