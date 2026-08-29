from __future__ import annotations

import copy
import unittest

import r4_gmail_oauth_bootstrap_v2_contract as contract


class GmailOAuthBootstrapV2ContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.payload = contract.json.loads(contract.CONTRACT.read_text(encoding="utf-8"))

    def test_frozen_contract_is_valid(self) -> None:
        self.assertEqual(contract.validate(self.payload), [])

    def test_authorization_before_preflight_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.payload)
        mutated["readinessGate"]["authorizationUrlBeforePreflight"] = True
        self.assertIn("authorization URL readiness gate drifted", contract.validate(mutated))

    def test_message_and_ssh_automation_are_forbidden(self) -> None:
        mutated = copy.deepcopy(self.payload)
        mutated["execution"]["maximumGoogleApiMessageRequests"] = 1
        mutated["operatorManagedTunnel"]["sshAutomation"] = 1
        errors = contract.validate(mutated)
        self.assertIn("message operation boundary drifted", errors)
        self.assertIn("SSH automation boundary drifted", errors)

    def test_scope_or_digest_mutation_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.payload)
        mutated["scope"] = "https://www.googleapis.com/auth/gmail.modify"
        self.assertIn("scope drifted", contract.validate(mutated))
        self.assertNotEqual(contract.canonical_digest(mutated), contract.EXPECTED_DIGEST)


if __name__ == "__main__":
    unittest.main()
