# R4-411 HERE provider retirement

Date: 2026-08-28  
Status: `CLOSED_NOT_SELECTED / SUPERSEDED_BY_GOOGLE / NO_LIVE_CLAIM`

The non-sensitive outcome of HERE support ticket `CS0184597` records that Japan
Matrix Routing API v8 access is a commercial entitlement inquiry requiring the
HERE sales path. RouteMind will not pursue that path. HERE is therefore retired
from the active provider/runtime/deployment selection and replaced by the
independent Google Maps Routes path.

No HERE account identifier, API key value, provider response, or live request is
stored here. No HERE live validation was performed and no production claim is
made. The frozen HERE contracts and all prior failure, preparation, cost, and
teardown evidence remain immutable historical records.

## Active boundary

- Active primary: `GoogleRoutesProvider` (zero live calls authorized by the
  current Google contract).
- Deterministic fallback: `LocalRoutingProvider`/`deterministic-local` with
  explicit fallback provenance and no durable-truth substitution.
- Active secret name: `ROUTEMIND_GOOGLE_ROUTES_API_KEY` (presence-only checks).
- Retired secret name: `ROUTEMIND_TRAVEL_PROVIDER_API_KEY`; it is not an active
  runtime/configuration requirement.
- Google live validation remains a separate Human Gate under R4-411B.

## Residue classification

- A: historical HERE contracts and evidence are retained for audit.
- B: historical ADRs and frozen-contract validators are retained and labeled.
- C-G: no HERE runtime adapter/dependency remains; active config, tests, and
  documentation use the provider-neutral/Google boundary.

R3-325 remains frozen as `E-PASS / X-PASS / S-FAIL / C-NO-CLAIM`.
