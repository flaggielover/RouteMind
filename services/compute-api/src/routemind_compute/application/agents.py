from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

AgentMetadata = tuple[tuple[str, str], ...]
ToolPermission = Literal["read", "research"]
AuditOutcome = Literal["accepted", "rejected", "failed"]
OrchestrationMode = Literal["tool-results", "deterministic-fallback"]
ToolHandler = Callable[[AgentMetadata], AgentMetadata]
MAX_METADATA_ITEMS = 16
MAX_TEXT_LENGTH = 256


def _validate_text(value: str, name: str) -> None:
    if not value.strip():
        raise ValueError(f"{name} must not be blank")
    if len(value) > MAX_TEXT_LENGTH:
        raise ValueError(f"{name} is too long")


def _normalize_metadata(values: AgentMetadata) -> AgentMetadata:
    if len(values) > MAX_METADATA_ITEMS:
        raise ValueError("agent metadata has too many items")
    normalized = tuple(sorted(values))
    for key, value in normalized:
        _validate_text(key, "agent metadata key")
        _validate_text(value, "agent metadata value")
    if len({key for key, _ in normalized}) != len(normalized):
        raise ValueError("agent metadata keys must be unique")
    return normalized


@dataclass(frozen=True, slots=True)
class ToolDefinition:
    name: str
    permission: ToolPermission
    allowed_roles: tuple[str, ...]
    argument_names: tuple[str, ...]
    handler: ToolHandler

    def __post_init__(self) -> None:
        _validate_text(self.name, "tool name")
        if self.permission not in ("read", "research"):
            raise ValueError("tool permission must be read or research")
        if not self.allowed_roles or any(not role.strip() for role in self.allowed_roles):
            raise ValueError("tool roles must not be blank")
        if len(set(self.allowed_roles)) != len(self.allowed_roles):
            raise ValueError("tool roles must be unique")
        if len(set(self.argument_names)) != len(self.argument_names):
            raise ValueError("tool argument names must be unique")
        if any(not argument.strip() for argument in self.argument_names):
            raise ValueError("tool argument names must not be blank")


@dataclass(frozen=True, slots=True)
class AgentRequest:
    request_id: str
    actor: str
    role: str
    session_id: str
    tool_name: str
    arguments: AgentMetadata = ()

    def __post_init__(self) -> None:
        for value, name in (
            (self.request_id, "request_id"),
            (self.actor, "actor"),
            (self.role, "role"),
            (self.session_id, "session_id"),
            (self.tool_name, "tool_name"),
        ):
            _validate_text(value, name)
        object.__setattr__(self, "arguments", _normalize_metadata(self.arguments))


@dataclass(frozen=True, slots=True)
class ToolResponse:
    accepted: bool
    output: AgentMetadata
    audit_id: str
    reason: str


@dataclass(frozen=True, slots=True)
class AuditRecord:
    audit_id: str
    sequence: int
    request_id: str
    session_id: str
    actor: str
    role: str
    tool_name: str
    permission: ToolPermission | None
    outcome: AuditOutcome
    reason: str


@dataclass(frozen=True, slots=True)
class AgentPolicy:
    grants: tuple[tuple[str, tuple[str, ...]], ...]
    max_calls_per_session: int = 8

    def __post_init__(self) -> None:
        if self.max_calls_per_session <= 0:
            raise ValueError("max_calls_per_session must be positive")
        roles = tuple(role for role, _ in self.grants)
        if len(set(roles)) != len(roles) or any(not role.strip() for role in roles):
            raise ValueError("policy roles must be unique and non-blank")
        if any(
            len(set(tools)) != len(tools) or any(not tool.strip() for tool in tools)
            for _, tools in self.grants
        ):
            raise ValueError("policy tools must be unique")

    def allows(self, role: str, tool_name: str) -> bool:
        return any(role == candidate and tool_name in tools for candidate, tools in self.grants)


class AgentRuntime:
    """Bounded, read-oriented tool execution with immutable audit evidence."""

    def __init__(self, definitions: tuple[ToolDefinition, ...], policy: AgentPolicy) -> None:
        names = tuple(definition.name for definition in definitions)
        if len(set(names)) != len(names):
            raise ValueError("tool names must be unique")
        unknown_grants = {tool for _, tools in policy.grants for tool in tools if tool not in names}
        if unknown_grants:
            raise ValueError("policy grants an unknown tool")
        self._definitions = {definition.name: definition for definition in definitions}
        self._policy = policy
        self._calls: dict[str, int] = {}
        self._audit: list[AuditRecord] = []

    def invoke(self, request: AgentRequest) -> ToolResponse:
        definition = self._definitions.get(request.tool_name)
        if definition is None:
            return self._reject(request, None, "unknown_tool")
        if request.role not in definition.allowed_roles or not self._policy.allows(
            request.role, request.tool_name
        ):
            return self._reject(request, definition.permission, "permission_denied")
        if any(key not in definition.argument_names for key, _ in request.arguments):
            return self._reject(request, definition.permission, "argument_not_allowed")
        used = self._calls.get(request.session_id, 0)
        if used >= self._policy.max_calls_per_session:
            return self._reject(request, definition.permission, "call_budget_exceeded")
        self._calls[request.session_id] = used + 1
        try:
            output = _normalize_metadata(definition.handler(request.arguments))
        except Exception:
            audit_id = self._record(
                request, definition.permission, "failed", "tool_execution_failed"
            )
            return ToolResponse(False, (), audit_id, "tool_execution_failed")
        audit_id = self._record(request, definition.permission, "accepted", "ok")
        return ToolResponse(True, output, audit_id, "ok")

    def _reject(
        self, request: AgentRequest, permission: ToolPermission | None, reason: str
    ) -> ToolResponse:
        audit_id = self._record(request, permission, "rejected", reason)
        return ToolResponse(False, (), audit_id, reason)

    def _record(
        self,
        request: AgentRequest,
        permission: ToolPermission | None,
        outcome: AuditOutcome,
        reason: str,
    ) -> str:
        sequence = len(self._audit) + 1
        audit_id = f"audit-{sequence:06d}"
        self._audit.append(
            AuditRecord(
                audit_id,
                sequence,
                request.request_id,
                request.session_id,
                request.actor,
                request.role,
                request.tool_name,
                permission,
                outcome,
                reason,
            )
        )
        return audit_id

    @property
    def audit_records(self) -> tuple[AuditRecord, ...]:
        return tuple(self._audit)


@dataclass(frozen=True, slots=True)
class OrchestrationPlan:
    operation: str
    calls: tuple[AgentRequest, ...]
    fallback: AgentMetadata = (("mode", "deterministic-fallback"),)

    def __post_init__(self) -> None:
        if not self.operation.strip():
            raise ValueError("operation must not be blank")
        object.__setattr__(self, "fallback", _normalize_metadata(self.fallback))


@dataclass(frozen=True, slots=True)
class OrchestrationResult:
    mode: OrchestrationMode
    output: AgentMetadata
    audit_ids: tuple[str, ...]


class AgentOrchestrator:
    def __init__(self, runtime: AgentRuntime, *, max_plan_calls: int = 8) -> None:
        if max_plan_calls <= 0:
            raise ValueError("max_plan_calls must be positive")
        self.runtime = runtime
        self.max_plan_calls = max_plan_calls

    def execute(self, plan: OrchestrationPlan | None) -> OrchestrationResult:
        if plan is None:
            return OrchestrationResult(
                "deterministic-fallback",
                (("mode", "deterministic-fallback"), ("reason", "agent_unavailable")),
                (),
            )
        if len(plan.calls) > self.max_plan_calls:
            return self._fallback(plan, (), "plan_call_budget_exceeded")
        output: list[tuple[str, str]] = []
        audit_ids: list[str] = []
        for call in plan.calls:
            response = self.runtime.invoke(call)
            audit_ids.append(response.audit_id)
            if not response.accepted:
                return self._fallback(plan, tuple(audit_ids), response.reason)
            output.extend((f"{call.tool_name}.{key}", value) for key, value in response.output)
        return OrchestrationResult("tool-results", tuple(output), tuple(audit_ids))

    @staticmethod
    def _fallback(
        plan: OrchestrationPlan, audit_ids: tuple[str, ...], reason: str
    ) -> OrchestrationResult:
        return OrchestrationResult(
            "deterministic-fallback",
            (*plan.fallback, ("operation", plan.operation), ("reason", reason)),
            audit_ids,
        )
