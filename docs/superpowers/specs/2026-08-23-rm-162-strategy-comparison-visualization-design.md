# RM-162 Strategy Comparison Visualizations

Date: 2026-08-23

## Goal

Make strategy comparisons inspectable on the Strategy route without presenting
unsupported metrics as facts. The view must project actual metrics returned by
the recorded What-if/RouteBench run, expose manifest and lineage identifiers,
and show unavailable metrics explicitly.

## Design

Extend the existing What-if adapter with a bounded `runMany` operation so one
request can compare the recorded baseline with up to four strategy variants.
The Strategy Comparison panel selects a candidate strategy and runs a
comparison against the same recorded fixture. The panel renders horizontal
metric bars for assignment rate, simulated duration, observed compute runtime,
and scenario-risk index using the API values. It also renders a fixed metric
inventory for completion, overtime, distance, utilization, fairness, and cost;
these remain `Unavailable from recorded run` until a producer supplies them.

Every comparison keeps the `recorded_run_id`, comparison digest, variant
strategy/version, replay digest, manifest digest, and output digest visible for
inspection. The copy distinguishes `scenario comparison` from production
authority and never ranks a strategy using an unavailable metric.

The existing What-if control panel remains the variant authoring surface. The
new panel is read-only apart from the comparison request and does not mutate
Java state, simulation state, or strategy registry state. No new service or
charting dependency is introduced; CSS grid/flex bars provide stable,
accessible visualization primitives.

## Failure and verification

API errors, loading, empty, and unavailable states are visible and retryable.
Unit tests cover multi-variant request serialization and metric availability;
component tests cover bars, unavailable labels, provenance, clear, and errors.
Playwright desktop/mobile tests run a mocked multi-strategy comparison and
assert the actual metric values, unavailable inventory, and provenance labels.
Full compute, Web, browser, and control-plane gates remain mandatory.
