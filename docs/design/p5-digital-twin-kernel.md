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
