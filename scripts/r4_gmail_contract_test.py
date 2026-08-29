from __future__ import annotations

import unittest

import r4_gmail_contract as contract


class GmailContractTests(unittest.TestCase):
    def test_contract_is_bounded_and_not_authorized_by_preparation(self) -> None:
        payload = contract.json.loads(contract.CONTRACT.read_text(encoding="utf-8"))
        self.assertEqual(contract.validate(payload), [])
        self.assertFalse(payload["scope"]["fallbackAuthorized"])
        self.assertFalse(payload["claims"]["liveCallsExecuted"])

    def test_digest_changes_when_scope_is_changed(self) -> None:
        payload = contract.json.loads(contract.CONTRACT.read_text(encoding="utf-8"))
        payload["scope"]["maximumSendRequests"] = 2
        self.assertNotEqual(contract.canonical_digest(payload), contract.EXPECTED_DIGEST)


if __name__ == "__main__":
    unittest.main()
