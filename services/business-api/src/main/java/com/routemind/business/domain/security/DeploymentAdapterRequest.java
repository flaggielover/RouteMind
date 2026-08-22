package com.routemind.business.domain.security;

import java.util.List;

public record DeploymentAdapterRequest(
		String releaseManifestDigest,
		String stagedDecisionDigest,
		String authorizationPolicyVersion,
		String ratePolicyDigest,
		String targetEnvironment,
		DeploymentOperation operation,
		String identityIssuer,
		String identityAudience,
		String tlsKeyReference,
		String wafPolicyReference,
		String limiterReference,
		String secretManagerIdentity) {

	public DeploymentAdapterRequest {
		releaseManifestDigest = text(releaseManifestDigest);
		stagedDecisionDigest = text(stagedDecisionDigest);
		authorizationPolicyVersion = text(authorizationPolicyVersion);
		ratePolicyDigest = text(ratePolicyDigest);
		targetEnvironment = text(targetEnvironment);
		identityIssuer = text(identityIssuer);
		identityAudience = text(identityAudience);
		tlsKeyReference = text(tlsKeyReference);
		wafPolicyReference = text(wafPolicyReference);
		limiterReference = text(limiterReference);
		secretManagerIdentity = text(secretManagerIdentity);
	}

	List<String> canonicalFields() {
		return List.of(releaseManifestDigest, stagedDecisionDigest, authorizationPolicyVersion, ratePolicyDigest,
				targetEnvironment, operation == null ? "" : operation.name(), identityIssuer, identityAudience,
				tlsKeyReference, wafPolicyReference, limiterReference, secretManagerIdentity);
	}

	private static String text(String value) {
		return value == null ? "" : value.trim();
	}
}
