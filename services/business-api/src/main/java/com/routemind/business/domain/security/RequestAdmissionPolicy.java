package com.routemind.business.domain.security;

public final class RequestAdmissionPolicy {

	private RequestAdmissionPolicy() {
	}

	public static AdmissionDecision evaluate(RequestPolicy policy, RequestDescriptor request, UsageSnapshot usage) {
		if (policy == null || request == null || usage == null) {
			return reject(policy, "invalid_request");
		}
		if (!request.validUtf8()) {
			return reject(policy, "invalid_utf8");
		}
		if (request.containsControlCharacters()) {
			return reject(policy, "control_character");
		}
		if (request.command() && !request.idempotencyKeyPresent()) {
			return reject(policy, "idempotency_key_required");
		}
		if (request.bodyBytes() > policy.maxBodyBytes()) {
			return reject(policy, "body_limit");
		}
		if (request.fieldCount() > policy.maxFields()) {
			return reject(policy, "field_count_limit");
		}
		if (request.longestFieldLength() > policy.maxFieldLength()) {
			return reject(policy, "field_length_limit");
		}
		if (usage.usedRequests() >= policy.maxRequests() + policy.burstAllowance()) {
			long retryAfter = Math.max(1, policy.windowSeconds() - usage.windowElapsedSeconds());
			return new AdmissionDecision(AdmissionOutcome.THROTTLE, "rate_limit_exceeded", retryAfter, policy.digest());
		}
		return new AdmissionDecision(AdmissionOutcome.ALLOW, "admitted", 0, policy.digest());
	}

	private static AdmissionDecision reject(RequestPolicy policy, String reason) {
		String digest = policy == null ? "unavailable" : policy.digest();
		return new AdmissionDecision(AdmissionOutcome.REJECT, reason, 0, digest);
	}
}
