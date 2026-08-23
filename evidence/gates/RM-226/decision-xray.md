# RM-226 Decision X-Ray Evidence

Status: validating

## Scope

- Java exposes read-only GET /api/v1/dispatch-decisions/{decisionId} over the
  PostgreSQL-backed dispatch decision ledger.
- Web exposes structured Decision X-Ray provenance, candidates and rejection
  reasons, selected action, alternatives, objective/risk evidence, verification,
  digests, and bounded replay status.
- Snapshot-only fields remain explicitly unavailable; no travel metric is inferred.

## Local evidence

- Web npm run check: PASS - 25 test files, 74 tests, lint, typecheck, and Vite
  production build.
- Web Playwright full gate: PASS - 34 tests passed, 2 existing desktop-only
  skips.
- Web Decision X-Ray unit/component coverage includes snapshot projection,
  durable-ledger authority, bounded replay match/change, and unavailable state.
- Java JAVA_HOME=C:\Program Files\Java\jdk-17.0.1 .\mvnw.cmd
  -Dtest=BusinessApiApplicationTests test: 15 tests passed, including durable
  ledger lookup response assertions.

## Remote evidence

Pending checkpoint commit and GitHub Actions run.

## Boundaries

The demo and live operations snapshots do not automatically claim a durable
ledger record. The X-Ray labels snapshot projection authority until a Java ledger
record is attached. A full-gate Docker rerun remains environment-dependent; the
remote Compose/control-plane job is authoritative for that gate.
