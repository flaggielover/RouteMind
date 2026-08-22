package com.routemind.business.domain.security;

public record AuthorizationDecision(AuthorizationOutcome outcome, String reason, String policyVersion) {

	public AuthorizationDecision {
		if (outcome == null) {
			throw new NullPointerException("outcome must not be null");
		}
		if (reason == null || reason.isBlank()) {
			throw new IllegalArgumentException("reason must not be blank");
		}
		if (policyVersion == null || policyVersion.isBlank()) {
			throw new IllegalArgumentException("policyVersion must not be blank");
		}
	}
}
