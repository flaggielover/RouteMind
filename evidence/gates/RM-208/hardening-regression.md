# RM-208 Hardening Integration and Regression Evidence

## Executed local gates

- `scripts/verify.ps1` passed the task graph, security, recovery, release,
  staged-release, Compose syntax, and PowerShell checks.
- `scripts/business-api.ps1 -Action test` passed: Maven BUILD SUCCESS, 68 Java
  tests, 0 failures/errors.
- `scripts/compute-api.ps1 -Action check` passed: Ruff, format, mypy, 5
  schemas/15 fixtures, 160 Python tests, 95.84% coverage, and the seeded
  determinism gate.
- `scripts/web.ps1 -Action check` passed: 49 unit tests plus production build.
- `scripts/web.ps1 -Action e2e` passed: 34 Playwright tests, 2 existing
  desktop-only skips.
- GitHub Actions run `32629363069` for checkpoint `15f86f8` passed all five
  jobs: control plane, Java, Python/contracts, browser, and resilience.

## Infrastructure evidence boundary

`docker compose config --quiet` passed. A fresh
`scripts/full-gate.ps1 -Infrastructure` attempt could not progress because the
local Docker Desktop API stopped responding to `docker compose ps --status
running -q`; the command was interrupted after preserving the repository and
external data. No infrastructure behavior changed in RM-206, RM-207, or
RM-208. The real PostgreSQL 18.6, RabbitMQ 4.3.5, and Redis 8.10.1 recovery and
end-to-end probes remain recorded in `evidence/gates/RM-170/` and
`evidence/gates/RM-171/` and are reused for this regression gate. A future
Docker-backed rerun is a residual environment check, not a hidden claim of a
fresh live run.

## Regression conclusion

All changed hardening paths are green locally and remotely. Existing customer,
merchant, courier, operations, replay, simulation, What-if, dispatch, VRPTW,
RADS, and degradation behavior remained covered by the full available gates.
The repository has no tracked changes; `.codex-tmp/` remains untracked by policy.
