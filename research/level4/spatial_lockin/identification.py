from __future__ import annotations

import random
from dataclasses import dataclass
from itertools import pairwise
from math import isfinite, sqrt
from statistics import fmean, pstdev

from .linalg import (
    Matrix,
    Vector,
    add_matrix,
    condition_number,
    identity,
    inverse,
    matmul,
    matrix_rank,
    matvec,
    relative_frobenius_error,
    scale_matrix,
    spectral_radius_nonnegative,
    subtract_matrix,
    trace,
    transition_least_squares,
)
from .reason_codes import ResearchGateError
from .records import Trajectory


@dataclass(frozen=True, slots=True)
class ResidualDiagnostics:
    normalized_rmse: float
    lag_one_autocorrelation: float
    mean_in_sd: float
    rmse_by_magnitude: tuple[tuple[float, float], ...]
    monotonically_growing_scale: bool

    def payload(self) -> dict[str, object]:
        return {
            "normalized_rmse": self.normalized_rmse,
            "lag_one_autocorrelation": self.lag_one_autocorrelation,
            "mean_in_sd": self.mean_in_sd,
            "rmse_by_magnitude": self.rmse_by_magnitude,
            "monotonically_growing_scale": self.monotonically_growing_scale,
        }


@dataclass(frozen=True, slots=True)
class GateAssessment:
    passed: bool
    reason_codes: tuple[str, ...]

    def payload(self) -> dict[str, object]:
        return {"passed": self.passed, "reason_codes": self.reason_codes}


@dataclass(frozen=True, slots=True)
class LayerEstimate:
    layer: str
    a: Matrix
    m: Matrix
    j_probe: Matrix
    kappa: float
    kappa_ci95: tuple[float, float]
    alpha_c: float
    alpha_c_ci95: tuple[float, float]
    rank_by_alpha: tuple[tuple[float, int], ...]
    condition_by_alpha: tuple[tuple[float, float], ...]
    spectral_radius_a: float
    local_linearity_drift: float
    residuals: ResidualDiagnostics
    recovery_errors: tuple[tuple[str, float], ...]
    gate: GateAssessment

    def payload(self) -> dict[str, object]:
        return {
            "layer": self.layer,
            "a": self.a,
            "m": self.m,
            "j_probe": self.j_probe,
            "kappa": self.kappa,
            "kappa_ci95": self.kappa_ci95,
            "alpha_c": self.alpha_c,
            "alpha_c_ci95": self.alpha_c_ci95,
            "rank_by_alpha": self.rank_by_alpha,
            "condition_by_alpha": self.condition_by_alpha,
            "spectral_radius_a": self.spectral_radius_a,
            "local_linearity_drift": self.local_linearity_drift,
            "residuals": self.residuals.payload(),
            "recovery_errors": self.recovery_errors,
            "gate": self.gate.payload(),
        }


def _zero_matrix() -> Matrix:
    return ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0), (0.0, 0.0, 0.0))


def _gate_number(gates: dict[str, object], name: str) -> float:
    value = gates.get(name)
    if isinstance(value, bool) or not isinstance(value, (float, int)):
        raise TypeError(f"Gate {name} must be numeric")
    return float(value)


def feedback_coefficient(a: Matrix, m: Matrix) -> float:
    return trace(matmul(inverse(subtract_matrix(identity(), a)), m))


def _estimate_j(trajectories: tuple[Trajectory, ...]) -> tuple[Matrix, Matrix]:
    transitions = tuple(
        pair for trajectory in trajectories for pair in trajectory.transitions()
    )
    return transition_least_squares(transitions)


def _estimate_core(
    trajectories: tuple[Trajectory, ...], probe_alpha: float
) -> tuple[Matrix, Matrix, Matrix, tuple[tuple[float, Matrix], ...]]:
    alpha_values = sorted({trajectory.alpha for trajectory in trajectories})
    if alpha_values != [0.0, probe_alpha]:
        raise ValueError(
            "identification data do not match the pre-registered feedback settings"
        )
    estimates: list[tuple[float, Matrix]] = []
    grams: list[tuple[float, Matrix]] = []
    for alpha in alpha_values:
        selected = tuple(item for item in trajectories if item.alpha == alpha)
        estimate, gram = _estimate_j(selected)
        estimates.append((alpha, estimate))
        grams.append((alpha, gram))
    a = estimates[0][1]
    j_probe = estimates[1][1]
    m = scale_matrix(subtract_matrix(j_probe, a), 1.0 / probe_alpha)
    return a, m, j_probe, tuple(grams)


def _trajectory_sufficient(trajectory: Trajectory) -> tuple[Matrix, Matrix]:
    gram = _zero_matrix()
    cross = _zero_matrix()
    for before, after in trajectory.transitions():
        from .linalg import outer

        gram = add_matrix(gram, outer(before, before))
        cross = add_matrix(cross, outer(after, before))
    return gram, cross


def _j_from_sufficient(parts: tuple[tuple[Matrix, Matrix], ...]) -> Matrix:
    gram = _zero_matrix()
    cross = _zero_matrix()
    for part_gram, part_cross in parts:
        gram = add_matrix(gram, part_gram)
        cross = add_matrix(cross, part_cross)
    if matrix_rank(gram) < 3:
        raise ResearchGateError("RANK_DEFICIENT", "bootstrap resample")
    return matmul(cross, inverse(gram))


def _quantile(sorted_values: list[float], probability: float) -> float:
    if not sorted_values:
        raise ValueError("quantile sample is empty")
    position = (len(sorted_values) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(sorted_values) - 1)
    fraction = position - lower
    return sorted_values[lower] * (1 - fraction) + sorted_values[upper] * fraction


def _bootstrap_kappa(
    trajectories: tuple[Trajectory, ...], probe_alpha: float, resamples: int, seed: int
) -> tuple[float, float]:
    rng = random.Random(seed)
    by_alpha = {
        alpha: tuple(
            _trajectory_sufficient(item) for item in trajectories if item.alpha == alpha
        )
        for alpha in (0.0, probe_alpha)
    }
    samples: list[float] = []
    for _ in range(resamples):
        selected: dict[float, tuple[tuple[Matrix, Matrix], ...]] = {}
        for alpha, parts in by_alpha.items():
            selected[alpha] = tuple(
                parts[rng.randrange(len(parts))] for _ in range(len(parts))
            )
        a = _j_from_sufficient(selected[0.0])
        j_probe = _j_from_sufficient(selected[probe_alpha])
        m = scale_matrix(subtract_matrix(j_probe, a), 1.0 / probe_alpha)
        try:
            value = feedback_coefficient(a, m)
        except ResearchGateError:
            continue
        if isfinite(value):
            samples.append(value)
    if len(samples) < max(30, int(resamples * 0.9)):
        raise ResearchGateError(
            "KAPPA_CI_TOO_WIDE", "too many invalid bootstrap samples"
        )
    samples.sort()
    return _quantile(samples, 0.025), _quantile(samples, 0.975)


def _residual_diagnostics(
    trajectories: tuple[Trajectory, ...], estimates: dict[float, Matrix]
) -> ResidualDiagnostics:
    residuals: list[float] = []
    responses: list[float] = []
    lag_pairs: list[tuple[float, float]] = []
    by_magnitude: dict[float, list[float]] = {}
    for trajectory in trajectories:
        previous: Vector | None = None
        estimate = estimates[trajectory.alpha]
        for before, after in trajectory.transitions():
            predicted = matvec(estimate, before)
            residual: Vector = tuple(
                actual - expected
                for actual, expected in zip(after, predicted, strict=True)
            )  # type: ignore[assignment]
            residuals.extend(residual)
            responses.extend(after)
            by_magnitude.setdefault(trajectory.magnitude, []).extend(residual)
            if previous is not None:
                lag_pairs.extend(zip(previous, residual, strict=True))
            previous = residual
    residual_rmse = sqrt(fmean(value * value for value in residuals))
    response_sd = pstdev(responses)
    residual_sd = pstdev(residuals)
    normalized_rmse = residual_rmse / max(response_sd, 1e-15)
    mean_in_sd = abs(fmean(residuals)) / max(residual_sd, 1e-15)
    if lag_pairs:
        left = [pair[0] for pair in lag_pairs]
        right = [pair[1] for pair in lag_pairs]
        left_mean = fmean(left)
        right_mean = fmean(right)
        numerator = sum((a - left_mean) * (b - right_mean) for a, b in lag_pairs)
        denominator = sqrt(
            sum((item - left_mean) ** 2 for item in left)
            * sum((item - right_mean) ** 2 for item in right)
        )
        autocorrelation = numerator / denominator if denominator > 1e-15 else 0.0
    else:
        autocorrelation = 0.0
    rmse_by_magnitude = tuple(
        (magnitude, sqrt(fmean(value * value for value in values)))
        for magnitude, values in sorted(by_magnitude.items())
    )
    scales = [value for _, value in rmse_by_magnitude]
    monotonic = len(scales) > 1 and all(
        following >= current * (1 - 1e-9) for current, following in pairwise(scales)
    )
    return ResidualDiagnostics(
        normalized_rmse, abs(autocorrelation), mean_in_sd, rmse_by_magnitude, monotonic
    )


def _linearity_drift(trajectories: tuple[Trajectory, ...], probe_alpha: float) -> float:
    kappas: list[tuple[float, float]] = []
    for magnitude in sorted({item.magnitude for item in trajectories}):
        selected = tuple(item for item in trajectories if item.magnitude == magnitude)
        a, m, _, _ = _estimate_core(selected, probe_alpha)
        kappas.append((magnitude, feedback_coefficient(a, m)))
    drifts = [
        abs(following - current) / max(abs(current), 1e-12)
        for (_, current), (_, following) in pairwise(kappas)
    ]
    return max(drifts, default=0.0)


def identify_layer(
    trajectories: tuple[Trajectory, ...],
    *,
    probe_alpha: float,
    bootstrap_resamples: int,
    bootstrap_seed: int,
    gates: dict[str, object],
    true_a: Matrix | None = None,
    true_m: Matrix | None = None,
) -> LayerEstimate:
    if not trajectories:
        raise ValueError("identification trajectories are empty")
    layer = trajectories[0].layer
    if any(item.layer != layer for item in trajectories):
        raise ValueError("identification layers must not be mixed")
    a, m, j_probe, grams = _estimate_core(trajectories, probe_alpha)
    kappa = feedback_coefficient(a, m)
    kappa_ci = _bootstrap_kappa(
        trajectories, probe_alpha, bootstrap_resamples, bootstrap_seed
    )
    alpha_c = 1.0 / kappa if kappa > 0 else float("inf")
    alpha_ci = (
        1.0 / kappa_ci[1] if kappa_ci[1] > 0 else float("inf"),
        1.0 / kappa_ci[0] if kappa_ci[0] > 0 else float("inf"),
    )
    conditions = tuple((alpha, condition_number(gram)) for alpha, gram in grams)
    ranks = tuple((alpha, matrix_rank(gram)) for alpha, gram in grams)
    estimates = {0.0: a, probe_alpha: j_probe}
    residuals = _residual_diagnostics(trajectories, estimates)
    drift = _linearity_drift(trajectories, probe_alpha)
    radius = spectral_radius_nonnegative(a)
    recovery: list[tuple[str, float]] = []
    reasons: list[str] = []

    maximum_condition = _gate_number(gates, "condition_number_max")
    if any(rank < 3 for _, rank in ranks):
        reasons.append("RANK_DEFICIENT")
    if any(value > maximum_condition for _, value in conditions):
        reasons.append("CONDITION_EXCEEDED")
    if radius >= _gate_number(gates, "spectral_radius_max"):
        reasons.append("OPEN_LOOP_UNSTABLE")
    if not isfinite(kappa) or kappa <= 0:
        reasons.append("KAPPA_NOT_POSITIVE")
    if kappa_ci[0] <= 0:
        reasons.append("KAPPA_CI_CROSSES_ZERO")
    interval_width = (kappa_ci[1] - kappa_ci[0]) / max(abs(kappa), 1e-15)
    if interval_width > _gate_number(gates, "kappa_ci_relative_width_max"):
        reasons.append("KAPPA_CI_TOO_WIDE")
    if not isfinite(alpha_c) or not all(isfinite(item) for item in alpha_ci):
        reasons.append("THRESHOLD_NONFINITE")
    if drift > _gate_number(gates, "local_linearity_drift_max"):
        reasons.append("LOCAL_LINEARITY_DRIFT")
    if residuals.normalized_rmse > _gate_number(gates, "residual_nrmse_max"):
        reasons.append("RESIDUAL_RMSE_EXCEEDED")
    if residuals.lag_one_autocorrelation > _gate_number(
        gates, "residual_autocorrelation_max"
    ):
        reasons.append("RESIDUAL_AUTOCORRELATION")
    if residuals.mean_in_sd > _gate_number(gates, "residual_mean_sd_max"):
        reasons.append("RESIDUAL_MEAN_BIAS")
    if residuals.monotonically_growing_scale:
        reasons.append("RESIDUAL_SCALE_TREND")

    if true_a is not None and true_m is not None:
        a_error = relative_frobenius_error(a, true_a)
        m_error = relative_frobenius_error(m, true_m)
        true_kappa = feedback_coefficient(true_a, true_m)
        true_threshold = 1.0 / true_kappa
        threshold_error = abs(alpha_c - true_threshold) / true_threshold
        recovery.extend(
            (
                ("a_relative_error", a_error),
                ("m_relative_error", m_error),
                ("threshold_relative_error", threshold_error),
                ("true_threshold", true_threshold),
            )
        )
        if a_error > _gate_number(gates, "layer_r_a_relative_error_max"):
            reasons.append("SYNTHETIC_A_RECOVERY")
        if m_error > _gate_number(gates, "layer_r_m_relative_error_max"):
            reasons.append("SYNTHETIC_M_RECOVERY")
        if threshold_error > _gate_number(
            gates, "layer_r_threshold_relative_error_max"
        ):
            reasons.append("SYNTHETIC_THRESHOLD_RECOVERY")
        if not alpha_ci[0] <= true_threshold <= alpha_ci[1]:
            reasons.append("SYNTHETIC_THRESHOLD_COVERAGE")

    unique_reasons = tuple(dict.fromkeys(reasons))
    return LayerEstimate(
        layer,
        a,
        m,
        j_probe,
        kappa,
        kappa_ci,
        alpha_c,
        alpha_ci,
        ranks,
        conditions,
        radius,
        drift,
        residuals,
        tuple(recovery),
        GateAssessment(not unique_reasons, unique_reasons),
    )
