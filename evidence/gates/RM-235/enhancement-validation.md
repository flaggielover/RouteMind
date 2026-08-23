# RM-235 Enhancement E2E and Adversarial Validation

- Date: 2026-08-24 (Asia/Shanghai)
- Gate decision: PASS for the exercised repository scope; no production or scientific claim
- Implementation checkpoint: `bc00832`
- Remote CI: GitHub Actions run `32662822033`, all five jobs passed

## Current repository gates

- `./scripts/full-gate.ps1` -> PASS. Control-plane, Java, Python, Web, contract,
  security, recovery, determinism, archive, mart, and semantic gates passed.
- Java bounded degradation -> PASS: `BusinessApiApplicationTests` 15/15.
- Python bounded degradation -> PASS: `tests/test_resilience.py` 2/2.
- Python enhancement substrate regression -> PASS: 236 tests at 95.28% coverage,
  strict Ruff/format/mypy and contract/determinism/archive/mart/semantic gates.
- Web regression -> PASS: 34 test files, 92 unit tests, production build, and
  Playwright 34 passed with 2 pre-existing desktop-only skips.
- `python scripts/round2-adversarial-audit.py` -> PASS: 111 passed evidence paths,
  actionable buttons, fabricated-literal audit, and unavailable-state boundary.

## Cross-layer journeys

The real local gates below remain the executable evidence for the requested
fulfillment, location, ETA, archive, mart, dashboard, and lineage journey:

- RM-170 real golden delivery (`evidence/gates/RM-170/local-golden-e2e.md`) passed
  PostgreSQL, RabbitMQ, Redis GEO, Java/Python health, order lifecycle, dispatch,
  durable assignment, Outbox publication, and delivered-state assertions.
- RM-171 real failure/degradation E2E (`evidence/gates/RM-171/failure-e2e.md`)
  passed Redis loss/recovery, compute outage, RabbitMQ restart/Outbox recovery,
  idempotent duplicate delivery, offline/stale courier handling, and bounded SSE/
  dispatch timeout behavior.
- RM-211/RM-212/RM-213 evidence covers append-only archive, DuckDB marts, semantic
  metrics, lineage, and explicit unavailable/insufficient-data semantics.
- RM-228 through RM-232 evidence covers Twin, What-if, Reliability, Research, and
  bounded analytical-agent surfaces; all are read-oriented and provenance-linked.

## Adversarial and infrastructure limits

The current host re-run of `./scripts/golden-delivery.ps1 -TimeoutSeconds 240`
was stopped after Docker Compose startup produced no output and `docker compose ps`
did not return. This is an external Docker Desktop daemon availability block, not a
business assertion failure. The previously completed RM-170 and RM-171 real runs,
plus remote CI Compose validation, remain the accepted infrastructure evidence;
this run does not claim a new local Compose result.

The adversarial audit is static and repository-scoped. It does not claim production
load, live provider accuracy, multi-host resilience, or a scientific result. Those
capabilities remain explicitly deferred in the task graph and Round 3 preparation.

## Decision

All RM-235 acceptance categories have executable local or remote evidence within
the stated scope. RM-235 is closed and RM-236 is activated for closure reporting and
Round 3 research graph preparation.
