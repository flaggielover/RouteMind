# P4 Travel-Model Provider Abstraction

RM-040 defines point and matrix travel-time contracts without coupling dispatch
strategies to an external map service. `DeterministicLocalTravelProvider`
converts Haversine kilometres at a configured constant speed, making tests and
simulation reproducible. `FallbackTravelTimeProvider` bounds primary calls by
timeout, catches provider failures, and marks fallback results explicitly.

Provider identity is carried on every result and matrix. The abstraction is
stateless; it does not persist routes or become a source of business truth.

RM-140 extends the contract with an immutable `DynamicTravelContext` containing
simulated time, a deterministic traffic multiplier/profile, and incident delay
updates with stable incident identifiers. Local estimates apply the multiplier
and delay arithmetically, while simulated time remains explicit metadata so
replays are reproducible. Point and matrix results preserve provider identity,
fallback state, dimensions, and the full context metadata. Existing providers
that implement the original two-argument methods remain callable during
migration; the fallback wrapper adapts them without claiming live traffic.

RM-141 adds a bounded `TravelNetworkFixture` and replaceable
`NetworkTravelProvider`. Directed edges carry stable IDs, route seconds, and
zones; deterministic shortest-path search returns route geometry and edge/zone
metadata for both point and matrix calls. Missing nodes or routes fail with a
typed unavailable error so the existing fallback wrapper can mark substitution.
Large road graphs remain external data under `ROUTEMIND_DATA_ROOT`.

RM-142 defines the external artifact boundary used by matrices, road graphs,
and replay data. `DataArtifactManifest` is content-addressed and records
producer, revision, configuration, and seed. `DataRootArtifactAdapter` performs
symlink-aware containment and checksum verification before exposing a path;
unsafe or missing inputs fail closed and no generated payload is committed.

RM-143 adds versioned `TravelUpdate` records to the dynamic context. Updates
activate at simulated time and can perturb global traffic, named zones, route
edges, and incidents. Canonical ordering and a replay digest make fixed
scenarios reproducible; all traffic remains explicitly simulated until a live
provider is separately verified.
