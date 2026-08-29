package com.routemind.business.infrastructure.notification;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.Path;
import java.util.Objects;

/** Fail-closed validation for the external pinned known_hosts file. */
public final class GmailOAuthPasswordRemoteForwardPolicy {

	private GmailOAuthPasswordRemoteForwardPolicy() { }

	public static Path validate(Path repositoryRoot,
			GmailOAuthPasswordRemoteForwardConfiguration configuration) throws IOException {
		Objects.requireNonNull(repositoryRoot, "repositoryRoot");
		Objects.requireNonNull(configuration, "configuration");
		Path root = repositoryRoot.toAbsolutePath().normalize();
		if (!Files.isDirectory(root, LinkOption.NOFOLLOW_LINKS)) {
			throw new IllegalArgumentException("repositoryRoot must be an existing directory");
		}
		Path realRoot = root.toRealPath();
		Path knownHosts = configuration.knownHostsFile();
		if (!Files.isRegularFile(knownHosts, LinkOption.NOFOLLOW_LINKS)) {
			throw new IllegalArgumentException("known_hosts file is unavailable");
		}
		Path realKnownHosts = knownHosts.toRealPath();
		if (!samePath(realKnownHosts, knownHosts)) {
			throw new IllegalArgumentException("known_hosts file redirects through a link");
		}
		if (realKnownHosts.startsWith(realRoot)) {
			throw new IllegalArgumentException("known_hosts file must be outside the repository");
		}
		return realKnownHosts;
	}

	private static boolean samePath(Path left, Path right) {
		String leftText = left.toString();
		String rightText = right.toAbsolutePath().normalize().toString();
		return System.getProperty("os.name", "").toLowerCase().contains("win")
				? leftText.equalsIgnoreCase(rightText) : leftText.equals(rightText);
	}
}
