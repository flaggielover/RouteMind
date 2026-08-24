"""Paired estimation and uncertainty for the frozen Statistical RouteBench protocol."""

from __future__ import annotations

from dataclasses import dataclass
from math import exp, floor, isfinite, lgamma, log, log1p, sqrt
from statistics import fmean, median, stdev

from routemind_compute.application.execution import canonical_digest
from routemind_compute.application.statistical_routebench_randomness import (
    CommonRandomNumberPlan,
    derive_stream_seed,
)

_CONFIDENCE_LEVEL = 0.95
_TAIL_PROBABILITY = (1.0 + _CONFIDENCE_LEVEL) / 2.0
_STREAM_ORDER = ("demand", "merchant", "courier", "traffic")


class PairedEstimationError(ValueError):
    """Raised when a paired sample or numerical invariant is invalid."""


@dataclass(frozen=True, slots=True)
class PairedMetricSpec:
    metric_id: str
    minimum: float | None = None
    maximum: float | None = None

    def __post_init__(self) -> None:
        if not self.metric_id.strip():
            raise PairedEstimationError("metric identity must not be blank")
        for label, value in (("minimum", self.minimum), ("maximum", self.maximum)):
            if value is not None and not _is_finite_number(value):
                raise PairedEstimationError(f"metric {label} must be finite")
        if self.minimum is not None and self.maximum is not None and self.minimum > self.maximum:
            raise PairedEstimationError("metric minimum must not exceed maximum")


@dataclass(frozen=True, slots=True)
class PairedObservation:
    plan: CommonRandomNumberPlan
    candidate_value: float
    comparator_value: float

    def __post_init__(self) -> None:
        if not _is_finite_number(self.candidate_value) or not _is_finite_number(
            self.comparator_value
        ):
            raise PairedEstimationError("paired arm values must be finite numbers")

    @property
    def difference(self) -> float:
        return float(self.candidate_value) - float(self.comparator_value)


@dataclass(frozen=True, slots=True)
class PairSeedRecord:
    phase: str
    regime_id: str
    replicate: int
    streams: tuple[tuple[str, int, str], ...]
    plan_digest: str

    def payload(self) -> dict[str, object]:
        return {
            "phase": self.phase,
            "regime_id": self.regime_id,
            "replicate": self.replicate,
            "streams": [
                {"stream_name": name, "seed": seed, "stream_digest": digest}
                for name, seed, digest in self.streams
            ],
            "plan_digest": self.plan_digest,
        }


@dataclass(frozen=True, slots=True)
class StudentTInterval:
    confidence_level: float
    degrees_of_freedom: int
    critical_value: float
    standard_error: float
    lower: float
    upper: float
    method: str = "two-sided Student-t interval on paired differences"

    def payload(self) -> dict[str, object]:
        return {
            "confidence_level": self.confidence_level,
            "degrees_of_freedom": self.degrees_of_freedom,
            "critical_value": self.critical_value,
            "standard_error": self.standard_error,
            "lower": self.lower,
            "upper": self.upper,
            "method": self.method,
        }


@dataclass(frozen=True, slots=True)
class LeaveOnePairOutEstimate:
    omitted_replicate: int
    mean_difference: float

    def payload(self) -> dict[str, object]:
        return {
            "omitted_replicate": self.omitted_replicate,
            "mean_difference": self.mean_difference,
        }


@dataclass(frozen=True, slots=True)
class PairedEstimate:
    metric_id: str
    protocol_id: str
    phase: str
    regime_id: str
    n: int
    pair_seeds: tuple[PairSeedRecord, ...]
    candidate_mean: float
    comparator_mean: float
    mean_difference: float
    median_difference: float
    standard_deviation: float
    interval: StudentTInterval
    cohens_dz: float
    ten_percent_winsorized_mean: float
    leave_one_pair_out: tuple[LeaveOnePairOutEstimate, ...]
    leave_one_pair_out_minimum: float
    leave_one_pair_out_maximum: float
    leave_one_pair_out_max_absolute_shift: float
    difference_convention: str = "candidate_minus_comparator"
    sensitivity_disposition: str = "SENSITIVITY_CANNOT_REPLACE_PRIMARY"

    @property
    def report_digest(self) -> str:
        return canonical_digest(self.payload())

    def payload(self) -> dict[str, object]:
        return {
            "metric_id": self.metric_id,
            "protocol_id": self.protocol_id,
            "phase": self.phase,
            "regime_id": self.regime_id,
            "n": self.n,
            "pair_seeds": [item.payload() for item in self.pair_seeds],
            "candidate_mean": self.candidate_mean,
            "comparator_mean": self.comparator_mean,
            "mean_difference": self.mean_difference,
            "median_difference": self.median_difference,
            "standard_deviation": self.standard_deviation,
            "interval": self.interval.payload(),
            "cohens_dz": self.cohens_dz,
            "ten_percent_winsorized_mean": self.ten_percent_winsorized_mean,
            "leave_one_pair_out": [item.payload() for item in self.leave_one_pair_out],
            "leave_one_pair_out_minimum": self.leave_one_pair_out_minimum,
            "leave_one_pair_out_maximum": self.leave_one_pair_out_maximum,
            "leave_one_pair_out_max_absolute_shift": (self.leave_one_pair_out_max_absolute_shift),
            "difference_convention": self.difference_convention,
            "sensitivity_disposition": self.sensitivity_disposition,
        }


def estimate_paired(
    metric: PairedMetricSpec, observations: tuple[PairedObservation, ...]
) -> PairedEstimate:
    if len(observations) < 2:
        raise PairedEstimationError("paired estimation requires at least two complete pairs")
    ordered = tuple(sorted(observations, key=lambda item: item.plan.pair.replicate))
    first = ordered[0].plan.pair
    identities = {
        (item.plan.pair.protocol_id, item.plan.pair.phase, item.plan.pair.regime_id)
        for item in ordered
    }
    if identities != {(first.protocol_id, first.phase, first.regime_id)}:
        raise PairedEstimationError("paired observations must share protocol, phase, and regime")
    replicates = tuple(item.plan.pair.replicate for item in ordered)
    if len(set(replicates)) != len(replicates):
        raise PairedEstimationError("paired observations contain a duplicate pair identity")
    for item in ordered:
        _validate_plan(item.plan)
        _validate_metric_range(metric, float(item.candidate_value), "candidate")
        _validate_metric_range(metric, float(item.comparator_value), "comparator")

    differences = tuple(item.difference for item in ordered)
    mean_difference = fmean(differences)
    standard_deviation = stdev(differences)
    if standard_deviation == 0.0:
        raise PairedEstimationError(
            "paired differences have zero variance; Student-t uncertainty and Cohen's dz "
            "are undefined"
        )
    standard_error = standard_deviation / sqrt(len(differences))
    critical_value = student_t_quantile(_TAIL_PROBABILITY, len(differences) - 1)
    margin = critical_value * standard_error
    leave_one_out = tuple(
        LeaveOnePairOutEstimate(
            item.plan.pair.replicate,
            fmean((*differences[:index], *differences[index + 1 :])),
        )
        for index, item in enumerate(ordered)
    )
    leave_means = tuple(item.mean_difference for item in leave_one_out)
    pair_seeds = tuple(_pair_seed_record(item.plan) for item in ordered)

    return PairedEstimate(
        metric_id=metric.metric_id,
        protocol_id=first.protocol_id,
        phase=first.phase,
        regime_id=first.regime_id,
        n=len(ordered),
        pair_seeds=pair_seeds,
        candidate_mean=fmean(float(item.candidate_value) for item in ordered),
        comparator_mean=fmean(float(item.comparator_value) for item in ordered),
        mean_difference=mean_difference,
        median_difference=median(differences),
        standard_deviation=standard_deviation,
        interval=StudentTInterval(
            _CONFIDENCE_LEVEL,
            len(differences) - 1,
            critical_value,
            standard_error,
            mean_difference - margin,
            mean_difference + margin,
        ),
        cohens_dz=mean_difference / standard_deviation,
        ten_percent_winsorized_mean=_winsorized_mean(differences, 0.10),
        leave_one_pair_out=leave_one_out,
        leave_one_pair_out_minimum=min(leave_means),
        leave_one_pair_out_maximum=max(leave_means),
        leave_one_pair_out_max_absolute_shift=max(
            abs(value - mean_difference) for value in leave_means
        ),
    )


def student_t_cdf(value: float, degrees_of_freedom: int) -> float:
    if not _is_finite_number(value):
        raise PairedEstimationError("Student-t value must be finite")
    _validate_degrees_of_freedom(degrees_of_freedom)
    numeric = float(value)
    if numeric == 0.0:
        return 0.5
    ratio = degrees_of_freedom / (degrees_of_freedom + numeric * numeric)
    tail = 0.5 * _regularized_incomplete_beta(ratio, degrees_of_freedom / 2.0, 0.5)
    return 1.0 - tail if numeric > 0.0 else tail


def student_t_quantile(probability: float, degrees_of_freedom: int) -> float:
    if not _is_finite_number(probability) or not 0.0 < float(probability) < 1.0:
        raise PairedEstimationError("Student-t probability must be strictly between zero and one")
    _validate_degrees_of_freedom(degrees_of_freedom)
    target = float(probability)
    if target == 0.5:
        return 0.0
    if target < 0.5:
        return -student_t_quantile(1.0 - target, degrees_of_freedom)
    lower = 0.0
    upper = 1.0
    while student_t_cdf(upper, degrees_of_freedom) < target:
        upper *= 2.0
        if not isfinite(upper):
            raise PairedEstimationError("Student-t quantile could not be bracketed")
    for _ in range(100):
        midpoint = (lower + upper) / 2.0
        if student_t_cdf(midpoint, degrees_of_freedom) < target:
            lower = midpoint
        else:
            upper = midpoint
    return (lower + upper) / 2.0


def _pair_seed_record(plan: CommonRandomNumberPlan) -> PairSeedRecord:
    streams = tuple((item.stream_name, item.seed, item.stream_digest) for item in plan.streams)
    if tuple(item[0] for item in streams) != _STREAM_ORDER:
        raise PairedEstimationError("paired seed record escaped the frozen stream order")
    return PairSeedRecord(
        plan.pair.phase,
        plan.pair.regime_id,
        plan.pair.replicate,
        streams,
        plan.plan_digest,
    )


def _validate_plan(plan: CommonRandomNumberPlan) -> None:
    for stream in plan.streams:
        if stream.seed != derive_stream_seed(plan.pair, stream.stream_name):
            raise PairedEstimationError("paired random stream seed does not match its pair")
        if stream.stream_digest != canonical_digest(stream.payload()):
            raise PairedEstimationError("paired random stream digest does not match its payload")


def _winsorized_mean(values: tuple[float, ...], proportion: float) -> float:
    ordered = sorted(values)
    count = floor(len(ordered) * proportion)
    if count == 0:
        return fmean(ordered)
    lower = ordered[count]
    upper = ordered[-count - 1]
    winsorized = [lower] * count + ordered[count : len(ordered) - count] + [upper] * count
    return fmean(winsorized)


def _regularized_incomplete_beta(value: float, alpha: float, beta: float) -> float:
    if value <= 0.0:
        return 0.0
    if value >= 1.0:
        return 1.0
    front = exp(
        lgamma(alpha + beta)
        - lgamma(alpha)
        - lgamma(beta)
        + alpha * log(value)
        + beta * log1p(-value)
    )
    if value < (alpha + 1.0) / (alpha + beta + 2.0):
        return front * _beta_continued_fraction(alpha, beta, value) / alpha
    return 1.0 - front * _beta_continued_fraction(beta, alpha, 1.0 - value) / beta


def _beta_continued_fraction(alpha: float, beta: float, value: float) -> float:
    epsilon = 3.0e-14
    floor_value = 1.0e-300
    qab = alpha + beta
    qap = alpha + 1.0
    qam = alpha - 1.0
    c = 1.0
    d = 1.0 - qab * value / qap
    d = floor_value if abs(d) < floor_value else d
    d = 1.0 / d
    result = d
    for iteration in range(1, 201):
        doubled = 2 * iteration
        coefficient = iteration * (beta - iteration) * value / ((qam + doubled) * (alpha + doubled))
        d = 1.0 + coefficient * d
        d = floor_value if abs(d) < floor_value else d
        c = 1.0 + coefficient / c
        c = floor_value if abs(c) < floor_value else c
        d = 1.0 / d
        result *= d * c
        coefficient = -(
            (alpha + iteration) * (qab + iteration) * value / ((alpha + doubled) * (qap + doubled))
        )
        d = 1.0 + coefficient * d
        d = floor_value if abs(d) < floor_value else d
        c = 1.0 + coefficient / c
        c = floor_value if abs(c) < floor_value else c
        d = 1.0 / d
        delta = d * c
        result *= delta
        if abs(delta - 1.0) < epsilon:
            return result
    raise PairedEstimationError("regularized incomplete beta did not converge")


def _validate_metric_range(metric: PairedMetricSpec, value: float, arm: str) -> None:
    if metric.minimum is not None and value < metric.minimum:
        raise PairedEstimationError(f"{arm} value is below the metric minimum")
    if metric.maximum is not None and value > metric.maximum:
        raise PairedEstimationError(f"{arm} value exceeds the metric maximum")


def _validate_degrees_of_freedom(value: int) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise PairedEstimationError("Student-t degrees of freedom must be a positive integer")


def _is_finite_number(value: object) -> bool:
    return (
        isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(float(value))
    )


__all__ = [
    "LeaveOnePairOutEstimate",
    "PairSeedRecord",
    "PairedEstimate",
    "PairedEstimationError",
    "PairedMetricSpec",
    "PairedObservation",
    "StudentTInterval",
    "estimate_paired",
    "student_t_cdf",
    "student_t_quantile",
]
