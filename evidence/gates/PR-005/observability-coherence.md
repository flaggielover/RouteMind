# PR-005 Operational Observability Summary

Status: implemented locally; source-scoped and read-only.

Reliability Center now derives a structured summary from existing bounded sources:
service health probes, the authenticated SSE cursor/status, per-order operational
freshness, and the authoritative dispatch latency field. Degraded reasons include
snapshot detail, stream stale reason, and stale order contexts. Publisher activity,
queue depth, and Redis projection inspection are shown as `unavailable` because no
authoritative local telemetry source is attached; no queue, Redis, or latency value
is inferred from UI state.

Verification: Java 17 integration 17/17; web lint/typecheck/build green; serial
Vitest 39 files / 108 tests green. Existing WebGL jsdom `getContext` notices are
environment output only. No external collector, broker, or provider was contacted.
