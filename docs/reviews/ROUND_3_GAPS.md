# Proposed Round 3 Gaps

Round 2 is a validated local and CI-ready product surface. The following are
deliberate next-stage gaps, not hidden failures in the Round 2 acceptance gate.

## Production readiness

- Deploy the Java/Python split with real secret management, migrations,
  backups, SLOs, alert routing, and a rollback rehearsal.
- Replace local Compose-only health assumptions with environment-specific
  readiness, liveness, and dependency budgets.
- Add authenticated multi-tenant isolation and an operator audit trail backed by
  a production identity provider.

## Dispatch and data science

- Add a production travel provider with freshness, quota, and error budgets,
  while retaining the local deterministic provider for tests.
- Expand RouteBench/RADS from fixture-sized comparisons to versioned datasets,
  statistical confidence intervals, drift checks, and a review workflow for
  accepting a strategy.
- Add larger-scale VRPTW/dynamic replanning benchmarks and a repeatable load
  profile beyond the RM-180 bounded gate.

## Product surfaces

- Add authenticated customer, merchant, and courier sessions instead of the
  current role-switching shell.
- Persist user preferences, operator annotations, and notification delivery
  state; define retention and deletion policies.
- Extend browser coverage to real mobile devices, assistive technology, and
  localization/long-label layouts.

## Operations and research

- Add distributed tracing export, cost attribution, and incident drill evidence
  across Java, Python, RabbitMQ, Redis, and PostgreSQL.
- Turn Digital Twin perturbations into scheduled experiments with lineage,
  approvals, and reproducible artifact storage.
- Define the LLM-agent evaluation harness and guardrails for analysis and
  orchestration without allowing agents to own hard real-time correctness.
