# RouteMind Semantic Metrics

Status: executable registry introduced by RM-213  
Authority: analytical read model only; never durable business truth

All consumers use the definitions in
`routemind_compute.application.semantic_metrics`. The public catalog is exposed
at `GET /api/v1/analytics/metrics/catalog`; `consumer=web`, `report`, and
`agent` return the same definition digests. Executable SQL is not exposed and
callers cannot submit SQL or alter a denominator.

## Time and availability rules

- Every query uses event time in a UTC-normalized half-open window:
  `event_time >= start AND event_time < end`.
- Count metrics return zero for an empty window.
- Ratio metrics return `status=unavailable`, `value=null`, and
  `unavailable_reason=no_eligible_records` when their denominator is zero.
- Records with absent or unrecognized eligibility fields are excluded from a
  qualified denominator. They never silently become failures or successes.
- Every result carries the definition digest and exact evaluated window.

## Initial registry

### `archived_event_count`

- Unit: event
- Source: `fact_event.event_time`, `fact_event.record_id`
- Numerator: all unique archived records
- Denominator: none
- Aggregation: record count in the selected event-time window

### `order_count`

- Unit: order
- Source: `fact_order.event_time`, `fact_order.record_id`
- Numerator: all order records
- Denominator: none
- Aggregation: order record count in the selected event-time window

### `dispatch_decision_count`

- Unit: decision
- Source: `fact_decision.event_time`, `fact_decision.decision_id`
- Numerator: all dispatch decision records
- Denominator: none
- Aggregation: decision record count in the selected event-time window

### `dispatch_assignment_rate`

- Unit: ratio
- Source: `fact_decision.event_time`, `payload.selected_courier`
- Numerator: decisions with a non-empty selected courier
- Denominator: all dispatch decision records
- Unavailable: no dispatch decision exists in the selected window

### `dispatch_fallback_rate`

- Unit: ratio
- Source: `fact_decision.event_time`, `payload.fallback_used`
- Numerator: decisions whose fallback flag parses as true
- Denominator: decisions whose fallback flag parses as a boolean
- Unavailable: no decision has a valid boolean fallback flag

### `solver_success_rate`

- Unit: ratio
- Source: `fact_solver_run.event_time`, `payload.status`
- Numerator: runs with `success` or `succeeded` status
- Denominator: runs with `success`, `succeeded`, `failed`, or `error` status
- Unavailable: no run has a recognized terminal status

### `simulation_completion_rate`

- Unit: ratio
- Source: `fact_simulation_run.event_time`, `payload.status`
- Numerator: runs with `completed` status
- Denominator: runs with `completed`, `failed`, or `cancelled` status
- Unavailable: no run has a recognized terminal status

The catalog endpoint is the machine-readable source. This document is an
operator-oriented snapshot and must be updated whenever the registry changes.
