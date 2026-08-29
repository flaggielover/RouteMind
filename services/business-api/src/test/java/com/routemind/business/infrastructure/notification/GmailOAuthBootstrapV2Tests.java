package com.routemind.business.infrastructure.notification;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatIllegalArgumentException;
import static org.assertj.core.api.Assertions.assertThatIllegalStateException;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.HashMap;
import java.util.Map;
import org.junit.jupiter.api.Test;

class GmailOAuthBootstrapV2Tests {

	@Test
	void configurationRequiresExternalKnownHostsAndBoundedMacPort() {
		Map<String, String> environment = new HashMap<>();
		environment.put(GmailOAuthBootstrapConfiguration.CLIENT_FILE_ENV, "C:/operator/client.json");
		environment.put(GmailOAuthBootstrapConfiguration.TOKEN_STORE_ENV, "C:/operator/tokens");
		environment.put(GmailOAuthBootstrapConfiguration.USER_ID_ENV, "operator");
		environment.put(GmailOAuthBootstrapV2Configuration.KNOWN_HOSTS_ENV, "C:/operator/known_hosts");
		environment.put(GmailOAuthBootstrapV2Configuration.MAC_PORT_ENV, "52817");
		GmailOAuthBootstrapV2Configuration configuration = GmailOAuthBootstrapV2Configuration
				.fromEnvironment(environment);
		assertThat(configuration.macLoopbackPort()).isEqualTo(52817);
		assertThatIllegalArgumentException().isThrownBy(() -> {
			environment.put(GmailOAuthBootstrapV2Configuration.MAC_PORT_ENV, "1023");
			GmailOAuthBootstrapV2Configuration.fromEnvironment(environment);
		});
	}

	@Test
	void knownHostsMustBeExternalAndNonRedirecting() throws Exception {
		Path root = Files.createTempDirectory("routemind-v2-repo-");
		Path outside = Files.createTempDirectory("routemind-v2-ssh-");
		Path knownHosts = Files.createFile(outside.resolve("known_hosts"));
		assertThat(GmailOAuthOperatorTunnelPolicy.validateKnownHosts(root, knownHosts))
				.isEqualTo(knownHosts.toRealPath());
		Path inside = Files.createFile(root.resolve("known_hosts"));
		assertThatIllegalArgumentException().isThrownBy(() ->
				GmailOAuthOperatorTunnelPolicy.validateKnownHosts(root, inside))
				.withMessageContaining("outside the repository");
	}

	@Test
	void readinessIsRequiredBeforeAuthorizationEligibility() {
		GmailOAuthBootstrapV2Session session = new GmailOAuthBootstrapV2Session();
		assertThat(session.authorizationUrlEligible()).isFalse();
		session.recordPreflight();
		assertThat(session.authorizationUrlEligible()).isTrue();
		assertThatIllegalStateException().isThrownBy(session::recordPreflight);
		assertThat(session.authorizationUrlEligible()).isFalse();
	}

	@Test
	void callbackValidatesPathStateAndSingleUseWithoutLoggingParameters() {
		GmailOAuthBootstrapV2Session session = new GmailOAuthBootstrapV2Session();
		assertThat(session.callback(java.net.URI.create(
				"http://127.0.0.1/oauth2callback?state=missing&code=before-preflight"))
				.accepted()).isFalse();
		session = new GmailOAuthBootstrapV2Session();
		session.recordPreflight();
		session.activateAuthorization();
		assertThat(session.callback(java.net.URI.create("http://127.0.0.1/wrong?state="
				+ session.expectedState() + "&code=ignored")).accepted()).isFalse();
		assertThat(session.callback(java.net.URI.create("http://127.0.0.1/oauth2callback?state=wrong&code=ignored"))
				.accepted()).isFalse();
		assertThat(session.terminalFailure()).isTrue();

		session = new GmailOAuthBootstrapV2Session();
		session.recordPreflight();
		session.activateAuthorization();
		GmailOAuthBootstrapV2Session.Callback accepted = session.callback(java.net.URI.create(
				"http://127.0.0.1/oauth2callback?state=" + session.expectedState() + "&code=synthetic-code"));
		assertThat(accepted.accepted()).isTrue();
		assertThat(session.callback(java.net.URI.create(
				"http://127.0.0.1/oauth2callback?state=" + session.expectedState() + "&code=second"))
				.accepted()).isFalse();
	}

	@Test
	void manualTunnelInstructionIsLoopbackOnlyAndFixedIdentity() {
		String command = GmailOAuthOperatorTunnelInstructions.command("C:/operator/known_hosts", 52817, 52700);
		assertThat(command).contains("ExitOnForwardFailure=yes", "StrictHostKeyChecking=yes",
				"CheckHostIP=yes", "UserKnownHostsFile", "-R 127.0.0.1:52817:127.0.0.1:52700",
				"suzhe@10.10.1.27");
		assertThat(command).doesNotContain("0.0.0.0", "GatewayPorts", "IdentityFile", "sshpass", "-pw");
	}
}
