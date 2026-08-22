# RM-140 Dynamic Travel Model Contract

Date: 2026-08-22

## Implemented contract

- `DynamicTravelContext` carries simulated time, traffic multiplier/profile,
  incident delay, and canonical incident identifiers as immutable inputs.
- The deterministic local provider applies traffic and incident inputs
  arithmetically while retaining simulated time as replay metadata.
- Point and matrix results preserve provider, fallback, dimensions, and full
  context metadata. `with_incident` creates an explicit immutable update.
- The fallback provider forwards context to modern providers and keeps older
  two-argument providers usable during migration; fallback results are marked
  at both cell and matrix level.

## Evidence

- Compute check passes 76 tests at 95.80% coverage, including fixed-input
  reproducibility, context validation, incident updates, point/matrix metadata,
  fallback context propagation, and legacy provider compatibility.
- Full available gate passes Java 60 tests, Python 76 tests at 95.80%, Web 38
  unit tests/build, and 5 schemas/15 fixtures.
- No live traffic provider or production traffic claim is made; all dynamic
  behavior is deterministic and provider-neutral.

## Gate decision

Local L1 travel-contract and L2 dynamic-travel evidence is complete. Remote
Actions validation is required before RM-140 is finally marked passed.
