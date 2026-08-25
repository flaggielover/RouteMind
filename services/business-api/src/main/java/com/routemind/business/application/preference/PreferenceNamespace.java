package com.routemind.business.application.preference;

import java.util.Locale;
import java.util.Set;

public enum PreferenceNamespace {
	ACCESSIBILITY("accessibility"),
	LOCALE("locale"),
	NOTIFICATIONS("notifications"),
	QUIET_HOURS("quiet_hours");

	private static final Set<String> ROLES = Set.of("customer", "courier", "merchant", "analyst", "operator");
	private final String id;

	PreferenceNamespace(String id) {
		this.id = id;
	}

	public String id() {
		return id;
	}

	public boolean ownedBy(String role) {
		return ROLES.contains(role);
	}

	public static PreferenceNamespace parse(String value) {
		if (value == null || value.isBlank()) throw new IllegalArgumentException("preference_namespace_required");
		String normalized = value.trim().toLowerCase(Locale.ROOT);
		for (PreferenceNamespace namespace : values()) {
			if (namespace.id.equals(normalized)) return namespace;
		}
		throw new IllegalArgumentException("preference_namespace_unsupported");
	}
}
