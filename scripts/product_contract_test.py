from __future__ import annotations

import copy
import unittest

import product_contract as contract


class ProductContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.payload = contract.load_contract()

    def assert_rejected(self, mutate, expected: str) -> None:  # type: ignore[no-untyped-def]
        candidate = copy.deepcopy(self.payload)
        mutate(candidate)
        self.assertIn(expected, contract.validate_contract(candidate))

    def test_frozen_contract_is_valid_and_deterministic(self) -> None:
        self.assertEqual(contract.validate_contract(self.payload), [])
        self.assertEqual(contract.digest(self.payload), contract.digest(copy.deepcopy(self.payload)))

    def test_durable_authority_cannot_move_out_of_java(self) -> None:
        self.assert_rejected(
            lambda value: value["authority"].update(durableOwner="python_compute"),
            "authority:durableOwner",
        )

    def test_role_or_tenant_boundaries_cannot_be_weakened(self) -> None:
        self.assert_rejected(
            lambda value: value["ownership"].update(crossTenant="allow"),
            "ownership:crossTenant",
        )
        self.assert_rejected(
            lambda value: value["ownership"]["roles"].pop(),
            "ownership:roles",
        )
        self.assert_rejected(
            lambda value: value["ownership"]["roles"].append(
                copy.deepcopy(value["ownership"]["roles"][0])
            ),
            "ownership:roles",
        )

    def test_external_channels_fail_closed_by_default(self) -> None:
        self.assert_rejected(
            lambda value: value["defaults"]["channels"].update(sms=True),
            "defaults:channels_fail_closed",
        )

    def test_external_delivery_requires_explicit_consent(self) -> None:
        self.assert_rejected(
            lambda value: value["consent"]["purposes"][0].update(externalBasis="service_transaction"),
            "consent:external_basis:transactional_order",
        )

    def test_marketing_cannot_bypass_quiet_hours(self) -> None:
        self.assert_rejected(
            lambda value: value["quietHours"]["bypass"].append(
                {"purpose": "marketing", "condition": "campaign_priority"}
            ),
            "quiet_hours:bypass_scope",
        )

    def test_accessibility_requirements_cannot_be_deleted(self) -> None:
        self.assert_rejected(
            lambda value: value["accessibilityRequirements"].remove("keyboard_complete"),
            "accessibility:requirements",
        )

    def test_provider_acceptance_is_not_delivery(self) -> None:
        self.assert_rejected(
            lambda value: value["notificationLifecycle"]["deliveryEvidence"].update(
                providerAcceptanceIsDelivery=True
            ),
            "notification:false_delivery_claim",
        )

    def test_delivery_requires_authenticated_provider_receipt(self) -> None:
        self.assert_rejected(
            lambda value: value["notificationLifecycle"]["transitions"][14].update(
                guard="provider_acceptance_ack"
            ),
            "notification:delivery_transition",
        )

    def test_terminal_states_cannot_transition(self) -> None:
        self.assert_rejected(
            lambda value: value["notificationLifecycle"]["transitions"].append(
                {"from": "DELIVERED", "to": "READY", "guard": "manual_retry"}
            ),
            "notification:terminal_transition",
        )

    def test_non_delivery_transitions_are_also_frozen(self) -> None:
        self.assert_rejected(
            lambda value: value["notificationLifecycle"]["transitions"].pop(8),
            "notification:transition_graph",
        )

    def test_real_provider_send_remains_unauthorized(self) -> None:
        self.assert_rejected(
            lambda value: value["executionBoundary"].update(realProviderSendAuthorized=True),
            "execution:external_send_boundary",
        )


if __name__ == "__main__":
    unittest.main()
