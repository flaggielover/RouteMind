# ADR-0016: Location Integrity and Privacy-Bounded Hotspots

Date: 2026-08-24
Status: Accepted

## Context

Sequenced location history prevents stale writes but does not explain whether
reports imply impossible movement, event-time gaps, or an offline courier.
Operations also needs aggregate location concentration without exposing raw
trajectories or courier identities to analytical consumers.

## Decision

Keep integrity analysis in the Python compute domain as a deterministic,
read-oriented signal. It compares adjacent accepted sequences and reports
explicit `HEALTHY`, `DEGRADED`, `SUSPECT`, or `STALE` states with machine-readable
signals for duplicate/sequence gaps, event-time regression, impossible speed,
staleness, offline state, and ingestion lag. The API labels the result as an
operational signal and never bans, pauses, or otherwise disciplines a courier.

Hotspots use bounded grid aggregation and require at least three distinct
couriers per cell by default. Responses contain only cell coordinates,
observation count, and unique-courier count; raw points and courier IDs are not
returned. Inputs are capped at 1,000 observations per request and the library
has a 10,000-observation safety bound. Java remains the authority for accepted
location state and Redis remains a hot projection.

## Consequences

Operations can investigate location quality and concentration with explicit
limits and reproducible digests. A signal is not proof of fraud or a causal
explanation; threshold tuning and calibration require later evidence. The
privacy threshold reduces usefulness for sparse areas by design.
