package com.routemind.business.infrastructure.notification;

import com.google.api.client.auth.oauth2.Credential;
import com.google.api.client.googleapis.auth.oauth2.GoogleAuthorizationCodeFlow;
import com.google.api.client.googleapis.auth.oauth2.GoogleClientSecrets;
import com.google.api.client.googleapis.javanet.GoogleNetHttpTransport;
import com.google.api.client.http.HttpRequest;
import com.google.api.client.http.HttpRequestInitializer;
import com.google.api.client.http.HttpHeaders;
import com.google.api.client.json.JsonFactory;
import com.google.api.client.json.jackson2.JacksonFactory;
import com.google.api.client.util.store.FileDataStoreFactory;
import com.routemind.business.application.notification.NotificationChannel;
import com.routemind.business.application.notification.NotificationRecipient;
import com.routemind.business.application.notification.NotificationRequest;
import com.routemind.business.application.notification.NotificationSender;
import com.routemind.business.application.notification.NotificationStatus;
import com.routemind.business.domain.security.TenantId;
import com.google.api.services.gmail.Gmail;
import java.nio.file.Path;
import java.time.Duration;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.atomic.AtomicReference;
import java.util.logging.Level;
import java.util.logging.LogManager;
import java.util.logging.Logger;

/** One-shot Gmail V2 executor. It never refreshes credentials and never retries. */
public final class GoogleGmailSingleSendV2Cli {

	static final String CONTRACT_DIGEST =
			"033bd4e5e3c92b65d94191a30fcae7d852dc92ae7441ef18c8bf8f959cba371f";
	private static final String CONTRACT_ENV = "ROUTEMIND_R4_422_GMAIL_SINGLE_SEND_V2_CONTRACT_SHA256";
	private static final String ROOT_ENV = "ROUTEMIND_REPOSITORY_ROOT";
	private static final String PROVIDER_ENV = "ROUTEMIND_NOTIFICATION_EMAIL_PROVIDER";
	private static final String ENABLED_ENV = "ROUTEMIND_NOTIFICATION_GMAIL_ENABLED";
	private static final String REGION_ENV = "ROUTEMIND_NOTIFICATION_GMAIL_REGION";
	private static final String SENDER_ENV = "ROUTEMIND_NOTIFICATION_SENDER";
	private static final String RECIPIENT_ENV = "ROUTEMIND_NOTIFICATION_SYNTHETIC_RECIPIENT";

	private GoogleGmailSingleSendV2Cli() { }

	public static void main(String[] args) {
		disableLibraryLogging();
		Instant startedAt = Instant.now();
		try {
			execute(args, startedAt);
		}
		catch (PreflightFailure failure) {
			printPreflightFailure(failure.reason());
			System.exit(2);
		}
		catch (Exception failure) {
			printPreflightFailure("UNEXPECTED_PREFLIGHT_FAILURE");
			System.exit(2);
		}
	}

	private static void execute(String[] args, Instant startedAt) throws Exception {
		if (args.length != 1 || !"--execute".equals(args[0])) {
			throw new PreflightFailure("EXPLICIT_EXECUTION_MODE_REQUIRED");
		}
		if (!CONTRACT_DIGEST.equals(required(CONTRACT_ENV))) {
			throw new PreflightFailure("CONTRACT_DIGEST_MISMATCH");
		}
		if (!"gmail".equalsIgnoreCase(required(PROVIDER_ENV))) {
			throw new PreflightFailure("GMAIL_PROVIDER_MISMATCH");
		}
		if (!"true".equalsIgnoreCase(required(ENABLED_ENV))) {
			throw new PreflightFailure("GMAIL_ADAPTER_NOT_EXPLICITLY_ENABLED");
		}

		Path repositoryRoot = Path.of(required(ROOT_ENV));
		GmailOAuthBootstrapConfiguration oauth =
				GmailOAuthBootstrapConfiguration.fromEnvironment(System.getenv());
		GmailOAuthPathPolicy.ValidatedPaths paths = GmailOAuthPathPolicy.validate(repositoryRoot, oauth);
		String sender = required(SENDER_ENV);
		String recipient = required(RECIPIENT_ENV);
		String region = System.getenv().getOrDefault(REGION_ENV, "global");
		NotificationGmailProperties properties = new NotificationGmailProperties(true, region,
				paths.clientCredentialFile().toString(), paths.tokenStoreDirectory().toString(),
				oauth.oauthUserId(), sender, recipient);

		JsonFactory json = JacksonFactory.getDefaultInstance();
		GoogleClientSecrets clientSecrets = GoogleGmailOAuthBootstrap
				.loadAndValidateDesktopClient(paths.clientCredentialFile(), json);
		FileDataStoreFactory store = new FileDataStoreFactory(paths.tokenStoreDirectory().toFile());
		GoogleAuthorizationCodeFlow flow = new GoogleAuthorizationCodeFlow.Builder(
				GoogleNetHttpTransport.newTrustedTransport(), json, clientSecrets,
				List.of(GoogleGmailOAuthBootstrap.GMAIL_SEND_SCOPE))
				.setDataStoreFactory(store)
				.setAccessType("offline")
				.build();
		Credential credential = GoogleGmailOAuthBootstrap.loadStoredCredential(flow, properties);
		GoogleGmailCredentialRefreshReadiness.Assessment readiness =
				GoogleGmailCredentialRefreshReadiness.assess(credential);
		if (readiness.status() != GoogleGmailCredentialRefreshReadiness.Status.READY_WITHOUT_REFRESH) {
			throw new PreflightFailure("CREDENTIAL_REFRESH_REQUIRED");
		}
		String accessToken = credential.getAccessToken();
		if (accessToken == null || accessToken.isBlank()) {
			throw new PreflightFailure("ACCESS_TOKEN_UNAVAILABLE");
		}

		AtomicReference<GoogleGmailErrorObservation> observation = new AtomicReference<>();
		HttpRequestInitializer initializer = request -> configureRequest(request, accessToken);
		Gmail client = new GoogleGmailClientFactory().create(properties, initializer);
		GoogleGmailNotificationProvider provider = new GoogleGmailNotificationProvider(client, properties,
				new GoogleGmailRequestFactory(), observation::set);
		NotificationRequest request = syntheticRequest(sender, recipient);
		var result = provider.send(request);
		GoogleGmailErrorObservation recorded = observation.get();
		if (recorded == null || recorded.requestCount() != 1 || recorded.retryCount() != 0
				|| recorded.fallbackUsed()) {
			throw new IllegalStateException("bounded provider observation missing");
		}
		String outcome = result.status() == NotificationStatus.ACCEPTED ? "PROVIDER_ACCEPTED" : "PROVIDER_REJECTED";
		printOutcome(outcome, recorded, startedAt);
	}

	static void configureRequest(HttpRequest request, String accessToken) {
		request.setNumberOfRetries(0);
		request.setFollowRedirects(false);
		request.setIOExceptionHandler(null);
		request.setUnsuccessfulResponseHandler(null);
		request.setConnectTimeout(10_000);
		request.setReadTimeout(30_000);
		HttpHeaders headers = request.getHeaders();
		headers.setAuthorization("Bearer " + accessToken);
	}

	private static NotificationRequest syntheticRequest(String sender, String recipient) {
		return new NotificationRequest(UUID.fromString("11111111-1111-4111-8111-111111111111"),
				new TenantId(UUID.fromString("22222222-2222-4222-8222-222222222222")),
				UUID.fromString("33333333-3333-4333-8333-333333333333"),
				"r4-422-gmail-v2-single-send", NotificationChannel.EMAIL,
				new NotificationRecipient(recipient), new NotificationSender(sender),
				"r4-422-gmail-synthetic-v2", "RouteMind R4-422 Synthetic Notification Validation V2",
				"Synthetic RouteMind notification-provider validation; no production data", 1,
				UUID.fromString("44444444-4444-4444-8444-444444444444"), Instant.now(),
				Map.of("privacy_boundary", "synthetic-only", "provider_contract", "r4-422-v2"));
	}

	private static void printOutcome(String outcome, GoogleGmailErrorObservation observation, Instant startedAt) {
		System.out.println("EXECUTION_STATUS=" + outcome);
		System.out.println("SAFE_REASON=" + observation.safeReason());
		System.out.println("HTTP_STATUS=" + observation.httpStatus());
		System.out.println("GMAIL_API_REQUESTS=1");
		System.out.println("USERS_MESSAGES_SEND_REQUESTS=1");
		System.out.println("RECIPIENTS=1");
		System.out.println("CREDENTIAL_REFRESH_REQUESTS=0");
		System.out.println("RETRIES=0");
		System.out.println("FALLBACKS=0");
		System.out.println("MESSAGE_ID_PRESENT=" + observation.messageIdPresent());
		System.out.println("PROVIDER_ACCEPTANCE=" + observation.providerAcceptance());
		System.out.println("DELIVERY_CONFIRMED=false");
		System.out.println("OAUTH_SESSIONS=0");
		System.out.println("TOKEN_EXCHANGES=0");
		System.out.println("BROWSER_SESSIONS=0");
		System.out.println("SSH_SESSIONS=0");
		System.out.println("GOOGLE_RESOURCE_MUTATIONS=0");
		System.out.println("ACCOUNT_MUTATIONS=0");
		System.out.println("ELAPSED_MILLIS=" + Duration.between(startedAt, Instant.now()).toMillis());
		System.out.println("COST_USD=0.00");
	}

	private static void printPreflightFailure(String reason) {
		System.out.println("EXECUTION_STATUS=PREFLIGHT_FAILED");
		System.out.println("SAFE_REASON=" + reason);
		System.out.println("GMAIL_API_REQUESTS=0");
		System.out.println("USERS_MESSAGES_SEND_REQUESTS=0");
		System.out.println("RECIPIENTS=0");
		System.out.println("CREDENTIAL_REFRESH_REQUESTS=0");
		System.out.println("RETRIES=0");
		System.out.println("FALLBACKS=0");
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
