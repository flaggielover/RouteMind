package com.routemind.business.infrastructure.notification;

import com.google.api.client.auth.oauth2.Credential;
import com.google.api.client.auth.oauth2.CredentialRefreshListener;
import com.google.api.client.auth.oauth2.TokenErrorResponse;
import com.google.api.client.auth.oauth2.TokenResponse;
import com.google.api.client.googleapis.auth.oauth2.GoogleAuthorizationCodeFlow;
import com.google.api.client.googleapis.auth.oauth2.GoogleClientSecrets;
import com.google.api.client.googleapis.javanet.GoogleNetHttpTransport;
import com.google.api.client.http.HttpRequest;
import com.google.api.client.http.HttpResponseException;
import com.google.api.client.json.JsonFactory;
import com.google.api.client.json.jackson2.JacksonFactory;
import com.google.api.client.util.store.FileDataStoreFactory;
import java.io.IOException;
import java.nio.file.Path;
import java.time.Duration;
import java.time.Instant;
import java.util.List;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.logging.Level;
import java.util.logging.LogManager;
import java.util.logging.Logger;

/** Explicit, one-request Gmail credential refresh executor bound to the approved contract. */
public final class GmailCredentialRefreshRecoveryCli {

	static final String CONTRACT_DIGEST =
			"6c2b454101787c72459b3a5a7f01c18b25cf09d19ffd8ed90aaf3044e8b4b39f";

	private GmailCredentialRefreshRecoveryCli() { }

	public static void main(String[] args) {
		disableLibraryLogging();
		Instant startedAt = Instant.now();
		try {
			execute(args, startedAt);
		} catch (PreflightFailure failure) {
			printPreflightFailure(failure.reason());
			System.exit(2);
		} catch (Exception failure) {
			printPreflightFailure("UNEXPECTED_PREFLIGHT_FAILURE");
			System.exit(2);
		}
	}

	private static void execute(String[] args, Instant startedAt) throws Exception {
		if (args.length != 1 || !"--execute".equals(args[0])) {
			throw new PreflightFailure("EXPLICIT_EXECUTION_MODE_REQUIRED");
		}
		if (!CONTRACT_DIGEST.equals(required("ROUTEMIND_R4_422_GMAIL_REFRESH_CONTRACT_SHA256"))) {
			throw new PreflightFailure("CONTRACT_DIGEST_MISMATCH");
		}

		Path repositoryRoot = Path.of(required("ROUTEMIND_REPOSITORY_ROOT"));
		GmailOAuthBootstrapConfiguration configuration =
				GmailOAuthBootstrapConfiguration.fromEnvironment(System.getenv());
		GmailOAuthPathPolicy.ValidatedPaths paths = GmailOAuthPathPolicy.validate(repositoryRoot, configuration);
		JsonFactory json = JacksonFactory.getDefaultInstance();
		GoogleClientSecrets clientSecrets =
				GoogleGmailOAuthBootstrap.loadAndValidateDesktopClient(paths.clientCredentialFile(), json);
		FileDataStoreFactory store = new FileDataStoreFactory(paths.tokenStoreDirectory().toFile());
		AtomicInteger tokenResponses = new AtomicInteger();
		AtomicInteger tokenErrors = new AtomicInteger();
		GoogleAuthorizationCodeFlow flow = new GoogleAuthorizationCodeFlow.Builder(
				GoogleNetHttpTransport.newTrustedTransport(), json, clientSecrets,
				List.of(GoogleGmailOAuthBootstrap.GMAIL_SEND_SCOPE))
				.setDataStoreFactory(store)
				.setAccessType("offline")
				.setRequestInitializer(GmailCredentialRefreshRecoveryCli::configureRefreshRequest)
				.addRefreshListener(new CredentialRefreshListener() {
					@Override
					public void onTokenResponse(Credential credential, TokenResponse response) {
						tokenResponses.incrementAndGet();
					}

					@Override
					public void onTokenErrorResponse(Credential credential, TokenErrorResponse response) {
						tokenErrors.incrementAndGet();
					}
				})
				.build();

		Credential credential = flow.loadCredential(configuration.oauthUserId());
		GoogleGmailCredentialRefreshReadiness.Assessment readiness =
				GoogleGmailCredentialRefreshReadiness.assess(credential);
		if (readiness.status() != GoogleGmailCredentialRefreshReadiness.Status.REFRESH_REQUIRED_AND_AVAILABLE) {
			throw new PreflightFailure("CREDENTIAL_REFRESH_PRECONDITION_FAILED");
		}

		// The approved contract permits one refresh request and no retry or fallback.
		int refreshAttempts = 1;
		try {
			boolean refreshed = credential.refreshToken();
			printOutcome("SUCCESS", refreshed ? "REFRESHED" : "NO_NEW_TOKEN", 0,
					tokenResponses.get(), tokenErrors.get(), refreshAttempts, startedAt);
		} catch (IOException failure) {
			int httpStatus = failure instanceof HttpResponseException response
					? response.getStatusCode() : 0;
			printOutcome("FAILED", "REFRESH_REQUEST_FAILED", httpStatus,
					tokenResponses.get(), tokenErrors.get(), refreshAttempts, startedAt);
			System.exit(3);
		}
	}

	static void configureRefreshRequest(HttpRequest request) {
		request.setNumberOfRetries(0);
		request.setFollowRedirects(false);
		request.setIOExceptionHandler(null);
		request.setUnsuccessfulResponseHandler(null);
		request.setConnectTimeout(10_000);
		request.setReadTimeout(30_000);
	}

	private static void printOutcome(String status, String reason, int httpStatus,
			int tokenResponses, int tokenErrors, int refreshAttempts, Instant startedAt) {
		long elapsedMillis = Duration.between(startedAt, Instant.now()).toMillis();
		System.out.println("EXECUTION_STATUS=" + status);
		System.out.println("SAFE_REASON=" + reason);
		System.out.println("HTTP_STATUS=" + httpStatus);
		System.out.println("TOKEN_REFRESH_REQUESTS=" + refreshAttempts);
		System.out.println("TOKEN_RESPONSES=" + tokenResponses);
		System.out.println("TOKEN_ERROR_RESPONSES=" + tokenErrors);
		System.out.println("TOKEN_STORE_UPDATE=DELEGATED_TO_STANDARD_LIBRARY");
		System.out.println("AUTHORIZATION_CODE_EXCHANGES=0");
		System.out.println("OAUTH_SESSIONS=0");
		System.out.println("BROWSER_SESSIONS=0");
		System.out.println("SSH_SESSIONS=0");
		System.out.println("GMAIL_API_REQUESTS=0");
		System.out.println("EMAIL_SENDS=0");
		System.out.println("RETRIES=0");
		System.out.println("FALLBACKS=0");
		System.out.println("GOOGLE_RESOURCE_MUTATIONS=0");
		System.out.println("ACCOUNT_MUTATIONS=0");
		System.out.println("ELAPSED_MILLIS=" + elapsedMillis);
		System.out.println("COST_USD=0.00");
	}

	private static void printPreflightFailure(String reason) {
		System.out.println("EXECUTION_STATUS=PREFLIGHT_FAILED");
		System.out.println("SAFE_REASON=" + reason);
		System.out.println("TOKEN_REFRESH_REQUESTS=0");
		System.out.println("GMAIL_API_REQUESTS=0");
		System.out.println("EMAIL_SENDS=0");
		System.out.println("OAUTH_SESSIONS=0");
		System.out.println("AUTHORIZATION_CODE_EXCHANGES=0");
	}

	private static String required(String name) throws PreflightFailure {
		String value = System.getenv(name);
		if (value == null || value.isBlank()) throw new PreflightFailure(name + "_MISSING");
		return value;
	}

	private static void disableLibraryLogging() {
		LogManager.getLogManager().reset();
		Logger.getLogger("").setLevel(Level.OFF);
	}

	static final class PreflightFailure extends Exception {
		PreflightFailure(String reason) { super(reason); }
		String reason() { return getMessage(); }
	}
}
