"""Identity-preserving Holm correction for Statistical RouteBench."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from math import isfinite
from typing import Literal

from routemind_compute.application.execution import canonical_digest
from routemind_compute.application.statistical_routebench_protocol import (
    StatisticalRouteBenchProtocol,
)

PrimaryMetricId = Literal["scenario_risk_index", "assignment_rate"]

_METHOD = "holm_bonferroni_familywise"
_FAMILY = "eight_risk_superiority_and_eight_assignment_noninferiority_tests"
_METRIC_ORDER: tuple[PrimaryMetricId, ...] = ("scenario_risk_index", "assignment_rate")


class MultiplicityControlError(ValueError):
    """Raised when a confirmatory family or p-value is invalid."""


@dataclass(frozen=True, slots=True)
class ConfirmatoryHypothesisTest:
    protocol_id: str
    regime_id: str
    metric_id: PrimaryMetricId
    raw_p_value: float

    def __post_init__(self) -> None:
        if (
            not isinstance(self.protocol_id, str)
            or not isinstance(self.regime_id, str)
            or not self.protocol_id.strip()
            or not self.regime_id.strip()
        ):
            raise MultiplicityControlError("confirmatory test identities must not be blank")
        if self.metric_id not in _METRIC_ORDER:
            raise MultiplicityControlError(
                "confirmatory test metric is not a frozen primary metric"
            )
        if not _is_p_value(self.raw_p_value):
            raise MultiplicityControlError("raw p-value must be finite and between zero and one")

    @property
    def hypothesis_id(self) -> str:
        return f"{self.protocol_id}:{self.regime_id}:{self.metric_id}"

    def payload(self) -> dict[str, object]:
        return {
            "hypothesis_id": self.hypothesis_id,
            "protocol_id": self.protocol_id,
            "regime_id": self.regime_id,
            "metric_id": self.metric_id,
            "raw_p_value": float(self.raw_p_value),
        }


@dataclass(frozen=True, slots=True)
class HolmAdjustedTest:
    hypothesis_id: str
    protocol_id: str
    regime_id: str
    metric_id: PrimaryMetricId
    raw_p_value: float
    family_rank: int
    holm_multiplier: int
    sequential_alpha_threshold: float
    adjusted_p_value: float
    rejected: bool

    def payload(self) -> dict[str, object]:
        return {
            "hypothesis_id": self.hypothesis_id,
            "protocol_id": self.protocol_id,
            "regime_id": self.regime_id,
            "metric_id": self.metric_id,
            "raw_p_value": self.raw_p_value,
            "family_rank": self.family_rank,
            "holm_multiplier": self.holm_multiplier,
            "sequential_alpha_threshold": self.sequential_alpha_threshold,
            "adjusted_p_value": self.adjusted_p_value,
            "rejected": self.rejected,
        }


@dataclass(frozen=True, slots=True)
class HolmFamilyReport:
    protocol_id: str
    method: str
    family: str
    familywise_alpha: float
    family_size: int
    tests: tuple[HolmAdjustedTest, ...]
    rejected_count: int
    all_rejected: bool
    disposition: str
    claim_boundary: str = "MULTIPLICITY_ACCOUNTING_NOT_EFFECT_CLAIM"

    @property
    def report_digest(self) -> str:
        return canonical_digest(self.payload())

    def payload(self) -> dict[str, object]:
        return {
            "protocol_id": self.protocol_id,
            "method": self.method,
            "family": self.family,
            "familywise_alpha": self.familywise_alpha,
            "family_size": self.family_size,
            "tests": [item.payload() for item in self.tests],
            "rejected_count": self.rejected_count,
            "all_rejected": self.all_rejected,
            "disposition": self.disposition,
            "claim_boundary": self.claim_boundary,
        }


def apply_frozen_holm_family(
    protocol: StatisticalRouteBenchProtocol,
    tests: Sequence[ConfirmatoryHypothesisTest],
) -> HolmFamilyReport:
    expected = _expected_family(protocol)
    expected_set = set(expected)
    family_size = len(expected)
    if len(expected_set) != family_size:
        raise MultiplicityControlError("frozen family hypothesis identities must be unique")
    if protocol.multiplicity_method != _METHOD:
        raise MultiplicityControlError("multiplicity method drifted from the frozen protocol")
    if protocol.multiplicity_family != _FAMILY:
        raise MultiplicityControlError("multiplicity family description drifted")
    if protocol.number_of_confirmatory_tests != family_size:
        raise MultiplicityControlError("confirmatory test count does not match the frozen family")
    if not _is_probability(protocol.familywise_alpha):
        raise MultiplicityControlError(
            "familywise alpha must be finite and strictly between zero and one"
        )

    by_identity: dict[tuple[str, PrimaryMetricId], ConfirmatoryHypothesisTest] = {}
    for item in tests:
        if item.protocol_id != protocol.protocol_id:
            raise MultiplicityControlError("confirmatory test protocol identity drifted")
        identity = (item.regime_id, item.metric_id)
        if identity in by_identity:
            raise MultiplicityControlError(
                "confirmatory family contains a duplicate hypothesis identity"
            )
        by_identity[identity] = item
    if set(by_identity) != expected_set:
        raise MultiplicityControlError(
            "confirmatory family must cover every frozen hypothesis exactly once"
        )

    family_index = {identity: index for index, identity in enumerate(expected)}
    ordered_by_p = sorted(
        by_identity.items(),
        key=lambda entry: (float(entry[1].raw_p_value), family_index[entry[0]]),
    )
    running_adjusted = 0.0
    adjusted_by_identity: dict[tuple[str, PrimaryMetricId], HolmAdjustedTest] = {}
    for zero_based_rank, (identity, item) in enumerate(ordered_by_p):
        rank = zero_based_rank + 1
        multiplier = family_size - zero_based_rank
        running_adjusted = min(
            1.0,
            max(running_adjusted, float(item.raw_p_value) * multiplier),
        )
        adjusted_by_identity[identity] = HolmAdjustedTest(
            hypothesis_id=item.hypothesis_id,
            protocol_id=item.protocol_id,
            regime_id=item.regime_id,
            metric_id=item.metric_id,
            raw_p_value=float(item.raw_p_value),
            family_rank=rank,
            holm_multiplier=multiplier,
            sequential_alpha_threshold=protocol.familywise_alpha / multiplier,
            adjusted_p_value=running_adjusted,
            rejected=running_adjusted <= protocol.familywise_alpha,
        )

    adjusted = tuple(adjusted_by_identity[identity] for identity in expected)
    rejected_count = sum(item.rejected for item in adjusted)
    all_rejected = rejected_count == family_size
    return HolmFamilyReport(
        protocol_id=protocol.protocol_id,
        method=_METHOD,
        family=_FAMILY,
        familywise_alpha=protocol.familywise_alpha,
        family_size=family_size,
        tests=adjusted,
        rejected_count=rejected_count,
        all_rejected=all_rejected,
        disposition=(
            "ALL_CONFIRMATORY_TESTS_REJECTED"
            if all_rejected
            else "ONE_OR_MORE_CONFIRMATORY_TESTS_NOT_REJECTED"
        ),
    )


def _expected_family(
    protocol: StatisticalRouteBenchProtocol,
) -> tuple[tuple[str, PrimaryMetricId], ...]:
    return tuple(
        (regime_id, metric_id) for metric_id in _METRIC_ORDER for regime_id in protocol.regime_ids
    )


def _is_p_value(value: object) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and isfinite(float(value))
        and 0.0 <= float(value) <= 1.0
    )


def _is_probability(value: object) -> bool:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return False
    numeric = float(value)
    return isfinite(numeric) and 0.0 < numeric < 1.0


__all__ = [
    "ConfirmatoryHypothesisTest",
    "HolmAdjustedTest",
    "HolmFamilyReport",
    "MultiplicityControlError",
    "PrimaryMetricId",
    "apply_frozen_holm_family",
]
