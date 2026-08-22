package com.routemind.business.domain.security;

public record CommandAuthorizationRequest(String action, String resource, long expectedVersion,
		long currentVersion, boolean repeated) {

	public CommandAuthorizationRequest {
		action = text(action, "action");
		resource = text(resource, "resource");
		if (expectedVersion < 0 || currentVersion < 0) {
			throw new IllegalArgumentException("versions must be non-negative");
		}
	}

	private static String text(String value, String name) {
		if (value == null || value.isBlank()) {
			throw new IllegalArgumentException(name + " must not be blank");
		}
		return value.trim();
	}
}
