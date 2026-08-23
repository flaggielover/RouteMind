from __future__ import annotations

from routemind_compute.application.agents import AgentRequest
from routemind_compute.application.analytical_agents import (
    AnalyticalAgentSubstrate,
    AnalyticalReadModels,
)


def request(tool: str, role: str, key: str, value: str, session: str = "session-1") -> AgentRequest:
    return AgentRequest("request-1", "agent-1", role, session, tool, ((key, value),))


def test_analytical_substrate_exposes_bounded_read_tools_and_audits_calls() -> None:
    substrate = AnalyticalAgentSubstrate(
        AnalyticalReadModels(
            metrics=(("metric", "dispatch_assignment_rate"),),
            lineage=(("artifact", "archive-1"),),
            decision_xray=(("decision", "decision-1"),),
        )
    )

    metrics = substrate.invoke(request("metrics.read", "analyst", "consumer", "web"))
    lineage = substrate.invoke(request("lineage.read", "researcher", "artifact_id", "archive-1"))
    xray = substrate.invoke(request("decision.xray.read", "operator", "decision_id", "decision-1"))

    assert metrics.accepted is True
    assert ("kind", "metrics") in metrics.output
    assert ("metric", "dispatch_assignment_rate") in metrics.output
    assert lineage.accepted is True
    assert xray.accepted is True
    assert [record.sequence for record in substrate.audit_records] == [1, 2, 3]
    assert all(record.outcome == "accepted" for record in substrate.audit_records)


def test_analytical_substrate_rejects_unauthorized_and_state_changing_tools() -> None:
    substrate = AnalyticalAgentSubstrate()
    denied = substrate.invoke(request("decision.xray.read", "analyst", "decision_id", "d-1"))
    mutation = substrate.invoke(request("dispatch.assign", "operator", "order_id", "order-1"))
    wrong_argument = substrate.invoke(request("metrics.read", "analyst", "artifact_id", "a-1"))

    assert denied.reason == "permission_denied"
    assert mutation.reason == "unknown_tool"
    assert wrong_argument.reason == "argument_not_allowed"
    assert [record.outcome for record in substrate.audit_records] == [
        "rejected",
        "rejected",
        "rejected",
    ]


def test_analytical_substrate_preserves_call_budget() -> None:
    substrate = AnalyticalAgentSubstrate(max_calls_per_session=1)
    first = substrate.invoke(request("metrics.read", "analyst", "consumer", "agent"))
    second = substrate.invoke(request("metrics.read", "analyst", "consumer", "agent"))
    assert first.accepted is True
    assert second.reason == "call_budget_exceeded"
