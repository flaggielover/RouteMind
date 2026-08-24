from __future__ import annotations

import unittest

from research.level4.spatial_lockin.reason_codes import (
    REASON_CODES,
    ResearchGateError,
    fail,
)


class ReasonCodeTests(unittest.TestCase):
    def test_registry_is_unique_and_errors_are_stable(self) -> None:
        self.assertEqual(len(REASON_CODES), len(set(REASON_CODES)))
        with self.assertRaisesRegex(ResearchGateError, "RANK_DEFICIENT") as context:
            fail("RANK_DEFICIENT", "fixture")
        self.assertEqual(context.exception.reason.code, "RANK_DEFICIENT")
        self.assertEqual(context.exception.detail, "fixture")
        self.assertIn("DIAGNOSTIC_INPUT_MISMATCH", REASON_CODES)
        self.assertIn("DIAGNOSTIC_ARTIFACT_EXISTS", REASON_CODES)
        self.assertIn("REPLAY_FAILURE", REASON_CODES)

    def test_unregistered_reason_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "unregistered reason code"):
            fail("AD_HOC_RESULT_RESCUE")

    def test_gate2b_reason_codes_are_registered_before_execution(self) -> None:
        required = {
            "GATE2B_FROZEN_INPUT_MISMATCH",
            "GATE2B_ARTIFACT_EXISTS",
            "GATE2B_CLASSIFIER_CALIBRATION_FAILED",
            "GATE2B_NEGATIVE_CONTROL_FAILED",
            "GATE2B_WEAK_CONTROL_FAILED",
            "GATE2B_STRONG_CONTROL_FAILED",
            "GATE2B_NO_TRANSITION",
            "GATE2B_THRESHOLD_MISS",
            "GATE2B_TRANSITION_TOO_WIDE",
            "GATE2B_PATH_DEPENDENCE_FAILED",
            "GATE2B_LAYER_R_FAILED",
            "GATE2B_LAYER_M_FAILED",
            "GATE2B_OPERATIONAL_MISMATCH",
            "GATE2B_REPLAY_FAILED",
            "GATE2B_CONFIRMATORY_CONTAMINATION",
            "GATE2B_NONFINITE",
            "GATE2B_INCONCLUSIVE",
        }
        self.assertTrue(required.issubset(REASON_CODES))


if __name__ == "__main__":
    unittest.main()
