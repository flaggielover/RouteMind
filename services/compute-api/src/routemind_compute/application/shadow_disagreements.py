"""Fail-closed R3-351 shadow disagreement mining report generator."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal

_CATEGORIES = ("regime", "geography", "delay", "scarcity", "risk", "compute")
_REQUIRED = ("alternate_strategy_outcome", *_CATEGORIES)


class ShadowDisagreementError(ValueError):
    """Raised when a disagreement audit input is malformed."""


@dataclass(frozen=True, slots=True)
class ShadowDisagreementReport:
    status: Literal["INSUFFICIENT_DATA", "READY_FOR_ANALYSIS"]
    record_count: int
    disagreement_count: int
    available_fields: tuple[str, ...]
    missing_fields: tuple[str, ...]
    category_counts: tuple[tuple[str, int], ...]
    reason: str
    claim_boundary: str = "SHADOW_DISAGREEMENT_DOES_NOT_ESTABLISH_CANDIDATE_SUPERIORITY"


def audit_shadow_disagreements(
    records: Sequence[Mapping[str, object]],
) -> ShadowDisagreementReport:
    """Audit corpus support without replaying decisions or assigning authority."""

    if not isinstance(records, Sequence) or isinstance(records, (str, bytes, bytearray)):
        raise ShadowDisagreementError("shadow records must be an array")
    available = tuple(field for field in _REQUIRED if all(field in record for record in records))
    missing = tuple(field for field in _REQUIRED if field not in available)
    if missing:
        return ShadowDisagreementReport(
            "INSUFFICIENT_DATA",
            len(records),
            0,
            available,
            missing,
            tuple((category, 0) for category in _CATEGORIES),
            "Decision Corpus records retain one selected action but no alternate "
            "strategy outcomes or disagreement strata",
        )
    category_counts = tuple(
        (category, sum(1 for record in records if bool(record[category])))
        for category in _CATEGORIES
    )
    disagreements = sum(1 for record in records if bool(record["alternate_strategy_outcome"]))
    return ShadowDisagreementReport(
        "READY_FOR_ANALYSIS",
        len(records),
        disagreements,
        available,
        (),
        category_counts,
        "all preregistered disagreement strata and alternate outcomes are present",
    )


__all__ = ["ShadowDisagreementError", "ShadowDisagreementReport", "audit_shadow_disagreements"]
