# P7 Bounded Agent Runtime and Orchestrator

## Boundary

The Agent Runtime is a Python analysis boundary. It does not own orders,
dispatch correctness, transactions, or durable state. It accepts a plan from an
optional upstream model, but execution is fully deterministic and does not
require an LLM package or network access.

## Tool policy

Tools are registered with a stable name, `read` or `research` permission, an
explicit role allow-list, an argument-key allow-list, and a typed deterministic
handler. There is intentionally no write permission in this first runtime.
Requests carry bounded actor, role, session, and request identifiers plus sorted
string metadata. The runtime rejects unknown tools, roles, arguments, duplicate
keys, and calls beyond a per-session budget before invoking a handler.

## Audit and failure behavior

Every accepted, rejected, or failed invocation appends an immutable audit record
with a monotonic sequence, request/session identity, tool, outcome, and bounded
reason code. Handler exceptions become `tool_execution_failed` responses and do
not escape into an orchestration loop. Audit records are process-local evidence,
not a replacement for Java business audit tables.

## Orchestration

`AgentOrchestrator` executes a bounded tuple of tool calls. A missing plan,
permission rejection, call-budget exhaustion, or tool failure returns the same
deterministic fallback shape. Successful calls return tool outputs in plan order.
The dispatch registry remains directly callable and is never routed through this
runtime, proving hard real-time correctness does not depend on agent availability.

## Validation

Tests cover role and argument enforcement, call budgets, audit outcomes,
deterministic success/fallback behavior, handler failure isolation, and the
no-plan path. The security gate is local/static and does not claim production
identity integration or permission federation.
