package com.routemind.business.domain.security;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HexFormat;
import java.util.List;
import java.util.Locale;
import java.util.regex.Pattern;

public final class DeploymentEdgeAdapter {

	private static final Pattern DIGEST = Pattern.compile("[0-9a-f]{64}");
	private static final Pattern MUTABLE_REFERENCE = Pattern.compile(
			"(^|[/@:?#=])(?:latest|stable|current|main|master)(?:$|[/?:#=])");

	private DeploymentEdgeAdapter() {
	}

	public static DeploymentAdapterDecision evaluate(DeploymentAdapterRequest request,
			DeploymentAdapterCapabilities capabilities) {
		if (request == null || capabilities == null || request.operation() == null) {
			return blocked("invalid_request", "unavailable", "unavailable");
		}
		String operationId = digest(request.canonicalFields(), capabilities.provider(), capabilities.providerVersion());
		String requestReason = validateRequest(request);
		if (requestReason != null) {
			return blocked(requestReason, operationId, capabilities);
		}
		if (capabilities.provider().isBlank() || capabilities.providerVersion().isBlank()) {
			return blocked("provider_identity_missing", operationId, capabilities);
		}
		if (!capabilities.supports(request.operation())) {
			return blocked("capability_missing:" + request.operation().name().toLowerCase(Locale.ROOT), operationId,
					capabilities);
		}
		if (request.operation() == DeploymentOperation.PREFLIGHT || request.operation() == DeploymentOperation.PLAN) {
			return new DeploymentAdapterDecision(AdapterOutcome.READY, "read_only_ready", operationId,
					capabilities.provider(), capabilities.providerVersion(), true);
		}
		String verificationReason = firstUnverifiedReason(request, capabilities);
		if (verificationReason != null) {
			return blocked(verificationReason, operationId, capabilities);
		}
		if (!capabilities.externalGateVerified()) {
			return blocked("external_gate_required", operationId, capabilities);
		}
		return new DeploymentAdapterDecision(AdapterOutcome.ACCEPTED_EXTERNAL, "external_execution_required", operationId,
				capabilities.provider(), capabilities.providerVersion(), true);
	}

	private static String validateRequest(DeploymentAdapterRequest request) {
		if (!DIGEST.matcher(request.releaseManifestDigest()).matches()) {
			return request.releaseManifestDigest().isBlank() ? "release_manifest_digest_missing" : "release_manifest_digest_invalid";
		}
		if (!DIGEST.matcher(request.stagedDecisionDigest()).matches()) {
			return request.stagedDecisionDigest().isBlank() ? "staged_decision_digest_missing" : "staged_decision_digest_invalid";
		}
		if (!DIGEST.matcher(request.ratePolicyDigest()).matches()) {
			return request.ratePolicyDigest().isBlank() ? "rate_policy_digest_missing" : "rate_policy_digest_invalid";
		}
		if (request.authorizationPolicyVersion().isBlank()) {
			return "authorization_policy_version_missing";
		}
		if (request.targetEnvironment().isBlank()) {
			return "target_environment_missing";
		}
		String[] names = { "identity_issuer", "identity_audience", "tls_key_reference", "waf_policy_reference",
				"limiter_reference", "secret_manager_identity" };
		String[] values = { request.identityIssuer(), request.identityAudience(), request.tlsKeyReference(),
				request.wafPolicyReference(), request.limiterReference(), request.secretManagerIdentity() };
		for (int index = 0; index < values.length; index++) {
			if (values[index].isBlank()) {
				return names[index] + "_missing";
			}
			if (MUTABLE_REFERENCE.matcher(values[index].toLowerCase(Locale.ROOT)).find()) {
				return names[index] + "_mutable";
			}
		}
		return null;
	}

	private static String firstUnverifiedReason(DeploymentAdapterRequest request,
			DeploymentAdapterCapabilities capabilities) {
		if (!capabilities.identityVerified()) {
			return "identity_unverified";
		}
		if (!capabilities.tlsReferenceVerified()) {
			return "tls_reference_unverified";
		}
		if (!capabilities.wafPolicyVerified()) {
			return "waf_policy_unverified";
		}
		if (!capabilities.limiterReferenceVerified()) {
			return "limiter_reference_unverified";
		}
		if (!capabilities.secretManagerVerified()) {
			return "secret_manager_unverified";
		}
		return null;
	}

	private static DeploymentAdapterDecision blocked(String reason, String operationId,
			DeploymentAdapterCapabilities capabilities) {
		return new DeploymentAdapterDecision(AdapterOutcome.BLOCKED, reason, operationId, capabilities.provider(),
				capabilities.providerVersion(), true);
	}

	private static DeploymentAdapterDecision blocked(String reason, String operationId, String provider) {
		return new DeploymentAdapterDecision(AdapterOutcome.BLOCKED, reason, operationId, provider, "unavailable", true);
	}

	private static String digest(List<String> fields, String provider, String providerVersion) {
		try {
			MessageDigest digest = MessageDigest.getInstance("SHA-256");
			for (String field : fields) {
				byte[] bytes = field.getBytes(StandardCharsets.UTF_8);
				digest.update(Integer.toString(bytes.length).getBytes(StandardCharsets.US_ASCII));
				digest.update((byte) ':');
				digest.update(bytes);
			}
			for (String field : List.of(provider, providerVersion)) {
				byte[] bytes = field.getBytes(StandardCharsets.UTF_8);
				digest.update(Integer.toString(bytes.length).getBytes(StandardCharsets.US_ASCII));
				digest.update((byte) ':');
				digest.update(bytes);
			}
			return HexFormat.of().formatHex(digest.digest());
		}
		catch (NoSuchAlgorithmException exception) {
			throw new IllegalStateException("SHA-256 is unavailable", exception);
		}
	}
}
