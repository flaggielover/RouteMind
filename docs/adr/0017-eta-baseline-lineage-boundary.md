# ADR-0017: Honest ETA Baseline and Lineage Boundary

Date: 2026-08-24
Status: Accepted

## Context

ETA needs one composable contract spanning dispatch wait, travel, merchant
preparation, pickup, and delivery. The repository has deterministic travel and
preparation capabilities but no evidence to claim calibrated production
accuracy.

## Decision

Expose a Python-owned deterministic ETA baseline. A prediction includes the
timestamp, requested horizon, explicit component values/sources, model and
version, canonical input SHA-256 digest, predicted delivery time when all
required components exist, and an optional observed delivery outcome. Missing
preparation data leaves the prediction unavailable rather than silently
imputing a value. The endpoint labels the result as a baseline and not
calibrated production accuracy. Java order state remains authoritative; this
read-oriented contract does not write or alter fulfillment state.

## Consequences

Consumers can compare a baseline prediction with a later actual outcome using a
stable input digest. The contract is suitable for later calibration and delay
accounting, but it does not claim MAE, coverage, SLA confidence, or model
quality until RM-220 provides data-backed evidence.
