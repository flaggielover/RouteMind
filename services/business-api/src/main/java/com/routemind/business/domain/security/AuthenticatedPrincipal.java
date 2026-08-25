package com.routemind.business.domain.security;

import java.time.Instant;
import java.util.Set;

public record AuthenticatedPrincipal(
		String subject,
		String issuer,
		String tokenId,
		Instant issuedAt,
		Instant notBefore,
		Instant expiresAt,
		String audience,
		Set<String> roles,
		Set<String> scopes,
		TenantId tenantId,
		boolean active) {

	public AuthenticatedPrincipal {
		subject = text(subject, "subject");
		issuer = text(issuer, "issuer");
		tokenId = text(tokenId, "tokenId");
		audience = text(audience, "audience");
		if (tenantId == null) {
			throw new NullPointerException("tenantId must not be null");
		}
		if (issuedAt == null || notBefore == null || expiresAt == null) {
			throw new NullPointerException("principal timestamps must not be null");
		}
		if (expiresAt.isBefore(issuedAt) || expiresAt.equals(issuedAt)) {
			throw new IllegalArgumentException("expiresAt must be after issuedAt");
		}
		if (notBefore.isAfter(expiresAt)) {
			throw new IllegalArgumentException("notBefore must not be after expiresAt");
		}
		roles = normalizedSet(roles, "roles");
		scopes = normalizedSet(scopes, "scopes");
	}

	public AuthenticatedPrincipal(String subject, String issuer, String tokenId, Instant issuedAt,
			Instant notBefore, Instant expiresAt, String audience, Set<String> roles, Set<String> scopes,
			boolean active) {
		this(subject, issuer, tokenId, issuedAt, notBefore, expiresAt, audience, roles, scopes,
				TenantId.LEGACY, active);
	}

	public PrincipalValidation validateAt(Instant now, String expectedIssuer, String expectedAudience) {
		if (now == null) {
			throw new NullPointerException("now must not be null");
		}
		if (!issuer.equals(text(expectedIssuer, "expectedIssuer"))) {
			return new PrincipalValidation(false, "unknown_issuer");
		}
		if (!audience.equals(text(expectedAudience, "expectedAudience"))) {
			return new PrincipalValidation(false, "audience_mismatch");
		}
		if (!active) {
			return new PrincipalValidation(false, "principal_inactive");
		}
		if (now.isBefore(notBefore)) {
			return new PrincipalValidation(false, "credential_not_yet_valid");
		}
		if (!now.isBefore(expiresAt)) {
			return new PrincipalValidation(false, "credential_expired");
		}
		return new PrincipalValidation(true, "principal_valid");
	}

	private static String text(String value, String name) {
		if (value == null || value.isBlank()) {
			throw new IllegalArgumentException(name + " must not be blank");
		}
		if (value.chars().anyMatch(Character::isISOControl)) {
			throw new IllegalArgumentException(name + " must not contain control characters");
		}
		return value.trim();
	}

	private static Set<String> normalizedSet(Set<String> values, String name) {
		if (values == null || values.isEmpty() || values.stream().anyMatch(value -> value == null || value.isBlank())) {
			throw new IllegalArgumentException(name + " must contain non-blank values");
		}
		return Set.copyOf(values.stream().map(value -> text(value, name + " value")).toList());
	}
}
