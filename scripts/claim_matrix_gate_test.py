from __future__ import annotations

import unittest

from claim_matrix_gate import MATRIX_PATH, ClaimMatrixError, validate_claim_matrix


class ClaimMatrixGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.matrix = MATRIX_PATH.read_text(encoding="utf-8")

    def test_live_matrix_passes_with_no_supported_claims(self) -> None:
        result = validate_claim_matrix(self.matrix)

        self.assertEqual(result["claim_count"], 7)
        self.assertEqual(result["c_pass_count"], 0)
        self.assertEqual(result["c_no_novelty_count"], 2)
        self.assertEqual(result["c_no_claim_count"], 5)

    def test_pending_claim_status_is_rejected(self) -> None:
        mutated = self.matrix.replace("C-NO-CLAIM", "C-PENDING", 1)

        with self.assertRaisesRegex(ClaimMatrixError, "non-final claim status"):
            validate_claim_matrix(mutated)

    def test_status_drift_is_rejected(self) -> None:
        mutated = self.matrix.replace("C-NO-NOVELTY", "C-NO-CLAIM", 1)

        with self.assertRaisesRegex(ClaimMatrixError, "disposition drifted"):
            validate_claim_matrix(mutated)

    def test_unsupported_c_pass_is_rejected(self) -> None:
        mutated = self.matrix.replace("C-NO-CLAIM", "C-PASS", 1)

        with self.assertRaisesRegex(ClaimMatrixError, "disposition drifted"):
            validate_claim_matrix(mutated)

    def test_missing_reproduction_disposition_is_rejected(self) -> None:
        mutated = self.matrix.replace("R3-356 independently", "alternate checker independently", 1)

        with self.assertRaisesRegex(ClaimMatrixError, "reproduction disposition"):
            validate_claim_matrix(mutated)


if __name__ == "__main__":
    unittest.main()
