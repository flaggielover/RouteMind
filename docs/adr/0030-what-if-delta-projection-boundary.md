# ADR-0030: What-if Delta Projection Boundary

Date: 2026-08-24  
Status: Accepted

## Context

The compute What-if runner already returns bounded baseline and variant metrics,
manifests, replay digests, and output digests. Operators need the difference
against the recorded baseline without turning a scenario comparison into a
production score or causal claim.

## Decision

Web derives a pure `projectWhatIfDeltas` projection. It compares each variant
with the `baseline` result and reports coverage objective delta, simulated
duration delta, risk delta, changed/unchanged status, and source replay/output
digests. The objective is explicitly the recorded coverage objective
(`assignment_rate`); no combined score is invented.

## Consequences

- Delta values are reproducible from the existing comparison payload and remain
  linked to the recorded run and digests.
- A missing baseline yields no delta projection instead of an implicit guess.
- The panel labels results as bounded counterfactual computation and not a
  causal production claim.
