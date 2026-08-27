from __future__ import annotations

import copy
import unittest

from r4_vm_ssh_readiness_contract import load_contract, validate_contract, validate_iac


class SshReadinessContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = load_contract()

    def test_frozen_contract_and_iac_pass(self) -> None:
        self.assertEqual((), validate_contract(self.contract))
        self.assertEqual((), validate_iac())

    def test_paid_authorization_in_preparation_fails(self) -> None:
        candidate = copy.deepcopy(self.contract)
        candidate["approvalBoundary"]["spendAuthorized"] = True
        self.assertIn("approval_boundary", validate_contract(candidate))

    def test_larger_or_second_vm_fails(self) -> None:
        candidate = copy.deepcopy(self.contract)
        candidate["infrastructure"]["resources"][0]["plan"] = "vc2-2c-4gb"
        candidate["infrastructure"]["resources"].append(
            copy.deepcopy(candidate["infrastructure"]["resources"][0])
        )
        self.assertIn("infrastructure", validate_contract(candidate))

    def test_wide_firewall_fails(self) -> None:
        candidate = copy.deepcopy(self.contract)
        candidate["network"]["publicIngressRules"][0]["subnetSize"] = 0
        self.assertIn("network", validate_contract(candidate))

    def test_key_fingerprint_change_fails(self) -> None:
        candidate = copy.deepcopy(self.contract)
        candidate["sshIdentity"]["expectedPublicKeySha256"] = "SHA256:wrong"
        self.assertIn("ssh_identity", validate_contract(candidate))

    def test_tcp_ok_cannot_be_promoted(self) -> None:
        candidate = copy.deepcopy(self.contract)
        candidate["readinessStateMachine"]["tcpOkIsSufficient"] = True
        self.assertIn("state_machine", validate_contract(candidate))

    def test_round3_result_cannot_change(self) -> None:
        candidate = copy.deepcopy(self.contract)
        candidate["scientificBoundary"]["frozenR3_325"] = "PASS"
        self.assertIn("scientific_boundary", validate_contract(candidate))


if __name__ == "__main__":
    unittest.main(verbosity=2)
