from __future__ import annotations

import copy
import unittest

import r4_gmail_single_send_contract as contract


class GmailSingleSendContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.payload = contract.json.loads(contract.CONTRACT.read_text(encoding="utf-8"))

    def test_contract_is_exactly_one_send_and_not_executed(self) -> None:
        self.assertEqual(contract.validate(self.payload), [])
        self.assertEqual(self.payload["scope"]["maximumUsersMessagesSendRequests"], 1)
        self.assertEqual(self.payload["scope"]["maximumRetries"], 0)
        self.assertFalse(self.payload["claims"]["liveCallsExecuted"])

    def test_any_budget_or_scope_mutation_is_rejected(self) -> None:
        for field, value in (("maximumUsersMessagesSendRequests", 2), ("maximumRecipients", 2), ("maximumRetries", 1), ("maximumOauthSessions", 1), ("maximumSpendUsd", 0.2)):
            mutated = copy.deepcopy(self.payload)
            mutated["scope"][field] = value
            self.assertIn("contract digest mismatch", contract.validate(mutated))
            self.assertIn("bounded scope drifted", contract.validate(mutated))

    def test_oauth_or_historical_path_cannot_be_enabled(self) -> None:
        mutated = copy.deepcopy(self.payload)
        mutated["authentication"]["oauthSessionsAuthorized"] = 1
        self.assertIn("authentication boundary drifted", contract.validate(mutated))
        mutated = copy.deepcopy(self.payload)
        mutated["execution"]["historicalSesPath"] = "ALLOWED"
        self.assertIn("execution semantics drifted", contract.validate(mutated))

    def test_contract_contains_no_raw_addresses_or_secret_values(self) -> None:
        strings = contract._strings(self.payload)
        self.assertFalse(any("@" in value for value in strings))
        self.assertIn("credential_value", self.payload["dataBoundary"]["forbidden"])
        self.assertFalse(self.payload["claims"]["liveCallsExecuted"])


if __name__ == "__main__":
    unittest.main()
