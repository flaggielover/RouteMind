# R4 Telemetry Export Runbook

## Scope and evidence status

This runbook covers the RouteMind application-to-collector telemetry path. The
repository currently proves a local contract and failure boundary only. It does
not prove a running collector, selected backend, Vultr resource, Tokyo data
residency, production trace continuity, or production cost.

## Required deployment inputs

Provision these values through the approved secret/configuration mechanism:

- `ROUTEMIND_TELEMETRY_ATTRIBUTION_KEY`: at least 32 characters, generated and
  stored outside Git; use the same value for Java instances in one attribution
  epoch.
- `ROUTEMIND_TELEMETRY_OTLP_ENDPOINT`: the approved Tokyo-resident backend OTLP
  endpoint used by the collector.
- `ROUTEMIND_TELEMETRY_RECEIVER_CA_FILE`,
  `ROUTEMIND_TELEMETRY_RECEIVER_CERT_FILE`, and
  `ROUTEMIND_TELEMETRY_RECEIVER_KEY_FILE`: receiver-side mTLS material.
- `ROUTEMIND_TELEMETRY_EXPORTER_CA_FILE`,
  `ROUTEMIND_TELEMETRY_EXPORTER_CERT_FILE`, and
  `ROUTEMIND_TELEMETRY_EXPORTER_KEY_FILE`: backend client mTLS material.
- `ROUTEMIND_TELEMETRY_METRICS_ADDRESS`: Collector diagnostic bind address;
  use loopback locally and `0.0.0.0:8888` only behind the target `ClusterIP` and
  NetworkPolicy boundary.
- `ROUTEMIND_TELEMETRY_MAX_TENANT_KEYS`: optional runtime bound, 1 through 256;
  the frozen default is 64.
- Standard OTLP application endpoint and `OTEL_BSP_*` values matching the
  executable contract when application export is enabled.

Mount `/var/lib/otelcol/queue` on encrypted Tokyo-resident storage with bounded
capacity and explicit retention. Do not enable a provider backup until its
residency is contractually verified. The collector and backend must not export
customer payloads outside Tokyo.

## Preflight

Run:

```powershell
python scripts/telemetry_export_contract.py
python scripts/telemetry_export_contract_test.py
```

The validator must report five boundaries, 64 maximum active tenant keys,
`collectorVerified:false`, `productionCostVerified:false`, and
`targetStatus:TARGET_PENDING` until matching remote evidence exists. Mutation
tests must reject target-claim promotion, raw identity labels, unbounded queues,
changed authority, and collector pipeline drift.

Before target activation, verify the exact Vultr project, `nrt` resource IDs,
collector image digest, storage identity/residency, network policy, backend
identity, data retention, expected daily volume, maximum cost, and rollback and
cleanup scope. Resource creation or spend still requires separate approval.

## Tenant-safety checks

Use two isolated synthetic tenants and one over-budget fixture. Confirm:

1. Java emits stable `rtk_<24 lowercase hex>` keys and no raw tenant UUID in
   exported resource, span, event, or metric attributes.
2. Python accepts only the pseudonymous internal header and maps malformed or
   raw values to `rtk_unattributed`.
3. The 65th distinct key at the default limit maps to `rtk_overflow`.
4. Collector processors remove every raw identity attribute named by the
   executable contract.
5. Backend label and trace searches contain no tenant UUID, principal ID,
   courier ID, authorization value, or application secret.

Treat any leak as a failed qualification. Stop export, preserve redacted logs,
revoke affected credentials, determine the backend deletion boundary, and do
not claim cleanup without provider evidence.

## Correlation and cost qualification

For one synthetic scenario, retain trace and span identities across HTTP,
RabbitMQ publication/consumption, Outbox worker processing, simulation control,
and experiment execution. Confirm the durable request, event, scenario, and
manifest records retain their own identifiers independently of telemetry.

Reconcile `routemind_telemetry_attributed_records_total` by service, signal,
operation, and tenant key against backend-ingested records. Record overflow and
unattributed volume separately. A currency statement additionally requires the
backend rate card, billed usage window, retention/tier assumptions, and a
reproducible reconciliation. Logical record counts alone are not cost evidence.

## Outage and backpressure drill

Run only in the approved isolated target scope. Saturate the application and
collector queues within the authorized workload budget, then make the backend
unavailable for a bounded interval. Capture queue depth, rejected/dropped
telemetry diagnostics, memory pressure, recovery time, ingested/lost record
counts, and backend cost.

Throughout the drill, independently verify that HTTP business outcomes,
PostgreSQL commits, Outbox rows, Inbox deduplication, RabbitMQ acknowledgments,
and Redis rebuildability follow their normal business semantics. Telemetry loss
must not roll back, retry, duplicate, or acknowledge business work. If it does,
stop qualification and retain the failure as evidence.

## Rollback

Disable application OTLP export first, then stop collector ingestion. Preserve
only the approved redacted diagnostics and queue metadata. Revoke the collector
credential, remove the backend destination only within the reviewed resource
inventory, and verify application transactions and message processing continue.
Never delete business records or durable queues as telemetry rollback.
