# ADR 0035: Vultr Tokyo External Validation Backend

- Status: Accepted for bounded external validation; not deployed
- Date: 2026-08-25
- Decision owner: RouteMind engineering
- Tasks: R4-405, R4-406

## Context

R4-401 selected Vultr `nrt` (Tokyo, Japan) and Tokyo data residency. R4-405
needs credentialed traces, metrics, logs, failure/recovery, leakage, resource,
cost, and cleanup evidence. R4-406 needs a matching credentialed recovery-host
identity and target drill. The selected backend must keep all raw synthetic
telemetry in Tokyo, support deterministic automation, and require no paid SaaS
account or telemetry credential.

This decision prepares an external execution. It does not authorize spend or
resource mutation, and it is not runtime evidence.

## Considered options

### Self-hosted SigNoz

SigNoz is OpenTelemetry-native, accepts OTLP traces, metrics, and logs, and has
an official Kubernetes Helm installation path. The official Kubernetes guide
states a 4 CPU, 8 GiB memory, and 30 GiB storage minimum. Self-hosting inside
the validation VKE keeps the backend and ClickHouse in `nrt`. The chart can be
pinned and verified before deployment. This is the selected option.

Sources:

- https://signoz.io/docs/install/kubernetes/local/
- https://signoz.io/docs/ingestion/self-hosted/overview/
- https://signoz.io/docs/userguide/retention-period/

### Grafana OpenTelemetry LGTM

The image combines an OpenTelemetry Collector, Grafana, Loki, Mimir, and Tempo
and supports all three signals. Grafana's official documentation scopes it to
development, demo, and testing rather than production. It remains useful for
local smoke tests but is not the primary external qualification backend.

Source: https://grafana.com/docs/opentelemetry/docker-lgtm/

### Self-hosted Uptrace

Uptrace supports OpenTelemetry traces, metrics, and logs and can be self-hosted.
Its documented self-hosted stack introduces ClickHouse, PostgreSQL, and Redis.
That adds stateful dependencies without improving this bounded qualification,
so it remains a valid alternative but is not selected.

Source: https://uptrace.dev/get/hosted

## Decision

Deploy SigNoz chart `0.138.0` / application `v0.138.0` inside an isolated Vultr
`nrt` VKE only after the final Human Gate. The chart archive SHA-256 is
`b180a601b85b63b2e30ba953ea2242124a2c40f8f1cb66d8d948d71cd27d7418`.
The RouteMind gateway Collector uses OpenTelemetry Collector Contrib `0.159.0`.
All rendered container image digests must be resolved and recorded before Helm
installation; unresolved artifacts fail closed.

The topology is qualification workload -> two-replica RouteMind Collector ->
SigNoz Collector -> ClickHouse, all in `nrt`. Both OTLP hops use an ephemeral
execution-scoped private CA and mutual TLS. Services are `ClusterIP`; SigNoz UI
access is through the VKE control-plane tunnel only. There is no public
application ingress or load balancer.

The rendered storage inventory is five PVCs totaling 55 GiB. Raw backend
retention is bounded by the eight-hour execution and cleanup of all
namespaces and PVCs. Only sanitized evidence with hashes may leave Tokyo and it
has a 30-day retention target. No customer or production data may enter the
validation environment.

## Consequences

- No telemetry SaaS registration, external telemetry token, or cross-region
  payload transfer is required.
- The validation backend is single-instance and explicitly not production HA.
- Actual backend evidence comes from read-only ClickHouse queries after OTLP
  export; probe output alone cannot qualify a signal.
- The expected public-catalog execution cost is at most USD 5. The final
  authorization ceiling is USD 15 and eight hours; an authenticated quote above
  that ceiling aborts before provisioning.
- VKE resources are billed separately even though the VKE control plane is
  free. Relevant official material is:
  https://docs.vultr.com/support/products/vke/how-much-does-the-vultr-kubernetes-engine-cost
- R4-405 and R4-406 remain `TARGET_PENDING` until the complete credentialed
  evidence report validates and cleanup is proven.
- R3-325 remains exactly
  `E-PASS / X-PASS / S-FAIL / C-NO-CLAIM`; this operational execution is not
  scientific evidence.

The executable preparation contract is
`contracts/external-validation/r4-vultr-tokyo-external-validation-v1.json`.
