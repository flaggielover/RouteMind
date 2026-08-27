# R4-410 Travel Provider Human Gate Preparation

## Gate classification

R4-410 remains `BLOCKED / PREPARED_TRAVEL_PROVIDER_HUMAN_GATE`. This artifact
does not select, register, authenticate to, call, spend against, or validate an
external travel provider. The deterministic local provider remains the only
validated runtime provider.

The prior v1 contract remains immutable history at canonical SHA-256
`7f71f018a6d22fe1ee7f70026edda71149ea38efdbe87b82860861579e4675d7`.
The 2026-08-27 official-source audit found that v1 combined point and matrix
routing under one product name and did not elevate the documented Japan access
restriction or non-region-pinned processing boundary. It is superseded, not
approved or reinterpreted.

Current canonical preparation contract:

```text
contract = contracts/provider/r4-410-travel-provider-human-gate-v2.json
sha256 = 6d71059d2db366ce0ab3e54b7959f532346b0875101ebc1ab8da9189e8b3ac5c
recommended_provider = HERE_TECHNOLOGIES
point_product = HERE_ROUTING_API_V8
matrix_product = HERE_MATRIX_ROUTING_API_V8
selected_provider = UNAPPROVED
Japan_service_eligibility = UNCONFIRMED_REQUIRES_HERE
processing_region = NOT_REGION_PINNED
live_calls_authorized = false
allowed_live_calls_at_this_gate = 0
```

## Provider and product audit

The recommended candidate is HERE Technologies using two separate products:

- HERE Routing API v8, `GET https://router.hereapi.com/v8/routes`, for point
  routes.
- HERE Matrix Routing API v8,
  `POST https://matrix.router.hereapi.com/v8/matrix`, using bounded synchronous
  `async=false` requests for any later validation.

HERE documents point routes, time-aware routing, distance and duration, and
matrices up to 10,000 origins by 10,000 destinations. Capability documentation
does not prove RouteMind account entitlement, live quality, or production
fitness. The current Matrix Routing documentation states that access to the
Routing service in the Japan region is restricted and requires contacting HERE.
R4-410 therefore cannot assume that synthetic Tokyo requests are enabled.

Sources inspected 2026-08-27:

- <https://docs.here.com/routing/docs/routing-v8-intro>
- <https://docs.here.com/routing/docs/routing-v8-get-started>
- <https://docs.here.com/routing/docs/matrix-v8-intro>
- <https://docs.here.com/routing/docs/matrix-v8-get-started>
- <https://www.here.com/get-started/pricing>
- <https://legal.here.com/en-gb/data-protection-addendum>
- <https://www.here.com/en-gb/privacy/subprocessor-list>

Google Routes and Mapbox remain alternatives. No alternative was selected or
validated, and no provider account was created during this audit.

## Privacy and processing boundary

The only fields allowed to leave RouteMind in a later, separately approved live
validation are:

- origin and destination coordinates;
- departure time and transport mode;
- matrix origin/destination coordinates and a derived region definition;
- an opaque request identifier with no tenant, order, courier, principal, or
  customer meaning.

Tenant, principal, order, courier, name, street address, phone, email, message
body, credentials, and all durable business identifiers are forbidden. The live
fixture is synthetic Tokyo coordinates only. Raw coordinates, request query
strings, provider response bodies, provider request identifiers, and credentials
are forbidden from telemetry and committed evidence.

`processing_region = NOT_REGION_PINNED`. HERE's DPA permits storage or processing
in a country different from where a service is provided, and the published
subprocessor list includes multiple processing locations. Tokyo appears among
one subprocessor's possible locations but is not a Tokyo-only guarantee. The
privacy implication is explicit: synthetic location and time data leave
RouteMind control and may be processed outside Tokyo or Japan. No Tokyo data
residency claim is made.

## Credentials, budget, and fallback

No secret is required or accepted at the R4-410 gate. A later R4-411 live
validation would require the secret name
`ROUTEMIND_TRAVEL_PROVIDER_API_KEY`, injected from an external secret store or
process environment. Its value is forbidden in Git, logs, evidence, URLs shown
in diagnostics, and chat.

R4-410 authorizes zero live calls and zero spend. If R4-410 is ratified, a new
R4-411 execution contract and independent Human Gate would still be required.
The current future ceiling is 30 minutes, 20 point calls, five matrix requests,
100 total matrix elements, and USD 1. That ceiling is not present authority.

There is no fail-open provider behavior. Timeout, exception, invalid result,
partial matrix, quota rejection, or Japan entitlement failure closes the
external provider path and transitions to the deterministic local provider with
an explicit reason and provenance. Fallback cannot change durable business truth
or be represented as HERE truth.

## Evidence Contract

A later R4-411 validation must retain all of the following without secrets:

- HERE account and application identity plus confirmed Japan service eligibility;
- accepted contract/DPA and non-region-pinned processing decision;
- observed point and synchronous matrix product semantics;
- time context, units, synthetic fixture identity, and request counts;
- quota, timeout, error, invalid, and partial-matrix behavior;
- deterministic fallback transition, reason, and provenance;
- privacy and secret leakage scan;
- actual or conservative cost;
- timestamps, versions, and artifact digests.

Documentation alone satisfies none of those live evidence items.

## R4-410 Travel Provider Human Gate

Minimum exact human action:

```text
I approve R4-410 contract SHA-256 6d71059d2db366ce0ab3e54b7959f532346b0875101ebc1ab8da9189e8b3ac5c, ratify HERE Technologies using HERE Routing API v8 and HERE Matrix Routing API v8 as the RouteMind candidate travel provider, accept that Japan-region Routing service access requires HERE confirmation and that processing is not Tokyo-region-pinned under the reviewed HERE contract/DPA/subprocessor locations, accept the synthetic Tokyo coordinate privacy boundary and billing ownership, and acknowledge that this approval authorizes zero account creation and zero live calls.
```

After ratification, R4-410 may close as a frozen provider contract, not as live or
production validation. Account setup, Japan entitlement confirmation, credential
configuration, budget authorization, and any provider call remain R4-411 work
behind a new exact contract and Human Gate. R4-422 remains an independent gate.

Local validation passed eleven directed contract mutation tests, the Round 4
graph and active-mirror gate, tracked-secret isolation, supply-chain controls,
Compose validation, PowerShell syntax, and the complete repository
`scripts/verify.ps1` gate. Real GitHub Actions remains required for this
checkpoint before the Human Gate is declared ready.
