from __future__ import annotations

import copy
import unittest

import r4_gmail_refresh_if_required_single_send_contract as contract


class GmailRefreshIfRequiredSingleSendContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.payload = contract.json.loads(contract.CONTRACT.read_text(encoding="utf-8"))

    def test_contract_is_prepared_and_bounded(self) -> None:
        self.assertEqual(contract.validate(self.payload), [])
        self.assertEqual(self.payload["scope"]["maximumCredentialRefreshRequests"], 1)
        self.assertEqual(self.payload["scope"]["maximumUsersMessagesSendRequests"], 1)
        self.assertFalse(self.payload["claims"]["liveCallsExecuted"])
        self.assertFalse(self.payload["claims"]["historicalContractsReusable"])

    def test_refresh_send_and_budget_expansion_is_rejected(self) -> None:
        for field, value in (
            ("maximumCredentialRefreshRequests", 2),
            ("maximumUsersMessagesSendRequests", 2),
            ("maximumRecipients", 2),
            ("maximumRetries", 1),
            ("maximumFallbacks", 1),
            ("maximumMessageReads", 1),
            ("maximumSpendUsd", 0.2),
        ):
            mutated = copy.deepcopy(self.payload)
            mutated["scope"][field] = value
            self.assertIn("contract digest mismatch", contract.validate(mutated))
            self.assertIn("bounded scope drifted", contract.validate(mutated))

    def test_historical_reuse_and_live_claims_are_rejected(self) -> None:
        mutated = copy.deepcopy(self.payload)
        mutated["historicalContracts"]["reuse"] = "ALLOWED"
        self.assertIn("historical reuse boundary drifted", contract.validate(mutated))
        mutated = copy.deepcopy(self.payload)
        mutated["claims"]["liveCallsExecuted"] = True
        self.assertIn("claim boundary drifted", contract.validate(mutated))
        mutated = copy.deepcopy(self.payload)
        mutated["execution"]["refreshPolicy"] = "ALWAYS"
        self.assertIn("execution semantics drifted", contract.validate(mutated))

    def test_no_reads_or_message_extras_and_no_secret_or_address_values(self) -> None:
        self.assertEqual(self.payload["scope"]["maximumMessageReads"], 0)
        self.assertEqual(self.payload["scope"]["maximumCc"], 0)
        self.assertEqual(self.payload["scope"]["maximumBcc"], 0)
        self.assertEqual(self.payload["scope"]["maximumAttachments"], 0)
        self.assertFalse(any("@" in value for value in contract._strings(self.payload)))
        self.assertIn("authorization_header", self.payload["dataBoundary"]["forbidden"])


if __name__ == "__main__":
    unittest.main()
