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
