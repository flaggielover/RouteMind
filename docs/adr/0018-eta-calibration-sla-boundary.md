# ADR-0018: Evidence-Gated ETA Calibration and SLA Risk

Date: 2026-08-24
Status: Accepted

## Context

The RM-219 ETA baseline records prediction inputs and optional observed
outcomes, but a deterministic baseline is not calibrated accuracy. Consumers
need a bounded way to evaluate error and classify SLA exposure without turning
small or missing samples into customer promises.

## Decision

Keep calibration in the Python compute boundary and accept only explicit,
uniquely identified prediction/outcome samples. When samples exist, calculate
MAE, median absolute error, interpolated p90 absolute error, and interval
coverage for intervals that include both bounds. When samples are absent, all
calibration metrics remain `UNAVAILABLE` and no customer confidence is emitted.

Expose deterministic SLA labels using the predicted duration and SLA budget:
`ON_TRACK` at or below 90%, `AT_RISK` above 90% through 100%, and
`LIKELY_LATE` above 100%. The response is labeled calibration evidence only,
not a customer guarantee. The endpoint is read-oriented; Java remains the
owner of durable order state and no calibration result changes fulfillment.

## Consequences

Calibration can be replayed from a canonical digest and extended with real
outcomes later. The explicit unavailable state prevents fixture-only accuracy
claims and gates customer-facing confidence until evidence exists. SLA risk is
a transparent threshold classification, not a causal or probabilistic claim.
