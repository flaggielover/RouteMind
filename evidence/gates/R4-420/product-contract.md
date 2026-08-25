# R4-420 Product Semantics Contract Evidence

Date: 2026-08-25 (Asia/Shanghai)

Entry revision: `bf984d7e59033938dff2684dc0849920e47360b1`

Status: in progress - `LOCAL_VALIDATED / CI_PENDING`

## Frozen boundary

- `contracts/product/r4-420-product-semantics-v1.json` is the machine-readable
  authority for ownership, defaults, versioning, consent, quiet hours, locale,
  accessibility, notification states, privacy, and execution scope.
- Java/PostgreSQL retain durable authority. Verified tenant and principal are
  mandatory, self-scope is explicit, and cross-tenant/principal access fails.
- External channels default off and require explicit purpose/channel consent.
  Quiet-hour deferral rechecks consent; critical bypasses are narrow and audited.
- Exactly `DELIVERED` means delivered, and it requires an authenticated provider
  delivery receipt. Intent and provider acceptance are explicitly not delivery.
- Real provider sends remain unauthorized. This task ran no external call and
  does not claim provider, production, legal, or device-lab validation.

## Executable evidence

- `python scripts/product_contract.py`: passed. Canonical contract digest is
  `821e782c1d52b45f33139711a404e1a304695c81777a8793cf6f3b1ae0062406`.
  The summary contains five roles, five consent purposes, nine accessibility
  requirements, ten notification states, eighteen transitions, and
  `realProviderSendAuthorized=false`.
- Contract file SHA-256:
  `759d5addbbb419f87765ccf084be9f3b5338253790a540368427438fd94ba625`.
- `python scripts/product_contract_test.py`: 12 directed tests passed. Mutations
  to durable authority, tenant/role ownership, channel defaults, external
  consent, quiet-hour bypass, accessibility, state flags/transitions, provider
  receipts, terminal states, and external-send authority fail closed.
- `./scripts/verify.ps1`: passed with product contract and tests integrated into
  the fast repository gate.
- Real GitHub Actions: pending implementation commit.

## Scientific preservation

The contract does not change research data, results, thresholds, or claims.
R3-325 remains frozen exactly as `E-PASS / X-PASS / S-FAIL / C-NO-CLAIM` and
was not rerun, tuned, or reinterpreted.
