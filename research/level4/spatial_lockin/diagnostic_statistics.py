from __future__ import annotations

import cmath
import random
from math import isfinite, sqrt
from statistics import fmean, median, pstdev

from .linalg import (
    Matrix,
    Vector,
    add_matrix,
    frobenius_norm,
    matmul,
    scale_matrix,
    subtract_matrix,
    transpose,
)

ZERO_MATRIX: Matrix = ((0.0, 0.0, 0.0),) * 3


def quantile(values: tuple[float, ...], probability: float) -> float:
    if not values:
        raise ValueError("cannot calculate a quantile of an empty sequence")
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


def ols_slope(values: tuple[float, ...]) -> float:
    if len(values) < 2:
        return 0.0
    x_mean = (len(values) - 1) / 2.0
    y_mean = fmean(values)
    denominator = sum((index - x_mean) ** 2 for index in range(len(values)))
    if denominator == 0.0:
        return 0.0
    return (
        sum((index - x_mean) * (value - y_mean) for index, value in enumerate(values))
        / denominator
    )


def theil_sen_slope(values: tuple[float, ...]) -> float:
    if len(values) < 2:
        return 0.0
    slopes = tuple(
        (values[right] - values[left]) / (right - left)
        for left in range(len(values) - 1)
        for right in range(left + 1, len(values))
    )
    return median(slopes)


def mean_first_difference(values: tuple[float, ...]) -> float:
    if len(values) < 2:
        return 0.0
    return (values[-1] - values[0]) / (len(values) - 1)


def block_averaged_slope(values: tuple[float, ...], blocks: int = 10) -> float:
    if len(values) < blocks or len(values) % blocks != 0:
        raise ValueError("series length must be evenly divisible by block count")
    width = len(values) // blocks
    block_means = tuple(
        fmean(values[index * width : (index + 1) * width]) for index in range(blocks)
    )
    return ols_slope(block_means) / width


def moving_block_slope_interval(
    values: tuple[float, ...], *, block_length: int, samples: int, seed: int
) -> tuple[float, float]:
    if len(values) < block_length or block_length <= 0:
        raise ValueError("invalid moving-block bootstrap length")
    rng = random.Random(seed)
    block_count = (len(values) + block_length - 1) // block_length
    estimates: list[float] = []
    for _ in range(samples):
        resample: list[float] = []
        for _ in range(block_count):
            start = rng.randrange(len(values))
            resample.extend(
                values[(start + offset) % len(values)] for offset in range(block_length)
            )
        estimates.append(ols_slope(tuple(resample[: len(values)])))
    return quantile(tuple(estimates), 0.025), quantile(tuple(estimates), 0.975)


def moving_block_difference_interval(
    values: tuple[float, ...], *, block_length: int, samples: int, seed: int
) -> tuple[float, float]:
    if len(values) < block_length or block_length <= 0:
        raise ValueError("invalid moving-block bootstrap length")
    rng = random.Random(seed)
    block_count = (len(values) + block_length - 1) // block_length
    third = max(1, len(values) // 3)
    estimates: list[float] = []
    for _ in range(samples):
        resample: list[float] = []
        for _ in range(block_count):
            start = rng.randrange(len(values))
            resample.extend(
                values[(start + offset) % len(values)] for offset in range(block_length)
            )
        selected = tuple(resample[: len(values)])
        estimates.append(fmean(selected[-third:]) - fmean(selected[:third]))
    return quantile(tuple(estimates), 0.025), quantile(tuple(estimates), 0.975)


def autocorrelation(values: tuple[float, ...], lag: int) -> float:
    if lag <= 0 or len(values) <= lag:
        raise ValueError("lag must be positive and shorter than the series")
    value_mean = fmean(values)
    denominator = sum((value - value_mean) ** 2 for value in values)
    if denominator <= 1e-30:
        return 0.0
    numerator = sum(
        (values[index] - value_mean) * (values[index - lag] - value_mean)
        for index in range(lag, len(values))
    )
    return numerator / denominator


def distribution(values: tuple[float, ...]) -> dict[str, object]:
    if not values or not all(isfinite(value) for value in values):
        raise ValueError("distribution requires finite values")
    value_mean = fmean(values)
    value_sd = pstdev(values)
    skewness = (
        fmean(((value - value_mean) / value_sd) ** 3 for value in values)
        if value_sd > 0.0
        else 0.0
    )
    return {
        "count": len(values),
        "mean": value_mean,
        "median": median(values),
        "standard_deviation": value_sd,
        "variance": value_sd * value_sd,
        "minimum": min(values),
        "maximum": max(values),
        "quantiles": {
            "0.025": quantile(values, 0.025),
            "0.25": quantile(values, 0.25),
            "0.50": quantile(values, 0.50),
            "0.75": quantile(values, 0.75),
            "0.975": quantile(values, 0.975),
        },
        "fraction_positive": sum(value > 0.0 for value in values) / len(values),
        "fraction_negative": sum(value < 0.0 for value in values) / len(values),
        "fraction_zero": sum(value == 0.0 for value in values) / len(values),
        "skewness": skewness,
    }


def covariance_matrix(values: tuple[Vector, ...]) -> Matrix:
    if not values:
        raise ValueError("covariance requires observations")
    means: Vector = tuple(fmean(value[index] for value in values) for index in range(3))  # type: ignore[assignment]
    return tuple(
        tuple(
            fmean(
                (value[row] - means[row]) * (value[column] - means[column])
                for value in values
            )
            for column in range(3)
        )
        for row in range(3)
    )  # type: ignore[return-value]


def correlation(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    if len(left) != len(right) or not left:
        raise ValueError("correlation requires equal nonempty series")
    left_mean = fmean(left)
    right_mean = fmean(right)
    numerator = sum(
        (a - left_mean) * (b - right_mean) for a, b in zip(left, right, strict=True)
    )
    left_scale = sum((value - left_mean) ** 2 for value in left)
    right_scale = sum((value - right_mean) ** 2 for value in right)
    denominator = sqrt(left_scale * right_scale)
    return numerator / denominator if denominator > 1e-30 else 0.0


def determinant(value: Matrix) -> float:
    return (
        value[0][0] * (value[1][1] * value[2][2] - value[1][2] * value[2][1])
        - value[0][1] * (value[1][0] * value[2][2] - value[1][2] * value[2][0])
        + value[0][2] * (value[1][0] * value[2][1] - value[1][1] * value[2][0])
    )


def matrix_eigenvalues(value: Matrix) -> tuple[complex, complex, complex]:
    squared = matmul(value, value)
    matrix_trace = sum(value[index][index] for index in range(3))
    second = 0.5 * (
        matrix_trace * matrix_trace - sum(squared[index][index] for index in range(3))
    )
    constant = determinant(value)

    # Cardano's formula handles repeated roots deterministically, unlike a
    # simultaneous root iteration whose denominators vanish at multiplicity.
    quadratic = -matrix_trace
    linear = second
    scalar = -constant
    p = linear - quadratic * quadratic / 3.0
    q = 2.0 * quadratic**3 / 27.0 - quadratic * linear / 3.0 + scalar
    coefficient_scale = max(1.0, abs(quadratic), abs(linear), abs(scalar))
    if abs(p) <= 1e-13 * coefficient_scale and abs(q) <= 1e-13 * coefficient_scale:
        repeated = complex(-quadratic / 3.0, 0.0)
        return (repeated, repeated, repeated)
    discriminant = complex((q / 2.0) ** 2 + (p / 3.0) ** 3, 0.0)

    def cube_root(item: complex) -> complex:
        if abs(item) <= 1e-30:
            return 0j
        return cmath.exp(cmath.log(item) / 3.0)

    u = cube_root(-q / 2.0 + cmath.sqrt(discriminant))
    v = (
        -p / (3.0 * u)
        if abs(u) > 1e-24
        else cube_root(-q / 2.0 - cmath.sqrt(discriminant))
    )
    omega = complex(-0.5, sqrt(3.0) / 2.0)
    offset = -quadratic / 3.0
    roots = [
        u + v + offset,
        omega * u + omega.conjugate() * v + offset,
        omega.conjugate() * u + omega * v + offset,
    ]
    normalized = tuple(
        complex(
            root.real if abs(root.real) > 1e-14 else 0.0,
            root.imag if abs(root.imag) > 1e-12 else 0.0,
        )
        for root in roots
    )
    return tuple(sorted(normalized, key=lambda item: (item.real, item.imag)))  # type: ignore[return-value]


def solve_discrete_lyapunov(
    transition: Matrix,
    innovation: Matrix,
    *,
    tolerance: float = 1e-18,
    max_iterations: int = 100000,
) -> tuple[Matrix, int]:
    estimate = ZERO_MATRIX
    transition_t = transpose(transition)
    for iteration in range(1, max_iterations + 1):
        updated = add_matrix(
            matmul(matmul(transition, estimate), transition_t), innovation
        )
        if (
            max(
                abs(updated[row][column] - estimate[row][column])
                for row in range(3)
                for column in range(3)
            )
            <= tolerance
        ):
            return updated, iteration
        estimate = updated
    raise ArithmeticError("Lyapunov iteration did not converge")


def relative_matrix_error(estimate: Matrix, reference: Matrix) -> float:
    denominator = frobenius_norm(reference)
    if denominator <= 1e-30:
        return frobenius_norm(subtract_matrix(estimate, reference))
    return frobenius_norm(subtract_matrix(estimate, reference)) / denominator


def diagonal_matrix(value: float) -> Matrix:
    return scale_matrix(((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)), value)
