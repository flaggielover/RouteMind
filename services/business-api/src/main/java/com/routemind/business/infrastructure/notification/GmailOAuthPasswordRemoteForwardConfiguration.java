package com.routemind.business.infrastructure.notification;

import java.nio.file.Path;
import java.util.Map;
import java.util.Objects;

/** Non-secret inputs for the operator-password SSH remote-forward probe. */
public record GmailOAuthPasswordRemoteForwardConfiguration(
		Path knownHostsFile,
		int macLoopbackPort) {

	public static final String KNOWN_HOSTS_ENV = "ROUTEMIND_GMAIL_OAUTH_MAC_KNOWN_HOSTS";
	public static final String MAC_PORT_ENV = "ROUTEMIND_GMAIL_OAUTH_MAC_PORT";
	public static final String MAC_HOST = "10.10.1.27";
	public static final String MAC_USER = "suzhe";

	public GmailOAuthPasswordRemoteForwardConfiguration {
		knownHostsFile = requireAbsolutePath(knownHostsFile, "knownHostsFile");
		if (macLoopbackPort < 1024 || macLoopbackPort > 65535) {
			throw new IllegalArgumentException("macLoopbackPort must be between 1024 and 65535");
		}
	}

	public static GmailOAuthPasswordRemoteForwardConfiguration fromEnvironment(
			Map<String, String> environment) {
		Objects.requireNonNull(environment, "environment");
		String rawPort = required(environment, MAC_PORT_ENV);
		final int port;
		try {
			port = Integer.parseInt(rawPort);
		}
		catch (NumberFormatException exception) {
			throw new IllegalArgumentException(MAC_PORT_ENV + " must be numeric", exception);
		}
		return new GmailOAuthPasswordRemoteForwardConfiguration(
				Path.of(required(environment, KNOWN_HOSTS_ENV)), port);
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
}
