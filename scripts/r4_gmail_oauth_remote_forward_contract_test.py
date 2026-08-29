from __future__ import annotations

import copy
import unittest

import r4_gmail_oauth_remote_forward_contract as contract


class GmailOAuthRemoteForwardContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.payload = contract.json.loads(contract.CONTRACT.read_text(encoding="utf-8"))

    def test_frozen_contract_is_valid(self) -> None:
        self.assertEqual(contract.validate(self.payload, contract.canonical_digest(self.payload)), [])

    def test_wildcard_forward_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.payload)
        mutated["crossDeviceTopology"]["remoteForward"] = "0.0.0.0:<mac-port>:127.0.0.1:<windows-port>"
        self.assertIn("remote forward boundary drifted", contract.validate(mutated))

    def test_remote_command_or_message_operation_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.payload)
        mutated["execution"]["remoteCommands"] = 1
        self.assertIn("execution limits drifted", contract.validate(mutated))
        mutated = copy.deepcopy(self.payload)
        mutated["execution"]["maximumGoogleApiMessageRequests"] = 1
        self.assertIn("execution limits drifted", contract.validate(mutated))

    def test_digest_changes_on_host_mutation(self) -> None:
        mutated = copy.deepcopy(self.payload)
        mutated["crossDeviceTopology"]["sshHost"] = "192.0.2.1"
        self.assertNotEqual(contract.canonical_digest(mutated), contract.canonical_digest(self.payload))


if __name__ == "__main__":
    unittest.main()
