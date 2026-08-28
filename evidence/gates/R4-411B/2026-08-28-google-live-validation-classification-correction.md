# R4-411B classification correction

Contract: `a2d37bd79cc433e48fc76b5a1b4ba6518592bd5a1a8ac72bc38d1c000e3285d1`

The original redacted artifact
`google-live-validation-20260828T103154Z.json` is retained unchanged. Its
transport-level matrix result was HTTP 200, but one of the four returned cells
had status `ERROR` and error class `ROUTE_EXISTS`. The initial aggregator
reported the operation as `PASS`; that aggregate label was incorrect and is
superseded by this append-only correction.

Authoritative classification is now:

- `ComputeRoutes`: `PASS` (one provider response, HTTP 200)
- `ComputeRouteMatrix`: `PARTIAL` (three successful cells, one provider error)
- Overall: `PARTIAL`
- `provider_live_validated`: `false`
- Japan Matrix entitlement: not claimed
- Production claim: false

No additional provider call was made after this correction. The original
request counts and usage ledger remain authoritative and unchanged.
