# RM-141 Network and Zone Travel Provider

Date: 2026-08-22

## Implemented contract

- `TravelNetworkFixture` defines bounded nodes and directed edges with stable
  IDs, route seconds, and explicit zone metadata; topology validation rejects
  duplicate IDs, duplicate locations, and unknown endpoints.
- `NetworkTravelProvider` uses deterministic shortest-path search with edge-ID
  tie ordering, returns route geometry, edge IDs, and edge zones, and reuses the
  same provider for point and matrix estimates.
- Unavailable nodes and routes raise `NetworkRouteUnavailableError`, allowing
  the existing bounded fallback wrapper to mark provider substitution without
  hiding the failure. No external map service is claimed.

## Evidence

- Compute check passes 80 tests at 95.32% coverage, including deterministic
  tie-breaking, geometry/edge/zone metadata, matrix estimates, same-node
  routes, topology validation, unavailable routes, and fallback behavior.
- Full available gate passes Java 60 tests, Python 80 tests at 95.32%, Web 38
  unit tests/build, and 5 schemas/15 fixtures.

## Gate decision

Local L2 network-travel and L6 route-correctness evidence is complete. Remote
Actions run `32577972174` passed all five jobs; RM-141 is fully validated.
