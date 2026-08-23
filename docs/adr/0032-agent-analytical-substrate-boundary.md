# ADR-0032: Agent Analytical Substrate Boundary

Date: 2026-08-24  
Status: Accepted

## Context

Agent Runtime already enforces role grants, argument allow-lists, per-session
budgets, deterministic fallback, and immutable audit records. Enhancement
surfaces now expose metrics, lineage, and Decision X-Ray evidence that agents
may inspect without gaining authority over dispatch or durable state.

## Decision

Add three bounded read tools on the existing runtime: `metrics.read`,
`lineage.read`, and `decision.xray.read`. Their inputs and outputs are metadata
only, each invocation is audited, and roles are explicitly granted. No command,
mutation, broker, database, or remediation tool is registered. Unknown or
state-changing names fail through the existing rejection path.

## Consequences

- Agent analysis can be grounded in structured evidence and lineage.
- Audit IDs and call budgets remain the control boundary for orchestration.
- Durable Java state, dispatch correctness, and operator commands remain outside
  the agent substrate.
