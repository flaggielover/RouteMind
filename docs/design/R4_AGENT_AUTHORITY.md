# RouteMind Agent Authority Boundary

R4-450 freezes the boundary around the existing Python `AgentRuntime` and
`AgentOrchestrator`. Agents may read, analyze, and orchestrate bounded research
work. They never own Java durable state, hard real-time dispatch correctness,
notification sends, or a production or scientific claim.

The policy contract treats external text as untrusted data, requires an explicit
role/tool/argument allowlist and per-session/plan budgets, and records every
accepted, rejected, or failed call in append-only sequence order. Unknown tools,
denied roles, handler failures, timeouts, and unavailable agents fail closed or
return deterministic fallback. State-changing tools are reserved and denied by
default; any future state change requires explicit human approval plus Java
authority, idempotency, scope, audit, timeout, and rollback evidence.

The deterministic dispatch registry remains independent of agent availability.
No external LLM SDK, provider network, production data, or live command was
used by this local contract gate. Scientific FAIL and NO-CLAIM outcomes remain
valid terminal evidence.
