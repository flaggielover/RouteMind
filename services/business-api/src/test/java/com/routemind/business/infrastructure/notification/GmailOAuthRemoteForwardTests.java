package com.routemind.business.infrastructure.notification;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatIllegalArgumentException;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

class GmailOAuthRemoteForwardTests {

	@Test
	void environmentRequiresExternalIdentityKnownHostsAndBoundedMacPort() {
		Map<String, String> environment = new HashMap<>();
		Path temp = Path.of(System.getProperty("java.io.tmpdir")).toAbsolutePath();
		environment.put(GmailOAuthRemoteForwardConfiguration.SSH_IDENTITY_ENV,
				temp.resolve("operator-ssh-key").toString());
		environment.put(GmailOAuthRemoteForwardConfiguration.KNOWN_HOSTS_ENV,
				temp.resolve("operator-known_hosts").toString());
		environment.put(GmailOAuthRemoteForwardConfiguration.MAC_PORT_ENV, "43127");
		GmailOAuthRemoteForwardConfiguration configuration = GmailOAuthRemoteForwardConfiguration
				.fromEnvironment(environment);
		assertThat(configuration.macLoopbackPort()).isEqualTo(43127);
		assertThat(configuration.sshIdentityFile()).isAbsolute();
		assertThatIllegalArgumentException().isThrownBy(() ->
				new GmailOAuthRemoteForwardConfiguration(Path.of("C:/operator/key"),
						Path.of("C:/operator/known_hosts"), 1023));
	}

	@Test
	void externalSshMaterialIsAcceptedAndRepositoryMaterialIsRejected() throws Exception {
		Path root = Files.createTempDirectory("routemind-repo-");
		Path external = Files.createTempDirectory("routemind-ssh-");
		Path identity = Files.createFile(external.resolve("id_ed25519"));
		Path knownHosts = Files.createFile(external.resolve("known_hosts"));
		GmailOAuthRemoteForwardConfiguration valid = new GmailOAuthRemoteForwardConfiguration(
				identity, knownHosts, 43127);
		GmailOAuthRemoteForwardPolicy.ValidatedFiles files = GmailOAuthRemoteForwardPolicy.validate(root, valid);
		assertThat(files.sshIdentityFile()).isEqualTo(identity.toRealPath());
		assertThat(files.knownHostsFile()).isEqualTo(knownHosts.toRealPath());
		Path insideIdentity = Files.createFile(root.resolve("id_ed25519"));
		assertThatIllegalArgumentException().isThrownBy(() ->
				GmailOAuthRemoteForwardPolicy.validate(root,
						new GmailOAuthRemoteForwardConfiguration(insideIdentity, knownHosts, 43127)))
				.withMessageContaining("outside the repository");
	}

	@Test
	void commandUsesStrictHostKeyVerificationAndLoopbackRemoteForwardOnly() {
		Path temp = Path.of(System.getProperty("java.io.tmpdir")).toAbsolutePath();
		Path identity = temp.resolve("operator-id_ed25519");
		Path knownHosts = temp.resolve("operator-known_hosts");
		List<String> command = GmailOAuthRemoteForwardCommand.build(
				identity, knownHosts, 43127, 43210);
		String identityOption = "IdentityFile=" + identity;
		String knownHostsOption = "UserKnownHostsFile=" + knownHosts;
		assertThat(command).containsExactly(
				"ssh.exe", "-N", "-T", "-o", "BatchMode=yes", "-o", "ExitOnForwardFailure=yes",
				"-o", "StrictHostKeyChecking=yes", "-o", "CheckHostIP=yes", "-o", "IdentitiesOnly=yes",
				"-o", "LogLevel=ERROR", "-o", knownHostsOption,
				"-o", identityOption, "-o", "PermitRemoteOpen=127.0.0.1:43210",
				"-R", "127.0.0.1:43127:127.0.0.1:43210", "suzhe@10.10.1.27");
		assertThat(command).noneMatch(value -> value.contains("0.0.0.0") || value.equals("-g")
				|| value.startsWith("GatewayPorts"));
	}

	@Test
	void fixedRemoteIdentityAndNoMessageOperationAreExplicit() {
		assertThat(GmailOAuthRemoteForwardConfiguration.MAC_HOST).isEqualTo("10.10.1.27");
		assertThat(GmailOAuthRemoteForwardConfiguration.MAC_USER).isEqualTo("suzhe");
		String cli = readSource("GmailOAuthRemoteBootstrapCli.java");
		assertThat(cli).contains("GoogleGmailOAuthBootstrap.authorizationUrl(flow, redirectUri)");
		assertThat(cli).contains("createAndStoreCredential(token, userId)");
		assertThat(cli).doesNotContain("users.messages.send");
		assertThat(cli).doesNotContain("new Gmail.Builder");
	}

	private static String readSource(String fileName) {
		try {
			Path source = Path.of("src/main/java/com/routemind/business/infrastructure/notification", fileName);
			return Files.readString(source);
		}
		catch (Exception exception) {
			throw new AssertionError("source fixture unavailable", exception);
		}
	}
}
