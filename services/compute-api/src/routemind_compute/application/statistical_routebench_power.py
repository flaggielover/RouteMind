"""Prospective paired-t power accounting for Statistical RouteBench."""

from __future__ import annotations

import re
from dataclasses import dataclass
from importlib.metadata import version
from math import ceil, isfinite, sqrt
from statistics import NormalDist
from typing import Literal

from scipy.stats import nct, t

from routemind_compute.application.execution import canonical_digest
from routemind_compute.application.statistical_routebench_protocol import (
    StatisticalRouteBenchProtocol,
)

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SCIPY_VERSION = "1.18.0"
_SOURCE_KINDS = {"synthetic_validation", "r3_325_pilot"}
_MAXIMUM_NUMERICAL_PAIR_COUNT = 1_000_000_000


class ProspectivePowerError(ValueError):
    """Raised when prospective power inputs or numerical outputs are invalid."""


@dataclass(frozen=True, slots=True)
class PilotVarianceInput:
    protocol_id: str
    regime_id: str
    metric_id: str
    pilot_pair_count: int
    paired_variance: float
    source_kind: Literal["synthetic_validation", "r3_325_pilot"]
    source_digest: str

    def __post_init__(self) -> None:
        if not self.protocol_id.strip() or not self.regime_id.strip() or not self.metric_id.strip():
            raise ProspectivePowerError("pilot variance identities must not be blank")
        if (
            not isinstance(self.pilot_pair_count, int)
            or isinstance(self.pilot_pair_count, bool)
            or self.pilot_pair_count < 2
        ):
            raise ProspectivePowerError("pilot variance requires at least two complete pairs")
        if not _is_finite_number(self.paired_variance) or float(self.paired_variance) <= 0.0:
            raise ProspectivePowerError("pilot paired variance must be finite and positive")
        if self.source_kind not in _SOURCE_KINDS:
            raise ProspectivePowerError("pilot variance source kind is unsupported")
        if not _SHA256.fullmatch(self.source_digest):
            raise ProspectivePowerError("pilot variance source digest must be lowercase SHA-256")

    def payload(self) -> dict[str, object]:
        return {
            "protocol_id": self.protocol_id,
            "regime_id": self.regime_id,
            "metric_id": self.metric_id,
            "pilot_pair_count": self.pilot_pair_count,
            "paired_variance": float(self.paired_variance),
            "source_kind": self.source_kind,
            "source_digest": self.source_digest,
        }


@dataclass(frozen=True, slots=True)
class ProspectivePowerPlan:
    protocol_id: str
    regime_id: str
    metric_id: str
    pilot_pair_count: int
    pilot_paired_variance: float
    pilot_standard_deviation: float
    variance_source_kind: str
    variance_source_digest: str
    observed_pilot: bool
    null_boundary: float
    planning_alternative: float
    effect_distance_from_null: float
    standardized_effect_size: float
    familywise_alpha: float
    confirmatory_test_count: int
    local_alpha: float
    target_power: float
    minimum_pair_count: int
    maximum_pair_count: int
    round_up_to_pairs: int
    raw_required_pair_count: int
    required_pair_count: int
    planned_pair_count: int
    power_at_required_count: float
    power_at_cap: float
    disposition: str
    scipy_version: str
    method: str = "one-sided noncentral paired Student-t"
    alpha_method: str = "Bonferroni first-step bound for preregistered Holm family"
    claim_boundary: str = "PROSPECTIVE_DESIGN_NOT_OBSERVED_EFFECT"

    @property
    def plan_digest(self) -> str:
        return canonical_digest(self.payload())

    def payload(self) -> dict[str, object]:
        return {
            "protocol_id": self.protocol_id,
            "regime_id": self.regime_id,
            "metric_id": self.metric_id,
            "pilot_pair_count": self.pilot_pair_count,
            "pilot_paired_variance": self.pilot_paired_variance,
            "pilot_standard_deviation": self.pilot_standard_deviation,
            "variance_source_kind": self.variance_source_kind,
            "variance_source_digest": self.variance_source_digest,
            "observed_pilot": self.observed_pilot,
            "null_boundary": self.null_boundary,
            "planning_alternative": self.planning_alternative,
            "effect_distance_from_null": self.effect_distance_from_null,
            "standardized_effect_size": self.standardized_effect_size,
            "familywise_alpha": self.familywise_alpha,
            "confirmatory_test_count": self.confirmatory_test_count,
            "local_alpha": self.local_alpha,
            "target_power": self.target_power,
            "minimum_pair_count": self.minimum_pair_count,
            "maximum_pair_count": self.maximum_pair_count,
            "round_up_to_pairs": self.round_up_to_pairs,
            "raw_required_pair_count": self.raw_required_pair_count,
            "required_pair_count": self.required_pair_count,
            "planned_pair_count": self.planned_pair_count,
            "power_at_required_count": self.power_at_required_count,
            "power_at_cap": self.power_at_cap,
            "disposition": self.disposition,
            "scipy_version": self.scipy_version,
            "method": self.method,
            "alpha_method": self.alpha_method,
            "claim_boundary": self.claim_boundary,
        }


def plan_primary_power(
    protocol: StatisticalRouteBenchProtocol, pilot: PilotVarianceInput
) -> ProspectivePowerPlan:
    if pilot.protocol_id != protocol.protocol_id:
        raise ProspectivePowerError("pilot variance protocol identity drifted")
    if pilot.regime_id not in protocol.regime_ids:
        raise ProspectivePowerError("pilot variance regime is not frozen")
    if pilot.source_kind == "r3_325_pilot" and (
        pilot.pilot_pair_count != protocol.pilot_replicates_per_regime
    ):
        raise ProspectivePowerError("observed pilot must contain exactly the frozen pair count")
    null_boundary, planning_alternative = _primary_boundaries(protocol, pilot.metric_id)
    effect_distance = abs(planning_alternative - null_boundary)
    standard_deviation = sqrt(float(pilot.paired_variance))
    standardized_effect = effect_distance / standard_deviation
    local_alpha = protocol.familywise_alpha / protocol.number_of_confirmatory_tests
    raw_required = solve_paired_t_sample_size(
        standardized_effect,
        local_alpha,
        protocol.target_power,
        protocol.minimum_confirmatory_pairs_per_regime,
    )
    required = _round_up(raw_required, protocol.round_up_to_pairs)
    maximum = protocol.maximum_confirmatory_pairs_per_regime
    underpowered = required > maximum
    planned = maximum if underpowered else required
    scipy_version = version("scipy")
    if scipy_version != _SCIPY_VERSION:
        raise ProspectivePowerError("SciPy runtime identity drifted")
    return ProspectivePowerPlan(
        protocol_id=protocol.protocol_id,
        regime_id=pilot.regime_id,
        metric_id=pilot.metric_id,
        pilot_pair_count=pilot.pilot_pair_count,
        pilot_paired_variance=float(pilot.paired_variance),
        pilot_standard_deviation=standard_deviation,
        variance_source_kind=pilot.source_kind,
        variance_source_digest=pilot.source_digest,
        observed_pilot=pilot.source_kind == "r3_325_pilot",
        null_boundary=null_boundary,
        planning_alternative=planning_alternative,
        effect_distance_from_null=effect_distance,
        standardized_effect_size=standardized_effect,
        familywise_alpha=protocol.familywise_alpha,
        confirmatory_test_count=protocol.number_of_confirmatory_tests,
        local_alpha=local_alpha,
        target_power=protocol.target_power,
        minimum_pair_count=protocol.minimum_confirmatory_pairs_per_regime,
        maximum_pair_count=maximum,
        round_up_to_pairs=protocol.round_up_to_pairs,
        raw_required_pair_count=raw_required,
        required_pair_count=required,
        planned_pair_count=planned,
        power_at_required_count=paired_t_power(required, standardized_effect, local_alpha),
        power_at_cap=paired_t_power(maximum, standardized_effect, local_alpha),
        disposition=("UNDERPOWERED_AT_CAP" if underpowered else "POWER_TARGET_MET_WITHIN_CAP"),
        scipy_version=scipy_version,
    )


def paired_t_power(pair_count: int, standardized_effect: float, local_alpha: float) -> float:
    _validate_pair_count(pair_count)
    if not _is_finite_number(standardized_effect) or float(standardized_effect) <= 0.0:
        raise ProspectivePowerError("standardized effect must be finite and positive")
    if not _is_probability(local_alpha) or float(local_alpha) >= 0.5:
        raise ProspectivePowerError("local alpha must be strictly between zero and 0.5")
    degrees_of_freedom = pair_count - 1
    critical = float(t.ppf(1.0 - float(local_alpha), degrees_of_freedom))
    noncentrality = float(standardized_effect) * sqrt(pair_count)
    power = float(nct.sf(critical, degrees_of_freedom, noncentrality))
    if not isfinite(power) or not 0.0 <= power <= 1.0:
        raise ProspectivePowerError("paired-t power calculation returned an invalid value")
    return power


def solve_paired_t_sample_size(
    standardized_effect: float,
    local_alpha: float,
    target_power: float,
    minimum_pair_count: int = 2,
) -> int:
    _validate_pair_count(minimum_pair_count)
    if not _is_finite_number(standardized_effect) or float(standardized_effect) <= 0.0:
        raise ProspectivePowerError("standardized effect must be finite and positive")
    if not _is_probability(local_alpha) or float(local_alpha) >= 0.5:
        raise ProspectivePowerError("local alpha must be strictly between zero and 0.5")
    if not _is_probability(target_power) or float(target_power) <= 0.5:
        raise ProspectivePowerError("target power must be strictly between 0.5 and one")
    if paired_t_power(minimum_pair_count, standardized_effect, local_alpha) >= target_power:
        return minimum_pair_count

    normal = NormalDist()
    approximate_scale = (
        normal.inv_cdf(1.0 - float(local_alpha)) + normal.inv_cdf(float(target_power))
    ) / float(standardized_effect)
    if not isfinite(approximate_scale) or approximate_scale > sqrt(_MAXIMUM_NUMERICAL_PAIR_COUNT):
        raise ProspectivePowerError("required pair count exceeds the numerical planning range")
    approximate = ceil(approximate_scale**2)
    lower = minimum_pair_count + 1
    upper = max(lower, approximate)
    while paired_t_power(upper, standardized_effect, local_alpha) < target_power:
        upper *= 2
        if upper > _MAXIMUM_NUMERICAL_PAIR_COUNT:
            raise ProspectivePowerError("required pair count exceeds the numerical planning range")
    while lower < upper:
        midpoint = (lower + upper) // 2
        if paired_t_power(midpoint, standardized_effect, local_alpha) >= target_power:
            upper = midpoint
        else:
            lower = midpoint + 1
    return lower


def _primary_boundaries(
    protocol: StatisticalRouteBenchProtocol, metric_id: str
) -> tuple[float, float]:
    if metric_id == "scenario_risk_index":
        return 0.0, protocol.minimum_detectable_risk_difference
    if metric_id == "assignment_rate":
        return protocol.assignment_noninferiority_margin, 0.0
    raise ProspectivePowerError("power planning is limited to frozen primary metrics")


def _round_up(value: int, increment: int) -> int:
    if not isinstance(increment, int) or isinstance(increment, bool) or increment < 1:
        raise ProspectivePowerError("pair-count rounding increment must be positive")
    return ((value + increment - 1) // increment) * increment


def _validate_pair_count(value: int) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 2:
        raise ProspectivePowerError("paired-t power requires at least two pairs")


def _is_probability(value: object) -> bool:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return False
    numeric = float(value)
    return isfinite(numeric) and 0.0 < numeric < 1.0


def _is_finite_number(value: object) -> bool:
    return (
        isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(float(value))
    )


__all__ = [
    "PilotVarianceInput",
    "ProspectivePowerError",
    "ProspectivePowerPlan",
    "paired_t_power",
    "plan_primary_power",
    "solve_paired_t_sample_size",
]
