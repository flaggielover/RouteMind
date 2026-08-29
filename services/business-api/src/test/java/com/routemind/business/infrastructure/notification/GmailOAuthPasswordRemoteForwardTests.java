package com.routemind.business.infrastructure.notification;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatIllegalArgumentException;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

class GmailOAuthPasswordRemoteForwardTests {

	@Test
	void configurationRequiresOnlyKnownHostsAndBoundedMacPort() {
		Map<String, String> environment = new HashMap<>();
		Path temp = Path.of(System.getProperty("java.io.tmpdir")).toAbsolutePath();
		environment.put(GmailOAuthPasswordRemoteForwardConfiguration.KNOWN_HOSTS_ENV,
				temp.resolve("operator-known_hosts").toString());
		environment.put(GmailOAuthPasswordRemoteForwardConfiguration.MAC_PORT_ENV, "43127");
		GmailOAuthPasswordRemoteForwardConfiguration configuration =
				GmailOAuthPasswordRemoteForwardConfiguration.fromEnvironment(environment);
		assertThat(configuration.macLoopbackPort()).isEqualTo(43127);
		assertThat(configuration.knownHostsFile()).isAbsolute();
		assertThatIllegalArgumentException().isThrownBy(() ->
				new GmailOAuthPasswordRemoteForwardConfiguration(Path.of("C:/operator/known_hosts"), 1023));
	}

	@Test
	void externalKnownHostsIsAcceptedAndRepositoryMaterialIsRejected() throws Exception {
		Path root = Files.createTempDirectory("routemind-repo-");
		Path external = Files.createTempDirectory("routemind-ssh-");
		Path knownHosts = Files.createFile(external.resolve("known_hosts"));
		GmailOAuthPasswordRemoteForwardConfiguration valid =
				new GmailOAuthPasswordRemoteForwardConfiguration(knownHosts, 43127);
		Path validated = GmailOAuthPasswordRemoteForwardPolicy.validate(root, valid);
		assertThat(validated).isEqualTo(knownHosts.toRealPath());
		Path insideKnownHosts = Files.createFile(root.resolve("known_hosts"));
		assertThatIllegalArgumentException().isThrownBy(() ->
				GmailOAuthPasswordRemoteForwardPolicy.validate(root,
						new GmailOAuthPasswordRemoteForwardConfiguration(insideKnownHosts, 43127)))
				.withMessageContaining("outside the repository");
	}

	@Test
	void commandUsesInteractivePasswordAndStrictLoopbackForward() {
		Path temp = Path.of(System.getProperty("java.io.tmpdir")).toAbsolutePath();
		Path knownHosts = temp.resolve("operator-known_hosts");
		List<String> command = GmailOAuthPasswordRemoteForwardCommand.build(knownHosts, 43127, 43210);
		assertThat(command).containsExactly(
				"ssh.exe", "-N", "-T", "-o", "BatchMode=no", "-o", "ExitOnForwardFailure=yes",
				"-o", "StrictHostKeyChecking=yes", "-o", "CheckHostIP=yes",
				"-o", "PubkeyAuthentication=no", "-o", "PasswordAuthentication=yes",
				"-o", "KbdInteractiveAuthentication=yes",
				"-o", "PreferredAuthentications=keyboard-interactive,password",
				"-o", "NumberOfPasswordPrompts=1", "-o", "LogLevel=ERROR", "-o",
				"UserKnownHostsFile=" + knownHosts, "-o", "PermitRemoteOpen=127.0.0.1:43210",
				"-R", "127.0.0.1:43127:127.0.0.1:43210", "suzhe@10.10.1.27");
		assertThat(command).noneMatch(value -> value.contains("IdentityFile")
				|| value.contains("IdentitiesOnly") || value.contains("0.0.0.0") || value.equals("-g"));
	}

	@Test
	void fixedRemoteIdentityAndSyntheticBoundaryAreExplicit() throws Exception {
		assertThat(GmailOAuthPasswordRemoteForwardConfiguration.MAC_HOST).isEqualTo("10.10.1.27");
		assertThat(GmailOAuthPasswordRemoteForwardConfiguration.MAC_USER).isEqualTo("suzhe");
		Path source = Path.of("src/main/java/com/routemind/business/infrastructure/notification",
				"GmailOAuthPasswordRemoteForwardProbeCli.java");
		String cli = Files.readString(source);
		assertThat(cli).contains("/synthetic-probe");
		assertThat(cli).contains("redirectInput(ProcessBuilder.Redirect.INHERIT)");
		assertThat(cli).doesNotContain("AuthorizationCodeRequestUrl");
		assertThat(cli).doesNotContain("gmail.send");
	}
}
