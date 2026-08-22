# RM-143 Traffic and Incident Travel Updates

Date: 2026-08-22

## Implemented contract

- `TravelUpdate` is immutable and versioned with an update ID, revision,
  simulated effective time, source, global multiplier, zone multipliers, edge
  delays, and incident delay.
- `DynamicTravelContext` canonicalizes updates, rejects duplicate IDs, and
  exposes a replay digest derived from the complete deterministic input.
- Network routes apply only updates active at the simulated time and only to
  the route's matching zones and edges. Point and matrix results retain the
  update metadata through the existing provider/fallback contract.
- All traffic is explicitly simulated; no live external traffic claim is made.

## Evidence

- Compute check passes 89 tests at 96.40% coverage, including time activation,
  global/zone/edge/incident perturbations, canonical ordering, replay digest,
  validation, fallback behavior, and stable metadata.
- Full available gate passes Java 60 tests, Python 89 tests at 96.40%, Web 38
  unit tests/build, and 5 schemas/15 fixtures.

## Gate decision

Local L2 traffic-model and L6 travel-robustness evidence is complete. Remote
Actions validation is required before RM-143 is finally marked passed.
