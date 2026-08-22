package com.routemind.business.domain.security;

import java.util.List;

public record DeploymentAdapterCapabilities(
		String provider,
		String providerVersion,
		boolean supportsPreflight,
		boolean supportsPlan,
		boolean supportsApply,
		boolean supportsRollback,
		boolean identityVerified,
		boolean tlsReferenceVerified,
		boolean wafPolicyVerified,
		boolean limiterReferenceVerified,
		boolean secretManagerVerified,
		boolean externalGateVerified) {

	public DeploymentAdapterCapabilities {
		provider = text(provider);
		providerVersion = text(providerVersion);
	}

	boolean supports(DeploymentOperation operation) {
		return switch (operation) {
			case PREFLIGHT -> supportsPreflight;
			case PLAN -> supportsPlan;
			case APPLY -> supportsApply;
			case ROLLBACK -> supportsRollback;
		};
	}

	List<Boolean> edgeVerification() {
		return List.of(identityVerified, tlsReferenceVerified, wafPolicyVerified, limiterReferenceVerified,
				secretManagerVerified);
	}

	private static String text(String value) {
		return value == null ? "" : value.trim();
	}
}
