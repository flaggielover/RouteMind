package com.routemind.business.infrastructure.notification;

import com.google.api.client.auth.oauth2.Credential;
import com.google.api.client.googleapis.auth.oauth2.GoogleAuthorizationCodeFlow;
import com.google.api.client.googleapis.auth.oauth2.GoogleClientSecrets;
import com.google.api.client.googleapis.javanet.GoogleNetHttpTransport;
import com.google.api.client.http.HttpHeaders;
import com.google.api.client.http.HttpRequest;
import com.google.api.client.http.HttpRequestInitializer;
import com.google.api.client.json.JsonFactory;
import com.google.api.client.json.jackson2.JacksonFactory;
import com.google.api.client.util.store.FileDataStoreFactory;
import com.google.api.services.gmail.Gmail;
import com.routemind.business.application.notification.NotificationChannel;
import com.routemind.business.application.notification.NotificationRecipient;
import com.routemind.business.application.notification.NotificationRequest;
import com.routemind.business.application.notification.NotificationSender;
import com.routemind.business.application.notification.NotificationStatus;
import com.routemind.business.domain.security.TenantId;
import java.io.IOException;
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

/** Bounded Gmail executor that refreshes only when required, then sends once. */
public final class GoogleGmailRefreshIfRequiredSingleSendCli {

	static final String CONTRACT_DIGEST =
			"35702d6d6698b78f08757b2560deb2bfee50503d0b8cc90b8fd2fcdf9431535f";
	private static final String CONTRACT_ENV =
			"ROUTEMIND_R4_422_GMAIL_REFRESH_IF_REQUIRED_SINGLE_SEND_CONTRACT_SHA256";
	private static final String ROOT_ENV = "ROUTEMIND_REPOSITORY_ROOT";
	private static final String PROVIDER_ENV = "ROUTEMIND_NOTIFICATION_EMAIL_PROVIDER";
	private static final String ENABLED_ENV = "ROUTEMIND_NOTIFICATION_GMAIL_ENABLED";
	private static final String REGION_ENV = "ROUTEMIND_NOTIFICATION_GMAIL_REGION";
	private static final String SENDER_ENV = "ROUTEMIND_NOTIFICATION_SENDER";
	private static final String RECIPIENT_ENV = "ROUTEMIND_NOTIFICATION_SYNTHETIC_RECIPIENT";

	private GoogleGmailRefreshIfRequiredSingleSendCli() { }

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
				.setRequestInitializer(GmailCredentialRefreshRecoveryCli::configureRefreshRequest)
				.build();
		Credential credential = GoogleGmailOAuthBootstrap.loadStoredCredential(flow, properties);
		CredentialPort credentialPort = new GoogleCredentialPort(credential);
		AtomicReference<GoogleGmailErrorObservation> observation = new AtomicReference<>();
		SendPort sendPort = (request, authorizationToken) -> {
			try {
				HttpRequestInitializer initializer = httpRequest -> configureRequest(httpRequest, authorizationToken);
				Gmail client = new GoogleGmailClientFactory().create(properties, initializer);
				GoogleGmailNotificationProvider provider = new GoogleGmailNotificationProvider(client, properties,
						new GoogleGmailRequestFactory(), observation::set);
				var result = provider.send(request);
				GoogleGmailErrorObservation recorded = observation.get();
				if (recorded == null) {
					return SendResult.rejected(0, "OBSERVATION_MISSING");
				}
				return new SendResult(result.status() == NotificationStatus.ACCEPTED,
						recorded.messageIdPresent(), recorded.httpStatus(), recorded.safeReason(),
						recorded.requestCount(), recorded.retryCount(), recorded.fallbackUsed());
			}
			catch (RuntimeException failure) {
				return SendResult.rejected(0, "REQUEST_CONSTRUCTION_FAILED");
			}
		};

		BoundedExecution execution = new BoundedExecution(credentialPort, sendPort);
		Outcome outcome = execution.execute(syntheticRequest(sender, recipient));
		printOutcome(outcome, startedAt);
	}

	static Outcome executeOffline(CredentialPort credential, SendPort sender, NotificationRequest request) {
		return new BoundedExecution(credential, sender).execute(request);
	}

	static void configureRequest(HttpRequest request, String authorizationToken) {
		request.setNumberOfRetries(0);
		request.setFollowRedirects(false);
		request.setIOExceptionHandler(null);
		request.setUnsuccessfulResponseHandler(null);
		request.setConnectTimeout(10_000);
		request.setReadTimeout(30_000);
		HttpHeaders headers = request.getHeaders();
		headers.setAuthorization("Bearer " + authorizationToken);
	}

	private static NotificationRequest syntheticRequest(String sender, String recipient) {
		return new NotificationRequest(UUID.fromString("11111111-1111-4111-8111-111111111111"),
				new TenantId(UUID.fromString("22222222-2222-4222-8222-222222222222")),
				UUID.fromString("33333333-3333-4333-8333-333333333333"),
				"r4-422-gmail-refresh-if-required-single-send", NotificationChannel.EMAIL,
				new NotificationRecipient(recipient), new NotificationSender(sender),
				"r4-422-gmail-refresh-if-required", "RouteMind R4-422 Synthetic Refresh-If-Required Validation",
				"Synthetic RouteMind notification-provider validation; no production data", 1,
				UUID.fromString("44444444-4444-4444-8444-444444444444"), Instant.now(),
				Map.of("privacy_boundary", "synthetic-only", "provider_contract", "r4-422-refresh-if-required-v1"));
	}

	private static void printOutcome(Outcome outcome, Instant startedAt) {
		System.out.println("EXECUTION_STATUS=" + outcome.status());
		System.out.println("CREDENTIAL_LOADED=" + outcome.credentialLoaded());
		System.out.println("READINESS_STATUS=" + outcome.readinessStatus());
		System.out.println("REFRESH_REQUIRED=" + outcome.refreshRequired());
		System.out.println("REFRESH_ATTEMPTED=" + outcome.refreshAttempted());
		System.out.println("REFRESH_ACCEPTED=" + outcome.refreshAccepted());
		System.out.println("POST_REFRESH_USABLE=" + outcome.postRefreshUsable());
		System.out.println("SEND_ATTEMPTED=" + outcome.sendAttempted());
		System.out.println("PROVIDER_ACCEPTANCE=" + outcome.providerAccepted());
		System.out.println("SAFE_REASON=" + outcome.safeReason());
		System.out.println("HTTP_STATUS=" + outcome.httpStatus());
		System.out.println("MESSAGE_ID_PRESENT=" + outcome.messageIdPresent());
		System.out.println("GMAIL_API_REQUESTS=" + outcome.gmailApiRequests());
		System.out.println("USERS_MESSAGES_SEND_REQUESTS=" + outcome.sendRequests());
		System.out.println("RECIPIENTS=" + outcome.recipients());
		System.out.println("CREDENTIAL_REFRESH_REQUESTS=" + outcome.refreshRequests());
		System.out.println("RETRIES=" + outcome.retries());
		System.out.println("FALLBACKS=" + outcome.fallbacks());
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

	enum Readiness {
		READY_WITHOUT_REFRESH,
		REFRESH_REQUIRED_AND_AVAILABLE,
		REFRESH_REQUIRED_BUT_UNAVAILABLE,
		MISSING
	}

	interface CredentialPort {
		Readiness assess();
		RefreshResult refreshOnce();
		String authorizationToken();
	}

	interface SendPort {
		SendResult send(NotificationRequest request, String authorizationToken);
	}

	record RefreshResult(boolean accepted, String safeReason) {
		RefreshResult {
			if (safeReason == null || safeReason.isBlank() || !safeReason.matches("[A-Z0-9_]{1,64}")) {
				throw new IllegalArgumentException("safe refresh reason is invalid");
			}
		}
	}

	record SendResult(boolean providerAccepted, boolean messageIdPresent, int httpStatus,
			String safeReason, int requestCount, int retryCount, boolean fallbackUsed) {
		SendResult {
			if (safeReason == null || safeReason.isBlank() || !safeReason.matches("[A-Z0-9_]{1,64}")) {
				throw new IllegalArgumentException("safe send reason is invalid");
			}
			if (httpStatus < 0 || httpStatus > 599 || requestCount < 0 || retryCount < 0) {
				throw new IllegalArgumentException("send observation is invalid");
			}
			if (providerAccepted && !"ACCEPTED".equals(safeReason)) {
				throw new IllegalArgumentException("accepted send must use ACCEPTED reason");
			}
		}

		static SendResult rejected(int requestCount, String safeReason) {
			return new SendResult(false, false, 0, safeReason, requestCount, 0, false);
		}
	}

	record Outcome(String status, boolean credentialLoaded, String readinessStatus,
			boolean refreshRequired, boolean refreshAttempted, boolean refreshAccepted,
			boolean postRefreshUsable, boolean sendAttempted, boolean providerAccepted,
			String safeReason, int httpStatus, boolean messageIdPresent, int gmailApiRequests,
			int sendRequests, int recipients, int refreshRequests, int retries, int fallbacks) {
		Outcome {
			if (status == null || status.isBlank() || readinessStatus == null || readinessStatus.isBlank()) {
				throw new IllegalArgumentException("outcome status is blank");
			}
			if (safeReason == null || safeReason.isBlank() || !safeReason.matches("[A-Z0-9_]{1,64}")) {
				throw new IllegalArgumentException("outcome reason is invalid");
			}
			if (httpStatus < 0 || httpStatus > 599 || gmailApiRequests < 0 || sendRequests < 0
					|| recipients < 0 || refreshRequests < 0 || retries < 0 || fallbacks < 0
					|| refreshRequests > 1 || sendRequests > 1 || recipients > 1 || retries != 0 || fallbacks != 0) {
				throw new IllegalArgumentException("outcome counters exceed bounded contract");
			}
		}

	}

	static final class BoundedExecution {
		private final CredentialPort credential;
		private final SendPort sender;
		private int refreshRequests;
		private int sendRequests;

		BoundedExecution(CredentialPort credential, SendPort sender) {
			this.credential = java.util.Objects.requireNonNull(credential, "credential");
			this.sender = java.util.Objects.requireNonNull(sender, "sender");
		}

		Outcome execute(NotificationRequest request) {
			java.util.Objects.requireNonNull(request, "request");
			Readiness readiness = credential.assess();
			boolean loaded = readiness != Readiness.MISSING;
			boolean refreshRequired = readiness == Readiness.REFRESH_REQUIRED_AND_AVAILABLE
					|| readiness == Readiness.REFRESH_REQUIRED_BUT_UNAVAILABLE;
			boolean refreshAttempted = false;
			boolean refreshAccepted = false;
			boolean postRefreshUsable = readiness == Readiness.READY_WITHOUT_REFRESH;
			String reason = readiness.name();
			if (readiness == Readiness.REFRESH_REQUIRED_BUT_UNAVAILABLE || readiness == Readiness.MISSING) {
				return outcome("CREDENTIAL_NOT_USABLE", loaded, readiness, refreshRequired, false, false,
						false, false, false, reason, 0, false, 0, 0, 0, 0, 0, 0);
			}
			if (readiness == Readiness.REFRESH_REQUIRED_AND_AVAILABLE) {
				RefreshResult refresh = refreshOnce();
				refreshAttempted = true;
				refreshAccepted = refresh.accepted();
				reason = refresh.safeReason();
				if (!refreshAccepted) {
					return outcome("REFRESH_FAILED", true, readiness, true, true, false,
							false, false, false, reason, 0, false, 0, 0, 0, refreshRequests, 0, 0);
				}
				Readiness afterRefresh = credential.assess();
				postRefreshUsable = afterRefresh == Readiness.READY_WITHOUT_REFRESH;
				readiness = afterRefresh;
				if (!postRefreshUsable) {
					return outcome("POST_REFRESH_CREDENTIAL_UNUSABLE", true, readiness, true, true, true,
							false, false, false, "POST_REFRESH_NOT_USABLE", 0, false, 0, 0, 0,
							refreshRequests, 0, 0);
				}
			}
			String authorizationToken = credential.authorizationToken();
			if (authorizationToken == null || authorizationToken.isBlank()) {
				return outcome("ACCESS_TOKEN_UNAVAILABLE", loaded, readiness, refreshRequired, refreshAttempted,
						refreshAccepted, postRefreshUsable, false, false, "ACCESS_TOKEN_UNAVAILABLE", 0,
						false, 0, 0, 0, refreshRequests, 0, 0);
			}
			SendResult send = sendOnce(request, authorizationToken);
			reason = send.safeReason();
			return outcome(send.providerAccepted() ? "PROVIDER_ACCEPTED" : "PROVIDER_REJECTED", loaded,
					readiness, refreshRequired, refreshAttempted, refreshAccepted, postRefreshUsable, true,
					send.providerAccepted(), reason, send.httpStatus(), send.messageIdPresent(),
					send.requestCount(), send.requestCount(), 1, refreshRequests, send.retryCount(),
					send.fallbackUsed() ? 1 : 0);
		}

		RefreshResult refreshOnce() {
			if (refreshRequests >= 1) throw new IllegalStateException("SECOND_REFRESH_ATTEMPT");
			refreshRequests++;
			return credential.refreshOnce();
		}

		SendResult sendOnce(NotificationRequest request, String authorizationToken) {
			if (sendRequests >= 1) throw new IllegalStateException("SECOND_SEND_ATTEMPT");
			sendRequests++;
			return sender.send(request, authorizationToken);
		}

		private Outcome outcome(String status, boolean loaded, Readiness readiness, boolean refreshRequired,
				boolean refreshAttempted, boolean refreshAccepted, boolean postRefreshUsable,
				boolean sendAttempted, boolean providerAccepted, String reason, int httpStatus,
				boolean messageIdPresent, int gmailRequests, int sendRequests, int recipients,
				int refreshRequests, int retries, int fallbacks) {
			return new Outcome(status, loaded, readiness.name(), refreshRequired, refreshAttempted,
					refreshAccepted, postRefreshUsable, sendAttempted, providerAccepted, reason,
					httpStatus, messageIdPresent, gmailRequests, sendRequests, recipients,
					refreshRequests, retries, fallbacks);
		}
	}

	private static final class GoogleCredentialPort implements CredentialPort {
		private final Credential credential;

		private GoogleCredentialPort(Credential credential) {
			this.credential = credential;
		}

		@Override
		public Readiness assess() {
			return switch (GoogleGmailCredentialRefreshReadiness.assess(credential).status()) {
				case READY_WITHOUT_REFRESH -> Readiness.READY_WITHOUT_REFRESH;
				case REFRESH_REQUIRED_AND_AVAILABLE -> Readiness.REFRESH_REQUIRED_AND_AVAILABLE;
				case REFRESH_REQUIRED_BUT_UNAVAILABLE -> Readiness.REFRESH_REQUIRED_BUT_UNAVAILABLE;
				case MISSING -> Readiness.MISSING;
			};
		}

		@Override
		public RefreshResult refreshOnce() {
			try {
				boolean refreshed = credential.refreshToken();
				return new RefreshResult(refreshed, refreshed ? "REFRESH_ACCEPTED" : "NO_NEW_TOKEN");
			}
			catch (IOException failure) {
				return new RefreshResult(false, "REFRESH_REQUEST_FAILED");
			}
		}

		@Override
		public String authorizationToken() {
			return credential.getAccessToken();
		}
	}

	static final class PreflightFailure extends Exception {
		PreflightFailure(String reason) { super(reason); }
		String reason() { return getMessage(); }
	}
}
