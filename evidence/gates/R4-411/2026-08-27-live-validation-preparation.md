# R4-411 Live Travel Provider Validation Preparation

Date: 2026-08-27

## Contract

The exact preparation contract is:

```text
contract = contracts/provider/r4-411-travel-provider-live-validation-v1.json
sha256 = 4eacaad0c0d8a71a73715b750b370d58a4439d70b1f9dd1cc97d119599da6d1c
contract_id = r4-411-travel-provider-live-validation-v1
status = PREPARED_TRAVEL_PROVIDER_LIVE_VALIDATION_HUMAN_GATE
authorized = false
```

It is bound to the approved R4-410 v2 contract SHA-256
`6d71059d2db366ce0ab3e54b7959f532346b0875101ebc1ab8da9189e8b3ac5c`. The
R4-410 approval remains zero-account, zero-credential, zero-live-call, and
zero-spend authority; this document does not expand that authority.

## Exact bounded manifest

- HERE Routing API v8 point endpoint: 20 planned calls, IDs `P01`-`P20`.
- HERE Matrix Routing API v8 endpoint: 5 planned synchronous requests, IDs
  `M01`-`M05`, 20 elements each, 100 total elements.
- Maximum duration: 30 minutes.
- Maximum spend: USD 1 (100 cents).
- Synthetic Tokyo fixture only; no durable business identifiers and no Tokyo
  residency claim.
- Any overage, missing secret, Japan entitlement failure, invalid response, or
  partial matrix stops the external path before overage and uses the explicit
  deterministic-local fallback.

## Account, secret, and privacy prerequisites

Before any future execution, HERE must provide account/application identity and
written Japan Routing service eligibility confirmation. The reviewed contract,
DPA, non-region-pinned processing, synthetic-coordinate privacy boundary, and
billing ownership must be accepted by a separate Human Gate.

The only required secret name is `ROUTEMIND_TRAVEL_PROVIDER_API_KEY`. It may be
injected only through an external secret store or process environment scoped to
one bounded process. Presence may be reported as `SET`/`MISSING`; the value must
never enter Git, output, URLs, logs, telemetry, evidence, fixtures, screenshots,
or chat. The process value and ephemeral mount are removed during teardown.

## Evidence and teardown contract

Future execution must retain account identity without secrets, Japan eligibility,
accepted processing terms, manifest and artifact digests, per-call timestamps and
redacted statuses, point/matrix units, quota/timeout/network/HTTP classifications,
fallback reason and provenance, leakage-scan output, conservative cost, versions,
and cleanup metadata. Provider response bodies, raw coordinates, request URLs,
provider request IDs, and secret values are excluded from evidence and telemetry.

No provider resources are created by this contract. Teardown stops the bounded
process, unsets the secret, removes ephemeral secret mounts and runtime output,
retains only redacted evidence/digests, and fails closed if cleanup cannot be
verified.

## Local validation

The independent contract gate now validates the exact R4-411 contract, R4-410
binding, 20/5/100 call limits, zero authorization, secret isolation, leakage
scan, fallback, teardown, and conservative claims. `python
scripts/r4_independent_human_gates_test.py` passed 19 tests. The full repository
verification and Round 4 graph gate passed before push, and the pushed commit
also passed the required remote CI jobs.

## Human Gate boundary

R4-411 remains `BLOCKED / DEFERRED_EXTERNAL`. No HERE account was created, no
credential was acquired or configured, no provider call was made, and no spend
occurred. The exact next approval must name this contract SHA-256 and explicitly
authorize only the bounded manifest after HERE account/Japan eligibility and
secret readiness are independently confirmed. A provider live-validation result
must not be inferred from this preparation.

Remote validation checkpoint:

- Commit `5017b72a08e91dfe43882f641c05e6a76847d256` was pushed to `main`.
- Real GitHub Actions CI run `33082754675` completed successfully; all five
  required jobs passed.

- Documentation synchronization commit `ecf76a9271c33826d35cfd5172f82b38210bc709`
  passed real GitHub Actions CI run `33083090749`; all five required jobs passed.

- Final Human Gate record commit `467f333d5c4d0529f862920571ea4d9747249398`
  passed real GitHub Actions CI run `33083434000`; all five required jobs passed.

- DAG blocker correction commit `cb99abce233999b90299b66a64908d8dcef83b8f`
  passed all five required jobs in real GitHub Actions CI run `33084375382`.
  The active graph now records only the genuine account/Japan eligibility,
  external-secret, and separate-Human-Gate blockers; the prepared contract is
  no longer incorrectly represented as missing.

## Prerequisite revalidation - 2026-08-28

This append-only revalidation records the owner's current prerequisite facts;
the historical preparation and blocked checkpoints above remain unchanged.
No HERE endpoint was called, the API key was not tested, and no account or
billing action occurred during this revalidation.

- `HERE_ACCOUNT = CONFIRMED` (owner-provided fact; no secret recorded).
- `HERE_APPLICATION = CONFIRMED` and application state is reported as Active
  (owner-provided fact; no application credential recorded).
- `HERE_API_KEY = SET` was checked by presence only in the Windows User
  environment. The key value was not read, printed, copied, logged, captured,
  or committed. The current shell process did not inherit a value, so a future
  run must still inject the key into one bounded process through the approved
  external mechanism.
- HERE Routing API v8 Japan car-routing coverage is
  `DOCUMENTED_SUPPORTED` according to the reviewed official documentation.
  This documents the point-product capability only; it is not live validation.
- HERE Matrix Routing API v8 Japan access remains
  `RESTRICTED / REQUIRES_HERE_CONFIRMATION`, as stated by the reviewed official
  documentation. An API key's presence cannot promote Matrix Japan eligibility.
- Overall `JAPAN_SERVICE_ELIGIBILITY = PARTIAL_PENDING_CONFIRMATION` because
  the point-product documentation is supported while the Matrix entitlement
  still requires explicit HERE confirmation.

R4-411 therefore remains `BLOCKED / HUMAN_GATE_PENDING` with the frozen
contract SHA-256 unchanged at
`4eacaad0c0d8a71a73715b750b370d58a4439d70b1f9dd1cc97d119599da6d1c`. The
remaining execution boundary is written Matrix Japan confirmation, secure
process-scoped secret injection, and the separate Human Gate for the exact
bounded manifest. No live/provider/production claim is made.
