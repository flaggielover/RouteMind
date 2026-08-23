# RM-215 Continuous Reconciliation Evidence

Date: 2026-08-23
Validation worktree base: `aea09db`
Implementation checkpoint: `d26a121`
GitHub Actions: `32647766636` - PASS across all five jobs

## Scope

- Java-owned scheduled and manual detect-only reconciliation
- independent `PASS`, `FAIL`, and `UNAVAILABLE` invariant results
- aggregate `HEALTHY`, `DRIFT_DETECTED`, and `DEGRADED` status
- lease/assignment, terminal-order, decision-reference, and courier-projection
  checks with bounded entity evidence
- append-only PostgreSQL run evidence with SHA-256 report digest
- evidence-write failure represented as degradation rather than false health
- explicit no-repair behavior

## Executable evidence

Command: `./scripts/business-api.ps1 -Action test`

Result: PASS - 77 tests. Five focused service tests cover all-pass health,
durable drift plus unavailable projection, query/evidence-store degradation, and
missing/orphaned projection membership including the combined 100-entry evidence
bound. The Spring integration scenario creates
an assigned order, moves it to `CANCELLED`, removes its decision-ledger reference,
and verifies three exact violation codes. It proves the append-only V13 row and
JSON report can be read back while the committed lease remains unchanged.

Command: `./scripts/full-gate.ps1`

Result: PASS - control-plane, security, supply-chain, recovery/release/staged
release, Compose, Java 76, Python 185 at 95.24% coverage, five schemas/15
fixtures, deterministic replay/archive/mart/semantic metric probes, Web format,
lint, typecheck, 51 unit tests, and production build.

Command: `./scripts/verify.ps1`

Result: PASS - task graph schema/dependencies/states/evidence, tracked-secret
isolation, lock metadata, least-privilege workflow, Compose hygiene/configuration,
control-contract self-tests, required files, and PowerShell syntax.

Command: `./scripts/resilience.ps1`

Result: PASS - 15 Java HTTP/degradation integration tests and two Python
dependency-failure tests. Reconciliation retains explicit unavailable status and
does not change existing bounded Redis or travel-provider degradation behavior.

## Evidence gate boundaries

- `repairMode` is constrained to `DETECT_ONLY` in both the Java record and V13.
- PostgreSQL is the durable source; Redis membership is compared as a rebuildable
  projection and is never accepted as durable truth.
- A failed query, projection read, serialization, or append cannot produce a
  healthy report.
- Violation evidence is bounded to 100 entries per check and no business record
  is modified by reconciliation.
- No production alerting, retention, repair policy, or autonomous remediation is
  claimed.

## Remote evidence

GitHub Actions run `32647766636` passed control-plane/Compose, clean Java,
frozen Python/contracts, bounded degradation, and Web static/unit/browser jobs
for implementation checkpoint `d26a121`.
