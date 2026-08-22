package com.routemind.business.domain.security;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;

class DeploymentEdgeAdapterTests {

	private static final DeploymentAdapterRequest REQUEST = request(DeploymentOperation.PREFLIGHT);
	private static final DeploymentAdapterCapabilities CAPABILITIES = new DeploymentAdapterCapabilities("edge-fixture",
			"v1", true, true, true, true, true, true, true, true, true, true);

	private static DeploymentAdapterRequest request(DeploymentOperation operation) {
		return new DeploymentAdapterRequest("a".repeat(64), "b".repeat(64), "auth-v3", "c".repeat(64), "staging",
				operation, "https://issuer.example/v1", "routemind-api-v1", "secret://edge/tls/v7",
				"waf://edge/policy/v3", "limiter://edge/policy/v4", "vault://routemind/staging-v7");
	}

	@Test
	void bindsImmutableDigestsAndProducesStableOperationIdWithoutSecrets() {
		DeploymentAdapterDecision first = DeploymentEdgeAdapter.evaluate(REQUEST, CAPABILITIES);
		DeploymentAdapterDecision second = DeploymentEdgeAdapter.evaluate(REQUEST, CAPABILITIES);

		assertThat(first.outcome()).isEqualTo(AdapterOutcome.READY);
		assertThat(first.operationId()).isEqualTo(second.operationId()).hasSize(64);
		assertThat(REQUEST.secretManagerIdentity()).contains("vault://").doesNotContain("secret-value");
	}

	@Test
	void localPreflightAndPlanRemainReadOnly() {
		DeploymentAdapterDecision preflight = DeploymentEdgeAdapter.evaluate(request(DeploymentOperation.PREFLIGHT), CAPABILITIES);
		DeploymentAdapterDecision plan = DeploymentEdgeAdapter.evaluate(request(DeploymentOperation.PLAN), CAPABILITIES);

		assertThat(preflight.outcome()).isEqualTo(AdapterOutcome.READY);
		assertThat(plan.outcome()).isEqualTo(AdapterOutcome.READY);
		assertThat(preflight.localReadOnly()).isTrue();
		assertThat(plan.localReadOnly()).isTrue();
	}

	@Test
	void missingOrMutableEdgeReferencesBlockBeforeApply() {
		DeploymentAdapterRequest missingTls = new DeploymentAdapterRequest("a".repeat(64), "b".repeat(64), "auth-v3",
				"c".repeat(64), "staging", DeploymentOperation.APPLY, "issuer", "audience", "", "waf://edge/v3",
				"limiter://edge/v4", "vault://routemind/staging-v7");
		DeploymentAdapterRequest mutableWaf = new DeploymentAdapterRequest("a".repeat(64), "b".repeat(64), "auth-v3",
				"c".repeat(64), "staging", DeploymentOperation.APPLY, "issuer", "audience", "tls://edge/v3",
				"waf://edge/latest", "limiter://edge/v4", "vault://routemind/staging-v7");

		assertThat(DeploymentEdgeAdapter.evaluate(missingTls, CAPABILITIES).reason()).isEqualTo("tls_key_reference_missing");
		assertThat(DeploymentEdgeAdapter.evaluate(mutableWaf, CAPABILITIES).reason()).isEqualTo("waf_policy_reference_mutable");
	}

	@Test
	void applyAndRollbackOnlyBecomeExternalAcceptedAfterAllGatesVerify() {
		DeploymentAdapterDecision apply = DeploymentEdgeAdapter.evaluate(request(DeploymentOperation.APPLY), CAPABILITIES);
		DeploymentAdapterDecision rollback = DeploymentEdgeAdapter.evaluate(request(DeploymentOperation.ROLLBACK), CAPABILITIES);

		assertThat(apply.outcome()).isEqualTo(AdapterOutcome.ACCEPTED_EXTERNAL);
		assertThat(rollback.outcome()).isEqualTo(AdapterOutcome.ACCEPTED_EXTERNAL);
		assertThat(apply.reason()).isEqualTo("external_execution_required");
		assertThat(apply.localReadOnly()).isTrue();
	}

	@Test
	void unverifiedIdentityOrMissingExternalGateFailsClosed() {
		DeploymentAdapterCapabilities unverified = new DeploymentAdapterCapabilities("edge-fixture", "v1", true, true,
				true, true, false, true, true, true, true, true);
		DeploymentAdapterCapabilities noExternalGate = new DeploymentAdapterCapabilities("edge-fixture", "v1", true, true,
				true, true, true, true, true, true, true, false);

		assertThat(DeploymentEdgeAdapter.evaluate(request(DeploymentOperation.APPLY), unverified).reason())
				.isEqualTo("identity_unverified");
		assertThat(DeploymentEdgeAdapter.evaluate(request(DeploymentOperation.ROLLBACK), noExternalGate).reason())
				.isEqualTo("external_gate_required");
	}
}
