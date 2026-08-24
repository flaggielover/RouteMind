from __future__ import annotations

import inspect
import random
import unittest
from pathlib import Path
from typing import ClassVar, cast

from research.level4.spatial_lockin import mechanism
from research.level4.spatial_lockin.mechanism import DeliveryMechanism
from research.level4.spatial_lockin.preregistration import Preregistration
from research.level4.spatial_lockin.reduced_model import ReducedModel

PACKAGE_ROOT = Path(__file__).resolve().parents[1]


class ModelTests(unittest.TestCase):
    payload: ClassVar[dict[str, object]]

    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = Preregistration.load(
            PACKAGE_ROOT / "configs" / "preregistration.json"
        ).payload

    def test_reduced_model_replays_same_seed(self) -> None:
        model = ReducedModel.from_config(
            cast(dict[str, object], self.payload["layer_r"])
        )
        first = model.simulate(
            (0.01, 0.0, 0.0), 0.35, 12, 7, 0.00002, magnitude=0.01, direction_id="d00"
        )
        second = model.simulate(
            (0.01, 0.0, 0.0), 0.35, 12, 7, 0.00002, magnitude=0.01, direction_id="d00"
        )
        self.assertEqual(first, second)

    def test_layer_m_is_source_independent_from_layer_r(self) -> None:
        source = inspect.getsource(mechanism)
        self.assertNotIn("reduced_model", source)
        self.assertNotIn("nonlinearities", source)
        self.assertNotIn("ReducedModel", source)

    def test_mechanism_maps_population_to_operational_metrics(self) -> None:
        model = DeliveryMechanism.from_config(
            cast(dict[str, object], self.payload["layer_m"])
        )
        initial = model.symmetric_state((0.01, -0.01, 0.005))
        following, metrics = model.step(
            initial, 0.35, rng=random.Random(9), noise_sd=0.0
        )
        self.assertEqual(len(model.observe(following)), 3)
        self.assertGreater(metrics.served_a, 0)
        self.assertGreater(metrics.served_b, 0)
        self.assertGreaterEqual(metrics.service_inequality, 0)
        self.assertLessEqual(metrics.service_inequality, 1)


if __name__ == "__main__":
    unittest.main()
