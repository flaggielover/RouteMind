package com.routemind.business.infrastructure.notification;

import java.util.Objects;

/** Offline-only readiness classification; it deliberately never resolves credentials. */
public final class AwsSesAuthenticationReadiness {

	public enum Status {
		AVAILABLE,
		MISSING,
		INVALID_CONFIGURATION
	}

	private AwsSesAuthenticationReadiness() {
	}

	public static Status assess(NotificationSesProperties properties, String environmentProfile) {
		Objects.requireNonNull(properties, "properties");
		if (!properties.enabled()) {
			return Status.MISSING;
		}
		try {
			return properties.effectiveProfile(environmentProfile).isBlank() ? Status.MISSING : Status.AVAILABLE;
		}
		catch (IllegalArgumentException exception) {
			return Status.INVALID_CONFIGURATION;
		}
	}
}
