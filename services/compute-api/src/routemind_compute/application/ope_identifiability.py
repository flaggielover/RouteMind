"""Fail-closed R3-354 off-policy identifiability audit."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

_FIELDS = (
    "logged_propensity",
    "exploration_indicator",
    "action_overlap",
    "state_richness",
    "shared_resource_context",
)


class OpeIdentifiabilityError(ValueError):
    """Raised when an OPE support audit input is malformed."""


@dataclass(frozen=True, slots=True)
class OpeIdentifiabilityReport:
    status: Literal["OPE_NOT_IDENTIFIABLE_FROM_CURRENT_LOGS", "IDENTIFIABLE_FOR_SCOPE"]
    available_fields: tuple[str, ...]
    missing_fields: tuple[str, ...]
    reason: str
    claim_boundary: str = "OPE_AUDIT_DOES_NOT_ESTABLISH_OFF_POLICY_EFFECT"


def audit_ope_identifiability(support: Mapping[str, bool]) -> OpeIdentifiabilityReport:
    if set(support) != set(_FIELDS):
        raise OpeIdentifiabilityError("OPE support fields mismatch")
    available = tuple(field for field in _FIELDS if support[field])
    missing = tuple(field for field in _FIELDS if not support[field])
    if missing:
        return OpeIdentifiabilityReport(
            "OPE_NOT_IDENTIFIABLE_FROM_CURRENT_LOGS",
            available,
            missing,
            "Decision Corpus has selected actions and outcomes but no logged "
            "propensities or verified action support",
        )
    return OpeIdentifiabilityReport(
        "IDENTIFIABLE_FOR_SCOPE",
        available,
        (),
        "all preregistered OPE support fields are present; scope review remains required",
    )


__all__ = ["OpeIdentifiabilityError", "OpeIdentifiabilityReport", "audit_ope_identifiability"]
