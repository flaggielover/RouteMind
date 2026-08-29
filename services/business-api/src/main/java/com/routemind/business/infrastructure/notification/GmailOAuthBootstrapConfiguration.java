package com.routemind.business.infrastructure.notification;

import java.nio.file.Path;
import java.util.Map;
import java.util.Objects;

/** Non-secret inputs for the explicit operator OAuth bootstrap command. */
public record GmailOAuthBootstrapConfiguration(
		Path clientCredentialFile,
		Path tokenStoreDirectory,
		String oauthUserId) {

	public static final String CLIENT_FILE_ENV = "ROUTEMIND_GMAIL_OAUTH_CLIENT_FILE";
	public static final String TOKEN_STORE_ENV = "ROUTEMIND_GMAIL_TOKEN_STORE";
	public static final String USER_ID_ENV = "ROUTEMIND_GMAIL_OAUTH_USER_ID";

	public GmailOAuthBootstrapConfiguration {
		clientCredentialFile = requireAbsolutePath(clientCredentialFile, "clientCredentialFile");
		tokenStoreDirectory = requireAbsolutePath(tokenStoreDirectory, "tokenStoreDirectory");
		oauthUserId = requireSafeText(oauthUserId, "oauthUserId");
		if (oauthUserId.isBlank()) {
			throw new IllegalArgumentException("oauthUserId is required");
		}
	}

	public static GmailOAuthBootstrapConfiguration fromEnvironment(Map<String, String> environment) {
		Objects.requireNonNull(environment, "environment");
		return new GmailOAuthBootstrapConfiguration(
				Path.of(required(environment, CLIENT_FILE_ENV)),
				Path.of(required(environment, TOKEN_STORE_ENV)),
				required(environment, USER_ID_ENV));
	}

	private static String required(Map<String, String> environment, String name) {
		String value = environment.get(name);
		if (value == null || value.isBlank()) {
			throw new IllegalArgumentException(name + " is required");
		}
		return value;
	}

	private static Path requireAbsolutePath(Path value, String name) {
		Path normalized = Objects.requireNonNull(value, name).normalize();
		if (!normalized.isAbsolute()) {
			throw new IllegalArgumentException(name + " must be absolute");
		}
		return normalized;
	}

	private static String requireSafeText(String value, String name) {
		String normalized = Objects.requireNonNullElse(value, "").trim();
		if (normalized.length() > 256 || normalized.chars().anyMatch(Character::isISOControl)) {
			throw new IllegalArgumentException(name + " contains unsafe text");
		}
		return normalized;
	}
}
