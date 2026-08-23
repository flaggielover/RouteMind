# RM-158 What-if Scenario Comparison

Date: 2026-08-23

## Goal

Give operators a bounded, reproducible way to compare a recorded baseline run
with scenario variants while keeping production truth and experimental claims
separate. The surface must expose demand, supply, preparation, traffic,
strategy, and risk inputs, and every result must carry enough provenance to
reconstruct the comparison.

## Architecture

The compute API remains the owner of scenario execution. A new framework-free
`WhatIfRunner` reuses `ScenarioManifest`, `ScenarioKernel`, the registered
strategy catalog, and the existing deterministic travel provider. It accepts a
recorded baseline manifest plus at most four bounded variants. Each variant is
immutable and contains an id, label, demand multiplier, supply delta,
preparation delay ticks, traffic multiplier, strategy, and risk multiplier.

Variant derivation is deterministic and explicit: demands are stably ordered
and truncated or repeated with stable ids within the request bound; couriers
are stably removed or added from the fixture boundary; preparation delay is
added to the kernel delay ticks; traffic is passed to the kernel; strategy is
resolved through the registry; and risk is retained in the manifest and used
only for a clearly named scenario-risk metric. No variant mutates the base
manifest or durable business state.

The API exposes `POST /api/v1/experiments/what-if`. The response includes the
baseline recording identity, a comparison digest, one result per variant, the
strategy version, assignment and timing metrics, scenario-risk metric,
replay digest, manifest digest, and output digest. Validation rejects duplicate
variant ids, unknown strategies, unsafe bounds, malformed fixtures, and more
than four variants with explicit 4xx responses.

## Web surface

The Strategy route receives a typed What-if data source and a panel with
controls for demand, supply, preparation, traffic, risk, and strategy. A
primary action runs the comparison; a secondary action clears it. Results are
shown as a compact baseline/variant comparison with assignment rate, simulated
duration, risk index, strategy identity, and provenance digests. Loading,
unavailable, and validation errors remain visible. Copy explicitly states that
these are scenario comparisons and not causal production claims.

The browser calls the compute API through a replaceable adapter. E2E tests
route-mock the endpoint, so paid services and live credentials are not needed.
The existing Operations live/demo/replay/simulation source semantics remain
unchanged.

## Failure and integrity behavior

- The runner is pure per request and has no process-global scenario state.
- Input and variant bounds are enforced at the Pydantic boundary and again in
  the domain runner.
- A failed variant returns an explicit API error; the UI never substitutes a
  fabricated metric or silently falls back to a production run.
- Digests use canonical JSON and omit wall-clock runtime, preserving
  reproducibility while still returning observed runtime as an informational
  field.
- Results are labeled `what-if`/`scenario comparison` throughout; they do not
  become live dispatch authority.

## Verification

- Python unit tests cover deterministic repeated runs, each variant dimension,
  duplicate/unknown/boundary rejection, and digest/provenance stability.
- API tests cover successful comparison and explicit 4xx failures.
- Web unit tests cover control serialization, loading/error/clear states, and
  rendered provenance/claim labeling.
- Playwright desktop/mobile tests run a mocked comparison and assert visible
  metrics, strategy identity, provenance, and the non-causal label.
- The full repository gate and the existing accessibility smoke suite remain
  mandatory before the RM-158 Evidence Gate is marked complete.
