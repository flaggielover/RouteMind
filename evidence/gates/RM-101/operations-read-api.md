# RM-101 Java Authoritative Operations Read API

- Date: 2026-08-22 (Asia/Shanghai)
- Revision: `3237144` implementation checkpoint
- Boundary: Java read-only API over durable repositories and the courier location projection

## Contract

`GET /api/v1/operations/snapshot` is a Java-owned read path. The response is
versioned with `schemaVersion: v1` and `source: live`, and exposes stable order,
party, merchant, courier-location, courier, and health fields. Merchant and
courier projections are derived from the Java repository snapshot; they are not
fixture data and the endpoint performs no writes.

Empty durable state remains a successful live response with empty arrays. The
`health` object reports the read boundary itself: `status: UP` means the durable
repository and courier projection reads completed in this snapshot, while
`durableState` and `courierProjection` are explicit `available` markers. This is
not a claim about external production infrastructure health.

## Commands and results

1. `./scripts/business-api.ps1 -Action test` -> PASS; 50 Java tests passed.
2. `./scripts/full-gate.ps1` -> PASS; control, security, Compose, Java, Python,
   contract, Web static/unit/build, and resilience gates passed.
3. `python scripts/validate_control_plane.py` -> PASS.

## Verified behavior

- MockMvc verifies `schemaVersion`, `source`, stable order/party/merchant/courier
  arrays, and the health fields when durable state is empty.
- The service uses `@Transactional(readOnly = true)` and existing repository
  ports; the API layer has no infrastructure dependency.
- Existing `parties` and `courierLocations` projections remain present for the
  RM-100 adapter while dedicated merchant/courier fields make the product shape
  unambiguous.

## Evidence limits

This gate does not claim order commands, SSE/realtime freshness, production
availability, or a live Redis/RabbitMQ deployment. Those behaviors remain later
tasks or external gates.

## GitHub Actions

- Implementation run `32562416957` passed all five jobs: control plane and
  Compose, Java business runtime, Python compute and contracts, Role-aware web
  application, and bounded degradation and resilience.
