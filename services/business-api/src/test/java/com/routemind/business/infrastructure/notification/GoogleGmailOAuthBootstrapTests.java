package com.routemind.business.infrastructure.notification;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatIllegalArgumentException;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.google.api.client.json.jackson2.JacksonFactory;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

class GoogleGmailOAuthBootstrapTests {

	private static final String SCOPE = GoogleGmailOAuthBootstrap.GMAIL_SEND_SCOPE;

	@Test
	void scopeAllowlistAcceptsOnlyGmailSend() {
		GoogleGmailOAuthBootstrap.validateOnlyGmailSendScope(List.of(SCOPE));
		assertThatIllegalArgumentException().isThrownBy(() ->
				GoogleGmailOAuthBootstrap.validateOnlyGmailSendScope(
						List.of(SCOPE, "https://www.googleapis.com/auth/gmail.readonly")));
		assertThatIllegalArgumentException().isThrownBy(() ->
				GoogleGmailOAuthBootstrap.validateOnlyGmailSendScope(List.of(SCOPE, SCOPE)));
	}

	@Test
	void environmentInputsRequireOnlyNonSecretNames() {
		Map<String, String> environment = new HashMap<>();
		environment.put(GmailOAuthBootstrapConfiguration.CLIENT_FILE_ENV, "C:/operator/client.json");
		environment.put(GmailOAuthBootstrapConfiguration.TOKEN_STORE_ENV, "C:/operator/tokens");
		environment.put(GmailOAuthBootstrapConfiguration.USER_ID_ENV, "operator");
		GmailOAuthBootstrapConfiguration configuration = GmailOAuthBootstrapConfiguration.fromEnvironment(environment);
		assertThat(configuration.clientCredentialFile()).isAbsolute();
		assertThat(configuration.tokenStoreDirectory()).isAbsolute();
		assertThat(configuration.oauthUserId()).isEqualTo("operator");
		environment.remove(GmailOAuthBootstrapConfiguration.TOKEN_STORE_ENV);
		assertThatIllegalArgumentException().isThrownBy(() ->
				GmailOAuthBootstrapConfiguration.fromEnvironment(environment));
		environment.put(GmailOAuthBootstrapConfiguration.TOKEN_STORE_ENV, "relative/tokens");
		assertThatIllegalArgumentException().isThrownBy(() ->
				GmailOAuthBootstrapConfiguration.fromEnvironment(environment));
	}

	@Test
	void malformedDesktopClientIsRejectedWithoutNetwork() throws Exception {
		Path client = Files.createTempFile("routemind-gmail-client-", ".json");
		try {
			Files.writeString(client, "{\"web\":{\"client_id\":\"placeholder\"}}\n");
			assertThatThrownBy(() -> GoogleGmailOAuthBootstrap.loadAndValidateDesktopClient(
					client, JacksonFactory.getDefaultInstance()))
					.isInstanceOf(IllegalArgumentException.class)
					.hasMessageContaining("Desktop OAuth client credentials are malformed");
		}
		finally {
			Files.deleteIfExists(client);
		}
	}

	@Test
	void repositoryContainedClientOrTokenStoreIsRejected() throws Exception {
		Path root = Files.createTempDirectory("routemind-repo-");
		Path insideClient = Files.createFile(root.resolve("client.json"));
		Path outside = Files.createTempDirectory("routemind-secrets-");
		Path outsideClient = Files.createFile(outside.resolve("client.json"));
		Path outsideTokens = Files.createDirectory(outside.resolve("tokens"));
		GmailOAuthBootstrapConfiguration valid = new GmailOAuthBootstrapConfiguration(
				outsideClient, outsideTokens, "operator");
		GmailOAuthPathPolicy.ValidatedPaths validated = GmailOAuthPathPolicy.validate(root, valid);
		assertThat(validated.clientCredentialFile()).isEqualTo(outsideClient.toRealPath());
		assertThat(validated.tokenStoreDirectory()).isEqualTo(outsideTokens.toRealPath());
		GmailOAuthBootstrapConfiguration invalid = new GmailOAuthBootstrapConfiguration(
				insideClient, outsideTokens, "operator");
		assertThatIllegalArgumentException().isThrownBy(() -> GmailOAuthPathPolicy.validate(root, invalid))
				.withMessageContaining("outside the repository");
	}
}
