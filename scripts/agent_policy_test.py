from __future__ import annotations

import copy
import unittest

import agent_policy as policy


class AgentPolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.payload = policy.load_contract()

    def assert_rejected(self, mutate, expected: str) -> None:  # type: ignore[no-untyped-def]
        candidate = copy.deepcopy(self.payload)
        mutate(candidate)
        self.assertIn(expected, policy.validate_contract(candidate))

    def test_frozen_contract_is_valid_and_digest_is_stable(self) -> None:
        self.assertEqual(policy.validate_contract(self.payload), [])
        self.assertEqual(policy.digest(self.payload), policy.digest(copy.deepcopy(self.payload)))

    def test_java_owns_durable_and_hard_realtime_authority(self) -> None:
        self.assert_rejected(lambda value: value["ownership"].update(durableStateOwner="python_compute_api"), "ownership:durableStateOwner")
        self.assert_rejected(lambda value: value["ownership"].update(hardRealtimeDispatchOwner="llm"), "ownership:hardRealtimeDispatchOwner")
        self.assert_rejected(lambda value: value["ownership"].update(llmAuthority="dispatch"), "ownership:llmAuthority")

    def test_state_changing_tools_are_denied_and_read_tools_do_not_mutate(self) -> None:
        self.assert_rejected(lambda value: value["toolClasses"][-1].update(allowed=True), "tools:state_changing_fail_closed")
        self.assert_rejected(lambda value: value["toolClasses"][0].update(mutatesDurableState=True), "tools:read_only:read")
        self.assert_rejected(lambda value: value["toolClasses"].pop(), "tools:classes")

    def test_budgets_fallback_and_dispatch_independence_are_frozen(self) -> None:
        self.assert_rejected(lambda value: value["runtime"].update(maxCallsPerSession=99), "runtime:budgets")
        self.assert_rejected(lambda value: value["runtime"].update(agentUnavailable="raise"), "runtime:fallback")
        self.assert_rejected(lambda value: value["runtime"].update(dispatchRegistryIndependent=False), "runtime:dispatch_independence")

    def test_injection_leakage_approval_timeout_rollback_and_network_fail_closed(self) -> None:
        self.assert_rejected(lambda value: value["security"].update(promptInjection="trust_prompt"), "security:promptInjection")
        self.assert_rejected(lambda value: value["security"].update(dataLeakage="allow_principal_id"), "security:dataLeakage")
        self.assert_rejected(lambda value: value["security"].update(approval="agent_only"), "security:approval")
        self.assert_rejected(lambda value: value["security"].update(network="allow_provider"), "security:network")

    def test_agents_cannot_promote_claims_and_fail_is_terminal_evidence(self) -> None:
        self.assert_rejected(lambda value: value["claimBoundary"].update(agentMayPromoteScientificClaim=True), "claims:agentMayPromoteScientificClaim")
        self.assert_rejected(lambda value: value["claimBoundary"].update(agentMayAuthorizeNotificationSend=True), "claims:agentMayAuthorizeNotificationSend")
        self.assert_rejected(lambda value: value["claimBoundary"].update(scientificFailOrNoClaim="optimize_again"), "claims:negative_outcome")


if __name__ == "__main__":
    unittest.main()
