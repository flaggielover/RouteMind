package com.routemind.business.infrastructure.notification;

import com.google.api.client.auth.oauth2.AuthorizationCodeRequestUrl;
import com.google.api.client.auth.oauth2.Credential;
import com.google.api.client.googleapis.auth.oauth2.GoogleAuthorizationCodeFlow;
import com.google.api.client.googleapis.auth.oauth2.GoogleClientSecrets;
import com.google.api.client.http.HttpTransport;
import com.google.api.client.json.JsonFactory;
import com.google.api.client.json.jackson2.JacksonFactory;
import com.google.api.client.util.store.DataStoreFactory;
import java.io.IOException;
import java.io.Reader;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Collection;
import java.util.HashSet;
import java.util.List;
import java.util.Objects;
import java.util.Set;

/** Explicit operator bootstrap/load boundary; no consent flow runs at application startup. */
public final class GoogleGmailOAuthBootstrap {

	public static final String GMAIL_SEND_SCOPE = "https://www.googleapis.com/auth/gmail.send";

	private GoogleGmailOAuthBootstrap() { }

	public static GoogleAuthorizationCodeFlow buildFlow(HttpTransport transport, DataStoreFactory store,
			NotificationGmailProperties properties) throws IOException {
		Objects.requireNonNull(transport, "transport");
		Objects.requireNonNull(store, "store");
		Objects.requireNonNull(properties, "properties");
		if (!properties.enabled()) throw new IllegalStateException("Gmail adapter is disabled");
		Path repositoryRoot = Path.of(System.getProperty("routemind.repository.root", System.getProperty("user.dir")));
		GmailOAuthBootstrapConfiguration configuration = new GmailOAuthBootstrapConfiguration(
				Path.of(properties.clientSecretsPath()), Path.of(properties.tokenStorePath()), properties.oauthUserId());
		return buildFlow(transport, store, configuration, repositoryRoot);
	}

	public static GoogleAuthorizationCodeFlow buildFlow(HttpTransport transport, DataStoreFactory store,
			GmailOAuthBootstrapConfiguration configuration, Path repositoryRoot) throws IOException {
		Objects.requireNonNull(transport, "transport");
		Objects.requireNonNull(store, "store");
		Objects.requireNonNull(configuration, "configuration");
		validateOnlyGmailSendScope(List.of(GMAIL_SEND_SCOPE));
		GmailOAuthPathPolicy.ValidatedPaths paths = GmailOAuthPathPolicy.validate(repositoryRoot, configuration);
		JsonFactory json = JacksonFactory.getDefaultInstance();
		GoogleClientSecrets clientSecrets = loadAndValidateDesktopClient(paths.clientCredentialFile(), json);
		return new GoogleAuthorizationCodeFlow.Builder(transport, json, clientSecrets,
				List.of(GMAIL_SEND_SCOPE)).setDataStoreFactory(store).setAccessType("offline").build();
	}

	public static AuthorizationCodeRequestUrl authorizationUrl(GoogleAuthorizationCodeFlow flow) {
		return flow.newAuthorizationUrl().setAccessType("offline").set("prompt", "consent");
	}

	public static AuthorizationCodeRequestUrl authorizationUrl(GoogleAuthorizationCodeFlow flow, String redirectUri) {
		Objects.requireNonNull(redirectUri, "redirectUri");
		if (!redirectUri.startsWith("http://127.0.0.1:")) {
			throw new IllegalArgumentException("OAuth redirect must use the loopback host");
		}
		return flow.newAuthorizationUrl().setAccessType("offline").set("prompt", "consent")
				.setRedirectUri(redirectUri);
	}

	public static Credential loadStoredCredential(GoogleAuthorizationCodeFlow flow,
			NotificationGmailProperties properties) throws IOException {
		if (!properties.enabled()) throw new IllegalStateException("Gmail adapter is disabled");
		Credential credential = flow.loadCredential(properties.oauthUserId());
		if (credential == null) throw new IllegalStateException("stored Gmail OAuth credential is unavailable");
		return credential;
	}

	static void validateOnlyGmailSendScope(Collection<String> scopes) {
		if (scopes == null || scopes.size() != 1 || !new HashSet<>(scopes).equals(Set.of(GMAIL_SEND_SCOPE))) {
			throw new IllegalArgumentException("OAuth scope allowlist is restricted to gmail.send");
		}
	}

	static GoogleClientSecrets loadAndValidateDesktopClient(Path clientFile, JsonFactory json) throws IOException {
		GoogleClientSecrets clientSecrets;
		try (Reader reader = Files.newBufferedReader(clientFile)) {
			clientSecrets = GoogleClientSecrets.load(json, reader);
		}
		GoogleClientSecrets.Details installed = clientSecrets.getInstalled();
		if (installed == null || blank(installed.getClientId()) || blank(installed.getClientSecret())
				|| blank(installed.getAuthUri()) || blank(installed.getTokenUri())) {
			throw new IllegalArgumentException("Desktop OAuth client credentials are malformed");
		}
		if (clientSecrets.getWeb() != null) {
			throw new IllegalArgumentException("Web OAuth credentials are not accepted for this bootstrap");
		}
		return clientSecrets;
	}

	private static boolean blank(String value) {
		return value == null || value.isBlank();
	}
}
