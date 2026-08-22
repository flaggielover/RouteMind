# RM-103 Bounded Python Dispatch Snapshot API

- Date: 2026-08-22 (Asia/Shanghai)
- Revision: implementation checkpoint recorded by the accompanying commit
- Boundary: Python stateless dispatch computation, strategy registry, and travel metadata

## Contract

`POST /api/v1/dispatch/snapshot` accepts a validated pickup and at most 64
unique courier candidates. It returns a versioned registry decision, bounded
latency, rationale, trace identity, and travel-provider metadata. The endpoint
does not write durable business state; Java remains the order authority.

## Executable evidence

1. `./scripts/compute-api.ps1 -Action check` -> PASS; 59 Python tests passed,
   96.13% branch coverage, mypy/ruff and 4 schemas / 12 contract fixtures passed.
2. `./scripts/full-gate.ps1` -> PASS; control, security, Compose, Java (53
   tests), Python, contract, Web static/unit/build, and resilience gates passed.
3. `python scripts/validate_control_plane.py` -> PASS.

## Failure and fallback behavior

- Unknown strategy or malformed domain input returns HTTP 400.
- Strategy timeout/runtime/contract failure returns HTTP 503 with stable
  `strategy_unavailable`, trace identity, and explicit nearest-strategy fallback
  metadata. No silent strategy substitution occurs.
- Travel estimates use the bounded provider boundary and expose provider,
  candidate count, selected travel seconds, and whether a provider fallback was
  used. Travel-provider failure returns HTTP 503 with explicit fallback metadata.

## Evidence limits

The default travel provider is deterministic local computation. External traffic,
paid routing credentials, and production latency/SLO validation remain later
deployment concerns; this gate proves the local contract and bounded failure
semantics only.
