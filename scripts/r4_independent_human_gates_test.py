from __future__ import annotations

import copy
import unittest

import r4_independent_human_gates as gates


class IndependentHumanGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.travel = gates.load_contract(gates.TRAVEL)
        self.travel_approval = gates.load_contract(gates.TRAVEL_APPROVAL)
        self.notification = gates.load_contract(gates.NOTIFICATION)

    def assert_travel_rejected(self, mutate, expected: str) -> None:  # type: ignore[no-untyped-def]
        candidate = copy.deepcopy(self.travel)
        mutate(candidate)
        self.assertIn(expected, gates.validate_travel(candidate))

    def assert_notification_rejected(self, mutate, expected: str) -> None:  # type: ignore[no-untyped-def]
        candidate = copy.deepcopy(self.notification)
        mutate(candidate)
        self.assertIn(expected, gates.validate_notification(candidate))

    def assert_travel_approval_rejected(self, mutate, expected: str) -> None:  # type: ignore[no-untyped-def]
        candidate = copy.deepcopy(self.travel_approval)
        mutate(candidate)
        self.assertIn(expected, gates.validate_travel_approval(candidate, self.travel))

    def test_preparation_contracts_are_valid_and_digest_stable(self) -> None:
        self.assertEqual(gates.validate_travel(self.travel), [])
        self.assertEqual(
            gates.validate_travel_approval(self.travel_approval, self.travel), []
        )
        self.assertEqual(gates.validate_notification(self.notification), [])
        self.assertEqual(gates.digest(self.travel), gates.digest(copy.deepcopy(self.travel)))
        self.assertEqual(gates.digest(self.notification), gates.digest(copy.deepcopy(self.notification)))

    def test_travel_approval_is_bound_to_exact_frozen_contract(self) -> None:
        self.assertEqual(gates.digest(self.travel), gates.APPROVED_TRAVEL_DIGEST)
        self.assert_travel_approval_rejected(
            lambda value: value.update(approvedCanonicalSha256="0" * 64),
            "travel_approval:contract_binding",
        )
        self.assert_travel_approval_rejected(
            lambda value: value.update(approvalStatement="different"),
            "travel_approval:contract_binding",
        )

    def test_travel_approval_cannot_authorize_account_credentials_calls_or_spend(self) -> None:
        self.assert_travel_approval_rejected(
            lambda value: value["authorization"].update(accountCreation=True),
            "travel_approval:authorization_boundary",
        )
        self.assert_travel_approval_rejected(
            lambda value: value["authorization"].update(liveCalls=True),
            "travel_approval:authorization_boundary",
        )
        self.assert_travel_approval_rejected(
            lambda value: value["authorization"].update(maximumSpendUsdCents=1),
            "travel_approval:authorization_boundary",
        )

    def test_travel_approval_preserves_adverse_region_and_access_boundaries(self) -> None:
        self.assert_travel_approval_rejected(
            lambda value: value["ratification"].update(
                japanServiceEligibility="CONFIRMED"
            ),
            "travel_approval:ratification_boundary",
        )
        self.assert_travel_approval_rejected(
            lambda value: value["ratification"].update(processingRegion="TOKYO"),
            "travel_approval:ratification_boundary",
        )

    def test_travel_approval_cannot_inflate_live_or_production_claims(self) -> None:
        self.assert_travel_approval_rejected(
            lambda value: value["claims"].update(providerLiveValidated=True),
            "travel_approval:claims",
        )
        self.assert_travel_approval_rejected(
            lambda value: value["claims"].update(productionValidated=True),
            "travel_approval:claims",
        )

    def test_travel_provider_cannot_be_claimed_selected_or_validated(self) -> None:
        self.assert_travel_rejected(lambda value: value["selection"].update(selectedProvider="HERE"), "travel:selection_fail_closed")
        self.assert_travel_rejected(lambda value: value["recommendedProvider"].update(validated=True), "travel:provider_claim")
        self.assert_travel_rejected(lambda value: value["claims"].update(providerValidated=True), "travel:claims")

    def test_travel_calls_budget_and_fallback_fail_closed(self) -> None:
        self.assert_travel_rejected(lambda value: value["boundedLiveValidation"].update(authorized=True), "travel:execution_boundary")
        self.assert_travel_rejected(lambda value: value["boundedLiveValidation"].update(allowedCallsAtThisGate=1), "travel:execution_boundary")
        self.assert_travel_rejected(lambda value: value["requestContract"].update(timeoutMilliseconds=0), "travel:bounded_request")
        self.assert_travel_rejected(lambda value: value["fallback"].update(fallbackResultMayBeRepresentedAsProviderTruth=True), "travel:fallback")
        self.assert_travel_rejected(lambda value: value["fallback"].update(failOpen=True), "travel:fallback")

    def test_travel_privacy_and_credentials_are_frozen(self) -> None:
        self.assert_travel_rejected(lambda value: value["privacy"]["outboundAllowlist"].append("tenant_id"), "travel:privacy_allowlist")
        self.assert_travel_rejected(lambda value: value["privacy"]["outboundForbidden"].remove("phone"), "travel:privacy_forbidden")
        self.assert_travel_rejected(lambda value: value["credentials"].update(logs="allowed"), "travel:credentials")

    def test_travel_products_japan_access_and_processing_region_fail_closed(self) -> None:
        self.assert_travel_rejected(lambda value: value["recommendedProvider"]["products"]["point"].update(product="HERE_MATRIX_ROUTING_API_V8"), "travel:products")
        self.assert_travel_rejected(lambda value: value["recommendedProvider"]["documentedCapabilities"].update(japanRegionAccessRestricted=False), "travel:japan_access")
        self.assert_travel_rejected(lambda value: value["selection"].update(japanServiceEligibility="ASSUMED"), "travel:selection_fail_closed")
        self.assert_travel_rejected(lambda value: value["privacy"].update(processingRegion="TOKYO"), "travel:processing_region")
        self.assert_travel_rejected(lambda value: value["privacy"].update(tokyoResidencyGuaranteed=True), "travel:processing_region")
        self.assert_travel_rejected(lambda value: value["recommendedProvider"]["mandatoryHumanFindings"].pop(), "travel:processing_findings")

    def test_travel_human_gate_cannot_authorize_calls_or_claim_access(self) -> None:
        self.assert_travel_rejected(lambda value: value["humanGate"].update(approvalDoesNotAuthorizeLiveCalls=False), "travel:human_gate")
        self.assert_travel_rejected(lambda value: value["humanGate"].update(approvalDoesNotClaimJapanAccess=False), "travel:human_gate")
        self.assert_travel_rejected(lambda value: value["humanGate"]["requiredApprovals"].remove("NON_REGION_PINNED_PROCESSING"), "travel:human_gate")

    def test_travel_evidence_contract_cannot_drop_adverse_or_cost_evidence(self) -> None:
        self.assert_travel_rejected(lambda value: value["evidenceContract"].remove("Japan_service_eligibility_confirmation"), "travel:evidence_contract")
        self.assert_travel_rejected(lambda value: value["evidenceContract"].remove("privacy_and_secret_leakage_scan"), "travel:evidence_contract")
        self.assert_travel_rejected(lambda value: value["evidenceContract"].remove("actual_or_conservative_cost"), "travel:evidence_contract")

    def test_notification_provider_cannot_be_claimed_selected_or_validated(self) -> None:
        self.assert_notification_rejected(lambda value: value["selection"].update(selectedChannel="email"), "notification:selection_fail_closed")
        self.assert_notification_rejected(lambda value: value["recommendedProvider"].update(validated=True), "notification:provider_claim")
        self.assert_notification_rejected(lambda value: value["claims"].update(realMessageSent=True), "notification:claims")

    def test_notification_sends_and_resources_are_not_authorized(self) -> None:
        self.assert_notification_rejected(lambda value: value["boundedRealSend"].update(authorized=True), "notification:execution_boundary")
        self.assert_notification_rejected(lambda value: value["boundedRealSend"].update(accountOrResourceCreationAuthorized=True), "notification:execution_boundary")
        self.assert_notification_rejected(lambda value: value["boundedRealSend"].update(maximumMessages=100), "notification:execution_boundary")

    def test_notification_receipts_privacy_and_recipients_fail_closed(self) -> None:
        self.assert_notification_rejected(lambda value: value["localImplementationBoundary"].update(providerAcceptanceIsDelivery=True), "notification:local_boundary")
        self.assert_notification_rejected(lambda value: value["networkAndPrivacy"]["telemetryForbidden"].remove("recipient"), "notification:privacy")
        self.assert_notification_rejected(lambda value: value["identityAndRecipients"].update(syntheticRecipient="INJECTED_VALUE"), "notification:recipient_boundary")

    def test_notification_failure_matrix_cannot_drop_adverse_outcomes(self) -> None:
        self.assert_notification_rejected(lambda value: value["failureMatrix"].remove("authenticated_bounce_receipt"), "notification:failure_matrix")
        self.assert_notification_rejected(lambda value: value["failureMatrix"].remove("opt_out_before_retry_suppressed"), "notification:failure_matrix")


if __name__ == "__main__":
    unittest.main()
