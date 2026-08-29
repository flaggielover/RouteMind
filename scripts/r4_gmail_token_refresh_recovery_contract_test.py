from __future__ import annotations

import copy
import unittest

import r4_gmail_token_refresh_recovery_contract as contract


class GmailTokenRefreshRecoveryContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.payload = contract.json.loads(contract.CONTRACT.read_text(encoding="utf-8"))

    def test_contract_is_refresh_only_and_not_executed(self) -> None:
        self.assertEqual(contract.validate(self.payload), [])
        self.assertEqual(self.payload["scope"]["maximumTokenRefreshRequests"], 1)
        self.assertEqual(self.payload["scope"]["maximumGmailApiRequests"], 0)
        self.assertFalse(self.payload["claims"]["credentialRefreshValidated"])

    def test_any_live_operation_or_budget_mutation_is_rejected(self) -> None:
        for field, value in (
            ("maximumTokenRefreshRequests", 2),
            ("maximumGmailApiRequests", 1),
            ("maximumAuthorizationCodeExchanges", 1),
            ("maximumRetries", 1),
            ("maximumSpendUsd", 0.2),
        ):
            mutated = copy.deepcopy(self.payload)
            mutated["scope"][field] = value
            self.assertIn("contract digest mismatch", contract.validate(mutated))
            self.assertIn("bounded scope drifted", contract.validate(mutated))

    def test_browser_exchange_and_message_paths_are_forbidden(self) -> None:
        mutated = copy.deepcopy(self.payload)
        mutated["scope"]["maximumOauthAuthorizationSessions"] = 1
        self.assertIn("bounded scope drifted", contract.validate(mutated))
        mutated = copy.deepcopy(self.payload)
        mutated["configuration"]["gmailMessageOperations"] = "allowed"
        self.assertIn("configuration boundary drifted", contract.validate(mutated))

    def test_contract_contains_no_addresses_or_secret_values(self) -> None:
        strings = contract._strings(self.payload)
        self.assertFalse(any("@" in value for value in strings))
        self.assertIn("credentialValues", self.payload["dataBoundary"])
        self.assertEqual(self.payload["dataBoundary"]["credentialValues"], "forbidden")


if __name__ == "__main__":
    unittest.main()
