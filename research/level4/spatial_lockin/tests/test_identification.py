from __future__ import annotations

import unittest
from pathlib import Path
from typing import ClassVar, cast

from research.level4.spatial_lockin.identification import identify_layer
from research.level4.spatial_lockin.linalg import Vector
from research.level4.spatial_lockin.preregistration import Preregistration
from research.level4.spatial_lockin.reason_codes import ResearchGateError
from research.level4.spatial_lockin.records import Trajectory
from research.level4.spatial_lockin.reduced_model import ReducedModel

PACKAGE_ROOT = Path(__file__).resolve().parents[1]


class IdentificationTests(unittest.TestCase):
    payload: ClassVar[dict[str, object]]

    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = Preregistration.load(
            PACKAGE_ROOT / "configs" / "preregistration.json"
        ).payload

    def test_blind_recovery_of_reduced_model(self) -> None:
        model = ReducedModel.from_config(
            cast(dict[str, object], self.payload["layer_r"])
        )
        directions = (
            (1.0, 0.0, 0.0),
            (-1.0, 0.0, 0.0),
            (0.0, 1.0, 0.0),
            (0.0, -1.0, 0.0),
            (0.0, 0.0, 1.0),
            (0.0, 0.0, -1.0),
        )
        trajectories = tuple(
            model.simulate(
                cast(Vector, tuple(0.01 * item for item in direction)),
                alpha,
                12,
                1000 + seed,
                0.0,
                magnitude=0.01,
                direction_id=f"d{index}",
            )
            for alpha in (0.0, 0.35)
            for index, direction in enumerate(directions)
            for seed in range(4)
        )
        estimate = identify_layer(
            trajectories,
            probe_alpha=0.35,
            bootstrap_resamples=50,
            bootstrap_seed=42,
            gates=cast(dict[str, object], self.payload["gates"]),
            true_a=model.a,
            true_m=model.m,
        )
        errors = dict(estimate.recovery_errors)
        self.assertLess(errors["a_relative_error"], 1e-10)
        self.assertLess(errors["m_relative_error"], 0.001)
        self.assertLess(errors["threshold_relative_error"], 0.001)

    def test_rank_deficient_trajectory_fails_closed(self) -> None:
        trajectories = tuple(
            Trajectory(
                "R", alpha, 0.01, "d0", seed, ((0.01, 0.0, 0.0), (0.005, 0.0, 0.0))
            )
            for alpha in (0.0, 0.35)
            for seed in range(4)
        )
        with self.assertRaisesRegex(ResearchGateError, "RANK_DEFICIENT"):
            identify_layer(
                trajectories,
                probe_alpha=0.35,
                bootstrap_resamples=30,
                bootstrap_seed=1,
                gates=cast(dict[str, object], self.payload["gates"]),
            )


if __name__ == "__main__":
    unittest.main()
