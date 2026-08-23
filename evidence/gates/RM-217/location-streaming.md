# RM-217 Live Courier Location Streaming Evidence

Date: 2026-08-23
Implementation checkpoint: pending
GitHub Actions: pending

## Scope

Courier reports now carry a positive sequence, observed event time, server
ingestion time, and online state. Java accepts only a strictly newer sequence
for the durable current row, records at most the latest 128 sequences per
courier, and projects accepted state to Redis GEO. Duplicate and stale reports
return explicit projection outcomes and do not advance the hot projection.

## Local evidence

- `./scripts/business-api.ps1 test` - PASS, 80 Java tests, including durable
  current-state and bounded-history sequence tests.
- `./scripts/business-api.ps1 resilience` - PASS, 15 resilience/application
  tests with the location projection boundary intact.
- `./scripts/compute-api.ps1 check` - PASS, 185 Python tests at 95.24% coverage,
  6 schemas, and 18 contract fixtures.
- `./scripts/web.ps1 check` - PASS, 52 Web unit tests and production build.
- `./scripts/full-gate.ps1` - PASS, including repository, Java, Compute,
  contracts, Web, and reproducibility gates.
- `./scripts/verify.ps1` - PASS repository integrity and dependency/evidence
  validation.

## Persistence and realtime boundary

Migration V15 adds `courier_location_history` with a unique
`(courier_id, location_sequence)` key and keeps only the latest 128 accepted
sequences per courier. The existing `courier_locations` row is the durable
current state. Redis GEO and SSE are downstream projections; event payloads
carry sequence, observed time, ingestion time, online state, and projection
status so consumers can discard duplicates or late reports.

Remote Actions evidence is intentionally pending until the implementation
checkpoint is pushed and the five-job workflow completes.
