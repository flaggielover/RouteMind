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
import java.util.List;
import java.util.Objects;

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
		JsonFactory json = JacksonFactory.getDefaultInstance();
		GoogleClientSecrets clientSecrets;
		try (Reader reader = Files.newBufferedReader(Path.of(properties.clientSecretsPath()))) {
			clientSecrets = GoogleClientSecrets.load(json, reader);
		}
		return new GoogleAuthorizationCodeFlow.Builder(transport, json, clientSecrets,
				List.of(GMAIL_SEND_SCOPE)).setDataStoreFactory(store).setAccessType("offline").build();
	}

	public static AuthorizationCodeRequestUrl authorizationUrl(GoogleAuthorizationCodeFlow flow) {
		return flow.newAuthorizationUrl().setAccessType("offline").set("prompt", "consent");
	}

	public static Credential loadStoredCredential(GoogleAuthorizationCodeFlow flow,
			NotificationGmailProperties properties) throws IOException {
		if (!properties.enabled()) throw new IllegalStateException("Gmail adapter is disabled");
		Credential credential = flow.loadCredential(properties.oauthUserId());
		if (credential == null) throw new IllegalStateException("stored Gmail OAuth credential is unavailable");
		return credential;
	}
}
