# ADR 0011: Central semantic metric registry

- Status: Accepted
- Date: 2026-08-23

## Context

RouteMind has operational Web views, repeatable reports, and higher-level agent
analysis. Computing similarly named metrics independently in each consumer would
allow denominator, time-window, and missing-data semantics to drift. The
reproducible DuckDB marts provide an analytical source, but not metric meaning.

## Decision

Maintain a versioned Python registry of named metric definitions and evaluate
only registry-owned SQL against a read-only DuckDB connection. Each definition
declares its unit, exact source fields, aggregation, numerator, denominator,
UTC event-time semantics, and unavailable behavior. Web, report, and agent
catalog requests resolve to the same definitions and SHA-256 definition
digests. Public APIs expose definitions, not executable SQL.

Ratio metrics with no eligible denominator are unavailable rather than zero.
Count metrics over empty windows are zero. Analytical results remain read models
and have no authority to mutate Java-owned durable business state.

## Consequences

- Metric drift becomes detectable through definition digests and tests.
- Adding a metric requires an explicit denominator and missing-data policy.
- Arbitrary user SQL is outside the API and registry contract.
- Later dashboards, reports, and agents can carry the definition digest as
  lineage without duplicating calculations.
