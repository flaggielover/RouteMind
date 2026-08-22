# P5 Seeded Digital Twin Kernel

RM-050 represents demand, courier supply, delay choices, traffic multiplier, and
seed in an immutable `ScenarioManifest`. `ScenarioKernel` processes events in a
stable `(tick, request_id)` order, delegates dispatch and travel decisions to
the existing registries/providers, and emits assignment state transitions.

Each run is summarized into canonical JSON and a SHA-256 replay digest. The
same manifest and seed therefore produce byte-identical decisions and state
transitions; changing seed or scenario inputs changes provenance without adding
durable state to the compute runtime.

RM-150 makes the clock boundary explicit with `TwinClock`: simulated ticks and
seconds advance deterministically, while wall-clock elapsed time is observation
only and excluded from replay identity. The kernel records the simulated end
tick and remains framework-free and compute-owned.

RM-151 adds `DemandArrivalProfile` and `DemandArrivalGenerator` as the seeded
arrival boundary for continuous scenarios. Rates are converted to explicit
per-tick Bernoulli decisions, burst expansion is deterministic, and profile
metadata travels with each immutable `DemandEvent`. The canonical seed,
profiles, arrivals, and SHA-256 digest make generated demand replayable without
introducing durable business state into the compute runtime.

RM-153 adds `MerchantPreparationModel` as a simulation-only preparation
boundary. Merchant profiles define baseline time, capacity slots, profile
multipliers, and bounded seeded variability; each run records expected and
actual schedule outcomes in its replay digest. State snapshots expose queue
load, ready times, and late-preparation risk, while `apply_to` lets dispatch
consume the current simulated readiness without transferring durable lifecycle
ownership from Java.

RM-154 adds a single perturbation boundary for traffic, courier supply,
merchant delay, and dependency-failure scenarios. Each event has an explicit
scope, simulated-time window, source, and bounded effect; traffic events reuse
the versioned travel context, while failure metrics distinguish simulated
injection from live dependency failure. Active events and their metric effects
are part of the replayable scenario snapshot, not hidden mutable state.
