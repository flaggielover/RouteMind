# R4-411B Matrix Partial Root Cause Audit

Audit date: 2026-08-28  
Contract: `a2d37bd79cc433e48fc76b5a1b4ba6518592bd5a1a8ac72bc38d1c000e3285d1`  
Mode: offline only; no Google call was made for this audit.

## Frozen observation

The append-only live artifact
`google-live-validation-20260828T103154Z.json` remains unchanged. Its
`ComputeRouteMatrix` response was received at HTTP 200 and contains four
normalized cells: three `OK` cells and one `ERROR` cell. The failing cell is
matrix row `1`, column `0`:

- origin fixture: `SHINJUKU`
- destination fixture: `SHINJUKU`
- fixture coordinates: `(35.689592, 139.700413)` to the same coordinate
- normalized status: `ERROR`
- normalized provider error class: `ROUTE_EXISTS`
- normalized distance: absent (`null`)
- normalized duration: `0`
- fallback: not used
- transport response status: `200`

The persisted artifact is redacted and does not retain the raw provider JSON
body. Therefore this audit cannot establish whether `ROUTE_EXISTS` came from
the provider `condition` field or `status` field, nor can it infer an
unrecorded provider diagnostic message.

## Endpoint and payload cross-check

The committed synthetic fixture is:

- `TOKYO_STATION`: `(35.681236, 139.767125)`
- `SHINJUKU`: `(35.689592, 139.700413)`
- `SHIBUYA`: `(35.658034, 139.701636)`

The point call is `TOKYO_STATION -> SHINJUKU`. It is successful and has the
same normalized distance and duration as matrix cell `[0][0]`, which is the
same endpoint pair. There is no point-route call for the failing
`SHINJUKU -> SHINJUKU` pair. This is positive evidence for the coordinate
mapping of the non-self pair, not evidence that the failing self-pair is
reachable.

Offline construction of the two request bodies confirms that both operations
use `DRIVE` and `TRAFFIC_AWARE_OPTIMAL`, but their schemas differ:
`ComputeRoutes` uses singular `origin`/`destination` locations while
`ComputeRouteMatrix` uses `origins`/`destinations` waypoint arrays. The matrix
fixture intentionally includes the `SHINJUKU -> SHINJUKU` self-pair. The
redacted request digests are different, as required by these different
payloads.

## Parser and classification audit

`google_routes._parse_matrix` accepts `ROUTE_EXISTS`, `OK`, and `SUCCESS` only
when both distance and duration are valid. If either metric is absent, it
creates an explicit `TravelTime(status="ERROR")` carrying the normalized
status as `error_class`; the runner then classifies the operation as
`PARTIAL` when any cell is an error. The existing regression test
`test_matrix_partial_cell_is_not_promoted_to_pass` protects this behavior.

No adapter parsing defect is demonstrated by the retained evidence. Treating
`ROUTE_EXISTS` with missing metrics as a usable route would discard required
travel-time data and would weaken the fail-closed boundary. No change was made
to the parser or to the historical classification correction.

## Root-cause disposition

Classification: `INCONCLUSIVE_FIXTURE_REACHABILITY_OR_PROVIDER_CELL_SEMANTICS`  
Confidence: `MEDIUM_LOW`

The result is not a provider connectivity failure: the matrix transport was
HTTP 200 and three independent cells carried valid provider results. It is not
evidence of a provider capability failure: the matrix operation returned
successful cells. It is not an application normalization defect on the
available evidence. The self-pair and the absence of raw provider JSON leave
two live explanations that cannot be separated offline: provider-specific
self-route cell semantics, or a fixture-level reachability/response-shape
condition. `ROUTE_EXISTS` is not interpreted as a no-route result; the missing
metrics make the cell incomplete instead.

## Revalidation decision and claims

The consumed contract authorizes no retry, and no new bounded live validation
is scientifically justified from this artifact alone. A future Human Gate
would need a new contract and digest with a fixture that excludes self-pairs,
explicit per-endpoint point checks, and a raw-response retention rule that
still redacts secrets. No such contract is prepared or authorized here.

`ComputeRoutes` remains `PASS`; `ComputeRouteMatrix` remains `PARTIAL` (3/4
cells); R4-411B remains `FAILED / PARTIAL_NO_PRODUCTION_CLAIM`.
Provider-live validation, Google Matrix Japan entitlement, Tokyo-pinned
processing, and production readiness remain unclaimed. R3-325 remains frozen
as `E-PASS / X-PASS / S-FAIL / C-NO-CLAIM`.

