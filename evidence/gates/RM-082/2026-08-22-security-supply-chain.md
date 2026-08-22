# RM-082 Security and Supply-Chain Hygiene Evidence

Date: 2026-08-22
Local revision before checkpoint: `7b35b15`

## Scope

`scripts/security_gate.py` now provides a deterministic, Git-tracked-file-only
repository safety baseline. It scans for private-key material, high-confidence
provider tokens, non-placeholder secret assignments, tracked environment/key
files, malformed or missing dependency locks, broad workflow permissions, and
unsafe Compose image/port patterns. `scripts/verify.ps1` runs the gate and its
three standard-library self-tests on every control-plane invocation.

## Executed gates

`python scripts/security_gate.py` — PASS

- tracked secret isolation — PASS
- dependency lockfile metadata — PASS
- workflow least-privilege permissions — PASS
- Compose image and loopback hygiene — PASS

`python scripts/security_gate_test.py` — PASS (3 tests)

`./scripts/verify.ps1` — PASS, including the security gate and self-tests

`./scripts/full-gate.ps1` — PASS

- control-plane, security, Compose, and PowerShell gates — PASS
- Java: 34 tests — PASS
- Python: 56 tests, 96.05% coverage — PASS
- Web static checks, unit tests, and production build — PASS

## Behavioral evidence

- Git tracked-file enumeration excludes ignored local `.env` material from the
  committed surface and rejects tracked `.env`/key-file artifacts.
- Private-key markers, GitHub/AWS/Google-style high-confidence token patterns,
  and non-placeholder secret assignments produce file/line findings.
- Explicit local placeholders such as `change-me-local-only` and `${SECRET}`
  remain allowed for reproducible development configuration.
- `uv.lock` and npm lockfile v3 metadata are checked for presence and parseability.
- CI workflows require `contents: read` and reject broad/token-minting/write PR
  permissions.
- Compose service ports are required to bind to loopback and image tags may not
  use `latest`.

## Limits

This is a static repository hygiene gate. It does not claim CVE database
freshness, SBOM completeness, dependency exploitability analysis, runtime
container hardening, production authentication/authorization, penetration
testing, or secret validity in external systems.
