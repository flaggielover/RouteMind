from __future__ import annotations

import copy
import unittest

import google_routes_contract as contract


class GoogleRoutesContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.payload = contract.load()

    def test_contract_is_valid_and_live_calls_are_disabled(self) -> None:
        self.assertEqual(contract.validate(self.payload), [])
        self.assertFalse(self.payload["boundedLiveValidation"]["authorized"])
        self.assertFalse(self.payload["claims"]["realCallsExecuted"])

    def test_digest_is_stable_and_mutations_fail_closed(self) -> None:
        self.assertEqual(
            contract.canonical_digest(self.payload),
            contract.canonical_digest(copy.deepcopy(self.payload)),
        )
        mutated = copy.deepcopy(self.payload)
        mutated["boundedLiveValidation"]["authorized"] = True
        self.assertIn("budget", contract.validate(mutated))
        mutated = copy.deepcopy(self.payload)
        mutated["requestContract"]["outboundForbidden"].remove("tenant_id")
        self.assertIn("privacy", contract.validate(mutated))
        mutated = copy.deepcopy(self.payload)
        mutated["secretInjection"]["forbiddenDestinations"].remove("logs")
        self.assertIn("secret_injection", contract.validate(mutated))


if __name__ == "__main__":
    unittest.main()
