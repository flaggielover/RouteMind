# RM-070 Agent Runtime and Orchestrator Evidence

Date: 2026-08-22
Local revision before checkpoint: `8b3a88a`

## Scope

The Python compute boundary now provides a bounded `AgentRuntime` and
`AgentOrchestrator`. Tool definitions are limited to read/research permissions,
requests and metadata are length- and count-bounded, role/tool grants are
explicit, calls are budgeted per session, and immutable audit records capture
accepted, rejected, and failed outcomes. Orchestration returns deterministic
fallback results when no plan is available, a plan exceeds its call budget, or
a tool is denied or fails. The runtime does not own durable business state or
hard real-time dispatch correctness, and no LLM SDK or network dependency is
required.

## Executed gates

`./scripts/compute-api.ps1 check` — PASS

- Ruff lint and format checks — PASS
- strict mypy — PASS
- 4 API schemas and 12 contract fixtures — PASS
- 45 Python tests — PASS
- total statement/branch coverage: 96.47% — PASS

`./scripts/full-gate.ps1` — PASS

- control-plane, Compose, and PowerShell gates — PASS
- Java: 34 tests — PASS
- Python: 45 tests, 96.47% coverage — PASS
- Web static checks, unit tests, and production build — PASS

## Behavioral evidence

- Allowed read/research calls produce typed responses and immutable audit rows.
- Unknown tools, denied roles, unknown arguments, duplicate calls over budget,
  and handler failures are rejected or failed with bounded reasons.
- Orchestrator success, missing-plan fallback, denied-call fallback, and
  over-budget fallback are covered by unit tests.
- Existing dispatch registry remains a direct deterministic path independent of
  agent availability.

## Limits

This is a local deterministic runtime boundary. Production identity-provider
integration, external LLM availability, distributed policy storage, and live
multi-process authorization are not claimed by this gate.
