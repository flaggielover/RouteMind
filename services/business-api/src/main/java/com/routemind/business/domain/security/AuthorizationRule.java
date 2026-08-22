package com.routemind.business.domain.security;

public record AuthorizationRule(String role, String action, String resource, String requiredScope) {

	public AuthorizationRule {
		role = text(role, "role");
		action = text(action, "action");
		resource = text(resource, "resource");
		requiredScope = text(requiredScope, "requiredScope");
	}

	private static String text(String value, String name) {
		if (value == null || value.isBlank()) {
			throw new IllegalArgumentException(name + " must not be blank");
		}
		return value.trim();
	}
}
