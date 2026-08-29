package com.routemind.business.infrastructure.notification;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Objects;

/** Fail-closed validation for the operator's external pinned known_hosts file. */
final class GmailOAuthOperatorTunnelPolicy {

	private GmailOAuthOperatorTunnelPolicy() { }

	static Path validateKnownHosts(Path repositoryRoot, Path configuredPath) {
		try {
			Path root = Objects.requireNonNull(repositoryRoot, "repositoryRoot").toRealPath();
			Path candidate = Objects.requireNonNull(configuredPath, "configuredPath").toAbsolutePath().normalize();
			if (!Files.isRegularFile(candidate)) {
				throw new IllegalArgumentException("known_hosts file is unavailable");
			}
			if (Files.isSymbolicLink(candidate) || Files.isSymbolicLink(candidate.getParent())) {
				throw new IllegalArgumentException("known_hosts file redirects through a link");
			}
			Path real = candidate.toRealPath();
			if (real.startsWith(root)) {
				throw new IllegalArgumentException("known_hosts file must be outside the repository");
			}
			return real;
		}
		catch (IOException exception) {
			throw new IllegalArgumentException("known_hosts file cannot be resolved", exception);
		}
	}
}
