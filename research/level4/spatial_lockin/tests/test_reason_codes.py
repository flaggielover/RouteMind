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

    def test_unregistered_reason_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "unregistered reason code"):
            fail("AD_HOC_RESULT_RESCUE")


if __name__ == "__main__":
    unittest.main()
