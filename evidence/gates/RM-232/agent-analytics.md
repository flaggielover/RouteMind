# RM-232 Agent Analytical Substrate Evidence

Date: 2026-08-24  
Status: passed

## Scope

- Added read-only `metrics.read`, `lineage.read`, and `decision.xray.read`
  tools backed by immutable analytical read models.
- Reused AgentRuntime role grants, argument allow-lists, session budgets,
  deterministic fallback, and immutable audit records.
- Analyst role cannot query Decision X-Ray; operator/researcher roles can read
  all three. Unknown state-changing tool names are rejected.

## Local evidence

- `./scripts/compute-api.ps1 check`: PASS - 236 tests, 95.28% total coverage,
  strict Ruff, format, mypy, 6 schemas/18 fixtures, deterministic replay,
  archive, mart, and semantic-metrics gates.
- `tests/test_analytical_agents.py`: focused coverage for accepted read calls,
  audit sequences, role/argument rejection, unknown mutation rejection, and
  call-budget enforcement.

## Remote evidence

Checkpoint: `bc00832`

GitHub Actions: PASS - run `32662822033`, all five jobs.

## Boundaries

The substrate never owns dispatch correctness, durable business state, commands,
or autonomous remediation. It only returns bounded read evidence.
