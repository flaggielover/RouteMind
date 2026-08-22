# RM-160 Strategy Registry and Execution API

## Goal

Expose the compute-owned strategy catalog and a bounded execution boundary for
the Strategy Laboratory. The API must make strategy identity, runtime outcome,
and reproducibility provenance explicit without persisting business state or
claiming production metrics.

## Boundary and endpoints

- `GET /api/v1/strategies` returns a deterministic list sorted by strategy name.
  Each descriptor contains `name`, `version`, `capabilities`, and `status`.
  The initial status is `available` for registered implementations; the
  descriptor is metadata, not an operational health claim.
- `POST /api/v1/strategies/execute` accepts one bounded dispatch scenario. It
  reuses the existing pickup, candidate, capacity, readiness, risk, and time
  window validation rules, and adds a required scenario identifier, a bounded
  seed, and a bounded key/value configuration tuple. The response contains the
  decision plus candidate/eligibility/assignment/latency metrics and a
  provenance object with canonical input and output digests.

The existing `/api/v1/dispatch/snapshot` endpoint remains compatible and keeps
its live-snapshot response shape. The new execution endpoint is explicitly a
research/productization boundary and never writes Java-owned durable state.

## Application design

`StrategyRegistry` gains an immutable descriptor view. Implementations may
declare a tuple of capability labels; absent labels use a stable `dispatch`
capability. Registry execution continues to validate request identity, strategy
identity, version, and decision shape. A small application helper canonicalizes
the bounded execution request and decision metadata to produce a stable
SHA-256 provenance digest; measured latency is returned as an observation and
is not part of the reproducibility input digest.

The FastAPI adapter converts the request into `DispatchProblem`, calls the
registry, and serializes deterministic tuples rather than unbounded maps. A
missing strategy is a client error, malformed bounded input is rejected by
Pydantic, and strategy/runtime failures return an explicit unavailable result
with trace and fallback metadata. No fallback result is silently substituted
for the requested strategy.

## Validation

Tests cover sorted catalog metadata, descriptor validation, deterministic
execution provenance for repeated inputs, changed digest for changed seed or
configuration, constraint and size limits, unknown strategies, and explicit
failure responses. The compute check and full repository gate remain required;
remote GitHub Actions must pass before RM-160 is marked complete.
