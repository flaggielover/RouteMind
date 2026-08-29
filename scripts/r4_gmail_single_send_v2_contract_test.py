from __future__ import annotations

import copy
import unittest

import r4_gmail_single_send_v2_contract as contract


class GmailSingleSendV2ContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.payload = contract.json.loads(contract.CONTRACT.read_text(encoding="utf-8"))

    def test_contract_is_fresh_exactly_one_send_and_not_executed(self) -> None:
        self.assertEqual(contract.validate(self.payload), [])
        self.assertEqual(self.payload["scope"]["maximumUsersMessagesSendRequests"], 1)
        self.assertEqual(self.payload["scope"]["maximumCredentialRefreshRequests"], 0)
        self.assertFalse(self.payload["claims"]["liveCallsExecuted"])

    def test_any_send_refresh_or_budget_mutation_is_rejected(self) -> None:
        for field, value in (("maximumUsersMessagesSendRequests", 2), ("maximumCredentialRefreshRequests", 1), ("maximumRecipients", 2), ("maximumRetries", 1), ("maximumSpendUsd", 0.2)):
            mutated = copy.deepcopy(self.payload)
            mutated["scope"][field] = value
            self.assertIn("contract digest mismatch", contract.validate(mutated))
            self.assertIn("bounded scope drifted", contract.validate(mutated))

    def test_refresh_oauth_and_historical_paths_are_forbidden(self) -> None:
        mutated = copy.deepcopy(self.payload)
        mutated["authentication"]["credentialRefreshesAuthorized"] = 1
        self.assertIn("authentication boundary drifted", contract.validate(mutated))
        mutated = copy.deepcopy(self.payload)
        mutated["execution"]["credentialRefreshPolicy"] = "ALLOW"
        self.assertIn("execution semantics drifted", contract.validate(mutated))
        mutated = copy.deepcopy(self.payload)
        mutated["execution"]["priorGmailSendContract"] = "ALLOWED"
        self.assertIn("execution semantics drifted", contract.validate(mutated))

    def test_contract_contains_no_raw_addresses_or_secret_values(self) -> None:
        strings = contract._strings(self.payload)
        self.assertFalse(any("@" in value for value in strings))
        self.assertIn("credential_value", self.payload["dataBoundary"]["forbidden"])
        self.assertFalse(self.payload["claims"]["liveCallsExecuted"])


if __name__ == "__main__":
    unittest.main()
