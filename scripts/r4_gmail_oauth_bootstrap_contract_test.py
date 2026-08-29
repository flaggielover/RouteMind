from __future__ import annotations

import copy
import unittest

import r4_gmail_oauth_bootstrap_contract as contract


class GmailOAuthBootstrapContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.payload = contract.json.loads(contract.CONTRACT.read_text(encoding="utf-8"))

    def test_frozen_contract_is_valid(self) -> None:
        self.assertEqual(contract.validate(self.payload), [])

    def test_message_operation_is_forbidden(self) -> None:
        mutated = copy.deepcopy(self.payload)
        mutated["execution"]["maximumGoogleApiMessageRequests"] = 1
        self.assertIn("message operation boundary drifted", contract.validate(mutated))

    def test_broader_scope_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.payload)
        mutated["scope"] = "https://www.googleapis.com/auth/gmail.modify"
        self.assertIn("scope drifted", contract.validate(mutated))

    def test_digest_changes_on_scope_mutation(self) -> None:
        mutated = copy.deepcopy(self.payload)
        mutated["scope"] = "https://www.googleapis.com/auth/gmail.readonly"
        self.assertNotEqual(contract.canonical_digest(mutated), contract.EXPECTED_DIGEST)


if __name__ == "__main__":
    unittest.main()
