from __future__ import annotations

import unittest
from pathlib import Path
from typing import cast

from research.level4.spatial_lockin.diagnostic_statistics import (
    block_averaged_slope,
    diagonal_matrix,
    matrix_eigenvalues,
    mean_first_difference,
    ols_slope,
    solve_discrete_lyapunov,
    theil_sen_slope,
)
from research.level4.spatial_lockin.gate2 import RunSummary, _classify
from research.level4.spatial_lockin.mechanism import DeliveryMechanism
from research.level4.spatial_lockin.negative_control import (
    EPSILON,
    NOISE_SD,
    _mechanism_reference,
    _synthetic_controls,
    classifier_components,
)
from research.level4.spatial_lockin.preregistration import Preregistration
from research.level4.spatial_lockin.reduced_model import ReducedModel


def _summary(**overrides: object) -> RunSummary:
    values: dict[str, object] = {
        "layer": "R",
        "alpha": 0.0,
        "seed": 21000,
        "initial_id": "zero",
        "final_state": (0.0, 0.0, 0.0),
        "imbalance_mean": 0.001,
        "imbalance_median": 0.001,
        "imbalance_variance": 1e-8,
        "sign_persistence": 0.5,
        "projection_mean": 0.0,
        "projection_final": 0.0,
        "slope": 1e-8,
        "preceding_third_mean": 0.001,
        "final_third_mean": 0.0011,
        "trace_digest": "fixture",
        "operational": {},
    }
    values.update(overrides)
    return RunSummary(**values)  # type: ignore[arg-type]


class NegativeControlTests(unittest.TestCase):
    def test_classifier_decomposition_preserves_conjunction(self) -> None:
        result = classifier_components(_summary())
        self.assertTrue(result["magnitude_pass"])
        self.assertFalse(result["slope_pass"])
        self.assertFalse(result["window_pass"])
        self.assertFalse(result["all_pass"])
        self.assertEqual(result["frozen_classifier_label"], "AMBIGUOUS")

    def test_slope_estimators_recover_a_linear_reference(self) -> None:
        values = tuple(1.5 + 0.25 * index for index in range(300))
        self.assertAlmostEqual(ols_slope(values), 0.25)
        self.assertAlmostEqual(theil_sen_slope(values), 0.25)
        self.assertAlmostEqual(mean_first_difference(values), 0.25)
        self.assertAlmostEqual(block_averaged_slope(values), 0.25)

    def test_stationary_covariance_matches_diagonal_ar1_reference(self) -> None:
        transition = diagonal_matrix(0.65)
        innovation = diagonal_matrix(NOISE_SD**2)
        covariance, _ = solve_discrete_lyapunov(transition, innovation)
        expected = NOISE_SD**2 / (1.0 - 0.65**2)
        for index in range(3):
            self.assertAlmostEqual(covariance[index][index], expected, places=16)
        eigenvalues = matrix_eigenvalues(transition)
        self.assertTrue(all(abs(value - 0.65) < 1e-6 for value in eigenvalues))

    def test_synthetic_stable_and_locked_controls_are_reproducible(self) -> None:
        first = _synthetic_controls()
        second = _synthetic_controls()
        self.assertEqual(first, second)
        self.assertGreaterEqual(first["locked"]["locked_sensitivity"], 0.80)  # type: ignore[index]
        self.assertGreaterEqual(first["stable"]["false_negative_rate"], 0.50)  # type: ignore[index]
        self.assertTrue(first["deterministic_replay"])

    def test_reduced_model_replay_is_exact_for_a_seed(self) -> None:
        model = ReducedModel(
            ((0.5, 0.03, 0.12), (0.02, 0.52, 0.1), (0.01, 0.04, 0.58)),
            (0.07, 0.06, 0.05),
            (0.8, 0.7, 0.9),
            "tanh",
            "fixture",
        )
        arguments = ((0.0, 0.0, 0.0), 0.0, 12, 21000, NOISE_SD)
        first = model.simulate(*arguments, magnitude=0.0, direction_id="zero").states
        second = model.simulate(*arguments, magnitude=0.0, direction_id="zero").states
        self.assertEqual(first, second)
        self.assertNotEqual(first[-1], (0.0, 0.0, 0.0))

    def test_mechanism_reference_matches_noise_free_step(self) -> None:
        package_root = Path(__file__).resolve().parents[1]
        preregistration = Preregistration.load(
            package_root / "configs" / "preregistration.json"
        )
        model = DeliveryMechanism.from_config(
            cast(dict[str, object], preregistration.payload["layer_m"])
        )
        initial = (0.001, -0.0005, 0.00075)
        expected = _mechanism_reference(model, initial)
        observed = model.simulate(initial, 0.0, 1, 41000, 0.0).observations[-1]
        for actual, reference in zip(observed, expected, strict=True):
            self.assertAlmostEqual(actual, reference, places=15)

    def test_known_reference_labels_are_not_all_ambiguous(self) -> None:
        restored = _summary(slope=-1e-8, final_third_mean=0.0009)
        locked = _summary(
            imbalance_mean=0.05,
            imbalance_median=0.05,
            slope=0.0,
            preceding_third_mean=0.05,
            final_third_mean=0.05,
            sign_persistence=1.0,
        )
        self.assertEqual(_classify(restored, EPSILON), "RESTORED")
        self.assertEqual(_classify(locked, EPSILON), "LOCKED")


if __name__ == "__main__":
    unittest.main()
