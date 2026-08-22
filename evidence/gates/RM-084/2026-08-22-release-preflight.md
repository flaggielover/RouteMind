# RM-084 Release Provenance and Deployment Preflight Evidence

- Date: 2026-08-22 (Asia/Shanghai)
- Revision: `ada92bca754b874891e086680ea4b92a425c3f81`
- Worktree: clean after the implementation checkpoint

## Contract

`scripts/release_contract.py` defines immutable `ArtifactDescriptor` and
`ReleaseManifest` values plus a read-only `preflight()` result. Canonical JSON
and SHA-256 bind the release revision, service artifacts, provenance metadata,
contract versions, migration heads, health-check coverage, and rollback package
content digest. Artifact order and metadata order are normalized for stable
digests. Missing fields, mutable tags such as `latest`, non-semantic versions,
revision mismatches, duplicate or incomplete service coverage, unsafe required
paths, and non-content rollback references return sorted deterministic reason
codes.

## Commands and results

1. `python scripts/release_contract_test.py` -> 4 tests passed.
2. `python -m py_compile scripts/release_contract.py scripts/release_contract_test.py` -> passed.
3. `./scripts/verify.ps1` -> control-plane, security, recovery, release-contract,
   Compose, and PowerShell syntax gates passed.
4. `./scripts/full-gate.ps1` -> Java 34 tests passed; Python 56 tests passed at
   96.05% statement/branch coverage; 4 schemas and 12 fixtures passed; Web
   formatting, lint, typecheck, unit, and production build passed.

The release self-tests also verify that preflight does not create or mutate
files and that missing or traversal-prone required paths remain blocked.

## Boundary

This is a local, read-only release contract. Registry signature verification,
image vulnerability scanning, deployment orchestration, live service health,
and production rollback execution remain external gates and are not claimed.
