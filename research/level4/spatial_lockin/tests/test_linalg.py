from __future__ import annotations

import unittest

from research.level4.spatial_lockin.linalg import (
    identity,
    inverse,
    matmul,
    matrix_rank,
    matvec,
    transition_least_squares,
)


class LinearAlgebraTests(unittest.TestCase):
    def test_inverse_and_rank_are_consistent(self) -> None:
        value = ((2.0, 0.5, 0.0), (0.0, 1.5, 0.2), (0.1, 0.0, 1.0))
        product = matmul(value, inverse(value))
        for row, expected in zip(product, identity(), strict=True):
            for item, target in zip(row, expected, strict=True):
                self.assertAlmostEqual(item, target, places=10)
        self.assertEqual(matrix_rank(value), 3)

    def test_transition_estimator_recovers_known_matrix(self) -> None:
        truth = ((0.5, 0.1, 0.0), (0.0, 0.6, 0.1), (0.1, 0.0, 0.4))
        states = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0), (1.0, -1.0, 1.0))
        estimate, gram = transition_least_squares(
            tuple((state, matvec(truth, state)) for state in states)
        )
        self.assertEqual(matrix_rank(gram), 3)
        for row, expected in zip(estimate, truth, strict=True):
            for item, target in zip(row, expected, strict=True):
                self.assertAlmostEqual(item, target, places=10)


if __name__ == "__main__":
    unittest.main()
