package com.routemind.business.domain.security;

public record AdmissionDecision(AdmissionOutcome outcome, String reason, long retryAfterSeconds, String policyDigest) {

	public AdmissionDecision {
		if (outcome == null || reason == null || reason.isBlank() || policyDigest == null || policyDigest.isBlank()) {
			throw new IllegalArgumentException("admission decision fields are required");
		}
		if (retryAfterSeconds < 0) {
			throw new IllegalArgumentException("retryAfterSeconds must be non-negative");
		}
		if (outcome != AdmissionOutcome.THROTTLE && retryAfterSeconds != 0) {
			throw new IllegalArgumentException("only throttled requests have retry-after");
		}
	}
}
