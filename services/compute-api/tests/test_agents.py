from __future__ import annotations

import pytest

from routemind_compute.application.agents import (
    AgentOrchestrator,
    AgentPolicy,
    AgentRequest,
    AgentRuntime,
    OrchestrationPlan,
    ToolDefinition,
)


def echo(arguments: tuple[tuple[str, str], ...]) -> tuple[tuple[str, str], ...]:
    return arguments


def fail(_arguments: tuple[tuple[str, str], ...]) -> tuple[tuple[str, str], ...]:
    raise RuntimeError("injected handler failure")


def runtime(max_calls: int = 2) -> AgentRuntime:
    definitions = (
        ToolDefinition("health.read", "read", ("operator",), ("service",), echo),
        ToolDefinition("research.read", "research", ("researcher",), ("manifest",), echo),
        ToolDefinition("failing.read", "read", ("operator",), (), fail),
    )
    policy = AgentPolicy(
        (("operator", ("health.read", "failing.read")), ("researcher", ("research.read",))),
        max_calls,
    )
    return AgentRuntime(definitions, policy)


def request(
    tool_name: str = "health.read",
    *,
    role: str = "operator",
    session_id: str = "session-1",
    arguments: tuple[tuple[str, str], ...] = (("service", "compute-api"),),
) -> AgentRequest:
    return AgentRequest("request-1", "actor-1", role, session_id, tool_name, arguments)


def test_runtime_accepts_allowed_read_tool_and_audits_outcome() -> None:
    service = runtime()

    result = service.invoke(request())

    assert result.accepted is True
    assert result.output == (("service", "compute-api"),)
    assert result.audit_id == "audit-000001"
    assert service.audit_records[0].outcome == "accepted"
    assert service.audit_records[0].permission == "read"


def test_runtime_rejects_unknown_roles_arguments_and_tools() -> None:
    service = runtime()

    denied_role = service.invoke(request(role="researcher"))
    denied_argument = service.invoke(request(arguments=(("unexpected", "value"),)))
    unknown = service.invoke(request("missing.read"))

    assert [result.reason for result in (denied_role, denied_argument, unknown)] == [
        "permission_denied",
        "argument_not_allowed",
        "unknown_tool",
    ]
    assert all(result.accepted is False for result in (denied_role, denied_argument, unknown))
    assert [record.outcome for record in service.audit_records] == [
        "rejected",
        "rejected",
        "rejected",
    ]


def test_runtime_is_bounded_and_isolates_handler_failures() -> None:
    service = runtime(max_calls=1)

    failed = service.invoke(request("failing.read", arguments=()))
    over_budget = service.invoke(request(session_id="session-1"))

    assert failed.reason == "tool_execution_failed"
    assert over_budget.reason == "call_budget_exceeded"
    assert [record.outcome for record in service.audit_records] == ["failed", "rejected"]


def test_orchestrator_has_deterministic_success_and_fallback_paths() -> None:
    service = runtime()
    orchestrator = AgentOrchestrator(service, max_plan_calls=1)
    plan = OrchestrationPlan("health-check", (request(),))

    success = orchestrator.execute(plan)
    unavailable = orchestrator.execute(None)
    denied = orchestrator.execute(
        OrchestrationPlan("research-check", (request(role="researcher"),))
    )
    too_many = orchestrator.execute(OrchestrationPlan("bounded", (request(), request())))

    assert success.mode == "tool-results"
    assert success.output == (("health.read.service", "compute-api"),)
    assert success.audit_ids == ("audit-000001",)
    assert unavailable.output == (
        ("mode", "deterministic-fallback"),
        ("reason", "agent_unavailable"),
    )
    assert denied.mode == "deterministic-fallback"
    assert denied.output[-1] == ("reason", "permission_denied")
    assert too_many.output[-1] == ("reason", "plan_call_budget_exceeded")


def test_agent_input_validation_preserves_explicit_policy_boundary() -> None:
    with pytest.raises(ValueError, match="tool name"):
        ToolDefinition(" ", "read", ("operator",), (), echo)
    with pytest.raises(ValueError, match="permission"):
        ToolDefinition("write", "write", ("operator",), (), echo)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="roles"):
        ToolDefinition("read", "read", (), (), echo)
    with pytest.raises(ValueError, match="argument names"):
        ToolDefinition("read", "read", ("operator",), ("x", "x"), echo)
    with pytest.raises(ValueError, match="metadata"):
        AgentRequest("id", "actor", "operator", "session", "tool", (("", "value"),))
    with pytest.raises(ValueError, match="max_calls"):
        AgentPolicy((("operator", ("health.read",)),), 0)
    with pytest.raises(ValueError, match="unknown tool"):
        AgentRuntime(
            (ToolDefinition("health.read", "read", ("operator",), (), echo),),
            AgentPolicy((("operator", ("missing",)),)),
        )
    with pytest.raises(ValueError, match="operation"):
        OrchestrationPlan(" ", ())
