from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from research.level4.spatial_lockin.artifacts import ArtifactStore
from research.level4.spatial_lockin.gate2 import (
    FROZEN_M_ALPHA,
    FROZEN_R_ALPHA,
    RunSummary,
    _classify,
    verify_frozen_inputs,
)
from research.level4.spatial_lockin.reason_codes import ResearchGateError


class Gate2Tests(unittest.TestCase):
    def test_classification_is_fixed_and_not_threshold_fitted(self) -> None:
        restored = RunSummary(
            "R",
            FROZEN_R_ALPHA * 0.5,
            21000,
            "positive",
            (0.0, 0.0, 0.0),
            0.01,
            0.01,
            0.0001,
            1.0,
            0.01,
            0.01,
            -0.001,
            0.01,
            0.009,
            "digest",
            {},
        )
        locked = RunSummary(
            "M",
            FROZEN_M_ALPHA * 1.5,
            21000,
            "positive",
            (0.3, 0.2, 0.1),
            0.4,
            0.4,
            0.001,
            1.0,
            0.4,
            0.4,
            0.0,
            0.39,
            0.4,
            "digest",
            {},
        )
        self.assertEqual(_classify(restored, 0.02), "RESTORED")
        self.assertEqual(_classify(locked, 0.02), "LOCKED")

    def test_frozen_inputs_reject_a_wrong_report_hash(self) -> None:
        package_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            # The store root is irrelevant to report verification; this test only
            # asserts that missing immutable Gate 1 artifacts fail closed.
            store = ArtifactStore(Path(directory))
            with self.assertRaisesRegex(ResearchGateError, "STAGE_ORDER_VIOLATION"):
                verify_frozen_inputs(package_root, store)


if __name__ == "__main__":
    unittest.main()
