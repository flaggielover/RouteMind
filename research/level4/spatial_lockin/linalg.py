from __future__ import annotations

from math import isfinite, sqrt

from .reason_codes import fail

Vector = tuple[float, float, float]
Matrix = tuple[Vector, Vector, Vector]


def vector(values: object) -> Vector:
    if not isinstance(values, (list, tuple)) or len(values) != 3:
        fail("DIMENSION_INVALID", "expected a three-vector")
    result = tuple(float(item) for item in values)
    if not all(isfinite(item) for item in result):
        fail("NONFINITE_VALUE")
    return result  # type: ignore[return-value]


def matrix(values: object) -> Matrix:
    if not isinstance(values, (list, tuple)) or len(values) != 3:
        fail("DIMENSION_INVALID", "expected a 3x3 matrix")
    return tuple(vector(row) for row in values)  # type: ignore[return-value]


def identity() -> Matrix:
    return ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))


def dot(left: Vector, right: Vector) -> float:
    return sum(a * b for a, b in zip(left, right, strict=True))


def add_vector(left: Vector, right: Vector) -> Vector:
    return tuple(a + b for a, b in zip(left, right, strict=True))  # type: ignore[return-value]


def scale_vector(value: Vector, scalar: float) -> Vector:
    return tuple(scalar * item for item in value)  # type: ignore[return-value]


def matvec(value: Matrix, state: Vector) -> Vector:
    return tuple(dot(row, state) for row in value)  # type: ignore[return-value]


def transpose(value: Matrix) -> Matrix:
    return tuple(tuple(value[row][column] for row in range(3)) for column in range(3))  # type: ignore[return-value]


def matmul(left: Matrix, right: Matrix) -> Matrix:
    columns = transpose(right)
    return tuple(tuple(dot(row, column) for column in columns) for row in left)  # type: ignore[return-value]


def add_matrix(left: Matrix, right: Matrix) -> Matrix:
    return tuple(
        tuple(a + b for a, b in zip(left_row, right_row, strict=True))
        for left_row, right_row in zip(left, right, strict=True)
    )  # type: ignore[return-value]


def subtract_matrix(left: Matrix, right: Matrix) -> Matrix:
    return tuple(
        tuple(a - b for a, b in zip(left_row, right_row, strict=True))
        for left_row, right_row in zip(left, right, strict=True)
    )  # type: ignore[return-value]


def scale_matrix(value: Matrix, scalar: float) -> Matrix:
    return tuple(tuple(scalar * item for item in row) for row in value)  # type: ignore[return-value]


def outer(left: Vector, right: Vector) -> Matrix:
    return tuple(tuple(a * b for b in right) for a in left)  # type: ignore[return-value]


def trace(value: Matrix) -> float:
    return sum(value[index][index] for index in range(3))


def inverse(value: Matrix, *, tolerance: float = 1e-12) -> Matrix:
    augmented = [
        list(row) + list(unit) for row, unit in zip(value, identity(), strict=True)
    ]
    for column in range(3):
        pivot = max(range(column, 3), key=lambda row: abs(augmented[row][column]))
        if abs(augmented[pivot][column]) <= tolerance:
            fail("SINGULAR_MATRIX")
        augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        divisor = augmented[column][column]
        augmented[column] = [item / divisor for item in augmented[column]]
        for row in range(3):
            if row == column:
                continue
            factor = augmented[row][column]
            augmented[row] = [
                item - factor * pivot_item
                for item, pivot_item in zip(
                    augmented[row], augmented[column], strict=True
                )
            ]
    return tuple(tuple(row[3:]) for row in augmented)  # type: ignore[return-value]


def matrix_rank(value: Matrix, *, tolerance: float = 1e-10) -> int:
    rows = [list(row) for row in value]
    rank = 0
    for column in range(3):
        pivot = max(
            range(rank, 3), key=lambda row: abs(rows[row][column]), default=rank
        )
        if abs(rows[pivot][column]) <= tolerance:
            continue
        rows[rank], rows[pivot] = rows[pivot], rows[rank]
        divisor = rows[rank][column]
        rows[rank] = [item / divisor for item in rows[rank]]
        for row in range(3):
            if row != rank:
                factor = rows[row][column]
                rows[row] = [
                    item - factor * pivot_item
                    for item, pivot_item in zip(rows[row], rows[rank], strict=True)
                ]
        rank += 1
    return rank


def infinity_norm(value: Matrix) -> float:
    return max(sum(abs(item) for item in row) for row in value)


def condition_number(value: Matrix) -> float:
    return infinity_norm(value) * infinity_norm(inverse(value))


def frobenius_norm(value: Matrix) -> float:
    return sqrt(sum(item * item for row in value for item in row))


def relative_frobenius_error(estimate: Matrix, truth: Matrix) -> float:
    denominator = frobenius_norm(truth)
    if denominator <= 1e-15:
        fail("SINGULAR_MATRIX", "relative error denominator is zero")
    return frobenius_norm(subtract_matrix(estimate, truth)) / denominator


def spectral_radius_nonnegative(value: Matrix, *, iterations: int = 500) -> float:
    if any(item < -1e-8 for row in value for item in row):
        fail("CONFIG_INVALID", "spectral check requires a cooperative matrix")
    state: Vector = (1.0, 1.0, 1.0)
    eigenvalue = 0.0
    for _ in range(iterations):
        projected = matvec(value, state)
        scale = max(abs(item) for item in projected)
        if scale <= 1e-15:
            return 0.0
        state = scale_vector(projected, 1.0 / scale)
        eigenvalue = scale
    return eigenvalue


def transition_least_squares(
    samples: tuple[tuple[Vector, Vector], ...],
) -> tuple[Matrix, Matrix]:
    if len(samples) < 3:
        fail("RANK_DEFICIENT", "fewer than three local transitions")
    gram: Matrix = ((0.0, 0.0, 0.0),) * 3
    cross: Matrix = ((0.0, 0.0, 0.0),) * 3
    for before, after in samples:
        gram = add_matrix(gram, outer(before, before))
        cross = add_matrix(cross, outer(after, before))
    if matrix_rank(gram) < 3:
        fail("RANK_DEFICIENT")
    return matmul(cross, inverse(gram)), gram
