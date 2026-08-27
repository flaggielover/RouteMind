# R4-410 Travel Provider Human Gate Preparation

## Gate classification

R4-410 remains `BLOCKED / PREPARED_TRAVEL_PROVIDER_HUMAN_GATE`. This artifact
does not select, register, authenticate to, call, spend against, or validate an
external travel provider. The deterministic local provider remains the only
validated runtime provider.

Canonical preparation contract:

```text
contract = contracts/provider/r4-410-travel-provider-human-gate-v1.json
sha256 = 7f71f018a6d22fe1ee7f70026edda71149ea38efdbe87b82860861579e4675d7
recommended_candidate = HERE_MATRIX_ROUTING_V8
selected_provider = UNAPPROVED
live_calls_authorized = false
maximum_live_call_spend_if_separately_authorized = USD 1
```

## Original Evidence Contract audit

- Point and matrix inputs, time context, units, partial-result handling, 1.5
  second timeout, one retry, quota/cost evidence, and provider request identity
  are explicit.
- The only outbound business data allowed is the minimum synthetic coordinate,
  departure-time, transport-mode, and opaque-request identity set. Tenant,
  principal, order, courier, address, phone, email, and message fields are
  forbidden.
- `ROUTEMIND_TRAVEL_PROVIDER_API_KEY` is an external secret name, never a value
  in Git, logs, evidence, or chat.
- Timeout, exception, invalid result, or partial matrix fails closed to the
  existing deterministic local provider. Fallback results may not be described
  as provider truth.
- A provider name is not validated by documentation or contract preparation.
  R4-411 still requires separately approved live evidence.

## Candidate comparison

HERE Matrix Routing v8 is the recommended contract candidate because its
official documentation describes point/time-aware routing and matrices up to
10,000 origins and 10,000 destinations, while its Base Plan is transaction
metered. Google Routes is a strong alternative with per-element matrix billing;
the official limits are 625 non-transit elements and 100 elements for
`TRAFFIC_AWARE_OPTIMAL`. Mapbox is simpler but the documented
`mapbox/driving-traffic` matrix is limited to ten coordinates.

Sources inspected 2026-08-27:

- <https://docs.here.com/routing/docs/matrix-v8-intro>
- <https://www.here.com/get-started/pricing>
- <https://developers.google.com/maps/documentation/routes/compute_route_matrix>
- <https://developers.google.com/maps/documentation/routes/usage-and-billing>
- <https://docs.mapbox.com/api/navigation/matrix/>

Capability fit is not privacy approval. The owner must separately accept the
HERE contract/DPA, processing locations, Tokyo synthetic-coordinate use, and
billing ownership. No RouteMind evidence claims HERE data residency.

## Bounded future evidence

A later R4-411 execution contract, with its own digest and Human Gate, is required
before any live call. It is bounded to 30 minutes, 20 point calls, five matrix
requests, 100 total matrix elements, and USD 1. Evidence must retain observed
semantics, error/quota behavior, fallback transitions, cost, timestamps,
versions, artifact digests, and a zero-finding leakage scan.

## R4-410 Human Gate

Minimum human action:

```text
I approve R4-410 contract SHA-256 7f71f018a6d22fe1ee7f70026edda71149ea38efdbe87b82860861579e4675d7, ratify HERE Matrix Routing v8 as the RouteMind candidate travel provider, and accept the reviewed provider contract/DPA, processing locations, synthetic Tokyo coordinate privacy boundary, and billing ownership. This approval freezes R4-410 only and does not authorize live provider calls.
```

After ratification, credentials must be configured through the secure external
location named by `ROUTEMIND_TRAVEL_PROVIDER_API_KEY`; the value must not be sent
in chat. Live calls remain prohibited until a new exact R4-411 contract is
generated and separately approved.
