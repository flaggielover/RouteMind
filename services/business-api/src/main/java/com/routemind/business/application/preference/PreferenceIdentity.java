package com.routemind.business.application.preference;

public record PreferenceIdentity(String principalId, String role) {

	public PreferenceIdentity {
		principalId = bounded(principalId, "principal_id", 200);
		role = bounded(role, "role", 16).toLowerCase(java.util.Locale.ROOT);
	}

	private static String bounded(String value, String field, int max) {
		if (value == null || value.isBlank()) throw new IllegalArgumentException(field + "_required");
		String normalized = value.trim();
		if (normalized.length() > max || normalized.chars().anyMatch(Character::isISOControl)) {
			throw new IllegalArgumentException(field + "_invalid");
		}
		return normalized;
	}
}
