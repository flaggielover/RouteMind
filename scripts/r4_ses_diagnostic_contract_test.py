from __future__ import annotations

import copy
import unittest

import r4_ses_diagnostic_contract as contract


class SesDiagnosticContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.payload = contract.load_contract()

    def test_contract_is_valid_new_and_digest_stable(self) -> None:
        self.assertEqual(contract.validate_contract(self.payload), [])
        digest = contract.canonical_digest(self.payload)
        self.assertRegex(digest, r"^[0-9a-f]{64}$")
        self.assertNotIn(digest, contract.PRIOR_DIGESTS)
        self.assertEqual(digest, contract.canonical_digest(copy.deepcopy(self.payload)))

    def test_request_budget_and_operation_are_fail_closed(self) -> None:
        candidate = copy.deepcopy(self.payload)
        candidate["requestBoundary"]["sendEmailRequests"] = 2
        self.assertIn("request_sendEmailRequests", contract.validate_contract(candidate))
        candidate = copy.deepcopy(self.payload)
        candidate["provider"]["operation"] = "SendRawEmail"
        self.assertIn("provider_boundary", contract.validate_contract(candidate))

    def test_retry_fallback_and_mutation_boundaries_cannot_expand(self) -> None:
        candidate = copy.deepcopy(self.payload)
        candidate["scope"]["maximumRetries"] = 1
        self.assertIn("scope_boundary", contract.validate_contract(candidate))
        candidate = copy.deepcopy(self.payload)
        candidate["scope"]["fallbackProvider"] = "deterministic-local"
        self.assertIn("scope_boundary", contract.validate_contract(candidate))
        candidate = copy.deepcopy(self.payload)
        candidate["scope"]["iamMutationAuthorized"] = True
        self.assertIn("scope_boundary", contract.validate_contract(candidate))

    def test_historical_digest_reuse_and_sensitive_identity_fail_closed(self) -> None:
        candidate = copy.deepcopy(self.payload)
        candidate["frozenDependencies"]["priorContractDigestReuse"] = True
        self.assertIn("prior_digest_reuse", contract.validate_contract(candidate))
        candidate = copy.deepcopy(self.payload)
        candidate["identities"]["sender"]["valueInContract"] = "present"
        self.assertIn("sender_contract_value", contract.validate_contract(candidate))

    def test_human_gate_keeps_exact_new_contract_boundary(self) -> None:
        candidate = copy.deepcopy(self.payload)
        candidate["humanGate"]["approvalAuthorizesNoActionBeforeExactDigestApproval"] = False
        self.assertIn("human_gate_boundary", contract.validate_contract(candidate))
        candidate = copy.deepcopy(self.payload)
        candidate["humanGate"]["approvalStatementTemplate"] = "authorize one call"
        self.assertTrue(any(item.startswith("human_gate_text:") for item in contract.validate_contract(candidate)))


if __name__ == "__main__":
    unittest.main()
