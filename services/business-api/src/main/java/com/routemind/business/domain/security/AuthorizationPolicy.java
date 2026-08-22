package com.routemind.business.domain.security;

import java.time.Instant;
import java.util.List;
import java.util.Objects;

public final class AuthorizationPolicy {

	private final String expectedIssuer;
	private final String expectedAudience;
	private final String policyVersion;
	private final List<AuthorizationRule> rules;

	public AuthorizationPolicy(String expectedIssuer, String expectedAudience, String policyVersion,
			List<AuthorizationRule> rules) {
		this.expectedIssuer = text(expectedIssuer, "expectedIssuer");
		this.expectedAudience = text(expectedAudience, "expectedAudience");
		this.policyVersion = text(policyVersion, "policyVersion");
		if (rules == null || rules.isEmpty() || rules.stream().anyMatch(Objects::isNull)) {
			throw new IllegalArgumentException("rules must contain at least one non-null rule");
		}
		this.rules = List.copyOf(rules);
	}

	public AuthorizationDecision evaluate(AuthenticatedPrincipal principal, CommandAuthorizationRequest request,
			Instant now) {
		if (principal == null || request == null) {
			return decision(AuthorizationOutcome.INVALID_PRINCIPAL, "invalid_request");
		}
		PrincipalValidation validation = principal.validateAt(now, expectedIssuer, expectedAudience);
		if (!validation.accepted()) {
			return decision(AuthorizationOutcome.INVALID_PRINCIPAL, validation.reason());
		}
		if (request.repeated()) {
			return decision(AuthorizationOutcome.REPEATED, "command_repeated");
		}
		if (request.expectedVersion() != request.currentVersion()) {
			return decision(AuthorizationOutcome.STALE, "stale_version");
		}
		boolean allowed = principal.roles().stream().anyMatch(role -> rules.stream().anyMatch(rule ->
				rule.role().equals(role)
					&& rule.action().equals(request.action())
					&& rule.resource().equals(request.resource())
					&& principal.scopes().contains(rule.requiredScope())));
		return allowed
				? decision(AuthorizationOutcome.ALLOWED, "authorized")
				: decision(AuthorizationOutcome.FORBIDDEN, "permission_denied");
	}

	private AuthorizationDecision decision(AuthorizationOutcome outcome, String reason) {
		return new AuthorizationDecision(outcome, reason, policyVersion);
	}

	private static String text(String value, String name) {
		if (value == null || value.isBlank()) {
			throw new IllegalArgumentException(name + " must not be blank");
		}
		return value.trim();
	}
}
