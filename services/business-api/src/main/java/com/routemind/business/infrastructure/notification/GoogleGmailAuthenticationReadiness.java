package com.routemind.business.infrastructure.notification;

import java.util.Objects;

/** Offline configuration readiness only; it never reads OAuth tokens or makes a network call. */
public final class GoogleGmailAuthenticationReadiness {

	public enum Status {
		AVAILABLE_FOR_EXPLICIT_BOOTSTRAP,
		MISSING,
		INVALID_CONFIGURATION
	}

	private GoogleGmailAuthenticationReadiness() { }

	public static Status assess(NotificationGmailProperties properties) {
		Objects.requireNonNull(properties, "properties");
		if (!properties.enabled()) return Status.MISSING;
		if (properties.clientSecretsPath().isBlank() || properties.tokenStorePath().isBlank()
				|| properties.oauthUserId().isBlank()) return Status.MISSING;
		return Status.AVAILABLE_FOR_EXPLICIT_BOOTSTRAP;
	}
}
