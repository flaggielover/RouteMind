package com.routemind.business.infrastructure.notification;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.Path;
import java.util.Objects;

/** Fail-closed validation for external SSH material used by the remote forward. */
public final class GmailOAuthRemoteForwardPolicy {

	private GmailOAuthRemoteForwardPolicy() { }

	public static ValidatedFiles validate(Path repositoryRoot,
			GmailOAuthRemoteForwardConfiguration configuration) throws IOException {
		Objects.requireNonNull(repositoryRoot, "repositoryRoot");
		Objects.requireNonNull(configuration, "configuration");
		Path root = repositoryRoot.toAbsolutePath().normalize();
		if (!Files.isDirectory(root, LinkOption.NOFOLLOW_LINKS)) {
			throw new IllegalArgumentException("repositoryRoot must be an existing directory");
		}
		Path realRoot = root.toRealPath();
		Path identity = requireExternalFile(realRoot, configuration.sshIdentityFile(), "SSH identity file");
		Path knownHosts = requireExternalFile(realRoot, configuration.knownHostsFile(), "known_hosts file");
		return new ValidatedFiles(identity, knownHosts);
	}

	private static Path requireExternalFile(Path realRoot, Path candidate, String description) throws IOException {
		Path normalized = candidate.toAbsolutePath().normalize();
		if (!Files.isRegularFile(normalized, LinkOption.NOFOLLOW_LINKS)) {
			throw new IllegalArgumentException(description + " is unavailable");
		}
		Path realCandidate = normalized.toRealPath();
		if (!samePath(realCandidate, normalized)) {
			throw new IllegalArgumentException(description + " redirects through a link");
		}
		if (realCandidate.startsWith(realRoot)) {
			throw new IllegalArgumentException(description + " must be outside the repository");
		}
		return realCandidate;
	}

	private static boolean samePath(Path left, Path right) {
		String leftText = left.toString();
		String rightText = right.toAbsolutePath().normalize().toString();
		return System.getProperty("os.name", "").toLowerCase().contains("win")
				? leftText.equalsIgnoreCase(rightText) : leftText.equals(rightText);
	}

	public record ValidatedFiles(Path sshIdentityFile, Path knownHostsFile) { }
}
