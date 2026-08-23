# ADR-0019: Descriptive ETA Delay Accounting Boundary

Date: 2026-08-24
Status: Accepted

## Context

The ETA baseline and calibration contract provide component estimates and
outcome metrics, but operations also need to explain where an observed order
duration was accounted for. That explanation must not be mistaken for a causal
model, especially when events are incomplete or combine wall and simulated
clocks.

## Decision

Expose a Python compute endpoint that accepts per-record observed duration and
the five known ETA components: dispatch, travel, preparation, pickup, and
delivery. Every component is normalized into that stable order. Missing values
remain explicit, component sums and residuals are returned, and a record is
`RECONCILED` only when all components use the record clock domain and sum to the
observed duration within a small tolerance. Incomplete records are
`INCOMPLETE`; non-zero residuals are `UNRECONCILED`; mixed clocks are
`CLOCK_DOMAIN_MISMATCH` and do not report a residual as trustworthy.

The aggregate is a deterministic sum of record observations and accounted
components with a canonical digest. The API label is
`accounting decomposition; not causal inference`. No Java order state or
disciplinary decision is mutated.

## Consequences

Consumers can audit arithmetic reconciliation and data quality without
inventing missing durations. Simulated replay data cannot silently combine with
wall-clock observations. Residuals identify unaccounted duration, but they do
not identify causes; causal attribution and customer claims require later
lineage and research evidence.
