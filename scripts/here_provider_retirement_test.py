from __future__ import annotations

import copy
import unittest

import here_provider_retirement as retirement


class HereProviderRetirementTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = retirement.load(retirement.CONTRACT)

    def test_retirement_contract_and_active_boundary_are_valid(self) -> None:
        self.assertEqual(retirement.validate_contract(self.contract), [])
        self.assertEqual(retirement.validate_active_boundary(), [])
        self.assertEqual(
            retirement.digest(self.contract), retirement.digest(copy.deepcopy(self.contract))
        )

    def test_retirement_is_terminal_and_non_claiming(self) -> None:
        candidate = copy.deepcopy(self.contract)
        candidate["status"] = "passed"
        self.assertIn("retirement:terminal_status", retirement.validate_contract(candidate))
        candidate = copy.deepcopy(self.contract)
        candidate["claims"]["hereProviderLiveValidated"] = True
        self.assertIn("retirement:claims", retirement.validate_contract(candidate))

    def test_retirement_cannot_drop_historical_contract_binding(self) -> None:
        candidate = copy.deepcopy(self.contract)
        candidate["historicalContracts"] = []
        self.assertIn("retirement:historical_contracts", retirement.validate_contract(candidate))


if __name__ == "__main__":
    unittest.main()
