# ADR-0023: Toggleable Geo Analytical Layer Inventory

Date: 2026-08-24
Status: Accepted

## Context

The Operations surface now has city/zone and flow projections, but a layer
inventory can easily become a set of unlabeled visual claims. Layers must be
toggleable, bounded to the selected snapshot, and explicit about unavailable
inputs.

## Decision

Add a Web-owned layer projection and panel with explicit definitions for order
demand, courier supply, supply gap, SLA risk, congestion, travel degradation,
location integrity, utilization, and order flow. The first, second, third,
fourth, eighth, and ninth layers are enabled from existing snapshot and flow
records. Congestion and travel degradation remain disabled until a provider
travel metric is present. Location integrity is enabled only when courier
sequence, freshness, online, or stale metadata is present.

Every definition declares a unit and scale. Values are aggregated by the
existing city/zone projection or the RM-224 flow records, carry evidence
counts, and remain bounded to the selected snapshot. The panel exposes source,
freshness, enabled/disabled state, and a truthful empty/unavailable state.
Large record sets are represented by bounded zone/flow aggregates rather than
raw point rendering.

## Consequences

Operators can focus the map-adjacent analytical view without confusing absent
travel or integrity data with zero values. Provider adapters can enable the
deferred layers when their contracts include the required metrics. The layer
projection is read-only and cannot replace Java durable state or dispatch
correctness.
