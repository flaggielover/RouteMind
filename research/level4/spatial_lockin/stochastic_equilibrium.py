from __future__ import annotations

import hashlib
from dataclasses import dataclass
from itertools import pairwise
from math import isfinite, sqrt
from statistics import fmean

from .diagnostic_statistics import ols_slope, quantile
from .linalg import Vector, dot

Label = str


@dataclass(frozen=True, slots=True)
class EquilibriumStatistics:
    coordinate_means: Vector
    projection_mean: float
    covariance_trace: float
    cumulative_drift: float
    block_means: tuple[float, ...]
    block_mean_span: float
    positive_material_occupancy: float
    negative_material_occupancy: float
    material_sign_occupancy: float

    def payload(self) -> dict[str, object]:
        def finite_or_none(value: float) -> float | None:
            return value if isfinite(value) else None

        return {
            "coordinate_means": tuple(
                finite_or_none(value) for value in self.coordinate_means
            ),
            "projection_mean": finite_or_none(self.projection_mean),
            "covariance_trace": finite_or_none(self.covariance_trace),
            "cumulative_drift": finite_or_none(self.cumulative_drift),
            "block_means": tuple(finite_or_none(value) for value in self.block_means),
            "block_mean_span": finite_or_none(self.block_mean_span),
            "positive_material_occupancy": finite_or_none(
                self.positive_material_occupancy
            ),
            "negative_material_occupancy": finite_or_none(
                self.negative_material_occupancy
            ),
            "material_sign_occupancy": finite_or_none(self.material_sign_occupancy),
        }


@dataclass(frozen=True, slots=True)
class ClassifiedRun:
    layer: str
    alpha: float
    multiplier: float
    seed: int
    initial_id: str
    final_state: Vector
    statistics: EquilibriumStatistics
    label: Label
    trace_digest: str
    operational: dict[str, float]

    def payload(self) -> dict[str, object]:
        return {
            "layer": self.layer,
            "alpha": self.alpha,
            "multiplier": self.multiplier,
            "seed": self.seed,
            "initial_id": self.initial_id,
            "final_state": tuple(
                value if isfinite(value) else None for value in self.final_state
            ),
            "statistics": self.statistics.payload(),
            "label": self.label,
            "trace_digest": self.trace_digest,
            "operational": self.operational,
        }


@dataclass(frozen=True, slots=True)
class AlphaRegime:
    alpha: float
    multiplier: float
    label: str
    paired_restored_count: int
    paired_locked_count: int
    paired_transitional_count: int
    invalid_count: int
    zero_restored_count: int
    restored_wilson95: tuple[float, float]
    locked_wilson95: tuple[float, float]
    zero_restored_wilson95: tuple[float, float]
    pair_labels_by_seed: tuple[tuple[int, str], ...]

    def payload(self) -> dict[str, object]:
        return {
            "alpha": self.alpha,
            "multiplier": self.multiplier,
            "label": self.label,
            "paired_restored_count": self.paired_restored_count,
            "paired_locked_count": self.paired_locked_count,
            "paired_transitional_count": self.paired_transitional_count,
            "invalid_count": self.invalid_count,
            "zero_restored_count": self.zero_restored_count,
            "restored_wilson95": self.restored_wilson95,
            "locked_wilson95": self.locked_wilson95,
            "zero_restored_wilson95": self.zero_restored_wilson95,
            "pair_labels_by_seed": self.pair_labels_by_seed,
        }


def wilson_interval(successes: int, total: int) -> tuple[float, float]:
    if total <= 0 or successes < 0 or successes > total:
        return (0.0, 0.0)
    z = 1.959963984540054
    proportion = successes / total
    denominator = 1.0 + z * z / total
    center = (proportion + z * z / (2.0 * total)) / denominator
    radius = (
        z
        * sqrt(proportion * (1.0 - proportion) / total + z * z / (4 * total**2))
        / denominator
    )
    return max(0.0, center - radius), min(1.0, center + radius)


def trace_digest(states: tuple[Vector, ...]) -> str:
    digest = hashlib.sha256()
    for state in states:
        for value in state:
            digest.update(value.hex().encode("ascii"))
            digest.update(b",")
        digest.update(b";")
    return digest.hexdigest()


def equilibrium_statistics(
    states: tuple[Vector, ...],
    weights: Vector,
    *,
    terminal_start: int = 3001,
    terminal_stop: int = 4800,
    block_count: int = 6,
    material_sign_threshold: float = 0.002,
) -> EquilibriumStatistics:
    if terminal_start < 0 or terminal_stop < terminal_start:
        raise ValueError("invalid terminal indices")
    terminal = states[terminal_start : terminal_stop + 1]
    expected = terminal_stop - terminal_start + 1
    if len(terminal) != expected or expected % block_count != 0:
        raise ValueError("trajectory does not cover the frozen terminal window")
    if not all(isfinite(value) for state in terminal for value in state):
        raise ValueError("trajectory contains non-finite state")
    coordinate_means = tuple(
        fmean(state[index] for state in terminal) for index in range(3)
    )
    projection = tuple(dot(weights, state) for state in terminal)
    projection_mean = fmean(projection)
    denominator = len(terminal) - 1
    covariance_trace = sum(
        sum((state[index] - coordinate_means[index]) ** 2 for state in terminal)
        / denominator
        for index in range(3)
    )
    cumulative_drift = abs(ols_slope(projection)) * (len(projection) - 1)
    width = len(projection) // block_count
    block_means = tuple(
        fmean(projection[index * width : (index + 1) * width])
        for index in range(block_count)
    )
    positive = sum(value >= material_sign_threshold for value in projection) / len(
        projection
    )
    negative = sum(value <= -material_sign_threshold for value in projection) / len(
        projection
    )
    return EquilibriumStatistics(
        coordinate_means,  # type: ignore[arg-type]
        projection_mean,
        covariance_trace,
        cumulative_drift,
        block_means,
        max(block_means) - min(block_means),
        positive,
        negative,
        max(positive, negative),
    )


def classify_statistics(stats: EquilibriumStatistics) -> Label:
    numeric = (
        *stats.coordinate_means,
        stats.projection_mean,
        stats.covariance_trace,
        stats.cumulative_drift,
        *stats.block_means,
        stats.block_mean_span,
        stats.positive_material_occupancy,
        stats.negative_material_occupancy,
    )
    if not all(isfinite(value) for value in numeric):
        return "INVALID"
    restored = (
        all(abs(value) <= 0.002 for value in stats.coordinate_means)
        and abs(stats.projection_mean) <= 0.002
        and stats.covariance_trace <= 0.000025
        and stats.cumulative_drift <= 0.002
        and stats.block_mean_span <= 0.004
        and stats.material_sign_occupancy < 0.90
    )
    if restored:
        return "STOCHASTIC_RESTORED"
    sign = 1.0 if stats.projection_mean >= 0.0 else -1.0
    same_sign_occupancy = (
        stats.positive_material_occupancy
        if sign > 0.0
        else stats.negative_material_occupancy
    )
    locked = (
        abs(stats.projection_mean) >= 0.01
        and same_sign_occupancy >= 0.90
        and stats.covariance_trace <= 0.001
        and stats.cumulative_drift <= 0.004
        and all(sign * value > 0.0 for value in stats.block_means)
    )
    return "LOCKED" if locked else "TRANSITIONAL"


def classify_states(
    layer: str,
    alpha: float,
    multiplier: float,
    seed: int,
    initial_id: str,
    states: tuple[Vector, ...],
    weights: Vector,
    operational: dict[str, float] | None = None,
) -> ClassifiedRun:
    try:
        stats = equilibrium_statistics(states, weights)
        label = classify_statistics(stats)
    except (ValueError, OverflowError):
        stats = EquilibriumStatistics(
            (float("nan"),) * 3,
            float("nan"),
            float("nan"),
            float("nan"),
            (),
            float("nan"),
            float("nan"),
            float("nan"),
            float("nan"),
        )
        label = "INVALID"
    return ClassifiedRun(
        layer,
        alpha,
        multiplier,
        seed,
        initial_id,
        states[-1] if states else (float("nan"),) * 3,
        stats,
        label,
        trace_digest(states),
        dict(operational or {}),
    )


def aggregate_alpha(records: tuple[ClassifiedRun, ...]) -> AlphaRegime:
    if not records:
        raise ValueError("cannot aggregate empty records")
    alpha = records[0].alpha
    multiplier = records[0].multiplier
    seeds = sorted({record.seed for record in records})
    by_key = {(record.seed, record.initial_id): record for record in records}
    pair_rows: list[tuple[int, str]] = []
    invalid = 0
    for seed in seeds:
        positive = by_key.get((seed, "positive"))
        negative = by_key.get((seed, "negative"))
        if (
            positive is None
            or negative is None
            or "INVALID" in (positive.label, negative.label)
        ):
            invalid += 1
            pair_rows.append((seed, "INVALID"))
        elif positive.label == negative.label == "STOCHASTIC_RESTORED":
            pair_rows.append((seed, "PAIRED_RESTORED"))
        elif (
            positive.label == negative.label == "LOCKED"
            and positive.statistics.projection_mean
            * negative.statistics.projection_mean
            < 0.0
        ):
            pair_rows.append((seed, "PAIRED_LOCKED"))
        else:
            pair_rows.append((seed, "PAIRED_TRANSITIONAL"))
    total = len(seeds)
    restored = sum(label == "PAIRED_RESTORED" for _, label in pair_rows)
    locked = sum(label == "PAIRED_LOCKED" for _, label in pair_rows)
    transitional = total - restored - locked - invalid
    zero = [by_key.get((seed, "zero")) for seed in seeds]
    zero_restored = sum(
        item is not None and item.label == "STOCHASTIC_RESTORED" for item in zero
    )
    restored_interval = wilson_interval(restored, total)
    locked_interval = wilson_interval(locked, total)
    if restored >= 48 and restored_interval[0] > 0.60:
        label = "ROBUST_RESTORED"
    elif locked >= 48 and locked_interval[0] > 0.60:
        label = "ROBUST_LOCKED"
    else:
        label = "TRANSITIONAL"
    return AlphaRegime(
        alpha,
        multiplier,
        label,
        restored,
        locked,
        transitional,
        invalid,
        zero_restored,
        restored_interval,
        locked_interval,
        wilson_interval(zero_restored, total),
        tuple(pair_rows),
    )


def select_coarse_bracket(
    regimes: tuple[AlphaRegime, ...],
) -> tuple[AlphaRegime, AlphaRegime] | None:
    ordered = sorted(regimes, key=lambda item: item.alpha)
    for lower, upper in pairwise(ordered):
        if lower.label == "ROBUST_RESTORED" and upper.label == "ROBUST_LOCKED":
            return lower, upper
    return None


def observed_transition(
    regimes: tuple[AlphaRegime, ...],
) -> tuple[float, float] | None:
    ordered = sorted(regimes, key=lambda item: item.alpha)
    restored = [item for item in ordered if item.label == "ROBUST_RESTORED"]
    locked = [item for item in ordered if item.label == "ROBUST_LOCKED"]
    if not restored or not locked:
        return None
    lower = max(restored, key=lambda item: item.alpha)
    higher = [item for item in locked if item.alpha > lower.alpha]
    if not higher:
        return None
    upper = min(higher, key=lambda item: item.alpha)
    if any(
        item.alpha < lower.alpha and item.label == "ROBUST_LOCKED" for item in ordered
    ) or any(
        item.alpha > upper.alpha and item.label == "ROBUST_RESTORED" for item in ordered
    ):
        return None
    return lower.alpha, upper.alpha


def percentile_interval(values: tuple[float, ...]) -> tuple[float, float]:
    return quantile(values, 0.025), quantile(values, 0.975)
