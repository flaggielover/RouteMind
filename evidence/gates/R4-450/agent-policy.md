# R4-450 Agent Authority and Evaluation Boundary Evidence

Date: 2026-08-25 (Asia/Shanghai)

Status: `LOCAL_VALIDATED / CI_PENDING`

## Frozen contract

- `contracts/agent/r4-450-agent-authority-v1.json` binds Java to durable state
  and hard real-time dispatch correctness, Python to optimization/experiments,
  and agents to read/analysis/experiment orchestration only.
- Read, analysis, and experiment-orchestration tools are non-mutating. A
  state-changing class exists only as an explicit denied reservation. No LLM may
  authorize dispatch, durable writes, notification sends, production claims, or
  scientific claims.
- Prompt injection is untrusted data, tenant/secret leakage is forbidden,
  allowlists and budgets are required, audit is append-only, timeouts are
  bounded, Java owns rollback, and no implicit provider/network call is allowed.

## Executable evidence

- `python scripts/agent_policy.py`: passed. The canonical digest and summary
  are emitted by the validator.
- `python scripts/agent_policy_test.py`: five directed mutation tests passed.
  Mutations cover ownership, state-changing enablement, read-tool mutation,
  budgets/fallback, prompt injection, data leakage, approval, network, claim
  promotion, and negative-result semantics.
- Existing Python agent runtime evidence remains valid: bounded read/research
  tools, role/argument allowlists, per-session budgets, immutable audit rows,
  deterministic fallback, and dispatch-registry independence.
- No external LLM, provider, production data, state-changing command, or R3-325
  rerun occurred. R3-325 remains `E-PASS / X-PASS / S-FAIL / C-NO-CLAIM`.

Remote GitHub Actions validation is the remaining Evidence Gate for this task.
