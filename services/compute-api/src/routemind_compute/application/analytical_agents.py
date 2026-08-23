"""Bounded read tools for metrics, lineage, and decision evidence."""

from __future__ import annotations

from dataclasses import dataclass

from routemind_compute.application.agents import (
    AgentMetadata,
    AgentPolicy,
    AgentRequest,
    AgentRuntime,
    AuditRecord,
    ToolDefinition,
    ToolResponse,
)


@dataclass(frozen=True, slots=True)
class AnalyticalReadModels:
    """Small immutable projections supplied by the owning read models."""

    metrics: AgentMetadata = (
        ("source", "semantic-metrics"),
        ("contract", "v1"),
        ("state_changes", "mediated"),
    )
    lineage: AgentMetadata = (
        ("source", "artifact-lineage"),
        ("contract", "v1"),
        ("state_changes", "mediated"),
    )
    decision_xray: AgentMetadata = (
        ("source", "decision-xray"),
        ("contract", "v1"),
        ("state_changes", "mediated"),
    )


class AnalyticalAgentSubstrate:
    """Compose read-only analytical tools on the existing audited runtime."""

    def __init__(
        self,
        models: AnalyticalReadModels | None = None,
        *,
        max_calls_per_session: int = 8,
    ) -> None:
        selected = models or AnalyticalReadModels()
        definitions = (
            ToolDefinition(
                "metrics.read",
                "read",
                ("operator", "researcher", "analyst"),
                ("consumer",),
                lambda arguments: _read_model(selected.metrics, arguments, "metrics"),
            ),
            ToolDefinition(
                "lineage.read",
                "research",
                ("operator", "researcher", "analyst"),
                ("artifact_id",),
                lambda arguments: _read_model(selected.lineage, arguments, "lineage"),
            ),
            ToolDefinition(
                "decision.xray.read",
                "read",
                ("operator", "researcher"),
                ("decision_id",),
                lambda arguments: _read_model(selected.decision_xray, arguments, "decision_xray"),
            ),
        )
        policy = AgentPolicy(
            (
                ("operator", ("metrics.read", "lineage.read", "decision.xray.read")),
                ("researcher", ("metrics.read", "lineage.read", "decision.xray.read")),
                ("analyst", ("metrics.read", "lineage.read")),
            ),
            max_calls_per_session=max_calls_per_session,
        )
        self.runtime = AgentRuntime(definitions, policy)

    def invoke(self, request: AgentRequest) -> ToolResponse:
        return self.runtime.invoke(request)

    @property
    def audit_records(self) -> tuple[AuditRecord, ...]:
        return self.runtime.audit_records


def _read_model(
    model: AgentMetadata,
    arguments: AgentMetadata,
    kind: str,
) -> AgentMetadata:
    return (("kind", kind), *model, *arguments)


__all__ = ["AnalyticalAgentSubstrate", "AnalyticalReadModels"]
