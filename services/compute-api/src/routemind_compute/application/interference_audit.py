"""Fail-closed R3-353 dispatch-interference support audit."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

_FIELDS = (
    "shared_supply",
    "zone_spillover",
    "carryover",
    "treatment_assignments",
    "outcome_observations",
)


class InterferenceAuditError(ValueError):
    """Raised when interference support input is malformed."""


@dataclass(frozen=True, slots=True)
class InterferenceAudit:
    status: Literal["INSUFFICIENT_DATA", "READY_FOR_ANALYSIS"]
    available_fields: tuple[str, ...]
    missing_fields: tuple[str, ...]
    reason: str
    claim_boundary: str = "DISPATCH_INTERFERENCE_AUDIT_DOES_NOT_ESTABLISH_AB_OR_CAUSAL_EFFECT"


def audit_interference_support(support: Mapping[str, bool]) -> InterferenceAudit:
    if set(support) != set(_FIELDS):
        raise InterferenceAuditError("interference support fields mismatch")
    available = tuple(field for field in _FIELDS if support[field])
    missing = tuple(field for field in _FIELDS if not support[field])
    if missing:
        return InterferenceAudit(
            "INSUFFICIENT_DATA",
            available,
            missing,
            "R3-352 freezes interference mechanisms but no simulation outcomes are available",
        )
    return InterferenceAudit(
        "READY_FOR_ANALYSIS",
        available,
        (),
        "all preregistered interference support fields are present",
    )


__all__ = ["InterferenceAudit", "InterferenceAuditError", "audit_interference_support"]
