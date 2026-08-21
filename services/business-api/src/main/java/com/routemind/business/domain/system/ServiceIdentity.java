package com.routemind.business.domain.system;

public record ServiceIdentity(String name, String runtime, String architectureVersion) {

	public ServiceIdentity {
		name = requireText(name, "name");
		runtime = requireText(runtime, "runtime");
		architectureVersion = requireText(architectureVersion, "architectureVersion");
	}

	private static String requireText(String value, String field) {
		if (value == null || value.isBlank()) {
			throw new IllegalArgumentException(field + " must not be blank");
		}
		return value;
	}
}
