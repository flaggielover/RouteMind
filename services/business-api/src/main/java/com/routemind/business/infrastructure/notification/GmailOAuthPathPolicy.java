package com.routemind.business.infrastructure.notification;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.Path;
import java.util.Objects;

/** Fail-closed path policy for repository-external OAuth material. */
public final class GmailOAuthPathPolicy {

	private GmailOAuthPathPolicy() { }

	public static ValidatedPaths validate(Path repositoryRoot, GmailOAuthBootstrapConfiguration configuration)
			throws IOException {
		Objects.requireNonNull(repositoryRoot, "repositoryRoot");
		Objects.requireNonNull(configuration, "configuration");
		Path root = normalizeAbsolute(repositoryRoot, "repositoryRoot");
		if (!Files.isDirectory(root, LinkOption.NOFOLLOW_LINKS)) {
			throw new IllegalArgumentException("repositoryRoot must be an existing directory");
		}
		Path realRoot = root.toRealPath();
		Path client = requireExternalFile(realRoot, configuration.clientCredentialFile());
		Path tokenStore = requireExternalDirectory(realRoot, configuration.tokenStoreDirectory());
		return new ValidatedPaths(client, tokenStore);
	}

	private static Path requireExternalFile(Path realRoot, Path candidate) throws IOException {
		Path normalized = normalizeAbsolute(candidate, "clientCredentialFile");
		if (!Files.isRegularFile(normalized, LinkOption.NOFOLLOW_LINKS)) {
			throw new IllegalArgumentException("client credential file is unavailable");
		}
		return requireExternal(realRoot, normalized, "client credential file");
	}

	private static Path requireExternalDirectory(Path realRoot, Path candidate) throws IOException {
		Path normalized = normalizeAbsolute(candidate, "tokenStoreDirectory");
		if (!Files.isDirectory(normalized, LinkOption.NOFOLLOW_LINKS) || !Files.isWritable(normalized)) {
			throw new IllegalArgumentException("token store directory is unavailable");
		}
		return requireExternal(realRoot, normalized, "token store directory");
	}

	private static Path requireExternal(Path realRoot, Path candidate, String description) throws IOException {
		Path realCandidate = candidate.toRealPath();
		if (!samePath(realCandidate, candidate)) {
			throw new IllegalArgumentException(description + " redirects through a link");
		}
		if (realCandidate.startsWith(realRoot)) {
			throw new IllegalArgumentException(description + " must be outside the repository");
		}
		return realCandidate;
	}

	private static Path normalizeAbsolute(Path path, String description) {
		Path supplied = Objects.requireNonNull(path, description).normalize();
		if (!supplied.isAbsolute()) {
			throw new IllegalArgumentException(description + " must be absolute");
		}
		return supplied;
	}

	private static boolean samePath(Path left, Path right) {
		String leftText = left.toString();
		String rightText = right.toAbsolutePath().normalize().toString();
		return System.getProperty("os.name", "").toLowerCase().contains("win")
				? leftText.equalsIgnoreCase(rightText) : leftText.equals(rightText);
	}

	public record ValidatedPaths(Path clientCredentialFile, Path tokenStoreDirectory) { }
}
