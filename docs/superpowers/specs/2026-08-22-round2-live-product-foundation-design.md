# Round 2 Live Product Foundation Design

## Context

Round 1's web surface is a deterministic role-aware snapshot and the two
runtime services expose health/system probes only. Round 2 needs a real product
path without moving durable ownership into React or Python.

## Decision

Introduce a typed, provider-neutral frontend data boundary with three explicit
modes:

- `LIVE`: fetches authoritative snapshots from Java and compute state from
  configured service URLs. A successful response is marked live; an empty
  response is still live and is not replaced with demo data.
- `DEMO`: uses the existing deterministic fixture and is labeled in the shell.
- `REPLAY`: reserved for verified replay artifacts and must expose provenance;
  it is not silently substituted for live state.

The first slice adds a read-only operations snapshot contract and a minimal
Python dispatch snapshot contract. Java remains the authority for durable
order/party/courier state and Python remains the authority for dispatch
decisions. The browser composes the two responses through an adapter and
surfaces partial/unavailable service state explicitly.

The first slice does not add a new network service, move business writes into
the web app, or pretend that a local fixture is live. Commands, SSE, and the
full golden path are subsequent graph tasks with independent evidence.

## Contract shape

`OperationsSnapshot` carries source mode, generated time, orders, couriers,
merchants, dispatch summary, and service health. `LIVE` responses include the
source revision or trace metadata returned by services. A failed source is
represented as `UNAVAILABLE`/`DEGRADED` with a stable reason and does not erase
the last known state without labeling it stale.

The Java read endpoint is read-only and backed by repositories. The Python
endpoint accepts a bounded dispatch request and returns a versioned decision
using the existing registry; it never writes PostgreSQL. Requests and
responses use existing UUID/digest/trace conventions and are bounded by the
existing input policy before future command endpoints are added.

## Error and testing behavior

- malformed or oversized live responses fail closed to an explicit unavailable
  state;
- network timeout and HTTP errors retain mode metadata and display degraded
  status;
- demo mode remains deterministic for unit and browser smoke tests;
- live adapter tests use a fetch stub and contract fixtures;
- service endpoint tests prove response shape and ownership boundaries;
- the repository gate remains green before the planning checkpoint is pushed.

## Alternatives considered

1. Keep the web snapshot and only improve styling. Rejected because it does not
   satisfy live integration or truthful product state.
2. Make React call PostgreSQL/Redis directly. Rejected because it violates Java
   durable-state ownership and creates an unsafe second business boundary.
3. Add a new BFF service immediately. Deferred because the current boundary is
   small and does not yet justify another deployable; the adapter can later be
   extracted if independent scaling or failure isolation is demonstrated.

## Review note

This design is authorized for autonomous execution by the Round 2 prompt. It is
committed as a planning artifact before implementation, and the implementation
must still provide executable evidence before RM-100 can pass.
