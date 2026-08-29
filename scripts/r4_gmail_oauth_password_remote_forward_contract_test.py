from __future__ import annotations

import json
import unittest

import r4_gmail_oauth_password_remote_forward_contract as contract


class PasswordRemoteForwardContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = json.loads(contract.CONTRACT.read_text(encoding="utf-8"))

    def test_contract_passes_expected_digest(self) -> None:
        self.assertEqual(contract.validate(self.payload, contract.EXPECTED_DIGEST), [])

    def test_digest_is_not_placeholder(self) -> None:
        self.assertNotEqual(contract.EXPECTED_DIGEST, "__SET_AFTER_CANONICAL_HASH__")

    def test_oauth_and_password_capture_are_forbidden(self) -> None:
        forbidden = set(self.payload["forbiddenOperations"])
        self.assertIn("OAuth_authorization", forbidden)
        self.assertIn("token_exchange", forbidden)
        self.assertIn("password_automation", forbidden)
        self.assertFalse(self.payload["passwordBoundary"]["codexCapturesPassword"])

    def test_synthetic_stage_is_single_loopback_request(self) -> None:
        synthetic = self.payload["syntheticValidation"]
        self.assertEqual(synthetic["requestCount"], 1)
        self.assertEqual(synthetic["path"], "/synthetic-probe")
        self.assertEqual(synthetic["googleRequests"], 0)


if __name__ == "__main__":
    unittest.main()
