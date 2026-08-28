# R4-411B Google Routes provider evaluation

Status: `HUMAN_GATE_PENDING` (preparation only; no Google API call executed).

Frozen contract: `contracts/provider/r4-411b-google-routes-live-validation-v1.json`.
Canonical SHA-256 is recorded by `scripts/google_routes_contract.py`; the contract
keeps `authorized=false`, `providerLiveValidated=false`, and
`japanMatrixEntitlement=false`.

## Provider and prerequisites

The independent replacement candidate is Google Maps Platform, Google Maps Routes
API, using `ComputeRoutes` and `ComputeRouteMatrix`. The owner reports the Google
Cloud project, billing, API enablement, and key creation/configuration as complete.
The key is checked only by presence (`SET`/`MISSING`) under
`ROUTEMIND_GOOGLE_ROUTES_API_KEY`; its value is never read into evidence, logs,
tests, CI output, source, or frontend artifacts. A previously exposed key must be
rotated before any future live gate.

Google-managed processing is not asserted to be Tokyo-pinned. Japan point Routing
coverage is documented as supported; Matrix entitlement is not asserted from key
presence alone.

## Local implementation evidence

`GoogleRoutesProvider` implements the existing `TravelTimeProvider` point/matrix
seam. It emits only normalized `TravelTime`/`TravelTimeMatrix` values with provider
request digest, opaque request id, response status, and explicit error/fallback
classification. Provider JSON is not exposed to dispatch or durable business state.

The adapter has bounded timeout/retry/backoff, rate limiting, circuit breaking,
point/matrix request and element budgets, explicit 401/403/408/429/4xx/5xx,
malformed-response and missing-credential classes, partial matrix cell failures,
and the existing deterministic-local fallback remains explicit and provenance
marked. No transport is supplied by production wiring in this preparation, so no
live I/O is possible through the new code alone.

The request contract permits only synthetic Tokyo coordinates, departure time,
travel mode, routing preference, and an opaque request id. Tenant, customer,
courier, merchant, order, contact, name, textual address, and durable domain
serialization are forbidden. The fixture is synthetic-only and carries committed
provenance.

## Future bounded execution boundary

Only a separately approved execution contract may permit at most 20 point calls,
5 matrix calls, 100 matrix elements, 30 minutes, and USD 1. Account/resource
creation is forbidden. Unexpected quota, entitlement, billing, response, or
processing-region behavior fails closed. Real sends/calls are currently not
authorized.

Local tests cover point and matrix normalization, partial failures, timeout and
retry bounds, 401/403/429/5xx, malformed responses, missing credentials, circuit
open, explicit fallback, budget limits, provenance, and outbound data minimization.
Contract mutation tests and repository leakage gates are required before any
Human Gate closure.

## Required Human Gate statement

I approve R4-411B contract SHA-256 `a2d37bd79cc433e48fc76b5a1b4ba6518592bd5a1a8ac72bc38d1c000e3285d1`, authorize Google Maps
Platform Routes API `ComputeRoutes` and `ComputeRouteMatrix` for synthetic Tokyo
coordinates only, confirm key rotation and secure process-scoped injection of
`ROUTEMIND_GOOGLE_ROUTES_API_KEY`, accept Google-managed processing that is not
asserted Tokyo-region-pinned and that Matrix Japan entitlement remains separately
unconfirmed, and authorize only the separately bounded execution contract of at
most 20 point requests, 5 matrix requests, 100 matrix elements, 30 minutes, and
USD 1. This approval does not authorize account creation or live calls beyond that
execution contract.
